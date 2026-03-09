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


def graphql(query: str, variables: dict | None = None) -> dict:
    """Execute a GitHub GraphQL query and return the JSON response."""
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
    pullRequests(states: OPEN, first: 100, after: $cursor, orderBy: {field: UPDATED_AT, direction: DESC}) {
      pageInfo { hasNextPage endCursor }
      nodes {
        number
        title
        author { login }
        createdAt
        updatedAt
        labels(first: 50) { nodes { name } }
        reviewRequests(first: 20) {
          nodes {
            requestedReviewer {
              ... on User { login }
              ... on Team { name }
            }
          }
        }
        reviews(first: 50) {
          nodes { author { login } }
        }
        closingIssuesReferences(first: 20) {
          nodes { number }
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

        rows.append([
            link_pr(pr["number"]),
            pr["title"],
            link_profile(author),
            fmt_time(pr["createdAt"]),
            fmt_time(pr["updatedAt"]),
            ", ".join(sorted(reviewers)),
            ", ".join(linked_issues),
            ", ".join(labels),
        ])

    return rows


def build_issue_rows(issues: list[dict]) -> list[list[str]]:
    """Build the rows for the Issues sheet."""
    header = [
        "Issue #", "Title", "Author", "Opened", "Assignee(s)",
        "Assigned Date", "Last Updated", "Linked PRs",
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
        earliest_assign = ""
        if assign_dates:
            earliest_assign = fmt_time(min(assign_dates.values()))

        author = (issue["author"] or {}).get("login", "ghost")

        rows.append([
            link_issue(issue["number"]),
            issue["title"],
            link_profile(author),
            fmt_time(issue["createdAt"]),
            ", ".join(assignees),
            earliest_assign,
            fmt_time(issue["updatedAt"]),
            ", ".join(linked_prs),
        ])

    return rows


def build_contributor_rows(
    prs: list[dict], issues: list[dict]
) -> list[list[str]]:
    """Build the rows for the Contributor Activity sheet."""
    header = [
        "Contributor", "Open PRs", "Assigned Open Issues", "Last Activity",
    ]

    activity: dict[str, dict] = defaultdict(
        lambda: {"open_prs": 0, "assigned_issues": 0, "last_activity": ""}
    )

    for pr in prs:
        login = (pr["author"] or {}).get("login", "ghost")
        activity[login]["open_prs"] += 1
        if pr["updatedAt"] > activity[login]["last_activity"]:
            activity[login]["last_activity"] = pr["updatedAt"]

    for issue in issues:
        for assignee in issue["assignees"]["nodes"]:
            login = assignee["login"]
            activity[login]["assigned_issues"] += 1
            if issue["updatedAt"] > activity[login]["last_activity"]:
                activity[login]["last_activity"] = issue["updatedAt"]

    rows = [header]
    for login in sorted(activity, key=lambda k: activity[k]["open_prs"], reverse=True):
        info = activity[login]
        rows.append([
            link_profile(login),
            info["open_prs"],
            info["assigned_issues"],
            fmt_time(info["last_activity"]),
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

    pr_rows = build_pr_rows(prs)
    issue_rows = build_issue_rows(issues)
    contributor_rows = build_contributor_rows(prs, issues)

    print(f"Writing to Google Sheet {SHEET_ID} ...")
    gc = get_gspread_client()
    spreadsheet = gc.open_by_key(SHEET_ID)

    write_sheet(spreadsheet, "Open Pull Requests", pr_rows)
    write_sheet(spreadsheet, "Open Issues", issue_rows)
    write_sheet(spreadsheet, "Contributor Activity", contributor_rows)

    print("Done!")


if __name__ == "__main__":
    main()
