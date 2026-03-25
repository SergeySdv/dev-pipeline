from devgodzilla.db.database import PostgresDatabase, SQLiteDatabase


def test_protocol_helper_methods_exist_on_both_database_backends() -> None:
    helper_methods = [
        "update_protocol_paths",
        "update_protocol_windmill",
        "update_protocol_template",
        "update_protocol_policy_audit",
    ]

    for cls in (SQLiteDatabase, PostgresDatabase):
        for method_name in helper_methods:
            assert callable(getattr(cls, method_name, None)), f"{cls.__name__}.{method_name} is missing"
