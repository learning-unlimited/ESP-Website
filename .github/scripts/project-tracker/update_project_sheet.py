"""
update_project_sheet.py

Fetches open pull requests and issues from a GitHub repository via the
GraphQL API and writes three summary sheets to a Google Spreadsheet:
  1. Open Pull Requests
  2. Open Issues
  3. Contributor Activity

Required environment variables:
  GITHUB_TOKEN   – GitHub token with repo read access (provided by Actions)
  GOOGLE_SA_KEY  – JSON string of a Google service-account key
  SHEET_ID       – ID of the target Google Spreadsheet
  REPO_OWNER     – GitHub repository owner (org or user)
  REPO_NAME      – GitHub repository name
"""

import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone

import gspread
from google.oauth2.service_account import Credentials

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
GOOGLE_SA_KEY = os.environ["GOOGLE_SA_KEY"]
SHEET_ID = os.environ["SHEET_ID"]
REPO_OWNER = os.environ.get("REPO_OWNER", "learning-unlimited")
REPO_NAME = os.environ.get("REPO_NAME", "ESP-Website")

GRAPHQL_URL = "https://api.github.com/graphql"

# ---------------------------------------------------------------------------
# GraphQL helpers
# ---------------------------------------------------------------------------

import urllib.request


def graphql(query: str, variables: dict | None = None, *, allow_partial: bool = False) -> dict:
    """Execute a GitHub GraphQL query and return the JSON response.

    If *allow_partial* is True, errors are logged but execution continues
    as long as partial data was returned (useful for batched user lookups
    where bot accounts like ``dependabot`` are not found).
    """
    payload = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(
        GRAPHQL_URL,
        data=payload,
        headers={
            "Authorization": f"bearer {GITHUB_TOKEN}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())
    if "errors" in data:
        if allow_partial and data.get("data"):
            # Log but continue — some entries (e.g. bots) may not resolve
            pass
        else:
            print("GraphQL errors:", json.dumps(data["errors"], indent=2), file=sys.stderr)
            sys.exit(1)
    return data["data"]


def paginate(query: str, path: list[str], variables: dict | None = None) -> list:
    """
    Auto-paginate a GraphQL connection.

    *path* is the list of keys leading to the connection object that has
    ``pageInfo`` and ``nodes``, e.g. ["repository", "pullRequests"].
    """
    variables = dict(variables or {})
    variables["cursor"] = None
    all_nodes: list = []

    while True:
        data = graphql(query, variables)
        obj = data
        for key in path:
            obj = obj[key]
        all_nodes.extend(obj["nodes"])
        if obj["pageInfo"]["hasNextPage"]:
            variables["cursor"] = obj["pageInfo"]["endCursor"]
        else:
            break

    return all_nodes


# ---------------------------------------------------------------------------
# Fetch open pull requests
# ---------------------------------------------------------------------------

PR_QUERY = """
query($owner: String!, $repo: String!, $cursor: String) {
  repository(owner: $owner, name: $repo) {
    pullRequests(states: OPEN, first: 50, after: $cursor, orderBy: {field: UPDATED_AT, direction: DESC}) {
      pageInfo { hasNextPage endCursor }
      nodes {
        number
        title
        author { login }
        createdAt
        updatedAt
        changedFiles
        additions
        deletions
        labels(first: 50) { nodes { name } }
        reviewRequests(first: 20) {
          nodes {
            requestedReviewer {
              ... on User { login }
              ... on Team { name }
            }
          }
        }
        reviews(last: 20) {
          nodes { author { login } state }
        }
        closingIssuesReferences(first: 20) {
          nodes { number }
        }
        commits(last: 3) {
          nodes {
            commit {
              committedDate
              author { user { login } }
            }
          }
        }
        comments(last: 10) {
          nodes { createdAt author { login } }
        }
        reviewThreads(first: 100) {
          nodes { isResolved }
        }
      }
    }
  }
}
"""


def fetch_pull_requests() -> list[dict]:
    variables = {"owner": REPO_OWNER, "repo": REPO_NAME}
    return paginate(PR_QUERY, ["repository", "pullRequests"], variables)


# ---------------------------------------------------------------------------
# Fetch open issues
# ---------------------------------------------------------------------------

ISSUE_QUERY = """
query($owner: String!, $repo: String!, $cursor: String) {
  repository(owner: $owner, name: $repo) {
    issues(states: OPEN, first: 100, after: $cursor, orderBy: {field: UPDATED_AT, direction: DESC}) {
      pageInfo { hasNextPage endCursor }
      nodes {
        number
        title
        author { login }
        createdAt
        updatedAt
        labels(first: 50) { nodes { name } }
        assignees(first: 10) { nodes { login } }
        timelineItems(first: 100, itemTypes: [ASSIGNED_EVENT, CROSS_REFERENCED_EVENT]) {
          nodes {
            __typename
            ... on AssignedEvent {
              createdAt
              assignee { ... on User { login } }
            }
            ... on CrossReferencedEvent {
              source {
                ... on PullRequest { number state }
              }
            }
          }
        }
      }
    }
  }
}
"""


def fetch_issues() -> list[dict]:
    variables = {"owner": REPO_OWNER, "repo": REPO_NAME}
    return paginate(ISSUE_QUERY, ["repository", "issues"], variables)


# ---------------------------------------------------------------------------
# Data transformation helpers
# ---------------------------------------------------------------------------

def fmt_time(iso: str | None) -> str:
    """Convert an ISO-8601 timestamp to a readable string."""
    if not iso:
        return ""
    dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    return dt.strftime("%Y-%m-%d %H:%M UTC")


def days_since(iso: str | None) -> int | str:
    """Return the number of days between an ISO-8601 timestamp and now."""
    if not iso:
        return ""
    dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    return (datetime.now(timezone.utc) - dt).days


REPO_URL = f"https://github.com/{REPO_OWNER}/{REPO_NAME}"


def link_pr(number: int) -> str:
    """Google Sheets HYPERLINK formula for a pull request."""
    return f'=HYPERLINK("{REPO_URL}/pull/{number}", "#{number}")'


def link_issue(number: int) -> str:
    """Google Sheets HYPERLINK formula for an issue."""
    return f'=HYPERLINK("{REPO_URL}/issues/{number}", "#{number}")'


def link_profile(login: str) -> str:
    """Google Sheets HYPERLINK formula for a GitHub user profile."""
    return f'=HYPERLINK("https://github.com/{login}", "{login}")'


def build_pr_rows(prs: list[dict]) -> list[list[str]]:
    """Build the rows for the Pull Requests sheet."""
    header = [
        "PR #", "Title", "Author", "Opened", "Last Updated",
        "Files Changed", "Lines Changed",
        "Review State", "Days Since Author Activity",
        "Unresolved Review Threads",
        "Reviewers", "Linked Issues", "Labels",
    ]
    rows = [header]

    # Sort by PR number descending before building rows
    prs = sorted(prs, key=lambda p: p["number"], reverse=True)

    for pr in prs:
        # Combine requested + completed reviewers, deduplicated
        reviewers: set[str] = set()
        for rr in pr["reviewRequests"]["nodes"]:
            reviewer = rr.get("requestedReviewer") or {}
            reviewers.add(reviewer.get("login") or reviewer.get("name", ""))
        for rv in pr["reviews"]["nodes"]:
            if rv["author"]:
                reviewers.add(rv["author"]["login"])
        reviewers.discard("")

        linked_issues = [
            f"#{n['number']}"
            for n in pr["closingIssuesReferences"]["nodes"]
        ]
        labels = [l["name"] for l in pr["labels"]["nodes"]]
        author = (pr["author"] or {}).get("login", "ghost")

        # Count unresolved review threads (includes Copilot comments)
        unresolved = sum(
            1 for t in (pr.get("reviewThreads") or {}).get("nodes", [])
            if not t.get("isResolved")
        )

        # Determine the overall review state from the most recent
        # non-PENDING review per reviewer (latest wins)
        reviewer_states: dict[str, str] = {}
        for rv in pr["reviews"]["nodes"]:
            rv_author = (rv.get("author") or {}).get("login", "")
            state = rv.get("state", "")
            if rv_author and state != "PENDING":
                reviewer_states[rv_author] = state
        states = set(reviewer_states.values())
        if "CHANGES_REQUESTED" in states:
            review_state = "Changes Requested"
        elif "APPROVED" in states and unresolved > 0:
            review_state = "Approved (Comments Pending)"
        elif "APPROVED" in states:
            review_state = "Approved"
        elif unresolved > 0:
            review_state = "Comments Pending"
        elif reviewers:
            review_state = "Pending"
        else:
            review_state = "No Review"

        # Find the author's most recent activity on this PR:
        # their latest commit or comment
        author_last = pr["createdAt"]  # fallback to PR open date
        for commit_node in (pr.get("commits") or {}).get("nodes", []):
            commit = commit_node.get("commit") or {}
            commit_login = (
                (commit.get("author") or {}).get("user") or {}
            ).get("login")
            if commit_login == author:
                committed = commit.get("committedDate", "")
                if committed > author_last:
                    author_last = committed
        for comment in (pr.get("comments") or {}).get("nodes", []):
            comment_author = (comment.get("author") or {}).get("login", "")
            if comment_author == author:
                if comment["createdAt"] > author_last:
                    author_last = comment["createdAt"]

        rows.append([
            link_pr(pr["number"]),
            pr["title"],
            link_profile(author),
            fmt_time(pr["createdAt"]),
            fmt_time(pr["updatedAt"]),
            pr.get("changedFiles", 0),
            f"'+{pr.get('additions', 0)} / -{pr.get('deletions', 0)}",
            review_state,
            days_since(author_last),
            unresolved,
            ", ".join(sorted(reviewers)),
            ", ".join(linked_issues),
            ", ".join(labels),
        ])

    return rows


def build_issue_rows(issues: list[dict]) -> list[list[str]]:
    """Build the rows for the Issues sheet."""
    header = [
        "Issue #", "Title", "Author", "Opened", "Assignee(s)",
        "Assigned Date", "Days Since Assigned",
        "Last Updated", "Linked PRs", "Labels",
    ]
    rows = [header]

    # Sort by issue number descending before building rows
    issues = sorted(issues, key=lambda i: i["number"], reverse=True)

    for issue in issues:
        assignees = [a["login"] for a in issue["assignees"]["nodes"]]

        # Find the most recent AssignedEvent date for current assignees
        assign_dates: dict[str, str] = {}
        linked_prs: list[str] = []

        for event in issue["timelineItems"]["nodes"]:
            if event["__typename"] == "AssignedEvent":
                login = (event.get("assignee") or {}).get("login", "")
                if login in assignees:
                    assign_dates[login] = event["createdAt"]
            elif event["__typename"] == "CrossReferencedEvent":
                source = event.get("source") or {}
                if source.get("number"):
                    state_label = source.get("state", "").upper()
                    linked_prs.append(f"#{source['number']} ({state_label})")

        # Use the earliest assignment date across current assignees
        earliest_assign_raw = ""
        if assign_dates:
            earliest_assign_raw = min(assign_dates.values())

        author = (issue["author"] or {}).get("login", "ghost")
        labels = [l["name"] for l in issue["labels"]["nodes"]]

        rows.append([
            link_issue(issue["number"]),
            issue["title"],
            link_profile(author),
            fmt_time(issue["createdAt"]),
            ", ".join(assignees),
            fmt_time(earliest_assign_raw),
            days_since(earliest_assign_raw),
            fmt_time(issue["updatedAt"]),
            ", ".join(linked_prs),
            ", ".join(labels),
        ])

    return rows


def fetch_pr_counts(logins: list[str], search_filter: str) -> dict[str, int]:
    """
    Fetch PR counts per contributor for an arbitrary search filter using
    batched GraphQL search queries (up to 20 per request).

    *search_filter* is appended after ``repo:… is:pr author:{login}``,
    e.g. ``"is:merged"`` or ``"is:closed is:unmerged"``.
    """
    counts: dict[str, int] = {}
    batch_size = 20

    for i in range(0, len(logins), batch_size):
        batch = logins[i : i + batch_size]
        fragments = []
        for j, login in enumerate(batch):
            q = (
                f"repo:{REPO_OWNER}/{REPO_NAME} is:pr "
                f"author:{login} {search_filter}"
            )
            fragments.append(
                f'u{j}: search(query: "{q}", type: ISSUE) {{ issueCount }}'
            )
        query = "query {\n" + "\n".join(fragments) + "\n}"
        data = graphql(query)
        for j, login in enumerate(batch):
            counts[login] = data[f"u{j}"]["issueCount"]

    return counts


def fetch_profile_names(logins: list[str]) -> dict[str, str]:
    """
    Fetch display names from GitHub user profiles using batched GraphQL
    queries (up to 20 per request).  Bot accounts (e.g. dependabot) that
    don't resolve as User nodes are silently skipped.
    """
    names: dict[str, str] = {}
    batch_size = 20

    for i in range(0, len(logins), batch_size):
        batch = logins[i : i + batch_size]
        fragments = []
        for j, login in enumerate(batch):
            fragments.append(f'u{j}: user(login: "{login}") {{ name }}')
        query = "query {\n" + "\n".join(fragments) + "\n}"
        data = graphql(query, allow_partial=True)
        for j, login in enumerate(batch):
            user = data.get(f"u{j}") or {}
            names[login] = user.get("name") or ""

    return names


def link_count(url: str, count: int) -> str:
    """Google Sheets HYPERLINK formula displaying a count."""
    return f'=HYPERLINK("{url}", {count})'


# ---------------------------------------------------------------------------
# Fetch all PR authors since start of year
# ---------------------------------------------------------------------------

ALL_PR_AUTHORS_QUERY = """
query($searchQuery: String!, $cursor: String) {
  search(query: $searchQuery, type: ISSUE, first: 100, after: $cursor) {
    pageInfo { hasNextPage endCursor }
    nodes {
      ... on PullRequest {
        author { login }
      }
    }
  }
}
"""


def fetch_pr_authors_since(since: str) -> set[str]:
    """
    Return the set of all PR author logins since the given date
    (ISO date string like '2026-01-01').
    """
    search_query = (
        f"repo:{REPO_OWNER}/{REPO_NAME} is:pr created:>={since}"
    )
    variables = {"searchQuery": search_query}
    nodes = paginate(ALL_PR_AUTHORS_QUERY, ["search"], variables)
    logins: set[str] = set()
    for node in nodes:
        author = (node.get("author") or {}).get("login")
        if author:
            logins.add(author)
    return logins


def fetch_last_activity_dates(logins: list[str]) -> dict[str, str]:
    """
    Fetch each contributor's most recent activity (authored item or comment)
    using batched GraphQL queries.  Uses two aliased searches per contributor:

    1. Most recently *created* PR or issue they authored.
    2. Most recently updated item they *commented on*, with the last 20
       comments returned so we can find their actual comment timestamp.

    Returns a dict of login → ISO-8601 timestamp (or empty string).
    """
    dates: dict[str, str] = {}
    # Smaller batches — each login produces two search aliases with nested
    # comment data, so the response is heavier than a simple count query.
    batch_size = 10

    for i in range(0, len(logins), batch_size):
        batch = logins[i : i + batch_size]
        fragments = []
        for j, login in enumerate(batch):
            authored_q = (
                f"repo:{REPO_OWNER}/{REPO_NAME} "
                f"author:{login} sort:created-desc"
            )
            comment_q = (
                f"repo:{REPO_OWNER}/{REPO_NAME} "
                f"commenter:{login} sort:updated-desc"
            )
            fragments.append(
                f'authored_{j}: search(query: "{authored_q}", type: ISSUE, first: 1) {{\n'
                f"  nodes {{\n"
                f"    ... on PullRequest {{ createdAt }}\n"
                f"    ... on Issue {{ createdAt }}\n"
                f"  }}\n"
                f"}}\n"
                f'commented_{j}: search(query: "{comment_q}", type: ISSUE, first: 3) {{\n'
                f"  nodes {{\n"
                f"    ... on PullRequest {{ comments(last: 20) {{ nodes {{ createdAt author {{ login }} }} }} }}\n"
                f"    ... on Issue {{ comments(last: 20) {{ nodes {{ createdAt author {{ login }} }} }} }}\n"
                f"  }}\n"
                f"}}"
            )
        query = "query {\n" + "\n".join(fragments) + "\n}"
        data = graphql(query)

        for j, login in enumerate(batch):
            latest = ""

            # Check most recent authored item
            authored_nodes = data.get(f"authored_{j}", {}).get("nodes", [])
            if authored_nodes:
                created = authored_nodes[0].get("createdAt", "")
                if created > latest:
                    latest = created

            # Scan comments on recently-commented items to find their latest
            commented_nodes = data.get(f"commented_{j}", {}).get("nodes", [])
            for node in commented_nodes:
                for comment in (node.get("comments") or {}).get("nodes", []):
                    author = (comment.get("author") or {}).get("login")
                    if author == login and comment["createdAt"] > latest:
                        latest = comment["createdAt"]

            dates[login] = latest

    return dates


def build_contributor_rows(
    prs: list[dict], issues: list[dict], all_pr_authors: set[str]
) -> list[list[str]]:
    """Build the rows for the Contributor Activity sheet."""
    header = [
        "Contributor", "Name", "Open PRs", "Merged PRs", "Closed PRs",
        "Assigned Open Issues", "Oldest Open PR",
        "Last Activity", "Days Since Last Activity",
    ]

    activity: dict[str, dict] = defaultdict(
        lambda: {
            "open_prs": 0, "assigned_issues": 0, "oldest_open_pr": "",
        }
    )

    # Seed with all PR authors this year so contributors with only
    # merged/closed PRs still appear in the sheet
    for login in all_pr_authors:
        _ = activity[login]  # creates the default entry

    for pr in prs:
        login = (pr["author"] or {}).get("login", "ghost")
        activity[login]["open_prs"] += 1
        created = pr["createdAt"]
        if not activity[login]["oldest_open_pr"] or created < activity[login]["oldest_open_pr"]:
            activity[login]["oldest_open_pr"] = created

    # Track the most recent commit per contributor from open PRs
    latest_commit: dict[str, str] = {}
    for pr in prs:
        for commit_node in (pr.get("commits") or {}).get("nodes", []):
            commit = commit_node.get("commit") or {}
            commit_login = (
                (commit.get("author") or {}).get("user") or {}
            ).get("login")
            if commit_login:
                committed = commit.get("committedDate", "")
                if committed > latest_commit.get(commit_login, ""):
                    latest_commit[commit_login] = committed

    for issue in issues:
        for assignee in issue["assignees"]["nodes"]:
            login = assignee["login"]
            activity[login]["assigned_issues"] += 1

    # Fetch profile names, merged/closed counts, and last activity dates
    all_logins = list(activity.keys())
    profile_names = fetch_profile_names(all_logins)
    merged_counts = fetch_pr_counts(all_logins, "is:merged")
    closed_counts = fetch_pr_counts(all_logins, "is:closed is:unmerged")
    last_activity = fetch_last_activity_dates(all_logins)

    # Merge commit dates into last_activity (take the most recent)
    for login, committed in latest_commit.items():
        if committed > last_activity.get(login, ""):
            last_activity[login] = committed

    rows = [header]
    for login in sorted(activity, key=lambda k: activity[k]["open_prs"], reverse=True):
        info = activity[login]
        open_pr_url = f"{REPO_URL}/pulls/{login}"
        merged_pr_url = (
            f"{REPO_URL}/pulls?q=is%3Apr+is%3Amerged+author%3A{login}"
        )
        closed_pr_url = (
            f"{REPO_URL}/pulls?q=is%3Apr+is%3Aclosed+is%3Aunmerged+author%3A{login}"
        )
        issues_url = (
            f"{REPO_URL}/issues?q=is%3Aissue%20state%3Aopen%20assignee%3A{login}"
        )
        rows.append([
            link_profile(login),
            profile_names.get(login, ""),
            link_count(open_pr_url, info["open_prs"]),
            link_count(merged_pr_url, merged_counts.get(login, 0)),
            link_count(closed_pr_url, closed_counts.get(login, 0)),
            link_count(issues_url, info["assigned_issues"]),
            fmt_time(info["oldest_open_pr"]),
            fmt_time(last_activity.get(login, "")),
            days_since(last_activity.get(login, "")),
        ])

    return rows


# ---------------------------------------------------------------------------
# Google Sheets writer
# ---------------------------------------------------------------------------

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
]


def get_gspread_client() -> gspread.Client:
    """Authenticate with Google using the service-account JSON from env."""
    sa_info = json.loads(GOOGLE_SA_KEY)
    creds = Credentials.from_service_account_info(sa_info, scopes=SCOPES)
    return gspread.authorize(creds)


def write_sheet(
    spreadsheet: gspread.Spreadsheet,
    title: str,
    rows: list[list],
) -> None:
    """
    Write *rows* (including header) to a worksheet named *title*,
    creating it if it doesn't exist.
    """
    try:
        ws = spreadsheet.worksheet(title)
    except gspread.exceptions.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=title, rows=len(rows), cols=len(rows[0]))

    ws.clear()
    ws.update(rows, value_input_option="USER_ENTERED")

    # Bold the header row
    ws.format("1", {"textFormat": {"bold": True}})

    # Auto-resize isn't available via gspread, but freeze the header
    ws.freeze(rows=1)

    print(f"  ✓ '{title}' – {len(rows) - 1} data rows written")


def color_lines_changed(
    spreadsheet: gspread.Spreadsheet,
    title: str,
    rows: list[list],
    col: int,
) -> None:
    """
    Apply green/red rich text coloring to the Lines Changed column.

    Each cell contains text like ``+123 / -45``.  The additions portion
    is colored green, the separator is left as default, and the
    deletions portion is colored red.
    """
    ws = spreadsheet.worksheet(title)
    sheet_id = ws.id

    GREEN = {"red": 0.13, "green": 0.55, "blue": 0.13}
    GRAY = {"red": 0.4, "green": 0.4, "blue": 0.4}
    RED = {"red": 0.8, "green": 0.13, "blue": 0.13}

    cell_data = []
    for row in rows[1:]:  # skip header
        raw = str(row[col])
        # Strip the leading apostrophe used to force text mode
        text = raw.lstrip("'")

        if " / " not in text:
            cell_data.append({"values": [{}]})
            continue

        additions_part, _ = text.split(" / ", 1)
        sep_start = len(additions_part)
        removals_start = sep_start + len(" / ")

        cell_data.append({
            "values": [{
                "userEnteredValue": {"stringValue": text},
                "textFormatRuns": [
                    {"startIndex": 0,
                     "format": {"foregroundColorStyle": {"rgbColor": GREEN}}},
                    {"startIndex": sep_start,
                     "format": {"foregroundColorStyle": {"rgbColor": GRAY}}},
                    {"startIndex": removals_start,
                     "format": {"foregroundColorStyle": {"rgbColor": RED}}},
                ],
            }]
        })

    if not cell_data:
        return

    spreadsheet.batch_update({
        "requests": [{
            "updateCells": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 1,
                    "endRowIndex": 1 + len(cell_data),
                    "startColumnIndex": col,
                    "endColumnIndex": col + 1,
                },
                "rows": cell_data,
                "fields": "userEnteredValue,textFormatRuns",
            }
        }]
    })

    print(f"  ✓ '{title}' – Lines Changed column colored")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print(f"Fetching data for {REPO_OWNER}/{REPO_NAME} ...")

    print("  Fetching open pull requests ...")
    prs = fetch_pull_requests()
    print(f"    Found {len(prs)} open PRs")

    print("  Fetching open issues ...")
    issues = fetch_issues()
    print(f"    Found {len(issues)} open issues")

    year_start = datetime.now(timezone.utc).strftime("%Y") + "-01-01"
    print(f"  Fetching all PR authors since {year_start} ...")
    all_pr_authors = fetch_pr_authors_since(year_start)
    print(f"    Found {len(all_pr_authors)} unique PR authors")

    pr_rows = build_pr_rows(prs)
    issue_rows = build_issue_rows(issues)
    contributor_rows = build_contributor_rows(prs, issues, all_pr_authors)

    print(f"Writing to Google Sheet {SHEET_ID} ...")
    gc = get_gspread_client()
    spreadsheet = gc.open_by_key(SHEET_ID)

    write_sheet(spreadsheet, "Open Pull Requests", pr_rows)
    color_lines_changed(spreadsheet, "Open Pull Requests", pr_rows, col=6)
    write_sheet(spreadsheet, "Open Issues", issue_rows)
    write_sheet(spreadsheet, "Contributor Activity", contributor_rows)

    print("Done!")


if __name__ == "__main__":
    main()
