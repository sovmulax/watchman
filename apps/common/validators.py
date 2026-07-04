from __future__ import annotations

from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible


@deconstructible
class ValidatePositiveSmallIntRange:
    """Valide qu'un entier est dans une plage [min, max]."""

    def __init__(self, min_value: int = 0, max_value: int = 100) -> None:
        self.min_value = min_value
        self.max_value = max_value

    def __call__(self, value: int) -> None:
        if value < self.min_value or value > self.max_value:
            raise ValidationError(
                f"La valeur doit être comprise entre {self.min_value} et {self.max_value}."
            )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ValidatePositiveSmallIntRange):
            return NotImplemented
        return self.min_value == other.min_value and self.max_value == other.max_value

