#!/usr/bin/env python

def try_multi(n_tries):
    """
    Try the specified procedure up to N times.
    If it fails with an exception, keep trying.
    The N'th time, if it fails again, throw the exception like normal.
    """
    def try_multi_helper(fn):
        def retried_fn(*args, **kwargs):
            for x in range(n_tries - 1):
                try:
                    return fn(*args, **kwargs)
                except:
                    pass
            return fn(*args, **kwargs)
        return retried_fn
    return try_multi_helper



