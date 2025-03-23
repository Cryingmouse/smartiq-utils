from enum import IntEnum


class AliasIntEnum(IntEnum):
    __output_mapping__: dict["AliasIntEnum", str] = {}

    @property
    def alias(self):
        return self.__output_mapping__.get(self, self.name.lower())  # pylint: disable=no-member
