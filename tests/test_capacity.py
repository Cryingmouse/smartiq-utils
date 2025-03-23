import unittest

from smartiq_utils.capacity import capacity_conversion
from smartiq_utils.capacity import compare_capacity


class TestCapacityConversion(unittest.TestCase):
    def test_string_input_with_unit(self):
        # 测试带单位字符串解析（标准单位）
        self.assertEqual(capacity_conversion("10MB", target_unit="B"), 10_000_000)
        # 测试带单位字符串解析（非标准单位）
        self.assertEqual(capacity_conversion("10MB", is_non_standard=True, target_unit="B"), 10 * 1024**2)

    def test_string_input_without_unit(self):
        # 测试不带单位的字符串，使用指定单位
        self.assertEqual(capacity_conversion("1048576", unit="MiB", target_unit="GiB"), 1024)

    def test_integer_input(self):
        # 测试整数输入转换
        self.assertEqual(capacity_conversion(1, unit="GiB", target_unit="MiB"), 1024)

    def test_float_input(self):
        # 测试浮点数输入转换（非标准单位）
        result = capacity_conversion(2.5, unit="GB", target_unit="MiB", is_non_standard=True)
        self.assertEqual(result, 2560)

    def test_non_standard_conversion(self):
        # 测试非标准单位转换（MB -> MiB）
        self.assertEqual(capacity_conversion("7.2 TB", is_non_standard=True, target_unit="B"), int(7.2 * 1024**4))

    def test_fractional_result(self):
        # 测试返回浮点数并四舍五入
        self.assertEqual(capacity_conversion(1500, unit="B", target_unit="KiB"), 1.46)

    def test_invalid_unit(self):
        # 测试无效单位抛出异常
        with self.assertRaises(KeyError):
            capacity_conversion(100, unit="XX", target_unit="B")

    def test_zero_cases(self):
        # 直接0输入
        self.assertEqual(capacity_conversion(0, target_unit="TB"), 0)

        # 计算结果精确为0
        self.assertEqual(capacity_conversion(1024, unit="B", target_unit="KiB"), 1)  # 1024B=1KiB

        # 四舍五入后为0.00的情况
        self.assertEqual(capacity_conversion(500, unit="B", target_unit="KiB"), 0.49)  # 500/1024=0.48828125
        self.assertEqual(capacity_conversion(1, unit="MiB", target_unit="GiB"), 0)  # 1/1024=0.0009765625 → 0.00
        self.assertEqual(
            capacity_conversion(0.00049, unit="TiB", target_unit="PiB"), 0
        )  # 0.00049*1024=0.50176 PiB → 0.50
        self.assertEqual(
            capacity_conversion(0.004, unit="KiB", target_unit="MiB"), 0
        )  # 0.004/1024=0.00000390625 → 0.00


class TestCompareCapacity(unittest.TestCase):
    def test_mib_range_true(self):
        # 在MiB范围内且差异<=0.5
        self.assertTrue(compare_capacity(1 * 1024**2, 1.4 * 1024**2))

    def test_mib_range_false(self):
        # 在MiB范围内且差异>0.5
        self.assertFalse(compare_capacity(1 * 1024**2, 1.6 * 1024**2))

    def test_gib_range_true(self):
        # 在GiB范围内且差异<=0.5
        self.assertTrue(compare_capacity(2 * 1024**3, 2.4 * 1024**3))

    def test_gib_range_false(self):
        # 在GiB范围内且差异>0.5
        self.assertFalse(compare_capacity(2 * 1024**3, 2.6 * 1024**3))

    def test_tib_range_true(self):
        # 在TiB范围内且差异<=0.5
        self.assertTrue(compare_capacity(3 * 1024**4, 3.4 * 1024**4))

    def test_tib_range_false(self):
        # 在TiB范围内且差异>0.5
        self.assertFalse(compare_capacity(3 * 1024**4, 3.6 * 1024**4))

    def test_boundary_equal(self):
        # 容量完全相等
        self.assertTrue(compare_capacity(5 * 1024**3, 5 * 1024**3))

    def test_boundary_exact_half(self):
        # 差异正好0.5单位（GiB）
        self.assertTrue(compare_capacity(1 * 1024**3, 1.5 * 1024**3))
