# PR: Avoid mutable default arguments and handle invalid response IDs in survey views

## Related Issue
Fixes #issue.md (Avoid mutable default arguments and handle invalid response IDs in survey views)

## Changes Proposed
* **`esp.survey.views`**: Replaced mutable default argument `context = {}` with `context = None` across `survey_view`, `display_survey`, `survey_review`, `survey_graphical`, and `survey_review_single` to eliminate shared mutable state and cross-request state pollution. Safely parsed query parameter response ID in `survey_review_single` with `try...except (ValueError, TypeError)` to avoid unhandled 500 `ValueError` crashes.
* **`esp.survey.tests`**: Added `SurveyMutableDefaultTests` to verify via function signature inspection that `context` defaults to `None` for all survey view functions and is not shared across invocations.

## How Has This Been Tested?
Please describe the tests that you ran to verify your changes.
* [x] Unit test passed: Verified function signature defaults in `SurveyMutableDefaultTests`
* [x] Static analysis passed: `flake8 --config=.flake8` passed with 0 errors
* [x] Linter passed: `ruff check --select B006` verified 0 mutable default argument violations

## Checklist
- [x] My code follows the style guidelines of this project
- [x] I have performed a self-review of my own code
- [x] I have commented my code, particularly in hard-to-understand areas
- [x] My changes generate no new warnings
