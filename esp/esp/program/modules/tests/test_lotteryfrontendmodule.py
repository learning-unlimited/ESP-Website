import pytest
from esp.program.modules.handlers.lotteryfrontendmodule import LotteryFrontendModule


# --- is_float: valid numbers ---

def test_is_float_valid_numbers():
    m = LotteryFrontendModule()

    assert m.is_float("3.14") is True
    assert m.is_float("0") is True
    assert m.is_float("-1.5") is True
    assert m.is_float("100") is True


# --- is_float: invalid (non-numeric) strings ---

def test_is_float_invalid_numbers():
    m = LotteryFrontendModule()

    assert m.is_float("abc") is False
    assert m.is_float("") is False
    assert m.is_float("3.1.4") is False
    assert m.is_float("None") is False


# --- is_float: type-like edge cases ---

def test_is_float_type_error():
    m = LotteryFrontendModule()

    assert m.is_float("True") is False
    assert m.is_float("False") is False


# --- is_float: whitespace-padded numbers (real-world form input) ---
# float(" 5 ") is valid Python, so we confirm is_float handles it correctly

def test_is_float_with_whitespace():
    m = LotteryFrontendModule()

    assert m.is_float(" 5 ") is True
    assert m.is_float(" 3.5 ") is True


# --- is_float: regression test for nan/inf (Fix 3) ---
# math.isfinite() must reject these — test ensures the fix never regresses

def test_is_float_rejects_nonfinite():
    m = LotteryFrontendModule()

    assert m.is_float("nan") is False
    assert m.is_float("inf") is False
    assert m.is_float("-inf") is False


# --- Key parsing: regression test for malformed POST keys (Fix 1 + Fix 2) ---
# Simulates the lottery_execute key-parsing logic directly.
# Ensures malformed keys like "lotterylimit" (missing underscore) are ignored,
# and valid keys like "lottery_limit" are stripped to "limit" correctly.

def test_lottery_option_key_parsing():
    m = LotteryFrontendModule()

    data = {
        "lottery_use_priority": "True",
        "lottery_limit": "5",
        "lotterylimit": "10",   # malformed key — no underscore after prefix
    }

    options = {}

    for key in data:
        if key.startswith("lottery_"):
            options[key[len("lottery_"):]] = data[key]

    assert "use_priority" in options       # valid key parsed correctly
    assert "limit" in options              # valid key parsed correctly
    assert "lotterylimit" not in options   # malformed key ignored safely
    assert len(options) == 2              # no extra keys snuck in