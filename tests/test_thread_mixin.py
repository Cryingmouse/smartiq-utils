import time
import unittest
from unittest.mock import MagicMock

from smartiq_utils.thread_mixin import MultipleException
from smartiq_utils.thread_mixin import MultiThreadMixin


class TestMultiThreadMixin(unittest.TestCase):
    """MultiThreadMixin 单元测试"""

    def test_basic_functionality(self):
        """测试基本任务执行"""

        def dummy_func(x: int) -> int:
            return x * 2

        args_list = [1, 2, 3]
        output, exception = MultiThreadMixin.execute(dummy_func, args_list=args_list, thread_pool_size=2)

        self.assertEqual(len(output), 3)
        self.assertFalse(exception.has_exception())

        for (func, args, _), result in output.items():
            self.assertEqual(dummy_func, func)
            self.assertIn(args[0], args_list)
            self.assertEqual(result, args[0] * 2)

    def test_exception_handling(self):
        """测试异常捕获"""

        def error_func():
            raise ValueError("test error")

        _, exception = MultiThreadMixin.execute(error_func, raise_exception=False)

        self.assertTrue(exception.has_exception())
        self.assertEqual(len(exception), 1)

        for (func, args, _), exception in exception.items():
            self.assertEqual(error_func, func)
            self.assertIsInstance(exception, ValueError)

    def test_raise_exception_flag(self):
        """测试异常抛出开关"""

        def error_func():
            raise RuntimeError("critical error")

        with self.assertRaises(MultipleException):
            MultiThreadMixin.execute(error_func, raise_exception=True)

    def test_argument_padding(self):
        """测试参数自动填充"""
        mock_func = MagicMock(return_value=True)

        args_list = [1, 2]
        kwargs_list = [{"a": 1}, {"b": 2}, {"c": 3}]

        output, _ = MultiThreadMixin.execute(mock_func, args_list=args_list, kwargs_list=kwargs_list)

        # 应取最长列表长度（3）
        self.assertEqual(len(output), 3)
        mock_func.assert_any_call(1, a=1)
        mock_func.assert_any_call(2, b=2)
        mock_func.assert_any_call(*(), c=3)  # 第三个参数应为空tuple + 第三个kwargs

    def test_result_callback(self):
        """测试结果回调处理"""

        def check_result(res: int):
            if res < 0:
                raise ValueError("Negative result")

            return res * 10

        def sample_func(x: int) -> int:
            return x - 5

        args_list = [8, 3]
        output, exception = MultiThreadMixin.execute(
            sample_func, args_list=args_list, check_result_callback=check_result
        )

        for (func, args, _), result in output.items():
            self.assertEqual(sample_func, func)
            self.assertIn(args[0], args_list)
            self.assertEqual(result, (args[0] - 5) * 10)

        self.assertEqual(len(exception), 1)

        for (func, args, _), ex in exception.items():
            self.assertEqual(sample_func, func)
            self.assertIsInstance(ex, ValueError)

    def test_timeout_handling(self):
        """测试超时处理"""

        def long_running():
            time.sleep(2)
            return True

        with self.assertRaises(TimeoutError):
            MultiThreadMixin.execute(long_running, args_list=[()], timeout=1, thread_pool_size=1)

    def test_mixed_success_and_errors(self):
        """测试混合成功/失败场景"""

        def mixed_func(x: int):
            if x % 2 == 0:
                raise ValueError(f"Even {x}")
            return x

        args_list = [1, 2, 3, 4]
        output, exception = MultiThreadMixin.execute(mixed_func, args_list=args_list, raise_exception=False)

        self.assertEqual(len(output), 2)  # 1,3成功
        self.assertEqual(len(exception), 2)  # 2,4失败

    def test_kwargs_handling(self):
        """测试关键字参数处理"""

        def kw_func(a: int, b: int = 0):
            return a + b

        kwargs_list = [{"a": 1, "b": 2}, {"a": 3}, {}]  # 应触发TypeError
        output, exception = MultiThreadMixin.execute(kw_func, kwargs_list=kwargs_list, raise_exception=False)

        for (func, _, kwargs), result in output.items():
            self.assertEqual(kw_func, func)
            self.assertIn(kwargs, kwargs_list)
            self.assertEqual(result, 3)

        for (func, _, kwargs), ex in exception.items():
            self.assertEqual(kw_func, func)
            self.assertIn(kwargs, kwargs_list)
            self.assertIsInstance(ex, TypeError)

    def test_function_representation(self):
        """测试函数名表示"""

        class TestClass:
            def method(self):
                pass

        lambda_func = lambda: None

        # 测试普通函数
        results, _ = MultiThreadMixin.execute(time.sleep, args_list=[(1,)])
        for method, _, _ in results:
            self.assertEqual(str(time.sleep), str(method))

        # 测试类方法
        obj = TestClass()
        results, _ = MultiThreadMixin.execute(obj.method, args_list=[()])
        for method, _, _ in results:
            self.assertEqual(str(obj.method), str(method))

        # 测试lambda
        results, _ = MultiThreadMixin.execute(lambda_func, args_list=[()])
        for method, _, _ in results:
            self.assertEqual(str(lambda_func), str(method))
