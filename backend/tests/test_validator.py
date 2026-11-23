from app.security.validator import validate


def ok(sql, role="write"):
    return validate(sql, role)


def test_select_is_read_and_needs_no_confirmation():
    v = ok("SELECT * FROM customers WHERE city = 'Hyderabad'")
    assert v["valid"] and v["category"] == "read" and not v["requires_confirmation"]


def test_like_percent_is_fine():
    assert ok("SELECT * FROM t WHERE name LIKE '%a%'")["valid"]


def test_multiple_statements_rejected():
    assert not ok("SELECT 1; DROP TABLE users")["valid"]


def test_comments_rejected():
    assert not ok("SELECT 1 -- hi")["valid"]


def test_update_without_where_rejected():
    assert not ok("UPDATE customers SET email = 'x'")["valid"]


def test_tautology_where_rejected():
    assert not ok("DELETE FROM customers WHERE 1=1")["valid"]


def test_delete_with_where_needs_confirmation():
    v = ok("DELETE FROM customers WHERE id = 5")
    assert v["valid"] and v["requires_confirmation"] and v["target"] == "customers"


def test_drop_needs_admin():
    assert not ok("DROP TABLE customers", "write")["valid"]
    v = ok("DROP TABLE customers", "admin")
    assert v["valid"] and v["destructive"]


def test_readonly_blocks_writes():
    assert not ok("INSERT INTO t (a) VALUES (1)", "readonly")["valid"]


def test_string_containing_keyword_is_ok():
    assert ok("INSERT INTO movies (title) VALUES ('Kill Bill')")["valid"]


def test_system_schema_blocked():
    assert not ok("DROP DATABASE mysql", "admin")["valid"]


def test_file_access_blocked():
    assert not ok("SELECT * FROM t INTO OUTFILE '/tmp/x'")["valid"]
