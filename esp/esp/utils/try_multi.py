#!/usr/bin/env python
from __future__ import absolute_import

import functools
import logging
from six.moves import range

logger = logging.getLogger(__name__)


def try_multi(n_tries, exceptions=(Exception,), log_each_failure=False):
    """
    Retry a function up to ``n_tries`` times when it raises one of
    ``exceptions``. On final failure, log and re-raise.
    """
    if n_tries < 1:
        raise ValueError("n_tries must be >= 1")

    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            for attempt in range(1, n_tries + 1):
                try:
                    return fn(*args, **kwargs)
                except exceptions as exc:
                    if attempt == n_tries:
                        logger.exception(
                            "try_multi: exhausted %d tries calling %s",
                            n_tries,
                            getattr(fn, "__qualname__", repr(fn)),
                        )
                        raise

                    if log_each_failure:
                        logger.warning(
                            "try_multi: attempt %d/%d failed calling %s: %s",
                            attempt,
                            n_tries,
                            getattr(fn, "__qualname__", repr(fn)),
                            exc,
                            exc_info=True,
                        )

        return wrapper

    return decorator


