from datetime import UTC, date, datetime

from strands import tool


@tool
def get_current_datetime() -> str:
    """Return the current UTC date and time for deadline and schedule reasoning."""
    return datetime.now(UTC).isoformat()


def family_context(families, family_id: str) -> dict:
    """Return family profiles with an authoritative age for each child."""
    parent, children = families.snapshot(family_id)
    today = date.today()
    profiles = []
    for row in children:
        child = dict(row)
        born = child.get("birth_date")
        years = today.year - born.year - ((today.month, today.day) < (born.month, born.day)) if born else None
        child["age_years"] = years
        child["age"] = f"{years} year" if years == 1 else f"{years} years" if years is not None else ""
        profiles.append(child)
    return {"parent": dict(parent), "children": profiles}
