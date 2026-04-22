from django.http import HttpResponseBadRequest


def parse_int(value, field_name="value"):
    """
    Safely parse an integer from input.

    Returns:
        int if valid

    Raises:
        ValueError if invalid
    """
    if value is None or not str(value).isdigit():
        raise ValueError(f"Invalid {field_name}")

    return int(value)
