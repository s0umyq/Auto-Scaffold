import pytest
from calculator import add, divide, multiply


class TestAdd:
    def test_add_positive_integers(self):
        assert add(2, 3) == 5

    def test_add_negative_integers(self):
        assert add(-2, -3) == -5

    def test_add_mixed_integers(self):
        assert add(-2, 3) == 1
        assert add(2, -3) == -1

    def test_add_zero(self):
        assert add(0, 0) == 0
        assert add(5, 0) == 5
        assert add(0, 5) == 5

    def test_add_floats(self):
        assert add(2.5, 3.5) == 6.0
        assert add(-1.5, 2.5) == 1.0

    def test_add_large_numbers(self):
        assert add(10**10, 10**10) == 2 * 10**10


class TestMultiply:
    def test_multiply_positive_integers(self):
        assert multiply(2, 3) == 6

    def test_multiply_negative_integers(self):
        assert multiply(-2, -3) == 6

    def test_multiply_mixed_integers(self):
        assert multiply(-2, 3) == -6
        assert multiply(2, -3) == -6

    def test_multiply_by_zero(self):
        assert multiply(0, 0) == 0
        assert multiply(5, 0) == 0
        assert multiply(0, 5) == 0

    def test_multiply_by_one(self):
        assert multiply(5, 1) == 5
        assert multiply(1, 5) == 5
        assert multiply(-5, 1) == -5

    def test_multiply_floats(self):
        assert multiply(2.5, 4.0) == 10.0
        assert multiply(-1.5, 2.0) == -3.0

    def test_multiply_large_numbers(self):
        assert multiply(10**5, 10**5) == 10**10


class TestDivide:
    def test_divide_positive_integers(self):
        assert divide(6, 3) == 2

    def test_divide_negative_integers(self):
        assert divide(-6, -3) == 2

    def test_divide_mixed_integers(self):
        assert divide(-6, 3) == -2
        assert divide(6, -3) == -2

    def test_divide_floats(self):
        assert divide(7.5, 2.5) == 3.0
        assert divide(-7.5, 2.5) == -3.0

    def test_divide_by_one(self):
        assert divide(5, 1) == 5
        assert divide(-5, 1) == -5

    def test_divide_zero_by_number(self):
        assert divide(0, 5) == 0
        assert divide(0, -5) == 0

    def test_divide_by_zero_raises_error(self):
        with pytest.raises(ZeroDivisionError):
            divide(5, 0)

        with pytest.raises(ZeroDivisionError):
            divide(0, 0)

        with pytest.raises(ZeroDivisionError):
            divide(-5, 0)

    def test_divide_large_numbers(self):
        assert divide(10**10, 10**5) == 10**5

    def test_divide_precision(self):
        result = divide(1, 3)
        assert abs(result - 0.3333333333333333) < 1e-10


class TestEdgeCases:
    def test_add_very_small_floats(self):
        result = add(1e-10, 1e-10)
        assert abs(result - 2e-10) < 1e-15

    def test_multiply_very_small_floats(self):
        result = multiply(1e-5, 1e-5)
        assert abs(result - 1e-10) < 1e-15

    def test_divide_very_small_floats(self):
        result = divide(1e-10, 1e-5)
        assert abs(result - 1e-5) < 1e-15

    def test_operations_with_negative_zero(self):
        assert add(0.0, -0.0) == 0.0
        assert multiply(5.0, -0.0) == -0.0
        assert divide(-0.0, 5.0) == -0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])