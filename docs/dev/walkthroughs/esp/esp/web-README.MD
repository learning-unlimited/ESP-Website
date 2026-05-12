# `/esp/esp/web`

> The primary user-facing layer of the ESP site — handles routing, page views, navigation, forms, and user account management for all public and authenticated sections.

---

## Purpose

`esp/esp/web` is the Django application that wires together the public-facing website. It owns the views, URL routing, forms, models, and template tags needed to render every major page section: the homepage, contact form, user profile editor, teacher bios, class archives, and the top/side navigation bars. It sits at the presentation layer and acts as the orchestration hub, pulling data from `users`, `program`, `dbmail`, `miniblog`, and `tagdict` to assemble each page response. It also provides utility models (`NavBarCategory`, `NavBarEntry`) that every other page section relies on to render its secondary navigation.

---

## Key Functionalities

- **Page routing & views** — Dispatches requests to the homepage, program pages, contact form, user profile editor, teacher bios, class archives, onsite registration, and CSRF failure page.
- **Navigation system** — Provides both the primary top-bar (`get_primary_nav`) and the secondary sidebar nav (`makeNavBar`/`navbar_gen`), backed by `NavBarCategory` and `NavBarEntry` DB models.
- **User account management** — Handles password change (`myesp_passwd`), profile editing for all user roles (`profile_editor`), account management (`myesp_accountmanage`), identity switching (`myesp_switchback`), and onsite-user redirection (`myesp_onsite`).
- **Teacher bio display and editing** — Renders and saves teacher bios (including profile picture resizing) via `bio`, `bio_edit`, and `bio_edit_user_program`.
- **Class archives** — Provides filterable, sortable browsable views of historical ESP classes, teachers, and programs via `archive_classes`, `archive_teachers`, and `archive_programs`.
- **Form definitions** — Supplies reusable Django form classes for bio editing, file uploads, and public contact submissions (with reCAPTCHA).
- **Template tag and filter library** — Exposes custom Django inclusion tags (`get_primary_nav`, `navbar_gen`) and template filters (`mux_tl`, `extract_theme`, `truncatewords_char`, etc.) used across the site's templates.

---

## Subdirectories

| Directory | Description |
|-----------|-------------|
| `views/` | All Django view functions and classes — the actual request-handling logic for every page section owned by this app. |
| `forms/` | Django `Form` subclasses for user-facing inputs: bio editing, file upload, and the public contact form. |
| `templatetags/` | Custom Django template tag/filter libraries registered under `esp.web` — used directly inside HTML templates. |
| `migrations/` | Django database migration files for the `NavBarCategory` and `NavBarEntry` models. |
| `tests.py` | Unit tests for the `web` app — covers view behaviour, form validation, and navigation model logic. |

---

## Classes & Components

### Models (`models.py`)

| Name | Type | File | Description |
|------|------|------|-------------|
| `NavBarCategory` | Class | `models.py` | A DB-backed grouping for secondary nav entries, matched to a URL path prefix or section name. |
| `NavBarEntry` | Class | `models.py` | A single link in the secondary sidebar nav, belonging to a `NavBarCategory` and ordered by `sort_rank`. |
| `NavBarEntry.makeTitle` | Method | `models.py` | Returns `self.text` — used by templates that need a uniform title accessor. |
| `NavBarEntry.makeUrl` | Method | `models.py` | Returns `self.link` — used by templates that need a uniform URL accessor. |
| `NavBarEntry.is_link` | Method | `models.py` | Returns `True` if `self.link` is non-null and non-empty; used to decide whether to render an `<a>` tag. |
| `NavBarEntry.can_edit` | Method | `models.py` | Returns `True` only if the requesting user is an admin. |
| `NavBarCategory.from_request` | Static Method | `models.py` | Cache-decorated static method that resolves the best matching `NavBarCategory` for a given URL path or section name. |
| `NavBarCategory.get_navbars` | Method | `models.py` | Returns all `NavBarEntry` objects for a category, ordered by `sort_rank`. |
| `default_navbarcategory` | Function | `models.py` | Returns (and caches on the class) the `NavBarCategory` named `'default'`; used as the FK default. |
| `install` | Function | `models.py` | Creates the mandatory `'default'` `NavBarCategory` if it does not exist — called during site setup. |

### Views — `views/main.py`

| Name | Type | File | Description |
|------|------|------|-------------|
| `home` | Function | `views/main.py` | Renders the homepage (`index.html`) with the `'home'` navbar category; response-cached and CSRF-cookie-suppressed. |
| `program` | Function | `views/main.py` | Resolves a program by type/instance from the URL and delegates to `ProgramModuleObj.findModule` for program-specific pages. |
| `public_email` | Function | `views/main.py` | Renders a publicly-viewable archived email by `MessageRequest` id; response-cached. |
| `archives` | Function | `views/main.py` | Dispatches to the correct archive handler (`classes`, `teachers`, or `programs`) from `archive_handlers`. |
| `DefaultQSDView` | Class | `views/main.py` | `TemplateView` subclass whose `get_context_data` returns `esp_context_stuff()` — base for static QSD-backed pages. |
| `FAQView` | Class | `views/main.py` | `DefaultQSDView` rendering `faq.html`. |
| `ContactUsView` | Class | `views/main.py` | `DefaultQSDView` rendering `contact_qsd.html`. |
| `contact` | Function | `views/main.py` | Processes the public contact form; checks `contact_form_enabled` tag, detects password-recovery intent, and sends email via `send_mail`. |
| `registration_redirect` | Function | `views/main.py` | After profile completion, redirects a user to the single open registration for their role, or shows a list of open programs. |
| `set_csrf_token` | Function | `views/main.py` | Forces Django to set the CSRF cookie (via `get_token`) and returns an empty 200 — used by JS-heavy pages. |

### Views — `views/myesp.py`

| Name | Type | File | Description |
|------|------|------|-------------|
| `myesp_passwd` | Function | `views/myesp.py` | Lets an authenticated user change their own password; blocks the special `'onsite'` account. |
| `myesp_accountmanage` | Function | `views/myesp.py` | Renders the account management page (`users/account_manage.html`). |
| `myesp_switchback` | Function | `views/myesp.py` | Reverses a prior identity-switch performed by an admin by calling `user.switch_back(request)`. |
| `edit_profile` | Function | `views/myesp.py` | Detects the current user's role and delegates to `profile_editor` with the appropriate role string. |
| `profile_editor` | Function | `views/myesp.py` | Full profile edit/create flow: dynamically imports the correct role-specific form class, handles `RegistrationProfile` creation and updates for all configured user types (see `ESPUser.getAllUserTypes()`). |
| `myesp_onsite` | Function | `views/myesp.py` | Redirects a valid onsite user to their program's onsite page, or shows a picker if multiple programs are available. |

### Views — `views/bio.py`

| Name | Type | File | Description |
|------|------|------|-------------|
| `bio_edit` | Function | `views/bio.py` | Entry point for bio editing: resolves user from URL parameters (username or first/last/num) and optionally a `Program` via `progid`, then calls `bio_edit_user_program`. |
| `bio_edit_user_program` | Function | `views/bio.py` | Core bio-edit logic: validates permissions, loads `BioEditForm`, saves `TeacherBio` and resized picture on POST. |
| `bio` | Function | `views/bio.py` | Entry point for bio display: resolves user from URL parameters then calls `bio_user`. |
| `bio_user` | Function | `views/bio.py` | Renders a teacher bio page including taught classes (filtered to exclude future/unapproved classes) and `ArchiveClass` fallbacks. |
| `bio_not_found` | Function | `views/bio.py` | Returns a 404-status render of `users/teacherbionotfound.html`; optional `user` and `edit_url` params are passed into the template context as `biouser` and `edit_url`. |

### Views — `views/archives.py`

| Name | Type | File | Description |
|------|------|------|-------------|
| `ArchiveFilter` | Class | `views/archives.py` | Lightweight value object holding a `category` and `options` string pair that represents one active filter criterion. |
| `compute_range` | Function | `views/archives.py` | Calculates `start`/`end` slice indices for paginating archive results from POST/GET params. |
| `extract_criteria` | Function | `views/archives.py` | Parses POST/GET vars whose keys begin with `filter_` into a list of `ArchiveFilter` objects. |
| `filter_archive` | Function | `views/archives.py` | Applies a list of `ArchiveFilter` objects as Django ORM filters to an `ArchiveClass` queryset. |
| `title_heading` | Function | `views/archives.py` | Returns the first character of a title string for use as a jump-to heading, or `'[No Title]'` if empty. |
| `archive_classes` | Function | `views/archives.py` | Renders a filterable, sortable, paginated list of historical `ArchiveClass` records. |
| `archive_teachers` | Function | `views/archives.py` | Stub: sets `selection`, `category`, `options` in context and renders `program/archives.html` — **crashes with `TypeError`** when called via `archives()` because the dispatcher passes more positional arguments than this function accepts. |
| `archive_programs` | Function | `views/archives.py` | Stub: same signature mismatch as `archive_teachers` — also crashes with `TypeError`. |
| `archive_handlers` | Dict | `views/archives.py` | Maps the strings `'classes'`, `'teachers'`, `'programs'` to their respective view functions; used by `archives()` in `main.py`. |

### Views — `views/navBar.py`

| Name | Type | File | Description |
|------|------|------|-------------|
| `makeNavBar` | Function | `views/navBar.py` | Accepts `section`, `category`, and `path`; resolves the correct `NavBarCategory` and returns a context dict with keys `entries` (list of `{'entry': NavBarEntry}` dicts), `section`, `category`, and `next_sort_rank`. |

### Views — `views/csrf.py`

| Name | Type | File | Description |
|------|------|------|-------------|
| `csrf_failure` | Function | `views/csrf.py` | Custom CSRF failure view that tries to render `403_csrf_failure.html` with program context; falls back to Django's default on any exception. |

### Forms (`forms/`)

| Name | Type | File | Description |
|------|------|------|-------------|
| `ResizeImageField` | Class | `forms/__init__.py` | `ImageField` that resizes the uploaded image to fit within a given bounding box (aspect ratio preserved) using Pillow before returning it. |
| `BioEditForm` | Class | `forms/bioedit_form.py` | Form for editing a `TeacherBio`, including bio text, a profile picture (via `ResizeImageField`), and metadata fields. |
| `ContactForm` | Class | `forms/contact_form.py` | Public contact form capturing sender info, topic-based routing, a message body, and reCAPTCHA validation. See `forms/contact_form.py` for the full field list. |
| `FileUploadForm` | Class | `forms/fileupload_form.py` | Basic form for uploading a titled file. |
| `FileUploadForm_Admin` | Class | `forms/fileupload_form.py` | Admin variant of `FileUploadForm` with an additional target-object choice field whose options must be populated dynamically via `set_choices`. |
| `FileUploadForm_Admin.set_choices` | Method | `forms/fileupload_form.py` | Replaces `target_obj` with a new `ChoiceField` populated from the provided `new_choices` iterable. |
| `FileRenameForm` | Class | `forms/fileupload_form.py` | Inline rename form (short text input) for uploaded files. |

### Template Tags (`templatetags/`)

| Name | Type | File | Description |
|------|------|------|-------------|
| `get_primary_nav` | Tag | `templatetags/topbar.py` | Cache-backed inclusion tag that builds the top primary navigation bar structure based on the current URL path and user role. |
| `navbar_gen` | Tag | `templatetags/navbar.py` | Cache-backed inclusion tag that renders `inclusion/web/navbar_left.html` from a pre-built `navbar_list`. |
| `mux_tl` | Filter | `templatetags/main.py` | Swaps the top-level section (`teach`, `learn`, `manage`, etc.) in a URL path to a different one. |
| `extract_theme` | Filter | `templatetags/main.py` | Returns a theme-specific CSS class string by matching a URL against the theme's nav structure. |
| `get_nav_category` | Filter | `templatetags/main.py` | Returns the nav category dict from `ThemeController` settings whose `header_link` matches the URL's first path segment. |
| `truncatewords_char` | Filter | `templatetags/main.py` | Truncates a string to at most N characters, breaking only on word boundaries. |
| `as_form_label` | Filter | `templatetags/main.py` | Converts an underscore-separated identifier to a capitalised human-readable label. |
| `split` | Filter | `templatetags/main.py` | Splits a string on a given delimiter and returns the list. |
| `index` | Filter | `templatetags/main.py` | Safe index accessor for a list; returns `''` on `IndexError`. |
| `concat` | Filter | `templatetags/main.py` | Concatenates two strings. |
| `equal` | Filter | `templatetags/main.py` | Returns `obj1 == obj2`. |
| `notequal` | Filter | `templatetags/main.py` | Returns `obj1 != obj2`. |
| `bool_or` | Filter | `templatetags/main.py` | Returns `obj1 or obj2`. |
| `bool_and` | Filter | `templatetags/main.py` | Returns `obj1 and obj2`. |
| `get_field` | Filter | `templatetags/main.py` | Returns `getattr(object, field)`. |
| `regexsite` | Filter | `templatetags/main.py` | Escapes dots in a domain string for use in a regex. |
| `count_matching_chars` | Function | `templatetags/main.py` | Helper for `extract_theme` — returns the length of the common prefix between two strings. |

### Admin (`admin.py`)

| Name | Type | File | Description |
|------|------|------|-------------|
| `NavBarEntryAdmin` | Class | `admin.py` | Django admin config for `NavBarEntry`: lists by category, sort rank, text, and link; filters by category. |
| `NavBarCategoryAdmin` | Class | `admin.py` | Django admin config for `NavBarCategory`; overrides both `delete_model` (emits an error message) and `has_delete_permission` (returns `False`) to prevent deletion of the `'default'` category. |

### URL routing (`urls.py`)

`urls.py` registers the bio-related URL patterns. They are included in the root URL conf under `(?P<tl>teach|learn)/teachers/`, meaning every bio URL is reachable under EITHER `teach/teachers/` or `learn/teachers/`. The `tl` path segment is captured by the root conf and passed as a parameter to the bio views. All patterns map to views in `views/bio.py`:

| Full URL pattern | View | Notes |
|---------|------|-------|
| `(teach\|learn)/teachers/<username>/bio.html` | `bio.bio` | Current canonical bio URL |
| `(teach\|learn)/teachers/<username>/bio.edit.html` | `bio.bio_edit` | Current canonical bio-edit URL |
| `(teach\|learn)/teachers/<last>/<first><usernum>/bio.html` | `bio.bio` | Deprecated — issues permanent redirect |
| `(teach\|learn)/teachers/<last>/<first><usernum>/bio.edit.html` | `bio.bio_edit` | Deprecated — issues permanent redirect |

### App config (`apps.py`)

| Name | Type | File | Description |
|------|------|------|-------------|
| `WebConfig` | Class | `apps.py` | `InstallConfig` subclass that registers `'esp.web'` as a Django app. |

---

## Interactions with Other Directories

| Directory | How it connects |
|-----------|-----------------|
| **`/users`** | `profile_editor` imports `ESPUser`, `ContactInfo`, `TeacherInfo`, `StudentInfo`, `GuardianInfo`, `EducatorInfo`, `Permission`, `K12School`, and `RegistrationProfile` to read and write user profiles; `bio.py` uses `ESPUser` for teacher lookup; `myesp_passwd` uses `UserPasswdForm`. |
| **`/program`** | `program()` in `main.py` resolves a `Program` and delegates to `ProgramModuleObj.findModule`; `bio_user` reads `TeacherBio` and `ArchiveClass`; `archive_classes` queries `ArchiveClass`, `ClassSubject`, and `ClassCategories`; `csrf.py` looks up `Program` to provide context on CSRF failures. |
| **`/dbmail`** | `contact()` calls `send_mail` from `esp.dbmail.models`; `public_email` queries `MessageRequest`. |
| **`/miniblog`** | `myesp.py` imports `AnnouncementLink`, `Entry`, and `preview_miniblog` — however these imports appear to be **unused** in current view functions (likely vestigial from removed dashboard announcement logic). |
| **`/tagdict`** | `Tag.getBooleanTag` is called in `contact()` (to check `contact_form_enabled`), `registration_redirect` (for `automatic_registration_redirect`), and `profile_editor` (for `allow_change_grade_level`, `require_student_phonenum`). |
| **`/middleware`** | `ESPError` is raised in `myesp_passwd`, `myesp_switchback`, `myesp_onsite`, and `public_email`; `AutoRequestContext` is imported in `main.py`. |
| **`/utils`** | `render_to_response`, `esp_context_stuff`, `get_from_id` are used throughout views; `cache_inclusion_tag` backs template tags; `disable_csrf_cookie_update` decorates `home()`. |
| **`/themes`** | `ThemeController` is imported by `templatetags/main.py` for `extract_theme` and `get_nav_category`. |
| **`/db`** | `AjaxForeignKey` from `esp.db.fields` is imported in `models.py` but is **unused** — `NavBarEntry.category` is a standard Django `ForeignKey`. This is dead code. |

---

## Where to Look If You're Changing...

- **The homepage or any public static page** → `home()` in [views/main.py](views/main.py), and the `'home'` `NavBarCategory` in the database; template is `templates/index.html`.
- **The top navigation bar** (tabs: Discover ESP, Take a Class, etc.) → `get_primary_nav` in [templatetags/topbar.py](templatetags/topbar.py); the `sections` dict at the bottom of that file defines every top-level nav item and its URL.
- **The secondary/sidebar navigation** → `makeNavBar` in [views/navBar.py](views/navBar.py), `NavBarCategory`/`NavBarEntry` in [models.py](models.py), and `navbar_gen` in [templatetags/navbar.py](templatetags/navbar.py).
- **User profile creation or editing** → `profile_editor` in [views/myesp.py](views/myesp.py); the actual form class is loaded dynamically from `esp.users.forms.user_profile` based on the user's role.
- **Teacher bio pages** (display or edit) → `bio` / `bio_user` and `bio_edit` / `bio_edit_user_program` in [views/bio.py](views/bio.py); picture resizing lives in `ResizeImageField` in [forms/\_\_init\_\_.py](forms/__init__.py); bio data model is `TeacherBio` in `/program`.
- **The contact form** → `contact()` in [views/main.py](views/main.py) and `ContactForm` in [forms/contact_form.py](forms/contact_form.py); the `contact_form_enabled` Tag gates whether the form is active at all.

---

## Notes & Gotchas

- **`program()` is not a program-module view itself.** It only resolves the `Program` object and calls `ProgramModuleObj.findModule`. All actual program page logic lives in `/program/modules/`. If a module isn't found, this view raises a plain 404.

- **`get_primary_nav` uses two separate nav lists with different purposes.** `known_navlinks` (7 items) gates whether the tag renders anything at all — if the first URL path segment is not in this list the function returns `{}`. `basic_navlinks` (also 7 items, different set) controls which sections are *iterated* when building nav link dicts. These two lists overlap but are not identical; `contactinfo` is in `known_navlinks` but maps to a subsection under `about`, while admin/onsite links are injected separately based on user role. Adding a new top-level section requires updating *both* lists and the `sections` dict in [templatetags/topbar.py](templatetags/topbar.py).

- **`NavBarCategory.from_request` is cache-decorated via `argcache`.** It declares `depend_on_model('web.NavBarCategory')`, so the cache is invalidated on any `NavBarCategory` change. However, cache invalidation bugs here will produce wrong sidebar nav on pages — if nav seems stale, check the cache backend.

- **`profile_editor` dynamically imports the form class by string name.** The role string (e.g. `'teacher'`) maps to a form class name (e.g. `'UserContactForm'`) via `ESPUser.getAllUserTypes()`. If you add a new user role, you must add a corresponding entry there *and* create the matching form in `esp.users.forms.user_profile`, otherwise `profile_editor` will throw a `ValueError` (from `list.index()` on the unknown role string) or an `AttributeError` (from `getattr` on a missing form class) at runtime.

- **`bio_user` deliberately excludes classes whose end time is in the future.** This is a documented privacy decision: the course catalog for a not-yet-run program may not be public yet, so exposing class titles on the bio page would leak information. See the comment in [views/bio.py](views/bio.py).

- **`archive_teachers` and `archive_programs` crash on every call.** The dispatcher `archives()` in `main.py` always calls `archive_handlers[selection](request, category, options, sortparams)` with 4 positional arguments, but `archive_teachers(request, category, options)` and `archive_programs(request, category, options)` only accept 3. Any request to `/archives/teachers/` or `/archives/programs/` will raise `TypeError`. `archive_classes` is thCodebase commit: HEADe only handler that is both implemented and callable.

- **Old bio URLs permanently redirect.** Both `bio` and `bio_edit` detect "old URL" patterns (non-`teach` tl prefix, or first/last/num format) and issue `HttpResponsePermanentRedirect`. A `TODO` comment in [views/bio.py](views/bio.py) indicates these redirects were expected to be removed, but are still present.

- **`csrf_failure` resolves `prog` but never uses it.** In [views/csrf.py](views/csrf.py), `prog` is looked up and assigned but never added to the template context before `render_to_response` is called, so `403_csrf_failure.html` cannot access program-specific context. This appears to be a long-standing bug.

- **`ResizeImageField` calls `Image.ANTIALIAS`, which is removed in Pillow 10.** `Image.ANTIALIAS` was deprecated in Pillow 9.1.0 and fully removed in Pillow 10.0.0 (released 2023). Running on a modern Pillow version will raise `AttributeError` when a user uploads a profile picture. The fix is to replace it with `Image.LANCZOS`.

<!-- Last verified: 2026-03-05 | Verified by: Balasubramaniam12007 -->