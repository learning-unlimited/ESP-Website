from collections import Counter
from dataclasses import dataclass, asdict
from typing import List

# Views that require a class ID or extra path segment; linking to /tl/prog/view
# would not open a valid page. Excluded from admin search so users don't get
# broken links.
EXCLUDED_VIEW_NAMES = frozenset([
    "editclass", "manageclass", "addsection", "deletesection",
    "deleteclass", "approveclass", "rejectclass", "coteachers",
    "classavailability", "reviewclass",
])

# Human-readable labels for view names used in disambiguation. When multiple
# entries share the same title, we append " (label)" so users can tell them apart.
VIEW_DISPLAY_NAMES = {
    # Onsite / printables
    "onsiteregform": "Registration form",
    "onsiteaddclass": "Add class",
    "onsiteclearslot": "Clear slot",
    "onsitecatalog": "Catalog",
    "selfcheckin": "Self check-in",
    "onsitedetails": "Details",
    "onsitemap": "Map",
    "onsitesurvey": "Survey",
    "onsiteroster": "Roster",
    "studentonsite": "Student onsite",
    "teacheronsite": "Teacher onsite",
    # Manage class (some excluded from search but kept for consistency if used elsewhere)
    "editclass": "Edit class",
    "manageclass": "Manage class",
    "addsection": "Add section",
    "deletesection": "Delete section",
    "deleteclass": "Delete class",
    "approveclass": "Approve class",
    "rejectclass": "Reject class",
    "coteachers": "Co-teachers",
    "classavailability": "Class availability",
    "reviewclass": "Review class",
}


@dataclass
class AdminSearchEntry:
    """
    Lightweight description of an admin-facing page or tool that can be found
    via the Admin Dashboard search.
    """

    id: str
    url: str
    title: str
    category: str
    keywords: List[str]


def _humanize_view_name(view_name):
    """Return a human-readable label for view_name, for disambiguation."""
    if not view_name:
        return view_name
    key = view_name.lower()
    if key in VIEW_DISPLAY_NAMES:
        return VIEW_DISPLAY_NAMES[key]
    return view_name.replace("_", " ").strip().title()


def get_admin_search_entries(program):
    """
    Return a list of AdminSearchEntry objects by collecting metadata from each
    module. Modules can define get_admin_search_entry() with title, category,
    and keywords so search stays discoverable and keywords live next to the
    module code. Views without custom metadata get a default entry (title +
    basic keywords from link_title). When multiple entries share the same
    title (e.g. many "Student Onsite" links), the title is disambiguated by
    appending the view name in parentheses so users can tell them apart.
    """
    from esp.program.modules import handlers

    base = program.getUrlBase()
    view_map = program.getModuleViews(main_only=False)
    built = []
    seen_ids = set()

    for (tl, view_name), pmo in view_map.items():
        if view_name.lower() in EXCLUDED_VIEW_NAMES:
            continue
        url = "/%s/%s/%s" % (tl, base, view_name)
        entry_id = "%s_%s" % (tl, view_name)
        if entry_id in seen_ids:
            continue
        seen_ids.add(entry_id)

        handler_class = getattr(handlers, pmo.module.handler, None)
        if handler_class is None:
            continue

        entry = None
        if hasattr(handler_class, "get_admin_search_entry"):
            entry = handler_class.get_admin_search_entry(
                program, tl, view_name, pmo
            )

        if entry is None:
            title = pmo.get_link_title()
            keywords = [title]
            if pmo.module.link_title and pmo.module.link_title != title:
                keywords.append(pmo.module.link_title)
            entry = AdminSearchEntry(
                id=entry_id,
                url=url,
                title=title,
                category="Other",
                keywords=keywords,
            )

        # Ensure area (tl) and technical view_name are always searchable
        if tl not in entry.keywords:
            entry.keywords.append(tl)
        if view_name not in entry.keywords:
            entry.keywords.append(view_name)

        built.append((entry, view_name))

    # Disambiguate duplicate titles so "Student Onsite" x8 becomes
    # "Student Onsite (main)", "Student Onsite (class list)", etc.
    title_counts = Counter(e.title for e, _ in built)
    entries = []
    for entry, view_name in built:
        if title_counts[entry.title] > 1:
            entry = AdminSearchEntry(
                id=entry.id,
                url=entry.url,
                title=entry.title + " (" + _humanize_view_name(view_name) + ")",
                category=entry.category,
                keywords=entry.keywords,
            )
        entries.append(entry)

    return entries


def serialize_admin_search_entries(program):
    """
    Convenience helper used by views to obtain a JSON-serializable list of
    dicts for the template context.
    """
    return [asdict(e) for e in get_admin_search_entries(program)]
