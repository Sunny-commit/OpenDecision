import pytest
from pydantic import ValidationError

from opendecision import DecisionQuestion


def test_string_question_becomes_noul_contract():
    question = DecisionQuestion.from_input("Is this safe?")
    assert question.type == "noul"
    assert question.instructions == "Is this safe?"


def test_choice_requires_options_or_criteria():
    with pytest.raises(ValidationError):
        DecisionQuestion(type="choice", instructions="Choose")
