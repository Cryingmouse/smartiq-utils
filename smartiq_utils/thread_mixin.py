from __future__ import annotations

import concurrent.futures
import logging
from concurrent.futures import ThreadPoolExecutor
from types import FunctionType
from typing import Any
from typing import Callable
from typing import Dict
from typing import Iterator
from typing import List
from typing import Optional
from typing import Tuple

from smartiq_utils.hash_mapping import HashMapping

LOG = logging.getLogger()


class MultipleException(Exception):
    def __init__(self):
        self._exceptions = HashMapping()  # 假设 HashMapping 类似字典结构

    def add_exception(self, func_name_with_args, exception):
        self._exceptions[func_name_with_args] = exception

    def has_exception(self):
        return bool(self._exceptions)

    def __str__(self):
        return str(self._exceptions)

    def __len__(self):
        return len(self._exceptions)

    def items(self):
        return self._exceptions.items()

    def keys(self):
        return self._exceptions.keys()

    def values(self):
        return self._exceptions.values()


class MultiThreadMixin:
    @staticmethod
    def execute(
        func_name: Callable[..., Any],
        args_list: Optional[List[Any]] = None,
        kwargs_list: Optional[List[Dict[str, Any]]] = None,
        check_result_callback: Optional[Callable[..., Any]] = None,
        raise_exception: bool = False,
        thread_pool_size: int = 10,
        timeout: int = 180,
    ) -> Tuple[HashMapping, MultipleException]:
        result_dict = HashMapping()
        multi_exception = MultipleException()

        with ThreadPoolExecutor(max_workers=thread_pool_size) as executor:
            future_dict = {}

            args_list_ = args_list or []
            # Handle single parameter case
            args_list_ = [(arg,) if not isinstance(arg, tuple) else arg for arg in args_list_]
            kwargs_list_ = kwargs_list or []

            max_length = max(len(args_list_), len(kwargs_list_))
            # Pad args_list with empty tuples if shorter
            args_list_padded = args_list_ + [()] * (max_length - len(args_list_))
            # Pad kwargs_list with empty dicts if shorter
            kwargs_list_padded = kwargs_list_ + [{}] * (max_length - len(kwargs_list_))

            if args_list_padded and kwargs_list_padded:
                zip_pair: Iterator[Tuple[Tuple[Any, ...], Dict[str, Any]]] = zip(args_list_padded, kwargs_list_padded)
            else:
                zip_pair = iter([(tuple(), {})])

            for args, kwargs in zip_pair:
                future_dict.update({executor.submit(func_name, *args, **kwargs): (func_name, args, kwargs)})

            for future in concurrent.futures.as_completed(future_dict, timeout=timeout):
                func_name_with_args = future_dict[future]
                try:
                    result = future.result()
                    if check_result_callback:
                        callback_result = check_result_callback(result)
                        if isinstance(callback_result, Exception):
                            raise callback_result

                        if callback_result is not None:
                            result = callback_result
                except Exception as exc:  # pylint: disable=broad-exception-caught
                    func_repr = func_name.__name__ if isinstance(func_name, FunctionType) else str(func_name)
                    args_repr = [str(arg) for arg in func_name_with_args[1]]  # args part
                    kwargs_repr = [f"{k}={v}" for k, v in func_name_with_args[2].items()]  # kwargs part
                    arg_str = ",".join(args_repr + kwargs_repr)

                    LOG.error("Run %s(%s) failed with error: %s", func_repr, arg_str, exc)

                    multi_exception.add_exception(func_name_with_args, exc)
                else:
                    result_dict[func_name_with_args] = result

        if raise_exception and multi_exception.has_exception():
            raise multi_exception

        return result_dict, multi_exception
