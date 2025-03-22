import logging
import time
from datetime import datetime
from functools import wraps

import tenacity

LOG = logging.getLogger()


def measure_exec_time(func):
    """Calculate the running time of the decorated function.

    Args:
        func (callable): The function to be decorated.

    Returns:
        callable: The wrapped function that measures execution time.
    """

    @wraps(func)
    def func_wrapper(*args, **kwargs):
        # Record the start time and a human-readable timestamp
        wall_time_start = time.time()
        perf_time_start = time.perf_counter()
        start_str = datetime.fromtimestamp(wall_time_start).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        LOG.info(f'[TIMER] Start the function "{func.__qualname__}" at {start_str}.')

        try:
            # Call the original function
            result = func(*args, **kwargs)
        finally:
            # Calculate the elapsed time and the end time
            perf_time_end = time.perf_counter()
            wall_time_end = time.time()
            end_str = datetime.fromtimestamp(wall_time_end).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            time_spent = perf_time_end - perf_time_start

            LOG.info(
                f'[TIMER] the function "{func.__qualname__}" finished at {end_str}, ' f"took {time_spent:.3f} seconds."
            )

        return result

    return func_wrapper


def wait_until(delay=60, retry=tenacity.retry_if_result, retry_param=lambda v: v is False):
    """Retry until a function is executed successfully or a timeout is reached.

    Args:
        delay (int): the timeout to exist retry.
        retry (callable): the callable object to check retry condition.
        retry_param (callable): the callable object to check the return value
        of the executed functions.
    """

    def _decorator(f):
        @wraps(f)
        def func_wrapper(*args, **kwargs):
            r = tenacity.Retrying(
                before_sleep=tenacity.before_sleep_log(LOG, logging.DEBUG),
                after=tenacity.after_log(LOG, logging.DEBUG),
                stop=tenacity.stop_after_delay(delay),
                reraise=True,
                retry=retry(retry_param),
                wait=tenacity.wait_exponential(multiplier=1, max=10),
            )
            return r(f, *args, **kwargs)

        return func_wrapper

    return _decorator
