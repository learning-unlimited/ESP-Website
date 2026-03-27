from collections import Counter
from dataclasses import dataclass, asdict
from typing import List, Optional

# Views that require a class ID or extra path segment; linking to /tl/prog/view
# would not open a valid page. Excluded from admin search so users don't get
# broken links.
EXCLUDED_VIEW_NAMES = frozenset([
    "editclass", "manageclass", "addsection", "deletesection",
    "deleteclass", "approveclass", "rejectclass", "coteachers",
    "classavailability", "reviewclass",
])


@dataclass
class AdminSearchEntry:
    """
    Lightweight description of an admin-facing page or tool that can be found
    via the Admin Dashboard search. Only views that explicitly return an entry
    from get_admin_search_entry() are listed; JSON/AJAX and internal endpoints
    should return None so they do not appear.
    """

    id: str
    url: str
    title: str
    category: str
    keywords: List[str]
    # Optional short label for disambiguation when multiple entries share the same title.
    # Set in the module's get_admin_search_entry(); if unset, view_name is humanized.
    disambiguation_label: Optional[str] = None


def _humanize_view_name(view_name):
    """Return a human-readable label for view_name, for disambiguation when the module does not set disambiguation_label."""
    if not view_name:
        return view_name
    return view_name.replace("_", " ").strip().title()


def get_admin_search_entries(program):
    """
    Return a list of AdminSearchEntry objects by collecting metadata from each
    module. Only views for which the module's get_admin_search_entry() returns
    an AdminSearchEntry are included; returning None excludes the view (e.g. JSON/AJAX
    and internal endpoints). Title, category, keywords, and optional disambiguation_label
    are defined in the module so new modules stay discoverable without updating a central list.
    When multiple entries share the same title, the title is disambiguated by appending
    the module's disambiguation_label or a humanized view name in parentheses.
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

        # Only list views that explicitly opt in. Do not add default entries for
        # views that return None (e.g. JSON/AJAX endpoints, internal pages).
        if entry is None:
            continue

        # Ensure area (tl) and technical view_name are always searchable
        if tl not in entry.keywords:
            entry.keywords.append(tl)
        if view_name not in entry.keywords:
            entry.keywords.append(view_name)

        built.append((entry, view_name))

    # Disambiguate duplicate titles using the module's disambiguation_label or humanized view name.
    title_counts = Counter(e.title for e, _ in built)
    entries = []
    for entry, view_name in built:
        if title_counts[entry.title] > 1:
            label = entry.disambiguation_label or _humanize_view_name(view_name)
            entry = AdminSearchEntry(
                id=entry.id,
                url=entry.url,
                title=entry.title + " (" + label + ")",
                category=entry.category,
                keywords=entry.keywords,
                disambiguation_label=entry.disambiguation_label,
            )
        entries.append(entry)

    return entries


def serialize_admin_search_entries(program):
    """
    Convenience helper used by views to obtain a JSON-serializable list of
    dicts for the template context.
    """
    return [asdict(e) for e in get_admin_search_entries(program)]
