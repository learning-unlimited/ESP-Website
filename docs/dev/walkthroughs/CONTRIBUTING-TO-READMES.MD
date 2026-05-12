# Contributing to Module READMEs

> How to read, use, and update the per-directory README files in this codebase.

---

## What Are These Files?

Each major directory under `esp/esp/` has a README at `docs/walkthroughs/esp/esp/<dirname>-README.MD`. They are hand-written orientation documents — not API references — answering one question:

> *"I need to change X — where do I start?"*

---

## Reading a README (First Time)

1. **One-liner + Purpose** — confirms you're in the right directory.
2. **Subdirectories table** — orients you to the folder layout.
3. **"Where to Look If You're Changing..."** — go here first; follow the file/class links directly.
4. **Classes & Components tables** — if your change isn't in step 3, find the relevant file section here.
5. **Notes & Gotchas** — always read before writing code. Known bugs, deprecated patterns, and traps live here.

---

## Updating a README (After a Code Change)

| What you did | What to update |
|---|---|
| Added a function/class | Add a row to the Classes & Components table for its file |
| Deleted a function/class | Remove its row; update any "Where to Look" or Interactions entries that referenced it |
| Changed behaviour | Update the description row; remove any now-fixed Gotcha |
| Added a new file | Add a new `### <section> — \`path/file.py\`` block with a table |
| Added an import from another ESP module | Add/update a row in Interactions with Other Directories |
| Introduced a quirk or workaround | Add a bullet to Notes & Gotchas |

**New row format** for Classes & Components:

| Column | What to write |
|---|---|
| Name | Exact source name in backticks |
| Type | `Function`, `Class`, `Method`, or `Dict` |
| File | Relative path from module root (e.g. `views/main.py`) |
| Description | One sentence starting with a verb — what it *does*, not what it *is* |

---

## Pre-Commit Checklist

- [ ] Added rows for every new function/class
- [ ] Removed rows for every deleted function/class
- [ ] All descriptions start with a verb and reflect actual code — no guesses
- [ ] File paths match real paths in the repo
- [ ] New external imports are in the Interactions table
- [ ] Fixed bugs/gotchas have their notes removed or updated
- [ ] Footer updated: `<!-- Last verified: YYYY-MM-DD | Verified by: github-username | Codebase commit: abc1234 -->`
- [ ] If you **created a new walkthrough file**, added an entry for its directory in `docs/dev/directory_structure.rst` with a short description and the directory name linked to the new walkthrough doc (e.g. `` `web <../walkthroughs/esp/esp/web-README.MD>`_ ``)

---

## Creating a README from Scratch

1. Copy `docs/walkthroughs/templates_readme/README_TEMPLATE.MD` → `docs/walkthroughs/esp/esp/<dirname>-README.MD`
2. Read every source file before writing — do not guess.
3. Pay attention to: import statements, function signatures, `TODO`/`FIXME` comments, and decorators like `@cache_function` or `@login_required`.
4. Check `esp/esp/urls.py` to verify the full mounted path of any URL patterns.
5. Add the `<!-- Last verified -->` footer.
6. Add an entry for the directory in `docs/dev/directory_structure.rst` — a short description with the directory name linked to your new walkthrough doc (e.g. `` `web <../walkthroughs/esp/esp/web-README.MD>`_ ``).

---


## Common Mistakes

- **Using docstrings as the source of truth.** Docstrings here are often outdated — read the code.
- **Skipping class methods.** Public methods used by callers need their own rows.
- **Writing "stub" without saying whether it crashes.** Specify: does it return empty data, or raise a `TypeError`?
- **Not checking the root URL conf.** Module `urls.py` files are mounted with a prefix in `esp/esp/urls.py` — always verify the full URL.