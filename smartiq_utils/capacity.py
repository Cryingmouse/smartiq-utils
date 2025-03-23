import re
from enum import IntEnum
from typing import Union


class CapacityUnit(IntEnum):
    B = 1
    KB = 10**3
    MB = 10**6
    GB = 10**9
    TB = 10**12
    PB = 10**15
    KiB = 2**10  # pylint: disable=invalid-name
    MiB = 2**20  # pylint: disable=invalid-name
    GiB = 2**30  # pylint: disable=invalid-name
    TiB = 2**40  # pylint: disable=invalid-name
    PiB = 2**50  # pylint: disable=invalid-name


class NonStandardCapacityUnit(IntEnum):
    KB = CapacityUnit.KiB.value
    MB = CapacityUnit.MiB.value
    GB = CapacityUnit.GiB.value
    TB = CapacityUnit.TiB.value
    PB = CapacityUnit.PiB.value


def capacity_conversion(
    capacity: Union[str, int, float], unit: str = "B", target_unit: str = "B", is_non_standard=False
) -> Union[int, float]:
    # Parse the input capacity string
    if isinstance(capacity, str):
        _capacity = re.search(r"(?P<size>[0-9.]+)\s*(?P<unit>[KMGTP]?i?B)?", capacity)
        assert _capacity, f"{capacity} is an invalid capacity string"

        capacity_group = _capacity.groupdict()
        if capacity_group["unit"]:
            unit = capacity_group["unit"]
        capacity = float(capacity_group["size"])

    # Handle unit conversion
    unit_str = unit
    if is_non_standard and unit_str != CapacityUnit.B.name:
        try:
            unit_enum = NonStandardCapacityUnit[unit_str]
        except KeyError as e:
            raise KeyError(f"Invalid non-standard unit: {unit_str}") from e
    else:
        try:
            unit_enum = CapacityUnit[unit_str]  # type: ignore[assignment]
        except KeyError as e:
            raise KeyError(f"Invalid unit: {unit_str}") from e

    unit_int = unit_enum.value

    try:
        target_unit_enum = CapacityUnit[target_unit]
    except KeyError as e:
        raise KeyError(f"Invalid target unit: {target_unit}") from e

    # Convert to bytes and then calculate the value in the target unit
    byte_size = int(capacity * unit_int)
    target_size = byte_size / target_unit_enum.value

    # Determine the type of the result (integer or float)
    if target_size.is_integer() or target_unit_enum.name == CapacityUnit.B.name:
        result = int(target_size)
    else:
        result = round(target_size, 2)  # type: ignore[assignment]

    return result if result != 0 else 0


def compare_capacity(capacity_a: int, capacity_b: int) -> bool:
    MiB = 1024**2  # pylint: disable=invalid-name
    GiB = 1024**3  # pylint: disable=invalid-name
    TiB = 1024**4  # pylint: disable=invalid-name

    max_capacity = max(capacity_a, capacity_b)
    if max_capacity < GiB:
        unit = MiB
    elif max_capacity < TiB:
        unit = GiB
    else:
        unit = TiB

    converted_a = capacity_a / unit
    converted_b = capacity_b / unit

    return abs(converted_a - converted_b) <= 0.5
