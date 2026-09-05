import json


def validate_dependencies(rows):
    """Reject cycles and unsatisfiable dependencies before a plan commits."""
    index = {row['id']: row for row in rows}
    visited, visiting = set(), set()

    def visit(identity):
        if identity in visiting:
            raise ValueError('Assignment dependencies contain a cycle.')
        if identity in visited:
            return
        visiting.add(identity)
        row = index[identity]
        for dependency in json.loads(row['depends_on']):
            if dependency not in index:
                raise ValueError('Dependency refers to a task outside this goal.')
            if index[dependency]['status'] == 'cancelled' and row['status'] not in {'cancelled','completed'}:
                raise ValueError('Revise or cancel assignments that depend on cancelled work.')
            visit(dependency)
        visiting.remove(identity)
        visited.add(identity)

    for identity in index:
        visit(identity)
