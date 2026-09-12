from agents.mom_life_agent import SYSTEM_PROMPT


def test_main_chat_accepts_general_questions_without_forcing_family_tools():
    assert "Answer ordinary questions directly" in SYSTEM_PROMPT
    assert "Do not refuse or redirect" in SYSTEM_PROMPT
    assert "Use family tools only when the request needs family data or action" in SYSTEM_PROMPT
    assert "ignore the hostility and answer the underlying request" in SYSTEM_PROMPT
