"""Schema-level contracts that must hold for every model.

This guards a bug class that is invisible on SQLite and fatal on PostgreSQL,
which is the database CI and production actually run on.
"""

from django.apps import apps

# Django's ``models.E034`` rejects index names longer than this. When it
# fires, ``migrate`` aborts outright, so a single over-long index name leaves
# a fresh PostgreSQL database with zero tables — every DB-backed test then
# errors with ``relation ... does not exist``. SQLite never noticed because
# the RLS statements that surface it are skipped there, so the suite looked
# green while CI stayed red.
MAX_INDEX_NAME_LENGTH = 30


def test_index_names_respect_djangos_length_limit():
    offenders = [
        f"{model._meta.label}.{index.name} ({len(index.name)} chars)"
        for model in apps.get_models()
        for index in model._meta.indexes
        if len(index.name) > MAX_INDEX_NAME_LENGTH
    ]
    assert not offenders, (
        f"Index names must be <= {MAX_INDEX_NAME_LENGTH} characters; longer "
        "names trigger models.E034 and abort migrate on PostgreSQL: " + ", ".join(sorted(offenders))
    )
