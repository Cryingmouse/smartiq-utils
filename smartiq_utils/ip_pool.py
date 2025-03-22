#
#  Copyright (c) 2023-present Lenovo. All right reserved.
#  Confidential and Proprietary
#

import ipaddress
import logging
from ipaddress import IPv4Interface
from ipaddress import IPv6Interface
from typing import List
from typing import Tuple
from typing import TypeVar
from typing import Union

LOG = logging.getLogger()


IPInterfaceType = TypeVar("IPInterfaceType", IPv4Interface, IPv6Interface)  # pylint: disable=invalid-name
IPPair = Tuple[IPInterfaceType, IPInterfaceType]
IPPairList = List[IPPair]


class IPPoolException(Exception):
    """Base exception for IP Pool related errors."""


class InvalidIPAddressError(IPPoolException):
    pass


class InvalidIPAddressRangeError(IPPoolException):
    pass


class InvalidIPVersionError(IPPoolException):
    pass


class InvalidNetworkError(IPPoolException):
    pass


class IPNotInListError(Exception):
    def __init__(self, ip: Union[IPv4Interface, IPv6Interface], ip_list: IPPairList) -> None:
        self.ip: Union[IPv4Interface, IPv6Interface] = ip
        self.ip_list: IPPairList = ip_list


class NotInAvailableIPPoolError(IPPoolException):
    def __init__(self, ip: Union[IPv4Interface, IPv6Interface], ip_list: IPPairList) -> None:
        self.ip: Union[IPv4Interface, IPv6Interface] = ip
        self.ip_list: IPPairList = ip_list


class NotInUsedIPsError(IPPoolException):
    def __init__(self, ip: Union[IPv4Interface, IPv6Interface], ip_list: IPPairList) -> None:
        self.ip: Union[IPv4Interface, IPv6Interface] = ip
        self.ip_list: IPPairList = ip_list


class TooManyIPsToExtendError(IPPoolException):
    def __init__(self, ip_pool) -> None:
        self.ip_pool = ip_pool


def sort_and_merge_ip_ranges(ranges: IPPairList) -> IPPairList:
    """Sort and merge a list of two-element tuples representing IP ranges.

    Args:
        ranges (IPPairList): List of IP ranges to be sorted
        and merged.

    Returns:
        IPPairList: Sorted and merged list of IP ranges.
    """
    if not ranges:
        return []

    sorted_ranges = sorted(ranges, key=lambda x: (x[0].ip, x[1].ip))
    merged = [sorted_ranges[0]]

    for current_start, current_end in sorted_ranges[1:]:
        last_start, last_end = merged[-1]
        if current_start.ip <= last_end.ip + 1:
            merged[-1] = (last_start, max(last_end, current_end))
        else:
            merged.append((current_start, current_end))

    return merged


def remove_ip_from_ranges(ranges: IPPairList, interface: Union[IPv4Interface, IPv6Interface]) -> IPPairList:
    """Remove an IP from a list of IP ranges.

    Args:
        ranges (IPPairList): List of IP ranges.
        interface (Union[IPv4Interface, IPv6Interface]): IP to remove.

    Returns:
        IPPairList: Updated list of IP ranges.

    Raises:
        IPNotInList: If the IP is not found in any range.
    """
    new_ranges = []
    ip_found = False

    for start, end in ranges:
        if start.ip <= interface.ip <= end.ip:
            ip_found = True
            if start.ip < interface.ip:
                new_ranges.append((start, ipaddress.ip_interface(f"{interface.ip - 1}/{start.network.prefixlen}")))
            if end.ip > interface.ip:
                new_ranges.append((ipaddress.ip_interface(f"{interface.ip + 1}/{start.network.prefixlen}"), end))
        else:
            new_ranges.append((start, end))

    if not ip_found:
        raise IPNotInListError(ip=interface, ip_list=ranges)

    return new_ranges


def is_in_ranges(ip: Union[IPv4Interface, IPv6Interface], ranges: IPPairList) -> bool:
    """Check if an IP is in a list of IP ranges.

    Args:
        ip (Union[IPv4Interface, IPv6Interface]): IP to check.
        ranges (IPPairList): List of IP ranges.

    Returns:
        bool: True if the IP is in any range, False otherwise.
    """
    ip_type = type(ip.ip)

    return any(
        start.ip <= ip.ip <= end.ip  # type: ignore
        for start, end in ranges
        if isinstance(start.ip, ip_type) and isinstance(end.ip, ip_type)
    )


class IPPool:
    def __init__(self, ip_pool: str, sep: str = ",", ipv4_mask: int = 24, ipv6_mask: int = 64):
        """
        Args:
            ip_pool (str): IP pool string in the format of "start_ip-end_ip".
            sep (str, optional): Separator for IP range. Defaults to ",".
            ipv4_mask (int, optional): Default subnet mask for IPv4 address. Defaults to 24.
            ipv6_mask (int, optional): Default subnet mask for IPv6 address. Defaults to 64.
        """

        self.sep = sep

        # Declare self.network and self.version first,
        # because it will be updated in the function self._generate_ip_ranges()
        self.network = None
        self.version = None

        self.ipv4_mask = ipv4_mask
        self.ipv6_mask = ipv6_mask

        self.available_ip_pool: IPPairList = self._generate_ip_ranges(ip_pool)
        self.used_ips: IPPairList = []

    def allocate_ip(self) -> Union[IPv4Interface, IPv6Interface]:
        """Allocate an IP address from the available IP pool.

        Returns:
            Union[IPv4Interface, IPv6Interface]: Allocated IP address.

        Raises:
            ValueError: If no available IP addresses are found.
        """
        if not self.available_ip_pool:
            raise ValueError("No available IP addresses in the pool.")

        start, end = self.available_ip_pool.pop(0)
        self.used_ips.append((start, start))
        self.used_ips = sort_and_merge_ip_ranges(self.used_ips)

        if start != end:
            next_ip = ipaddress.ip_interface(f"{start.ip + 1}/{start.network.prefixlen}")
            self.available_ip_pool.insert(0, (next_ip, end))  # type: ignore

        return start  # type: ignore

    def set_used_ips(self, used_ips: List[str]):
        """Set used IP addresses and remove them from the available pool.

        Args:
            used_ips (List[str]): List of used IP addresses.

        Raises:
            IPNotInListError: If an invalid IP address is provided.
            NotInAvailableIPPoolError: If an IP is not in the available pool.
        """
        for ip in used_ips:
            ip_interface = self._update_netmask(ip)
            try:
                self.available_ip_pool = remove_ip_from_ranges(self.available_ip_pool, ip_interface)
            except IPNotInListError as e:
                raise NotInAvailableIPPoolError(ip=e.ip, ip_list=e.ip_list) from e
            self.used_ips.append((ip_interface, ip_interface))

        self.used_ips = sort_and_merge_ip_ranges(self.used_ips)

    def unset_used_ips(self, used_ips: List[Union[str, IPv4Interface, IPv6Interface]]):
        """Recycle used IP addresses back to the available pool.

        Args:
            used_ips (List[Union[str, IPv4Interface, IPv6Interface]]): List of IP addresses to recycle.

        Raises:
            InvalidIPAddress: If an invalid IP address is provided.
            IPNotInList: If an IP is not in the used IPs list.
        """
        for ip in used_ips:
            ip_interface = ip if isinstance(ip, (IPv4Interface, IPv6Interface)) else self._update_netmask(ip)
            try:
                self.used_ips = remove_ip_from_ranges(self.used_ips, ip_interface)
            except IPNotInListError as e:
                raise NotInUsedIPsError(ip=e.ip, ip_list=e.ip_list) from e
            self.available_ip_pool.append((ip_interface, ip_interface))  # type: ignore

        self.available_ip_pool = sort_and_merge_ip_ranges(self.available_ip_pool)

    def cleanup_used_ips(self):
        """Cleanup used IPs by recycling them back to the available pool."""
        self.unset_used_ips(self.list_used_ips())

    def list_available_ip(
        self, include_netmask=True, is_string: bool = False
    ) -> List[Union[str, IPv4Interface, IPv6Interface]]:
        """Get a list of all available IPs in the available IP pool.

        Args:
            include_netmask (bool, optional): Whether to include the netmask in the output. Defaults to True.
            is_string (bool, optional): Whether to include the string in the output. Defaults to False.

        Returns:
            List[Union[str, IPv4Interface, IPv6Interface]]: List of available IP addresses.

        Raises:
            TooManyIPsToExtendError: If there are too many IPs to extend.
        """
        return self._list_ips(self.available_ip_pool, include_netmask=include_netmask, is_string=is_string)

    def list_used_ips(
        self, include_netmask=True, is_string: bool = False
    ) -> List[Union[str, IPv4Interface, IPv6Interface]]:
        """Get a list of all used IPs.

        Args:
            include_netmask (bool, optional): Whether to include the netmask in the output. Defaults to True.
            is_string (bool, optional): Whether to include the string in the output. Defaults to False.

        Returns:
            List[Union[str, IPv4Interface, IPv6Interface]]: List of used IP addresses.

        Raises:
            TooManyIPsToExtendError: If there are too many IPs to extend.
        """
        return self._list_ips(self.used_ips, include_netmask=include_netmask, is_string=is_string)

    def _list_ips(
        self, ip_tuple_list: IPPairList, include_netmask: bool = True, is_string: bool = False
    ) -> List[Union[str, IPv4Interface, IPv6Interface]]:
        """Get a list of IPs.

        Args:
            ip_tuple_list (list): List of IP tuples, e.g. self.used_ips or self.available_ip_pool.
            include_netmask (bool, optional): Whether to include the netmask in the output. Defaults to True.
            is_string (bool, optional): Whether to include the string in the output. Defaults to False.

        Returns:
            List[Union[str, IPv4Interface, IPv6Interface]]: List of IP addresses.

        Raises:
            TooManyIPsToExtendError: If there are too many IPs to extend.
        """
        ips: List[Union[str, IPv4Interface, IPv6Interface]] = []
        for start, end in ip_tuple_list:
            current_ip = start.ip
            while current_ip <= end.ip:
                if len(ips) > 65536:
                    raise TooManyIPsToExtendError(ip_pool=self)
                ip_str = f"{current_ip}/{start.network.prefixlen}" if include_netmask else str(current_ip)
                ips.append(ip_str if is_string else ipaddress.ip_interface(ip_str))
                current_ip += 1
        return ips

    def is_in_available_ip_pool(self, ip: str) -> bool:
        """Check if an IP is in the available IP pool.

        Args:
            ip (str): IP address to check.

        Returns:
            bool: True if the IP is in the available pool, False otherwise.
        """
        return is_in_ranges(self._update_netmask(ip), self.available_ip_pool)

    def is_in_used_ips(self, ip: str) -> bool:
        """Check if an IP is in the used IPs list.

        Args:
            ip (str): IP address to check.

        Returns:
            bool: True if the IP is in the used IPs list, False otherwise.
        """
        return is_in_ranges(self._update_netmask(ip), self.used_ips)

    def _generate_ip_ranges(self, ip_pool: str) -> IPPairList:
        """Generate a list of IP ranges from a given IP pool string.

        Args:
            ip_pool (str): IP pool string.

        Returns:
            List[Union[Tuple[IPv4Interface, IPv4Interface], Tuple[IPv6Interface, IPv6Interface]]]: List of IP ranges.

        Raises:
            InvalidIPVersionError: If IP versions are mixed in the pool.
            InvalidNetworkError: If different subnets are mixed in the pool.
        """
        ip_ranges = ip_pool.split(self.sep)
        result = []

        for ip_range in ip_ranges:
            start, end = self._parse_ip_range(ip_range)
            if self.version is None or self.network is None:
                self.version = start.version
                self.network = start.network

            if start.version != self.version:
                raise InvalidIPVersionError(f"IP pool {ip_pool} contains mixed IP versions.")

            if start.network != self.network:
                raise InvalidNetworkError(f"IP pool {ip_pool} contains different subnets.")

            result.append((start, end))

        return sort_and_merge_ip_ranges(result)

    def _parse_ip_range(self, ip_range: str) -> IPPair:
        """Parse an IP range string into start and end IP addresses.

        Args:
            ip_range (str): IP range string.

        Returns:
            Tuple[ipaddress.ip_interface, ipaddress.ip_interface]: Start and end IP addresses.

        Raises:
            InvalidIPAddressRangeError: If the IP range is invalid.
        """
        if "-" in ip_range:
            start_ip, end_ip = map(str.strip, ip_range.split("-"))
            start_interface = self._update_netmask(start_ip)
            end_interface = self._update_netmask(end_ip)

            if start_interface.version != end_interface.version:
                raise InvalidIPAddressRangeError(f"IP range '{start_ip}-{end_ip}' contains different IP versions.")

            if start_interface.network != end_interface.network:
                raise InvalidIPAddressRangeError(f"IP range '{start_ip}-{end_ip}' contains different networks.")

            if start_interface > end_interface:  # type: ignore
                raise InvalidIPAddressRangeError(f"IP range '{start_ip}-{end_ip}': start IP is greater than end IP.")

            return start_interface, end_interface

        ip = self._update_netmask(ip_range.strip())
        return ip, ip

    def _update_netmask(self, ip: str) -> Union[IPv4Interface, IPv6Interface]:
        """Update the netmask of an IP address.

        Args:
            ip (str): IP address in CIDR notation or without mask.

        Returns:
            ipaddress.ip_interface: Updated IP interface with the new netmask.

        Raises:
            InvalidIPAddressError: If the input IP address is invalid.
        """
        try:
            ip_iface = ipaddress.ip_interface(ip)
        except ValueError as e:
            LOG.error("Invalid IP address %s: %s", ip, e)
            raise InvalidIPAddressError(f"Invalid IP address {ip}") from e

        if "/" in ip:  # Check if the interface already contains a subnet mask
            return ip_iface

        if ip_iface.version == 4:
            LOG.info("Input IP %s does not have a subnet mask. Default IPv4 mask is applied.", ip)
            return ipaddress.ip_interface(f"{ip}/{self.ipv4_mask}")

        LOG.info("Input IP %s does not have a subnet mask. Default IPv6 mask is applied.", ip)
        return ipaddress.ip_interface(f"{ip}/{self.ipv6_mask}")

    def __contains__(self, item: Union[str, IPv4Interface, IPv6Interface]) -> bool:
        """Check if an IP address is within the IP pool (available or used).

        Args:
            item (str): IP address to check.

        Returns:
            bool: True if the IP address is within the pool, False otherwise.

        Raises:
            InvalidIPAddressError: If the input IP address is invalid.
        """
        if isinstance(item, str):
            ip_interface = self._update_netmask(item)
        elif isinstance(item, (IPv4Interface, IPv6Interface)):
            ip_interface = item
        else:
            raise InvalidIPAddressError(f"Invalid IP address {item}")

        return is_in_ranges(ip_interface, self.available_ip_pool + self.used_ips)

    def __eq__(self, other) -> bool:
        """Check if two IPPool objects are equal.

        Args:
            other (IPPool): Another IPPool object to compare.

        Returns:
            bool: True if the IPPool objects are equal, False otherwise.
        """
        return (
            isinstance(other, IPPool)
            and self.available_ip_pool == other.available_ip_pool
            and self.used_ips == other.used_ips
        )

    def __repr__(self) -> str:
        """String representation of the IPPool object.

        Returns:
            str: String representation of the IP pool.
        """
        ip_pool = sort_and_merge_ip_ranges(self.available_ip_pool + self.used_ips)
        return ",".join(str(start) if start == end else f"{start}-{end}" for start, end in ip_pool)

    def to_string(self) -> str:
        """String representation of the IPPool object for external use.

        Returns:
            str: String representation of the IP pool in a format suitable for external use.
        """
        ip_pool = sort_and_merge_ip_ranges(self.available_ip_pool + self.used_ips)
        return ",".join(str(start.ip) if start == end else f"{start.ip}-{end.ip}" for start, end in ip_pool)
