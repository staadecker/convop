import pytest
import polars as pl

from pyoframe.core import Expression, Variable


@pytest.fixture
def expression_with_dimensions():
    df = pl.DataFrame(
        {
            "x": [1, 2, 1, 2],
            "y": [1, 1, 2, 2],
        }
    )

    return (
        5 * Variable(df)
        + 3.4 * Variable(df)
        - 2.1 * Variable(df)
        + 1.1231237019273 * Variable(df)
    )


def test_variables_to_string():
    expression = (
        5 * Variable()
        + 3.4 * Variable()
        - 2.1 * Variable()
        + 1.1231237019273 * Variable()
    )
    assert str(expression) == "5 x1 +3.4 x2 -2.1 x3 +1.1231237019273 x4"


def test_variables_to_string_with_dimensions(expression_with_dimensions: Expression):
    result = expression_with_dimensions.to_str(include_header=False)
    expected_result = "\n".join(
        [
            "[1,1]: 5 x1 +3.4 x5 -2.1 x9 +1.1231237019273 x13",
            "[2,1]: 5 x2 +3.4 x6 -2.1 x10 +1.1231237019273 x14",
            "[1,2]: 5 x3 +3.4 x7 -2.1 x11 +1.1231237019273 x15",
            "[2,2]: 5 x4 +3.4 x8 -2.1 x12 +1.1231237019273 x16",
        ]
    )
    assert result == expected_result


def test_expression_with_const_to_str():
    expr = 5 + 2 * Variable()
    assert str(expr) == "2 x1 +5"


def test_quadratic_objective_to_str():
    kwargs = dict(
        include_prefix=False, include_const_variable=True, quadratic_divider=2
    )
    expr = (
        5 * Variable() - 2 * Variable() ** 2 + 3 + 2 * Variable() + 4 * Variable() ** 2
    )
    assert expr.to_str(**kwargs) == "5 x1 +3 x0 +2 x3 + [ -4 x2 * x2 +8 x4 * x4 ] / 2"


def test_quadratic_constraints_to_str():
    kwargs = dict(quadratic_divider=1)
    constraint = (
        5 * Variable() - 2 * Variable() ** 2 + 3 + 2 * Variable() + 4 * Variable() ** 2
        == 0
    )
    assert constraint.to_str(**kwargs) == "5 x1 +2 x3 + [ -2 x2 * x2 +4 x4 * x4 ] = -3"
    df = pl.DataFrame({"x": [1, 2]})
    constraint = (
        5 * Variable(df)
        - 2 * Variable(df) ** 2
        + 3
        + 2 * Variable(df)
        + 4 * Variable(df) ** 2
        == 0
    )
    assert (
        constraint.to_str(**kwargs)
        == """[1]: 5 x5 +2 x9 + [ 4 x11 * x11 -2 x7 * x7 ] = -3
[2]: 5 x6 +2 x10 + [ 4 x12 * x12 -2 x8 * x8 ] = -3"""
    )


if __name__ == "__main__":
    pytest.main([__file__])
