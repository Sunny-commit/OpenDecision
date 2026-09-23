import pytest
from pydantic import ValidationError
from opendecision import DecisionQuestion

def test_laya_choice_uses_criteria_not_options():
    question=DecisionQuestion(type="choice",instructions="Choose an outcome",options={"allow":"Proceed","block":"Stop"})
    assert question.to_laya()=={"type":"choice","instructions":"Choose an outcome","criteria":{"allow":"Proceed","block":"Stop"}}

@pytest.mark.parametrize("payload",[
    {"type":"choice","instructions":"Choose","options":{"Bad-Name":"x","ok":"y"}},
    {"type":"score","instructions":"Rate","criteria":["same","same"]},
    {"type":"noul","instructions":"Risk?","options":{"yes":"x","no":"y"}},
    {"type":"noul","instructions":"x","unknown":True},
])
def test_invalid_contracts_fail_early(payload):
    with pytest.raises(ValidationError): DecisionQuestion.model_validate(payload)
