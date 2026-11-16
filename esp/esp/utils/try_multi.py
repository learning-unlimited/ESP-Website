#!/usr/bin/env python

from functools import wraps
import logging

logger = logging.getLogger(__name__)


def try_multi(n_tries, exceptions=Exception):
    """
    Try the specified procedure up to N times.
    If it fails with a retryable exception, keep trying.
    If all attempts are exhausted, log the error and re-raise the exception.

    Args:
        n_tries (int): Maximum number of attempts (must be >= 1).
        exceptions (type or tuple): Exception class or tuple of exception
            classes that are safe to retry. Must inherit from Exception
            (BaseException subclasses like KeyboardInterrupt and SystemExit
            cannot be caught or retried). Defaults to Exception.
    """
    if callable(n_tries):
        fn = n_tries
        return try_multi(3, exceptions=Exception)(fn)

    if n_tries < 1:
        raise ValueError(f"n_tries must be at least 1, got {n_tries}")

    if exceptions is None:
        retryable_exceptions = (Exception,)
    elif isinstance(exceptions, (list, set)):
        retryable_exceptions = tuple(exceptions)
    elif isinstance(exceptions, type):
        retryable_exceptions = (exceptions,)
    elif isinstance(exceptions, tuple):
        retryable_exceptions = exceptions
    else:
        raise TypeError(
            "exceptions must be an Exception subclass or tuple of Exception subclasses, "
            f"got {type(exceptions).__name__}"
        )

    for exc in retryable_exceptions:
        if not (isinstance(exc, type) and issubclass(exc, Exception)):
            raise TypeError(
                f"Retryable exception {exc!r} must be a subclass of Exception"
            )

    def try_multi_helper(fn):
        @wraps(fn)
        def retried_fn(*args, **kwargs):
            for attempt in range(1, n_tries):
                try:
                    return fn(*args, **kwargs)
                except retryable_exceptions as e:
                    logger.warning(
                        "Attempt %d/%d for %s failed with %s: %s. Retrying...",
                        attempt,
                        n_tries,
                        getattr(fn, "__name__", str(fn)),
                        type(e).__name__,
                        e,
                    )
            try:
                return fn(*args, **kwargs)
            except retryable_exceptions as e:
                logger.error(
                    "All %d attempts for %s failed with %s: %s.",
                    n_tries,
                    getattr(fn, "__name__", str(fn)),
                    type(e).__name__,
                    e,
                    exc_info=True,
                )
                raise
        return retried_fn
    return try_multi_helper
