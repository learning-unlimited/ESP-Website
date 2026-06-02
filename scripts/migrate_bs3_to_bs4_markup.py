#!/usr/bin/env python3
"""Migrate Bootstrap 3 markup to Bootstrap 4 in ESP templates and theme assets."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# glyphicon-name -> bi-name (without bi- prefix)
GLYPHICON_TO_BI = {
    "home": "house",
    "user": "person",
    "search": "search",
    "tasks": "list-task",
    "th-large": "grid-3x3-gap",
    "pencil": "pencil",
    "info-sign": "info-circle",
    "log-in": "box-arrow-in-right",
    "log-out": "box-arrow-right",
    "check": "check",
    "calendar": "calendar",
    "th": "grid",
    "list": "list",
    "list-alt": "card-list",
    "shopping-cart": "cart",
    "random": "shuffle",
    "floppy-saved": "save",
    "education": "mortarboard",
    "option-horizontal": "three-dots",
    "cog": "gear",
    "plus": "plus",
    "lock": "lock",
    "asterisk": "asterisk",
    "ban-circle": "slash-circle",
    "eye-open": "eye",
    "remove": "x",
    "time": "clock",
    "exclamation-sign": "exclamation-circle",
    "warning-sign": "exclamation-triangle",
    "refresh": "arrow-clockwise",
    "ok": "check",
    "ok-sign": "check-circle",
    "download-alt": "download",
    "import": "box-arrow-in-down",
    "file": "file-earmark",
    "stats": "bar-chart",
    "heart": "heart",
    "edit": "pencil",
    "modal-window": "window",
    "arrow-left": "arrow-left",
    "repeat": "arrow-repeat",
    "euro": "currency-euro",
    "usd": "currency-dollar",
    "gbp": "currency-pound",
    "bell": "bell",
    "book": "book",
    "briefcase": "briefcase",
    "cloud": "cloud",
    "cloud-download": "cloud-download",
    "cloud-upload": "cloud-upload",
    "comment": "chat",
    "cut": "scissors",
    "dashboard": "speedometer",
    "duplicate": "copy",
    "envelope": "envelope",
    "facetime-video": "camera-video",
    "film": "film",
    "filter": "funnel",
    "fire": "fire",
    "flag": "flag",
    "flash": "lightning",
    "folder-close": "folder",
    "folder-open": "folder2-open",
    "gift": "gift",
    "glass": "eyeglasses",
    "globe": "globe",
    "headphones": "headphones",
    "hourglass": "hourglass",
    "inbox": "inbox",
    "indent-left": "text-indent-left",
    "indent-right": "text-indent-right",
    "link": "link",
    "map-marker": "geo-alt",
    "minus": "dash",
    "music": "music-note",
    "off": "power",
    "paperclip": "paperclip",
    "phone": "telephone",
    "picture": "image",
    "plane": "airplane",
    "play-circle": "play-circle",
    "print": "printer",
    "pushpin": "pin",
    "qrcode": "qr-code",
    "question-sign": "question-circle",
    "registration-mark": "r-circle",
    "resize-full": "arrows-fullscreen",
    "resize-horizontal": "arrows-expand",
    "resize-small": "arrows-collapse",
    "resize-vertical": "arrows-vertical",
    "retweet": "arrow-repeat",
    "road": "signpost",
    "save": "save",
    "saved": "save",
    "screenshot": "camera",
    "send": "send",
    "share": "share",
    "share-alt": "share",
    "shopping-cart": "cart",
    "signal": "reception-4",
    "sort": "arrow-down-up",
    "sort-by-alphabet": "sort-alpha-down",
    "sort-by-alphabet-alt": "sort-alpha-up",
    "sort-by-attributes": "sort-down",
    "sort-by-attributes-alt": "sort-up",
    "sort-by-order": "sort-numeric-down",
    "sort-by-order-alt": "sort-numeric-up",
    "star": "star",
    "star-empty": "star",
    "stats": "bar-chart",
    "step-backward": "skip-backward",
    "step-forward": "skip-forward",
    "tag": "tag",
    "tags": "tags",
    "text-height": "text-paragraph",
    "text-width": "text-wrap",
    "thumbs-down": "hand-thumbs-down",
    "thumbs-up": "hand-thumbs-up",
    "transfer": "arrow-left-right",
    "trash": "trash",
    "tint": "droplet",
    "tower": "broadcast",
    "unchecked": "square",
    "upload": "upload",
    "volume-down": "volume-down",
    "volume-off": "volume-mute",
    "volume-up": "volume-up",
    "warning-sign": "exclamation-triangle",
    "wrench": "wrench",
    "zoom-in": "zoom-in",
    "zoom-out": "zoom-out",
}

TEXT_REPLACEMENTS = [
    ("panel panel-default", "card"),
    ("panel-heading", "card-header"),
    ("panel-body", "card-body"),
    ("panel-group", "accordion"),
    ("panel-title", "mb-0"),
    ("btn btn-inverse", "btn btn-dark"),
    ("btn btn-default", "btn btn-secondary"),
    ("label label-default", "badge badge-secondary"),
    ("navbar navbar-inverse", "navbar navbar-dark"),
    ("navbar-inverse", "navbar-dark"),
    ("navbar-fixed-top", "fixed-top"),
    ("navbar-fixed-bottom", "fixed-bottom"),
    ("nav-header", "dropdown-header"),
    ("nav nav-list", "nav flex-column"),
    ("pull-right", "float-right"),
    ("pull-left", "float-left"),
    ("input-append", "input-group"),
    ("input-prepend", "input-group-prepend"),
    ("add-on", "input-group-text"),
    ("hero-unit", "jumbotron"),
    ("hidden-phone", "d-none d-md-block"),
    ("visible-phone", "d-md-none"),
]

GLYPHICON_CLASS_RE = re.compile(
    r'class="((?:[^"]*\s)?)glyphicon(?:\s+glyphicon-([a-z0-9-]+))+"'
)

GLYPHICON_SPAN_RE = re.compile(
    r'<span class="glyphicon(?:\s+glyphicon-([a-z0-9-]+))+(?:\s+glyphicon-([a-z0-9-]+))*"([^>]*)>'
)

SKIP_DIRS = {
    "node_modules",
    "yui",
    ".git",
    "__pycache__",
}

SKIP_PATH_PARTS = [
    "theme_editor/less/tests",
    ".claude/",
]


def glyphicon_tokens_to_bi(tokens: list[str]) -> str:
    bi = ["bi"]
    for token in tokens:
        if token == "btn-height":
            bi.append("bi-btn-height")
        elif token == "spin":
            bi.append("bi-spin")
        else:
            bi.append("bi-" + GLYPHICON_TO_BI.get(token, token))
    return " ".join(bi)


def migrate_glyphicon_classes(text: str) -> str:
    def span_repl(match: re.Match) -> str:
        tokens = re.findall(r"glyphicon-([a-z0-9-]+)", match.group(0))
        if not tokens:
            return match.group(0)
        bi_class = glyphicon_tokens_to_bi(tokens)
        attrs = match.group(match.lastindex or 0)
        if isinstance(attrs, str) and attrs.startswith(" "):
            return f'<span class="{bi_class}"{attrs}>'
        return match.group(0)

    # <i class="glyphicon glyphicon-user">
    def icon_repl(match: re.Match) -> str:
        tokens = re.findall(r"glyphicon-([a-z0-9-]+)", match.group(0))
        if not tokens:
            return match.group(0)
        return f'<i class="{glyphicon_tokens_to_bi(tokens)}">'

    text = re.sub(
        r'<i class="glyphicon(?:\s+glyphicon-[a-z0-9-]+)+">',
        icon_repl,
        text,
    )
    text = re.sub(
        r'<span class="glyphicon(?:\s+glyphicon-[a-z0-9-]+)+"[^>]*>',
        span_repl,
        text,
    )
    # Inline glyphicon pairs in JS strings
    def js_repl(match: re.Match) -> str:
        tokens = re.findall(r"glyphicon-([a-z0-9-]+)", match.group(0))
        return glyphicon_tokens_to_bi(tokens)

    text = re.sub(
        r'glyphicon(?:\s+glyphicon-[a-z0-9-]+)+',
        js_repl,
        text,
    )
    return text


def migrate_file(path: Path) -> bool:
    original = path.read_text(encoding="utf-8")
    updated = original
    for old, new in TEXT_REPLACEMENTS:
        updated = updated.replace(old, new)
    updated = migrate_glyphicon_classes(updated)
    if updated != original:
        path.write_text(updated, encoding="utf-8")
        return True
    return False


def should_process(path: Path) -> bool:
    rel = path.relative_to(ROOT).as_posix()
    for part in SKIP_PATH_PARTS:
        if part in rel:
            return False
    if path.suffix not in {".html", ".js"}:
        return False
    return True


def main() -> None:
    targets = [
        ROOT / "esp" / "templates",
        ROOT / "esp" / "esp" / "themes",
        ROOT / "esp" / "public" / "media" / "scripts" / "admin_bar.js",
        ROOT / "esp" / "public" / "media" / "scripts" / "nav.js",
        ROOT / "esp" / "public" / "media" / "scripts" / "qsd.js",
    ]
    changed = []
    for target in targets:
        if target.is_file():
            paths = [target]
        else:
            paths = sorted(target.rglob("*"))
        for path in paths:
            if not path.is_file() or not should_process(path):
                continue
            if migrate_file(path):
                changed.append(path)
    print(f"Updated {len(changed)} files")
    for path in changed[:30]:
        print(f"  {path.relative_to(ROOT)}")
    if len(changed) > 30:
        print(f"  ... and {len(changed) - 30} more")


if __name__ == "__main__":
    main()
