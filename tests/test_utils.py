import unittest
from smartiq_utils.utils import flatten_list
from smartiq_utils.utils import camel_to_snake


class TestFlattenList(unittest.TestCase):
    def test_basic_flattening(self):
        """Test basic list flattening with single elements, sub-lists, and None"""
        input_list = [1, [2, 3], None, "a"]
        expected = [1, 2, 3, "a"]
        self.assertEqual(flatten_list(input_list), expected)

    def test_all_none_elements(self):
        """Test list containing only None values"""
        self.assertEqual(flatten_list([None, None, None]), [])

    def test_empty_input(self):
        """Test empty list input"""
        self.assertEqual(flatten_list([]), [])

    def test_deeply_nested_lists(self):
        """Test multi-level nested lists (only one level is flattened)"""
        input_list = [[[1, 2], 3], [4, [5]]]
        expected = [[1, 2], 3, 4, [5]]  # Only one level flattened
        self.assertEqual(flatten_list(input_list), expected)

    def test_mixed_non_list_items(self):
        """Test mixed non-list elements (strings, numbers, objects)"""

        class Dummy:
            pass

        obj = Dummy()
        input_list = [123, "hello", obj, [True]]
        expected = [123, "hello", obj, True]
        self.assertEqual(flatten_list(input_list), expected)

    def test_preserve_order(self):
        """Test output order preservation matching input order"""
        input_list = [3, [1, 4], None, [2]]
        expected = [3, 1, 4, 2]
        self.assertEqual(flatten_list(input_list), expected)

    def test_non_list_containers(self):
        """Test non-list iterables (tuples, sets) are not flattened"""
        # The function is designed to flatten only lists; other containers remain intact
        input_list = [(1, 2), {"a", "b"}]
        expected = [(1, 2), {"a", "b"}]
        self.assertEqual(flatten_list(input_list), expected)


class TestCamelToSnake(unittest.TestCase):
    def setUp(self):
        self.converter = camel_to_snake

    def test_simple_camel_case(self):
        self.assertEqual(self.converter("CamelCase"), "camel_case")

    def test_all_caps(self):
        self.assertEqual(self.converter("HTTPResponse"), "http_response")

    def test_numbers_in_string(self):
        self.assertEqual(self.converter("CamelCase2Example"), "camel_case2_example")

    def test_multiple_uppercase_groups(self):
        self.assertEqual(self.converter("PDFFileParser"), "pdf_file_parser")

    def test_single_word(self):
        self.assertEqual(self.converter("Hello"), "hello")

    def test_empty_string(self):
        self.assertEqual(self.converter(""), "")

    def test_mixed_case_numbers(self):
        self.assertEqual(self.converter("XML2JSON"), "xml2_json")

    def test_consecutive_uppercase(self):
        self.assertEqual(self.converter("ABCDConverter"), "abcd_converter")
