"""Quantity and Series types for typed weather data."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class Quantity:
    """A single value with its unit.

    Represents a scalar quantity like total precipitation or average temperature.

    Attributes:
        value: The numeric value.
        unit: The unit string (e.g., "mm", "in", "C", "F").
    """

    value: float
    unit: str

    def __repr__(self) -> str:
        return f"Quantity({self.value:.4g} {self.unit})"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {"value": self.value, "unit": self.unit}


@dataclass(frozen=True, slots=True)
class Series:
    """A time series of values with a unit.

    Represents hourly data like temperature or wind speed over time.

    Attributes:
        values: List of numeric values (may contain None for missing data).
        unit: The unit string for all values.
    """

    values: tuple[float | None, ...]
    unit: str

    def __post_init__(self) -> None:
        # Ensure values is a tuple for immutability
        if not isinstance(self.values, tuple):
            object.__setattr__(self, "values", tuple(self.values))

    def __len__(self) -> int:
        return len(self.values)

    def __getitem__(self, index: int | slice) -> float | None | tuple[float | None, ...]:
        result = self.values[index]
        if isinstance(index, slice):
            return result
        return result

    def __repr__(self) -> str:
        n = len(self.values)
        if n <= 6:
            preview = str(list(self.values))
        else:
            preview = f"[{self.values[0]}, {self.values[1]}, ..., {self.values[-1]}]"
        return f"Series({preview}, unit='{self.unit}', n={n})"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {"values": list(self.values), "unit": self.unit}

    def slice(self, start: int, end: int) -> Series:
        """Return a new Series sliced to [start, end)."""
        return Series(values=self.values[start:end], unit=self.unit)

    def sum(self) -> float:
        """Sum all non-None values in the series."""
        return sum(v for v in self.values if v is not None)

    def mean(self) -> float | None:
        """Calculate the mean of non-None values."""
        valid = [v for v in self.values if v is not None]
        if not valid:
            return None
        return sum(valid) / len(valid)

    def min(self) -> float | None:
        """Return the minimum non-None value."""
        valid = [v for v in self.values if v is not None]
        if not valid:
            return None
        return min(valid)

    def max(self) -> float | None:
        """Return the maximum non-None value."""
        valid = [v for v in self.values if v is not None]
        if not valid:
            return None
        return max(valid)

