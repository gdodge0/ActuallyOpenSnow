"""Tests for Quantity and Series classes."""

import pytest
from weather.domain.quantities import Quantity, Series


class TestQuantity:
    """Tests for the Quantity class."""

    def test_creation(self):
        """Test basic Quantity creation."""
        q = Quantity(value=10.5, unit="mm")
        assert q.value == 10.5
        assert q.unit == "mm"

    def test_immutability(self):
        """Test that Quantity is immutable (frozen dataclass)."""
        q = Quantity(value=10.5, unit="mm")
        with pytest.raises(AttributeError):
            q.value = 20.0

    def test_repr(self):
        """Test __repr__ formatting."""
        q = Quantity(value=10.5, unit="mm")
        assert repr(q) == "Quantity(10.5 mm)"

    def test_repr_large_value(self):
        """Test __repr__ with large value uses scientific notation."""
        q = Quantity(value=12345.6789, unit="m")
        # Should use 4 significant figures
        assert "1.235e+04" in repr(q) or "12350" in repr(q)

    def test_repr_small_value(self):
        """Test __repr__ with small value."""
        q = Quantity(value=0.00123, unit="in")
        assert "0.00123" in repr(q) or "1.23e-03" in repr(q)

    def test_to_dict(self):
        """Test conversion to dictionary."""
        q = Quantity(value=25.4, unit="mm")
        d = q.to_dict()
        assert d == {"value": 25.4, "unit": "mm"}

    def test_to_dict_preserves_precision(self):
        """Test that to_dict preserves float precision."""
        q = Quantity(value=3.141592653589793, unit="m")
        d = q.to_dict()
        assert d["value"] == 3.141592653589793

    def test_equality(self):
        """Test Quantity equality."""
        q1 = Quantity(value=10.0, unit="mm")
        q2 = Quantity(value=10.0, unit="mm")
        assert q1 == q2

    def test_inequality_different_value(self):
        """Test Quantity inequality with different values."""
        q1 = Quantity(value=10.0, unit="mm")
        q2 = Quantity(value=20.0, unit="mm")
        assert q1 != q2

    def test_inequality_different_unit(self):
        """Test Quantity inequality with different units."""
        q1 = Quantity(value=10.0, unit="mm")
        q2 = Quantity(value=10.0, unit="cm")
        assert q1 != q2


class TestSeries:
    """Tests for the Series class."""

    def test_creation_with_tuple(self):
        """Test Series creation with tuple."""
        s = Series(values=(1.0, 2.0, 3.0), unit="C")
        assert s.values == (1.0, 2.0, 3.0)
        assert s.unit == "C"

    def test_creation_with_list_converts_to_tuple(self):
        """Test that list input is converted to tuple."""
        s = Series(values=[1.0, 2.0, 3.0], unit="C")
        assert isinstance(s.values, tuple)
        assert s.values == (1.0, 2.0, 3.0)

    def test_immutability(self):
        """Test that Series is immutable (frozen dataclass)."""
        s = Series(values=(1.0, 2.0, 3.0), unit="C")
        with pytest.raises(AttributeError):
            s.unit = "F"

    def test_len(self):
        """Test __len__ returns correct length."""
        s = Series(values=(1.0, 2.0, 3.0, 4.0, 5.0), unit="C")
        assert len(s) == 5

    def test_len_empty(self):
        """Test __len__ with empty series."""
        s = Series(values=(), unit="C")
        assert len(s) == 0

    def test_getitem_single_index(self):
        """Test __getitem__ with single index."""
        s = Series(values=(10.0, 20.0, 30.0), unit="C")
        assert s[0] == 10.0
        assert s[1] == 20.0
        assert s[2] == 30.0
        assert s[-1] == 30.0

    def test_getitem_with_none(self):
        """Test __getitem__ returns None for None values."""
        s = Series(values=(10.0, None, 30.0), unit="C")
        assert s[0] == 10.0
        assert s[1] is None
        assert s[2] == 30.0

    def test_getitem_slice(self):
        """Test __getitem__ with slice."""
        s = Series(values=(10.0, 20.0, 30.0, 40.0, 50.0), unit="C")
        result = s[1:4]
        assert result == (20.0, 30.0, 40.0)

    def test_getitem_out_of_bounds(self):
        """Test __getitem__ raises IndexError for out of bounds."""
        s = Series(values=(1.0, 2.0), unit="C")
        with pytest.raises(IndexError):
            _ = s[10]

    def test_repr_short_series(self):
        """Test __repr__ for short series (<=6 elements)."""
        s = Series(values=(1.0, 2.0, 3.0), unit="C")
        r = repr(s)
        assert "Series(" in r
        assert "[1.0, 2.0, 3.0]" in r
        assert "unit='C'" in r
        assert "n=3" in r

    def test_repr_long_series(self):
        """Test __repr__ for long series (>6 elements) is truncated."""
        values = tuple(float(i) for i in range(10))
        s = Series(values=values, unit="mm")
        r = repr(s)
        assert "Series(" in r
        assert "0.0" in r  # First element
        assert "1.0" in r  # Second element
        assert "9.0" in r  # Last element
        assert "..." in r  # Truncation indicator
        assert "n=10" in r

    def test_to_dict(self):
        """Test conversion to dictionary."""
        s = Series(values=(1.0, 2.0, 3.0), unit="C")
        d = s.to_dict()
        assert d == {"values": [1.0, 2.0, 3.0], "unit": "C"}

    def test_to_dict_with_none(self):
        """Test to_dict preserves None values."""
        s = Series(values=(1.0, None, 3.0), unit="C")
        d = s.to_dict()
        assert d == {"values": [1.0, None, 3.0], "unit": "C"}

    def test_slice_method(self):
        """Test slice method returns new Series."""
        s = Series(values=(10.0, 20.0, 30.0, 40.0, 50.0), unit="mm")
        sliced = s.slice(1, 4)
        assert isinstance(sliced, Series)
        assert sliced.values == (20.0, 30.0, 40.0)
        assert sliced.unit == "mm"

    def test_slice_preserves_unit(self):
        """Test that slice preserves the unit."""
        s = Series(values=(1.0, 2.0, 3.0), unit="F")
        sliced = s.slice(0, 2)
        assert sliced.unit == "F"

    def test_sum_basic(self):
        """Test sum of values."""
        s = Series(values=(1.0, 2.0, 3.0, 4.0), unit="mm")
        assert s.sum() == 10.0

    def test_sum_with_none_values(self):
        """Test sum ignores None values."""
        s = Series(values=(1.0, None, 3.0, None, 5.0), unit="mm")
        assert s.sum() == 9.0

    def test_sum_all_none(self):
        """Test sum of all None values returns 0."""
        s = Series(values=(None, None, None), unit="mm")
        assert s.sum() == 0.0

    def test_sum_empty(self):
        """Test sum of empty series returns 0."""
        s = Series(values=(), unit="mm")
        assert s.sum() == 0.0

    def test_mean_basic(self):
        """Test mean calculation."""
        s = Series(values=(10.0, 20.0, 30.0), unit="C")
        assert s.mean() == 20.0

    def test_mean_with_none_values(self):
        """Test mean ignores None values."""
        s = Series(values=(10.0, None, 30.0), unit="C")
        # Mean of 10 and 30 is 20
        assert s.mean() == 20.0

    def test_mean_all_none_returns_none(self):
        """Test mean of all None values returns None."""
        s = Series(values=(None, None, None), unit="C")
        assert s.mean() is None

    def test_mean_empty_returns_none(self):
        """Test mean of empty series returns None."""
        s = Series(values=(), unit="C")
        assert s.mean() is None

    def test_min_basic(self):
        """Test min calculation."""
        s = Series(values=(30.0, 10.0, 20.0), unit="C")
        assert s.min() == 10.0

    def test_min_with_none_values(self):
        """Test min ignores None values."""
        s = Series(values=(30.0, None, 10.0, None), unit="C")
        assert s.min() == 10.0

    def test_min_all_none_returns_none(self):
        """Test min of all None values returns None."""
        s = Series(values=(None, None), unit="C")
        assert s.min() is None

    def test_min_empty_returns_none(self):
        """Test min of empty series returns None."""
        s = Series(values=(), unit="C")
        assert s.min() is None

    def test_max_basic(self):
        """Test max calculation."""
        s = Series(values=(10.0, 30.0, 20.0), unit="C")
        assert s.max() == 30.0

    def test_max_with_none_values(self):
        """Test max ignores None values."""
        s = Series(values=(None, 10.0, None, 30.0), unit="C")
        assert s.max() == 30.0

    def test_max_all_none_returns_none(self):
        """Test max of all None values returns None."""
        s = Series(values=(None, None), unit="C")
        assert s.max() is None

    def test_max_empty_returns_none(self):
        """Test max of empty series returns None."""
        s = Series(values=(), unit="C")
        assert s.max() is None

    def test_negative_values(self):
        """Test operations with negative values."""
        s = Series(values=(-10.0, -5.0, 0.0, 5.0, 10.0), unit="C")
        assert s.sum() == 0.0
        assert s.mean() == 0.0
        assert s.min() == -10.0
        assert s.max() == 10.0

    def test_equality(self):
        """Test Series equality."""
        s1 = Series(values=(1.0, 2.0, 3.0), unit="C")
        s2 = Series(values=(1.0, 2.0, 3.0), unit="C")
        assert s1 == s2

    def test_inequality_different_values(self):
        """Test Series inequality with different values."""
        s1 = Series(values=(1.0, 2.0, 3.0), unit="C")
        s2 = Series(values=(1.0, 2.0, 4.0), unit="C")
        assert s1 != s2

    def test_inequality_different_unit(self):
        """Test Series inequality with different units."""
        s1 = Series(values=(1.0, 2.0, 3.0), unit="C")
        s2 = Series(values=(1.0, 2.0, 3.0), unit="F")
        assert s1 != s2

