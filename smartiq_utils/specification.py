import re
from abc import abstractmethod


class ISpecification:
    """Abstract base class for specifications using the Specification pattern.

    This class provides an interface for building complex specifications
    using logical operations (AND, OR, NOT). It allows combining multiple
    specifications to create more sophisticated matching criteria.

    The Specification pattern helps encapsulate business rules and allows them to be combined using boolean logic.
    """

    def and_specification(self, other: "ISpecification") -> "ISpecification":
        """Combine this specification with another using logical AND.

        Args:
            other (ISpecification): The specification to combine with the current one.

        Returns:
            ISpecification: A new specification that requires both specifications to be satisfied.
        """
        return AndSpecification(self, other)

    def or_specification(self, other: "ISpecification") -> "ISpecification":
        """Combine this specification with another using logical OR.

        Args:
            other (ISpecification): The specification to combine with the current one.

        Returns:
            ISpecification: A new specification that requires either specification to be satisfied.
        """
        return OrSpecification(self, other)

    def not_specification(self) -> "ISpecification":
        """Create a negation of this specification.

        Returns:
            ISpecification: A new specification that is satisfied when this specification is not.
        """
        return NotSpecification(self)

    @abstractmethod
    def is_satisfied_by(self, candidate) -> bool:
        """Check if the candidate satisfies this specification.

        This is an abstract method that must be implemented by concrete specifications.

        Args:
            candidate: The object to test against the specification.

        Returns:
            bool: True if the candidate satisfies the specification, False otherwise.

        Raises:
            NotImplementedError: If not implemented in a derived class.
        """
        raise NotImplementedError()


class AndSpecification(ISpecification):
    """A composite specification that combines multiple specifications using logical AND.

    The candidate must satisfy all contained specifications to satisfy this one.
    """

    def __init__(self, *specifications: ISpecification):
        """Initialize an AND composite specification.

        Args:
            *specifications (ISpecification): Variable number of specifications to combine
                with AND logic. All must be satisfied for the composite to be satisfied.
        """
        self.specifications = specifications

    def is_satisfied_by(self, candidate) -> bool:
        """Check if the candidate satisfies all contained specifications.

        Args:
            candidate: The object to test against all specifications.

        Returns:
            bool: True if ALL contained specifications are satisfied by the candidate,
                False if any specification is not satisfied.
        """
        return all(spec.is_satisfied_by(candidate) for spec in self.specifications)


class OrSpecification(ISpecification):
    """A composite specification that combines multiple specifications using logical OR.

    The candidate must satisfy at least one contained specification to satisfy this one.
    """

    def __init__(self, *specifications: ISpecification):
        """Initialize an OR composite specification.

        Args:
            *specifications (ISpecification): Variable number of specifications to combine
                with OR logic. At least one must be satisfied for the composite to be satisfied.
        """
        self.specifications = specifications

    def is_satisfied_by(self, candidate) -> bool:
        """Check if the candidate satisfies any contained specification.

        Args:
            candidate: The object to test against all specifications.

        Returns:
            bool: True if ANY contained specification is satisfied by the candidate, False if none are satisfied.
        """
        return any(spec.is_satisfied_by(candidate) for spec in self.specifications)


class NotSpecification(ISpecification):
    """A decorator specification that negates another specification.

    The candidate must not satisfy the wrapped specification to satisfy this one.
    """

    def __init__(self, specification: ISpecification):
        """Initialize a NOT specification.

        Args:
            specification (ISpecification): The specification whose result should be negated.
        """
        self.specification = specification

    def is_satisfied_by(self, candidate) -> bool:
        """Check if the candidate does not satisfy the wrapped specification.

        Args:
            candidate: The object to test against the wrapped specification.

        Returns:
            bool: True if the wrapped specification is NOT satisfied by the candidate, False if it is satisfied.
        """
        return not self.specification.is_satisfied_by(candidate)


class RegexSpecification(ISpecification):
    """A specification that matches strings against a regular expression pattern.

    The candidate string must match the regex pattern to satisfy this specification.
    """

    def __init__(self, pattern: str):
        """Initialize a regex-based specification.

        Args:
            pattern (str): The regular expression pattern to compile and match against.
                This pattern will be used to test candidate strings.
        """
        self.pattern = re.compile(pattern)

    def is_satisfied_by(self, candidate) -> bool:
        """Check if the candidate string matches the regex pattern.

        Args:
            candidate: The string to test against the compiled regex pattern.

        Returns:
            bool: True if the string matches the pattern (has a match at the start), False otherwise.
        """
        return bool(self.pattern.match(candidate))
