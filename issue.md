# Avoid mutable default arguments and handle invalid response IDs in survey views

## Description
In `esp/esp/survey/views.py`, multiple view functions (`survey_view`, `display_survey`, `survey_review`, `survey_graphical`, and `survey_review_single`) define `context = {}` as a default parameter value. In Python, default argument values are evaluated once at module definition time and shared across all invocations. When these views mutate `context` (such as `context['tl'] = tl`, `context['survey_id'] = ...`, or `context.update(...)`), the modifications persist in the shared dictionary across requests. This leads to cross-request state pollution, potential data leakage between different users or programs, and unpredictable template rendering.

Additionally, in `survey_review_single`, the view inspects `request.GET.items()` and directly passes `ints[0][0]` into `SurveyResponse.objects.filter(id=ints[0][0])` without verifying that the parameter is a valid integer. When non-numeric query parameters (e.g., `?survey_id=123` or malformed input) are passed, Django's ORM raises an unhandled `ValueError: Field 'id' expected a number`, resulting in a 500 Internal Server Error rather than gracefully displaying a user-friendly error message.

## Steps to Reproduce
1. Start the server and log in as a teacher or administrator.
2. Invoke `survey_view` or `display_survey` for a program survey where `context` is modified (e.g., access `/survey/teach/Splash/2026/`).
3. Concurrently or subsequently access another survey view without passing a custom `context` dictionary.
4. Observe that context variables from previous requests (e.g., previous user, program, or survey state) persist in the view context.
5. Navigate to `/survey/teach/Splash/2026/review_single?survey_id=1` or pass any non-numeric GET key.
6. See unhandled `ValueError: Field 'id' expected a number but got 'survey_id'`.

## Expected Behavior
- View functions should initialize a new dictionary instance per request when `context` is not explicitly passed (`context = None` -> `if context is None: context = {}`).
- Querying for survey response IDs should safely validate integer conversion and catch `ValueError`/`TypeError`, falling back to the standard friendly message if no valid response is found.

## Actual Behavior / Error Logs
```text
esp\esp\survey\views.py:59:92: B006 Do not use mutable data structures for argument defaults
esp\esp\survey\views.py:244:105: B006 Do not use mutable data structures for argument defaults
esp\esp\survey\views.py:617:94: B006 Do not use mutable data structures for argument defaults
esp\esp\survey\views.py:624:96: B006 Do not use mutable data structures for argument defaults
esp\esp\survey\views.py:631:108: B006 Do not use mutable data structures for argument defaults

ValueError: Field 'id' expected a number but got 'survey_id'.
  File "esp/esp/survey/views.py", line 644, in survey_review_single
    srs = SurveyResponse.objects.filter(id=ints[0][0])
```

## Proposed Fix
1. Replace default argument `context = {}` with `context = None` in `survey_view`, `display_survey`, `survey_review`, `survey_graphical`, and `survey_review_single`, initializing `context = {}` inside the function body if `context is None`.
2. In `survey_review_single`, wrap the response ID parsing in a `try...except (ValueError, TypeError)` block to ensure non-numeric keys do not crash the view.
3. Add unit tests in `esp/esp/survey/tests.py` verifying that default `context` values are not shared mutable objects.
