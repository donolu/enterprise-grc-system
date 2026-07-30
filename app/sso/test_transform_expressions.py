import pytest

from sso.utils import UnsafeTransformExpression, apply_transform_expression


def test_transform_expression_allows_common_string_methods():
    result = apply_transform_expression(
        "value.strip().lower()",
        "  PERSON@EXAMPLE.COM  ",
        {},
    )

    assert result == "person@example.com"


def test_transform_expression_allows_attribute_lookup_and_indexing():
    result = apply_transform_expression(
        'attributes.get("groups", [""])[0].upper()',
        "ignored",
        {"groups": ["risk-admins"]},
    )

    assert result == "RISK-ADMINS"


def test_transform_expression_rejects_builtin_calls():
    with pytest.raises(UnsafeTransformExpression):
        apply_transform_expression(
            '__import__("os").system("id")',
            "ignored",
            {},
        )
