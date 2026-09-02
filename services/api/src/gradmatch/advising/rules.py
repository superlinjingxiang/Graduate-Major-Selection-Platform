from __future__ import annotations

from typing import TypeGuard

from .models import EligibilityRule


class InvalidRuleDefinitionError(ValueError):
    pass


def evaluate_rule(rule: EligibilityRule, facts: dict[str, object]) -> bool | None:
    if rule.fact_key not in facts:
        return None
    actual = facts[rule.fact_key]
    expected = rule.expected_value

    if rule.operator == EligibilityRule.Operator.EQUALS.value:
        return actual == expected
    if rule.operator == EligibilityRule.Operator.IN.value:
        if not isinstance(expected, list):
            raise InvalidRuleDefinitionError("The 'in' operator requires a JSON list.")
        return actual in expected
    if rule.operator == EligibilityRule.Operator.GTE.value:
        if not _is_number(actual) or not _is_number(expected):
            raise InvalidRuleDefinitionError("The 'gte' operator requires numeric values.")
        return actual >= expected
    if rule.operator == EligibilityRule.Operator.IS_TRUE.value:
        return actual is True
    raise InvalidRuleDefinitionError(f"Unsupported eligibility operator '{rule.operator}'.")


def _is_number(value: object) -> TypeGuard[int | float]:
    return isinstance(value, (int, float)) and not isinstance(value, bool)
