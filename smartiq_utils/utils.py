import re
from itertools import chain


def flatten_list(elements: list) -> list:
    """Flatten a list containing items that could be single elements, sub-lists, or None.

    Args:
        elements (list): A list containing elements that may be single items, sub-lists, or None.
            Example: [1, [2, 3], None, "a"]

    Returns:
        list: A flattened list with no None values. Example: [1, 2, 3, "a"]
    """
    return list(
        chain.from_iterable(item if isinstance(item, list) else [item] for item in elements if item is not None)
    )


def camel_to_snake(camel_str: str) -> str:
    # Handle cases with consecutive uppercase letters followed by a lowercase letter
    # Example: "HTTPResponse" -> "HTTP_Response"
    snake_str = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", camel_str)

    # Insert underscore between lowercase/number and uppercase letters
    # Example: "CamelCase" -> "Camel_Case", "Case2Example" -> "Case2_Example"
    snake_str = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", snake_str)

    # Convert to lowercase for proper snake_case format
    return snake_str.lower()
