from datetime import date

from tools.family_tools import family_context


class Families:
    def snapshot(self, family_id):
        assert family_id == "family"
        return {"id": "parent", "name": "Sarah"}, [
            {"id": "amina", "name": "Amina", "birth_date": date(2018, 1, 1)},
            {"id": "lila", "name": "Lila", "birth_date": date(2024, 12, 31)},
        ]


def test_family_context_includes_authoritative_child_ages(monkeypatch):
    class Today(date):
        @classmethod
        def today(cls):
            return cls(2026, 9, 14)

    monkeypatch.setattr("tools.family_tools.date", Today)

    context = family_context(Families(), "family")

    assert context["children"][0]["age_years"] == 8
    assert context["children"][0]["age"] == "8 years"
    assert context["children"][1]["age_years"] == 1
    assert context["children"][1]["age"] == "1 year"
