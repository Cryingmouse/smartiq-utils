import unittest

from ddt import data
from ddt import ddt
from ddt import unpack

from smartiq_utils.ip_pool import InvalidIPAddressError
from smartiq_utils.ip_pool import InvalidIPAddressRangeError
from smartiq_utils.ip_pool import InvalidIPVersionError
from smartiq_utils.ip_pool import InvalidNetworkError
from smartiq_utils.ip_pool import IPPool
from smartiq_utils.ip_pool import NotInAvailableIPPoolError
from smartiq_utils.ip_pool import NotInUsedIPsError


@ddt
class TestIPPool(unittest.TestCase):

    @data(
        ("192.168.1.1", "192.168.1.1/24"),
        ("192.168.1.1-192.168.1.10", "192.168.1.1/24-192.168.1.10/24"),
        (
            "192.168.1.1-192.168.1.10,192.168.1.20-192.168.1.30",
            "192.168.1.1/24-192.168.1.10/24,192.168.1.20/24-192.168.1.30/24",
        ),
        ("2001:db8::1-2001:db8::10", "2001:db8::1/64-2001:db8::10/64"),
        ("192.168.1.1/23-192.168.1.10/23", "192.168.1.1/23-192.168.1.10/23"),
        ("10.0.0.1/8-10.0.0.10/8", "10.0.0.1/8-10.0.0.10/8"),
        ("172.16.0.1/16-172.16.0.100/16", "172.16.0.1/16-172.16.0.100/16"),
    )
    @unpack
    def test_init_valid_inputs(self, input_str, expected_output):
        pool = IPPool(input_str)
        self.assertEqual(str(pool), expected_output)

    @data(
        ("192.168.1.1,2001:db8::1", InvalidIPVersionError),
        ("192.168.1.1,192.168.2.1", InvalidNetworkError),
        ("192.168.1.1-192.168.1.300", InvalidIPAddressError),
        ("192.168.1.10-192.168.1.1", InvalidIPAddressRangeError),
        ("192.168.1.1/24-192.168.1.10/23", InvalidIPAddressRangeError),
        ("not_an_ip", InvalidIPAddressError),
        ("192.168.1.1-not_an_ip", InvalidIPAddressError),
    )
    @unpack
    def test_init_invalid_inputs(self, input_str, expected_exception):
        with self.assertRaises(expected_exception):
            IPPool(input_str)

    @data(
        ("192.168.1.1-192.168.1.3", ["192.168.1.1/24", "192.168.1.2/24", "192.168.1.3/24"]),
        ("10.0.0.1/8-10.0.0.3/8", ["10.0.0.1/8", "10.0.0.2/8", "10.0.0.3/8"]),
        ("172.16.0.1/16-172.16.0.3/16", ["172.16.0.1/16", "172.16.0.2/16", "172.16.0.3/16"]),
    )
    @unpack
    def test_allocate_ip(self, input_str, expected_ips):
        pool = IPPool(input_str)
        allocated_ips = [str(pool.allocate_ip()) for _ in range(len(expected_ips))]
        self.assertEqual(allocated_ips, expected_ips)
        with self.assertRaises(ValueError):
            pool.allocate_ip()

    @data(
        ("192.168.1.1-192.168.1.10", ["192.168.1.5", "192.168.1.6"]),
        ("10.0.0.1/8-10.0.0.10/8", ["10.0.0.3", "10.0.0.4"]),
        ("172.16.0.1/16-172.16.0.100/16", ["172.16.0.50", "172.16.0.51"]),
    )
    @unpack
    def test_set_used_ips(self, input_str, used_ips):
        pool = IPPool(input_str)
        pool.set_used_ips(used_ips)
        for ip in used_ips:
            self.assertTrue(pool.is_in_used_ips(ip))
            self.assertFalse(pool.is_in_available_ip_pool(ip))

    @data(
        ("192.168.1.1-192.168.1.10", ["192.168.1.20"]),
        ("10.0.0.1/8-10.0.0.10/8", ["10.0.0.11"]),
        ("172.16.0.1/16-172.16.0.100/16", ["172.16.0.101"]),
    )
    @unpack
    def test_set_used_ips_invalid(self, input_str, invalid_ips):
        pool = IPPool(input_str)
        with self.assertRaises(NotInAvailableIPPoolError):
            pool.set_used_ips(invalid_ips)

    @data(
        ("192.168.1.1-192.168.1.10", ["192.168.1.5", "192.168.1.6"], ["192.168.1.5"]),
        ("10.0.0.1/8-10.0.0.10/8", ["10.0.0.3", "10.0.0.4"], ["10.0.0.3"]),
        ("172.16.0.1/16-172.16.0.100/16", ["172.16.0.50", "172.16.0.51"], ["172.16.0.50"]),
    )
    @unpack
    def test_unset_used_ips(self, input_str, set_ips, unset_ips):
        pool = IPPool(input_str)
        pool.set_used_ips(set_ips)
        pool.unset_used_ips(unset_ips)
        for ip in unset_ips:
            self.assertFalse(pool.is_in_used_ips(ip))
            self.assertTrue(pool.is_in_available_ip_pool(ip))
        for ip in set(set_ips) - set(unset_ips):
            self.assertTrue(pool.is_in_used_ips(ip))

    @data(
        ("192.168.1.1-192.168.1.10", ["192.168.1.20"]),
        ("10.0.0.1/8-10.0.0.10/8", ["10.0.0.11"]),
        ("172.16.0.1/16-172.16.0.100/16", ["172.16.0.101"]),
    )
    @unpack
    def test_unset_used_ips_invalid(self, input_str, invalid_ips):
        pool = IPPool(input_str)
        with self.assertRaises(NotInUsedIPsError):
            pool.unset_used_ips(invalid_ips)

    @data(
        ("192.168.1.1-192.168.1.3", ["192.168.1.1/24", "192.168.1.2/24", "192.168.1.3/24"]),
        ("10.0.0.1/8-10.0.0.3/8", ["10.0.0.1/8", "10.0.0.2/8", "10.0.0.3/8"]),
        ("172.16.0.1/16-172.16.0.3/16", ["172.16.0.1/16", "172.16.0.2/16", "172.16.0.3/16"]),
    )
    @unpack
    def test_list_available_ip(self, input_str, expected_ips):
        pool = IPPool(input_str)
        self.assertEqual(pool.list_available_ip(is_string=True), expected_ips)

    @data(
        ("192.168.1.1-192.168.1.10", "192.168.1.5", True),
        ("192.168.1.1-192.168.1.10", "192.168.1.20", False),
        ("10.0.0.1/8-10.0.0.10/8", "10.0.0.5", True),
        ("10.0.0.1/8-10.0.0.10/8", "10.0.0.11", False),
        ("172.16.0.1/16-172.16.0.100/16", "172.16.0.50", True),
        ("172.16.0.1/16-172.16.0.100/16", "172.16.0.101", False),
    )
    @unpack
    def test_contains(self, input_str, test_ip, expected):
        pool = IPPool(input_str)
        self.assertEqual(test_ip in pool, expected)

    def test_eq(self):
        pool1 = IPPool("192.168.1.1-192.168.1.10")
        pool2 = IPPool("192.168.1.1-192.168.1.10")
        pool3 = IPPool("192.168.1.1-192.168.1.5")
        self.assertEqual(pool1, pool2)
        self.assertNotEqual(pool1, pool3)


if __name__ == "__main__":
    unittest.main()
