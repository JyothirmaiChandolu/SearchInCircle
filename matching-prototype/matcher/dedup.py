from __future__ import annotations


# "Show once": a self-entry and a tag describing the same *registered* user
# collapse into one person-key. Tags about a non-user never merge by name --
# two different people can share a name, and nothing proves two non-user
# tags are the same person (see data/matching-testset/README.md, scenario
# same_name_different_person).
def person_key(kind: str, entry: dict) -> str:
    if kind == 'self_entry':
        return f"user:{entry['owner_user_id']}"
    subject = entry.get('subject_user_id')
    if subject:
        return f"user:{subject}"
    return f"tag:{entry['id']}"
