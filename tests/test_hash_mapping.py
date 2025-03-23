import unittest

from smartiq_utils.hash_mapping import HashMapping


def _build_func_key(func, args, kwargs) -> tuple:
    """Build a standardized function signature key"""
    return func.__name__, args, tuple(sorted(kwargs.items()))


class TestHashMapping(unittest.TestCase):
    def setUp(self):
        # Basic test data
        self.sample_data = [
            (5, "five"),
            ("test", [1, 2, 3]),
            ({"a": 1}, "dict_key"),
            ([1, 2, 3], "list_key"),
            ((1, 2), "tuple_key"),
        ]

        # Function signature test data
        def func1(a, b):
            pass

        def func2(a, b):
            pass  # Same structure, different names

        self.func_test_cases = [
            (func1, (1, 2), {}, "case1"),
            (func1, (1,), {"b": 2}, "case2"),
            (func1, (1, 3), {}, "case3"),
            (func1, (), {"a": 1, "b": 2}, "case4"),
            (func2, (1, 2), {}, "case5"),
            (func1, (1, 2), {"c": 3}, "case6"),
            (func1, (1, 2), {"b": 4}, "case7"),
        ]

    def test_basic_operations(self):
        hm = HashMapping()

        # Test setting and getting
        for key, value in self.sample_data:
            hm[key] = value
            self.assertEqual(hm[key], value)

        # Verify length
        self.assertEqual(len(hm), len(self.sample_data))

        # Verify iteration
        keys = [key for key, _ in self.sample_data]
        for k in hm:
            self.assertIn(k, keys)

        # Test deletion
        del hm[self.sample_data[0][0]]
        self.assertEqual(len(hm), len(self.sample_data) - 1)
        with self.assertRaises(KeyError):
            _ = hm[self.sample_data[0][0]]

    def test_equality(self):
        hm1 = HashMapping(self.sample_data)
        hm2 = HashMapping(self.sample_data)

        self.assertEqual(hm1, hm2)  # Equal with the same data

        hm2[self.sample_data[0][0]] = "modified"
        self.assertNotEqual(hm1, hm2)  # Not equal after modification

    def test_key_hash_collision(self):
        # Construct keys with hash collisions
        class FakeHash:
            def __init__(self, real_data):
                self.real_data = real_data

            def __hash__(self):
                return 12345

        key1 = FakeHash("data1")
        key2 = FakeHash("data2")

        hm = HashMapping()
        hm[key1] = "first"
        hm[key2] = "second"  # Overwrite the previous value

        self.assertEqual(len(hm), 1)
        self.assertEqual(hm[key1], "second")

    def test_views(self):
        hm = HashMapping(self.sample_data)

        # Verify the items view
        items = list(hm.items())
        self.assertEqual(len(items), len(self.sample_data))
        for (k, v), (expected_k, expected_v) in zip(items, self.sample_data):
            self.assertEqual(k, expected_k)
            self.assertEqual(v, expected_v)

        # Verify the keys view
        self.assertEqual(list(hm.keys()), [k for k, _ in self.sample_data])

        # Verify the values view
        self.assertEqual(list(hm.values()), [v for _, v in self.sample_data])

    def test_function_keys(self):
        hm = HashMapping()

        def normal_func():
            pass

        lambda_func = lambda x: x
        closure_func = (lambda y: lambda: y)(10)

        test_cases = [
            (normal_func, "normal"),
            (lambda_func, "lambda"),
            (closure_func, "closure"),
        ]

        # Store and verify
        for func, value in test_cases:
            hm[func] = value
            self.assertEqual(hm[func], value)

        # Verify different objects with the same code
        def duplicate_func():
            pass  # Same code as normal_func

        hm[duplicate_func] = "dup"
        self.assertEqual(len(hm), len(test_cases) + 1)

    def test_function_signature_keys(self):
        hm = HashMapping()

        # Store function signature keys
        for func, args, kwargs, value in self.func_test_cases:
            key = _build_func_key(func, args, kwargs)
            hm[key] = value

        # Verify the correctness of storage (7 independent keys)
        self.assertEqual(len(hm), 7)

        # Verify different call forms
        key1 = _build_func_key(self.func_test_cases[0][0], (1, 2), {})
        self.assertEqual(hm[key1], "case1")

        key2 = _build_func_key(self.func_test_cases[1][0], (1,), {"b": 2})
        self.assertEqual(hm[key2], "case2")

    def test_parameter_normalization(self):
        hm = HashMapping()

        def sample_func(a, b):
            pass

        # Different parameter forms
        key1 = _build_func_key(sample_func, (1, 2), {})
        key2 = _build_func_key(sample_func, (1,), {"b": 2})
        key3 = _build_func_key(sample_func, (), {"a": 1, "b": 2})

        hm[key1] = "pos"
        hm[key2] = "mixed"
        hm[key3] = "kw"

        self.assertEqual(len(hm), 3)
        self.assertEqual(hm[key1], "pos")

    def test_complex_parameters(self):
        hm = HashMapping()

        def data_processor():
            pass

        # Complex parameter structure
        complex_args = ([1, {"a": 2}], {"b": (3, 4)}, "text", 3.14)
        kwargs = {"config": {"debug": True}}

        key = _build_func_key(data_processor, complex_args, kwargs)
        hm[key] = "complex"

        # Same structure, different instances
        same_key = _build_func_key(
            data_processor,
            ([1, {"a": 2}], {"b": (3, 4)}, "text", 3.14),  # New list instance  # New dictionary instance
            {"config": {"debug": True}},
        )
        self.assertEqual(hm[same_key], "complex")

        # Modify the nested structure
        modified_key = _build_func_key(
            data_processor, ([1, {"a": 3}], {"b": (3, 4)}, "text", 3.14), kwargs  # Modify the internal value
        )
        self.assertNotIn(modified_key, hm)

    def test_empty_parameters(self):
        hm = HashMapping()

        def empty_func():
            pass

        # Empty parameter key
        empty_key = _build_func_key(empty_func, (), {})
        hm[empty_key] = "empty"

        self.assertEqual(hm[empty_key], "empty")
        self.assertEqual(len(hm), 1)

    def test_large_parameters(self):
        hm = HashMapping()

        def big_func():
            pass

        # Large data parameters
        big_args = tuple(range(1000))
        big_kwargs = {f"key{i}": i for i in range(100)}
        key = _build_func_key(big_func, big_args, big_kwargs)

        hm[key] = "big"
        self.assertEqual(hm[key], "big")

    def test_equal_keys(self):
        hm1 = HashMapping([(1, "a"), (2, "b")])
        hm2 = HashMapping([(1, "x"), (2, "y")])
        hm3 = HashMapping([(3, "c")])

        self.assertTrue(hm1.equal_keys(hm2))
        self.assertFalse(hm1.equal_keys(hm3))
        self.assertTrue(hm1.equal_keys({1: None, 2: None}))
        self.assertFalse(hm1.equal_keys({1: None, 3: None}))

    def test_clear(self):
        hm = HashMapping(self.sample_data)
        hm.clear()
        self.assertEqual(len(hm), 0)
