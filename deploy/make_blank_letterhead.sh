#!/bin/bash
# Create a blank esp/public/media/latex_media/letterhead.pdf if there isn't
# one already.  Letters and completion certificates draw on it, so they can't
# compile without it.  Production has a real letterhead there, which is
# gitignored, so dev and CI copies need a stand-in.  Never overwrites a file.
set -euf -o pipefail

cd "$(dirname "$0")/.."
target=esp/public/media/latex_media/letterhead.pdf
if [ -e "$target" ]; then
    exit 0
fi

mkdir -p "$(dirname "$target")"
work=$(mktemp -d)
printf '%s\n' '\documentclass[letterpaper]{article}' '\pagestyle{empty}' \
    '\begin{document}' '\mbox{}' '\end{document}' > "$work/letterhead.tex"
(cd "$work" && pdflatex -interaction nonstopmode -halt-on-error letterhead.tex > /dev/null)
cp "$work/letterhead.pdf" "$target"
rm -rf "$work"
echo "Created a blank $target"
