"""Authentication: hashing, registration, login, throttling, sessions, reset codes."""

import hashlib

import pytest

from auth import (
    authenticate, create_user, end_session, issue_reset_code, login, register, register_teacher,
    reset_password_with_code, start_session, user_for_session, username_exists,
)
from auth import authentication, passwords
from database.connection import session_scope
from database.repository import UserRepository

GOOD = "Passw0rd!xyz"


def test_password_hash_is_salted_and_verifiable():
    first, second = passwords.hash_password(GOOD), passwords.hash_password(GOOD)
    assert first != second                                  # random salt
    assert GOOD not in first
    assert passwords.verify_password(GOOD, first)
    assert not passwords.verify_password("wrong-password", first)


def test_legacy_sha256_hash_still_logs_in_and_is_upgraded():
    legacy = hashlib.sha256(GOOD.encode()).hexdigest()
    with session_scope() as s:
        from database.models import User

        UserRepository(s).add(User(username="old", password_hash=legacy, role="student", full_name="Old Timer"))
    user, reason = login("old", GOOD)
    assert user is not None, reason
    with session_scope() as s:
        stored = UserRepository(s).get_by_username("old").password_hash
    assert stored != legacy and not passwords.needs_rehash(stored)


def test_register_and_login_roundtrip():
    ok, _ = register("alice", GOOD, "Alice Wang")
    assert ok and username_exists("ALICE")                  # usernames are case-insensitive
    assert authenticate("alice", GOOD).full_name == "Alice Wang"
    assert authenticate("alice", "nope-nope-nope") is None


@pytest.mark.parametrize("username,password", [("a", GOOD), ("ok name", GOOD), ("alice", "short"), ("alice", "alice")])
def test_registration_validation(username, password):
    ok, message = register(username, password, "Alice")
    assert not ok and message


def test_duplicate_username_rejected():
    assert register("bob", GOOD, "Bob")[0]
    ok, message = register("bob", GOOD, "Bobby")
    assert not ok and "taken" in message.lower()


def test_public_registration_can_never_create_teachers():
    ok, _ = register("evil", GOOD, "Evil", role="teacher")
    assert not ok and not username_exists("evil")


def test_teacher_invite_code(monkeypatch):
    assert not register_teacher("teacher1", GOOD, "T One", "anything")[0]          # disabled until configured
    monkeypatch.setenv("PRELUMA_TEACHER_INVITE_CODE", "s3cret-code")
    assert not register_teacher("teacher1", GOOD, "T One", "wrong")[0]
    assert register_teacher("teacher1", GOOD, "T One", "s3cret-code")[0]
    assert authenticate("teacher1", GOOD).is_teacher


def test_login_is_throttled_after_repeated_failures():
    register("carol", GOOD, "Carol")
    for _ in range(authentication.MAX_FAILED_LOGINS):
        assert login("carol", "bad-password-x")[0] is None
    user, reason = login("carol", GOOD)                     # even the right password is refused now
    assert user is None and "too many" in reason.lower()


def test_sessions_are_opaque_and_revocable():
    user = create_user("dave", GOOD, "Dave")
    token = start_session(user)
    assert "dave" not in token and len(token) >= 32
    assert user_for_session(token).username == "dave"
    end_session(token)
    assert user_for_session(token) is None
    assert user_for_session("garbage") is None


def test_reset_code_flow_and_permissions():
    teacher = create_user("teach", GOOD, "Teach", "teacher")
    create_user("stu", GOOD, "Stu")
    student2 = create_user("stu2", GOOD, "Stu Two")
    assert not issue_reset_code(student2.id, "stu")[0]                       # students cannot issue codes
    ok, code = issue_reset_code(teacher.id, "stu")
    assert ok
    assert not reset_password_with_code("stu", "wrong-code", "N3w-Passw0rd!")[0]
    assert reset_password_with_code("stu", code, "N3w-Passw0rd!")[0]
    assert authenticate("stu", "N3w-Passw0rd!") is not None
    assert not reset_password_with_code("stu", code, "An0ther-Passw0rd")[0]  # one-time use
    create_user("teach2", GOOD, "Teach Two", "teacher")
    assert not issue_reset_code(teacher.id, "teach2")[0]                     # only admins may reset teachers
    assert issue_reset_code(teacher.id, "stu2")[0]


def test_issuing_a_new_reset_code_invalidates_the_previous_one():
    teacher = create_user("reset-teach", GOOD, "Reset Teacher", "teacher")
    create_user("reset-student", GOOD, "Reset Student")
    ok, first = issue_reset_code(teacher.id, "reset-student")
    assert ok
    ok, second = issue_reset_code(teacher.id, "reset-student")
    assert ok and first != second
    assert not reset_password_with_code("reset-student", first, "N3w-Passw0rd!")[0]
    assert reset_password_with_code("reset-student", second, "N3w-Passw0rd!")[0]


def test_demo_users_only_come_from_configuration(monkeypatch):
    from auth import ensure_demo_users

    assert ensure_demo_users() == 0 and not username_exists("demo")
    monkeypatch.setenv("DEMO_USERS_JSON", '[{"username":"demo","password":"Passw0rd!xyz","role":"student","full_name":"Demo"}]')
    assert ensure_demo_users() == 1 and username_exists("demo")
    assert ensure_demo_users() == 0                                           # idempotent


def test_no_secrets_or_default_credentials_in_source():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    haystack = "\n".join(p.read_text(encoding="utf-8", errors="ignore")
                         for folder in ("auth", "config.py", "app.py", "views", "services")
                         for p in ([root / folder] if (root / folder).is_file() else (root / folder).glob("*.py")))
    for forbidden in ("PRELUMA-TEACH-2024", "preluma-ynu-2024-session-key"):
        assert forbidden not in haystack
