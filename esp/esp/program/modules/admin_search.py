from dataclasses import dataclass, asdict
from typing import List


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


def get_admin_search_entries(program):
    """
    Return a list of AdminSearchEntry objects describing key admin views for
    the given program. This is intentionally small and hand-curated for now;
    more entries can be added incrementally over time.
    """
    base = program.getUrlBase()

    entries = [
        AdminSearchEntry(
            id="resources",
            url=f"/manage/{base}/resources",
            title="Resources",
            category="Configure",
            keywords=["rooms", "classrooms", "spaces", "timeslots", "resources"],
        ),
        AdminSearchEntry(
            id="deadlines",
            url=f"/manage/{base}/deadlines",
            title="Deadlines",
            category="Configure",
            keywords=["registration", "open", "close", "dates", "deadlines"],
        ),
        AdminSearchEntry(
            id="teacher_events",
            url=f"/manage/{base}/teacher_events",
            title="Teacher Training / Interviews",
            category="Configure",
            keywords=["teacher", "training", "interviews", "events"],
        ),
        AdminSearchEntry(
            id="lunch_constraints",
            url=f"/manage/{base}/lunch_constraints",
            title="Lunch Constraints",
            category="Configure",
            keywords=["lunch", "constraints", "schedule", "availability"],
        ),
        AdminSearchEntry(
            id="registrationtype_management",
            url=f"/manage/{base}/registrationtype_management",
            title="Student Registration Types",
            category="Configure",
            keywords=["registration", "types", "student", "sections", "schedule"],
        ),
        AdminSearchEntry(
            id="surveys",
            url=f"/manage/{base}/surveys",
            title="Surveys",
            category="Configure",
            keywords=["survey", "feedback", "student survey", "teacher survey"],
        ),
        AdminSearchEntry(
            id="settings",
            url=f"/manage/{base}/settings",
            title="Program Settings",
            category="Configure",
            keywords=["settings", "program", "registration", "options"],
        ),
        AdminSearchEntry(
            id="modules",
            url=f"/manage/{base}/modules",
            title="Manage Modules",
            category="Configure",
            keywords=["modules", "required", "sequence", "student registration", "teacher registration"],
        ),
        AdminSearchEntry(
            id="tags",
            url=f"/manage/{base}/tags",
            title="Tag Settings",
            category="Configure",
            keywords=["tags", "advanced", "experts", "settings"],
        ),
        AdminSearchEntry(
            id="email",
            url=f"/manage/{base}/commpanel",
            title="Email (Communications Panel)",
            category="Coordinate",
            keywords=["email", "communications", "commpanel", "messages"],
        ),
        AdminSearchEntry(
            id="admin_morph",
            url=f"/manage/{base}/admin_morph",
            title="Morph into User",
            category="Coordinate",
            keywords=["impersonate", "morph", "see as user", "debug"],
        ),
        AdminSearchEntry(
            id="select_list",
            url=f"/manage/{base}/selectList",
            title="Arbitrary User List",
            category="Coordinate",
            keywords=["user list", "search users", "export", "mailing list"],
        ),
        AdminSearchEntry(
            id="dashboard",
            url=f"/manage/{base}/dashboard",
            title="Dashboard",
            category="Logistics",
            keywords=["classes", "stats", "overview", "enrollment", "logistics"],
        ),
        AdminSearchEntry(
            id="ajax_scheduling",
            url=f"/manage/{base}/ajax_scheduling",
            title="Scheduling",
            category="Logistics",
            keywords=["schedule", "rooms", "times", "ajax", "scheduling"],
        ),
        AdminSearchEntry(
            id="get_materials",
            url=f"/manage/{base}/get_materials",
            title="Documents",
            category="Logistics",
            keywords=["documents", "files", "upload", "download", "materials"],
        ),
        AdminSearchEntry(
            id="volunteering",
            url=f"/manage/{base}/volunteering",
            title="Volunteers",
            category="Logistics",
            keywords=["volunteers", "shifts", "signups"],
        ),
        # Quick Links (student/teacher/volunteer views)
        AdminSearchEntry(
            id="learn_catalog",
            url=f"/learn/{base}/catalog",
            title="Student Catalog",
            category="Quick Links",
            keywords=["catalog", "classes", "student view"],
        ),
        AdminSearchEntry(
            id="learn_studentreg",
            url=f"/learn/{base}/studentreg",
            title="Student Registration",
            category="Quick Links",
            keywords=["student registration", "signup", "enroll"],
        ),
        AdminSearchEntry(
            id="teach_teacherreg",
            url=f"/teach/{base}/teacherreg",
            title="Teacher Registration",
            category="Quick Links",
            keywords=["teacher registration", "propose class", "teach"],
        ),
        AdminSearchEntry(
            id="volunteer_signup",
            url=f"/volunteer/{base}/signup",
            title="Volunteer Signup",
            category="Quick Links",
            keywords=["volunteer", "signup", "shifts"],
        ),
        AdminSearchEntry(
            id="onsite_main",
            url=f"/onsite/{base}/main",
            title="Onsite Interface",
            category="Quick Links",
            keywords=["onsite", "check-in", "day-of", "logistics"],
        ),
        # Printables and related views
        AdminSearchEntry(
            id="manage_catalog",
            url=f"/manage/{base}/catalog",
            title="PDF Catalog",
            category="Printables",
            keywords=["printable", "pdf catalog", "classes"],
        ),
        AdminSearchEntry(
            id="student_schedules",
            url=f"/manage/{base}/studentschedules",
            title="Student Schedules",
            category="Printables",
            keywords=["printable", "student schedules", "schedules"],
        ),
        AdminSearchEntry(
            id="studentscheduleform",
            url=f"/manage/{base}/studentscheduleform",
            title="Student Schedule Formatter",
            category="Printables",
            keywords=["formatter", "student schedules", "printable"],
        ),
        AdminSearchEntry(
            id="selectidoptions",
            url=f"/manage/{base}/selectidoptions",
            title="Nametags",
            category="Printables",
            keywords=["nametags", "name tags", "ids", "badges"],
        ),
        AdminSearchEntry(
            id="printoptions",
            url=f"/manage/{base}/printoptions",
            title="All Printables",
            category="Printables",
            keywords=["printables", "all printables", "pdf", "documents"],
        ),
    ]

    # Mirror the feature flags used in the template where reasonable.
    # This keeps results from pointing to views that are not available.
    flags = dict(program=program)

    def is_available(entry_id):
        # Configure group
        if entry_id == "resources":
            return getattr(program, "getModules", None) is not None
        # For now, keep all entries; the template already guards visibility
        # with context flags. If desired, we can pass those flags in here
        # and filter more aggressively in the future.
        return True

    return [e for e in entries if is_available(e.id)]


def serialize_admin_search_entries(program):
    """
    Convenience helper used by views to obtain a JSON-serializable list of
    dicts for the template context.
    """
    return [asdict(e) for e in get_admin_search_entries(program)]

