---
name: CSS theme compilation
description: How to compile theme_compiled.css for the ESP-Website Django app.
---

## Rule
To compile the CSS theme, two things must be available:

1. **`lessc`** — install globally: `npm install -g less` (binary ends up at `~/.config/npm/node_global/bin/lessc`; add to PATH before running manage.py)
2. **Bootstrap 3 LESS files** — install in the theme_editor directory: `cd esp/public/media/theme_editor && npm install bootstrap@3.3.7`

Then run: `python3 manage.py recompile_theme --settings=esp.settings`

Output file: `esp/public/media/styles/theme_compiled.css`

**Why:** The "default" theme uses Bootstrap 3's LESS pipeline. The `package.json` in `theme_editor/` only ships Bootstrap 4 (SCSS), so Bootstrap 3 must be added manually. The `lessc` binary is not pre-installed in the Replit environment.

**SCSS themes** (barebones, circles, droplets, bigpicture, fruitsalad, floaty) use `dart-sass` via `node_modules/sass/sass.js` — `npm install` in theme_editor is enough for those. Do NOT switch to a SCSS theme without loading its template customizations first — the fruitsalad theme causes a `NoneType is not iterable` error in `extract_theme` when template settings haven't been initialized.

**How to apply:** Any time the server is freshly set up and `/media/styles/theme_compiled.css` returns 404, run the two npm steps above then `recompile_theme`.
