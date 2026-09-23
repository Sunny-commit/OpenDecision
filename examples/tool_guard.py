"""Guard a tool call with a reusable decision contract."""

from opendecision import DecisionGuard, load_policy

policy = load_policy("decision_packs/security/tool_risk.yaml")
guard = DecisionGuard()

result = guard.decide(
    state={
        "tool": "delete_database",
        "arguments": {"database": "production"},
        "user_confirmed": False,
    },
    question=policy.question,
)

print(result.model_dump_json(indent=2))
