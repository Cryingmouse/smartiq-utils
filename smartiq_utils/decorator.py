import logging
import time
from datetime import datetime
from datetime import timedelta
from functools import wraps
from typing import Any
from typing import Callable
from typing import Optional
from typing import Union

import tenacity
from tenacity.wait import wait_base

LOG = logging.getLogger()


def measure_exec_time(func: Callable[..., Any]) -> Callable[..., Any]:
    """Calculate the running time of the decorated function.

    Args:
        func (Callable): The function to be decorated.

    Returns:
        Callable: The wrapped function that measures execution time.
    """

    @wraps(func)
    def func_wrapper(*args: Any, **kwargs: Any) -> Any:
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


def wait_until(
    delay: Union[int | float | timedelta] = 60,
    retry: Callable[..., Any] = tenacity.retry_if_result,
    retry_param: Callable[..., Any] = lambda v: v is False,
):
    """Retry until a function is executed successfully or a timeout is reached.

    Args:
        delay (int, optional): the timeout to exist retry.
        retry (Callable, optional): the callable object to check retry condition.
        retry_param (Callable, optional): the callable object to check the return value of the executed functions.
    """

    def _decorator(f) -> Callable[..., Any]:
        @wraps(f)
        def func_wrapper(*args: Any, **kwargs: Any):
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


def last_for(
    delay=60,
    retry=tenacity.retry_if_result,
    retry_param=lambda value: value is True,
    wait: wait_base = tenacity.wait_random(min=1, max=2),
):
    """Retry a function until success or a timeout is reached.

    Args:
        delay (int, optional): the timeout to exit retry.
        retry (callable, optional): the callable object to check retry condition.
        retry_param (callable, optional): the callable object to check the return value of the executed functions.
        wait (wait_base, optional): the wait time between retry.
    """

    def _decorator(f):
        @wraps(f)
        def _wrapper(*args, **kwargs):
            r = tenacity.Retrying(
                before_sleep=tenacity.before_sleep_log(LOG, logging.DEBUG),
                after=tenacity.after_log(LOG, logging.DEBUG),
                stop=tenacity.stop_after_delay(delay),
                reraise=True,
                retry=retry(retry_param),
                wait=wait,
            )
            try:
                return r(f, *args, **kwargs)
            except tenacity.RetryError as e:
                return e.last_attempt.result()

        return _wrapper

    return _decorator


def function_logging(
    level: int = logging.INFO,
    start_msg: Optional[str] = None,
    end_msg: Optional[str] = None,
    error_msg: Optional[str] = None,
    include_args: bool = False,
):
    """A decorator to log the start, end, and errors of a function, including its arguments.

    Args:
        level (int, optional): Logging level (e.g., logging.INFO, logging.DEBUG).
        start_msg (str, optional): Custom message to log at the start.
        end_msg (str, optional): Custom message to log at the end.
        error_msg (str, optional): Custom message to log on error.
        include_args (bool, optional): Whether to include function arguments in the log messages.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cls_name = args[0].__class__.__name__ if args else "UnknownClass"
            func_name = f"{cls_name}.{func.__name__}"

            all_args = []
            if include_args:
                # Prepare arguments for logging
                args_repr = [repr(a) for a in args[1:]]
                kwargs_repr = [f"{k}={v!r}" for k, v in kwargs.items()]
                all_args = ", ".join(args_repr + kwargs_repr)

                # Log start message
                start_log = (
                    f"Start {func_name} with args: {all_args}. {start_msg}"
                    if start_msg
                    else f"Start {func_name} execution with args: {all_args}."
                )
            else:
                start_log = f"Start {func_name}: {start_msg}" if start_msg else f"Start {func_name} execution."
            LOG.log(level, start_log)

            try:
                result = func(*args, **kwargs)

                # Log end message
                end_log = (
                    f"End {func_name}: {end_msg}. Result: {result!r}"
                    if end_msg
                    else f"End {func_name} execution successfully. Result: {result!r}"
                )
                LOG.log(level, end_log)

                return result
            except Exception as e:
                # Log error message
                err_log = (
                    f"Execute {func_name} with args: {all_args} and error: {error_msg}"
                    if error_msg
                    else f"Execute {func_name} with args: {all_args} and error: {e}"
                )
                LOG.error(err_log)
                raise e

        return wrapper

    return decorator
