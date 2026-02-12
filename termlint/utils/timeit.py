"""
Utility functions for measuring execution time of functions.
"""

import time
from functools import wraps

from termlint.utils.logger import get_child_logger

logger = get_child_logger(__file__)


def timeit(func):
    """Decorator that measures the execution time of a function.

    This decorator logs the execution time of the decorated function, including
    the function name and its arguments.

    Args:
        func (Callable): The function to be decorated.

    Returns:
        Callable: The wrapped function that logs execution time.
    """

    @wraps(func)
    def timeit_wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        total_time = end_time - start_time
        logger.info(
            f"Function {func.__name__} Took {total_time:.4f} seconds with arguments {func.__name__}{args} {kwargs}" # pylint: disable=line-too-long
        )
        return result

    return timeit_wrapper
