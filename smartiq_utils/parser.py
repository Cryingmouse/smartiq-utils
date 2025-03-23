from abc import ABC
from abc import abstractmethod


class AbstractParser(ABC):
    @abstractmethod
    def read(self, content: str):
        pass

    @abstractmethod
    def write(self, file):
        pass
