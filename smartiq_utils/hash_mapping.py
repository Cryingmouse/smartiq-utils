import hashlib
import logging
from collections.abc import MutableMapping
from typing import Dict
from typing import Union

LOG = logging.getLogger()


def hash_complex_data(data):
    def convert(obj):
        if isinstance(obj, dict):
            return tuple(sorted((convert(k), convert(v)) for k, v in obj.items()))
        if isinstance(obj, (list, tuple)):
            return tuple(convert(item) for item in obj)
        return hash(obj)

    converted_data = convert(data)
    return hashlib.sha256(str(converted_data).encode()).hexdigest()


class HashMapping(MutableMapping):
    """A mapping that internally stores keys by their identity hash_complex_data(key).

    Keys can be ANYTHING, even non-hashable objects.
    Stores strong references to all keys and values.
    When determining if IdMappings are equal, keys are compared by identity, but values are compared by ==.
    Warning: key1 == key2 does NOT imply hash_complex_data(key1) == hash_complex_data(key2), which may be confusing if
    your keys are e.g. ints.
    """

    def __init__(self, *args, **kwargs):
        self.data = {}
        self.update(*args, **kwargs)

    def __getitem__(self, item):
        try:
            _, val = self.data[hash_complex_data(item)]
        except KeyError as exc:
            raise KeyError(item) from exc
        return val

    def __setitem__(self, key, value):
        self.data[hash_complex_data(key)] = (key, value)

    def __delitem__(self, key):
        try:
            del self.data[hash_complex_data(key)]
        except KeyError as exc:
            raise KeyError(key) from exc

    def __iter__(self):
        for key, _ in self.data.values():
            yield key

    def __len__(self):
        return len(self.data)

    def __eq__(self, other: object):
        if not isinstance(other, HashMapping):
            return False
        if len(self) != len(other):
            return False
        for key, val in self.data.values():
            try:
                if other[key] != val:
                    return False
            except KeyError:
                return False
        return True

    def equal_keys(self, other: Union["HashMapping", Dict]):
        if not isinstance(other, HashMapping):
            return self.keys() == other.keys()
        return self.data.keys() == other.data.keys()

    def clear(self) -> None:
        self.data.clear()
