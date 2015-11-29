#!/bin/bash -e

BASE_DIR="$(dirname "$(dirname "$(readlink -e "$0")")")" # /esp

echo "Running lint checks..."

# For now, ignore everything except:
#   F82x: undefined name, local variable referenced before assignment
#   F831: duplicate arg in function definition
#   W601: `has_key` instead of `in`
#   W603: <> instead of !=
#   W604: backticks instead of `repr`
# Errors I'd like to turn on sometime soon, but which still require some
# cleanup first:
#   E101: mixed tabs and spaces
#   E11x: other indentation issues (expected indented block, unexpected indent, not a multiple of four)
#   F811: redefinition of unused name
#   F841: unused name
#   W191: indentation contains tabs
#   W291: whitespace at end of line
#   W293: whitespace on blank line
flake8 --ignore "E,F,W" --select "F82,F831,W601,W603,W604" $BASE_DIR

echo "done."
