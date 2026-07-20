from dataclasses import dataclass

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.errors import AppError
from app.common.models import Notification
from app.common.workflow import TransitionStep, apply_transition, transition_history
from app.core.security import hash_password
from app.modules.auth.models import Role, User, UserRole

PASSWORD = "InitialPass1"


def make_user(db_session: Session, staff_no: str, roles: list[str]) -> User:
    user = User(
        staff_no=staff_no,
        password_hash=hash_password(PASSWORD),
        must_change_password=False,
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()
    for code in roles:
        role = db_session.scalars(select(Role).where(Role.code == code)).first()
        if role is None:
            role = Role(code=code, name_en=code, name_ar=code)
            db_session.add(role)
            db_session.flush()
        db_session.add(UserRole(user_id=user.id, role_id=role.id))
    db_session.commit()
    db_session.refresh(user)
    return user


@dataclass
class FakeEntity:
    id: int
    status: str


def test_apply_transition_success_mutates_status_and_writes_action(db_session: Session) -> None:
    actor = make_user(db_session, "9001", roles=["hr"])
    entity = FakeEntity(id=1, status="draft")
    table = {("draft", "submit"): TransitionStep(to="submitted", roles=frozenset({"hr"}))}

    action = apply_transition(
        db_session,
        entity=entity,
        entity_type="fake",
        table=table,
        action="submit",
        actor=actor,
        comment="go",
    )
    db_session.commit()

    assert entity.status == "submitted"
    assert action.from_status == "draft"
    assert action.to_status == "submitted"
    assert action.actor_role == "hr"
    assert action.comment == "go"


def test_apply_transition_writes_notification_when_requested(db_session: Session) -> None:
    actor = make_user(db_session, "9002", roles=["hr"])
    recipient = make_user(db_session, "9003", roles=["employee"])
    entity = FakeEntity(id=2, status="draft")
    table = {("draft", "submit"): TransitionStep(to="submitted", roles=frozenset({"hr"}))}

    apply_transition(
        db_session,
        entity=entity,
        entity_type="fake",
        table=table,
        action="submit",
        actor=actor,
        notify_user_id=recipient.id,
    )
    db_session.commit()

    notifications = list(
        db_session.scalars(select(Notification).where(Notification.user_id == recipient.id))
    )
    assert len(notifications) == 1
    assert notifications[0].entity_type == "fake"
    assert notifications[0].entity_id == 2


def test_apply_transition_no_notification_without_recipient(db_session: Session) -> None:
    actor = make_user(db_session, "9004", roles=["hr"])
    entity = FakeEntity(id=3, status="draft")
    table = {("draft", "submit"): TransitionStep(to="submitted", roles=frozenset({"hr"}))}

    apply_transition(
        db_session, entity=entity, entity_type="fake", table=table, action="submit", actor=actor
    )
    db_session.commit()

    assert db_session.scalars(select(Notification)).first() is None


def test_apply_transition_invalid_action_raises_400(db_session: Session) -> None:
    actor = make_user(db_session, "9005", roles=["hr"])
    entity = FakeEntity(id=4, status="draft")
    table = {("draft", "submit"): TransitionStep(to="submitted", roles=frozenset({"hr"}))}

    with pytest.raises(AppError) as exc_info:
        apply_transition(
            db_session,
            entity=entity,
            entity_type="fake",
            table=table,
            action="approve",
            actor=actor,
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.code == "invalid_transition"
    assert entity.status == "draft"  # untouched


def test_apply_transition_wrong_role_raises_403(db_session: Session) -> None:
    actor = make_user(db_session, "9006", roles=["employee"])
    entity = FakeEntity(id=5, status="draft")
    table = {("draft", "submit"): TransitionStep(to="submitted", roles=frozenset({"hr"}))}

    with pytest.raises(AppError) as exc_info:
        apply_transition(
            db_session, entity=entity, entity_type="fake", table=table, action="submit", actor=actor
        )

    assert exc_info.value.status_code == 403
    assert entity.status == "draft"


def test_apply_transition_guard_failure_raises_403(db_session: Session) -> None:
    actor = make_user(db_session, "9007", roles=["hr"])
    entity = FakeEntity(id=6, status="draft")
    table = {
        ("draft", "submit"): TransitionStep(
            to="submitted", roles=frozenset({"hr"}), guard=lambda _db, _e, _a: False
        )
    }

    with pytest.raises(AppError) as exc_info:
        apply_transition(
            db_session, entity=entity, entity_type="fake", table=table, action="submit", actor=actor
        )

    assert exc_info.value.status_code == 403
    assert entity.status == "draft"


def test_transition_history_orders_chronologically(db_session: Session) -> None:
    actor = make_user(db_session, "9008", roles=["hr"])
    entity = FakeEntity(id=7, status="draft")
    table = {
        ("draft", "submit"): TransitionStep(to="submitted", roles=frozenset({"hr"})),
        ("submitted", "approve"): TransitionStep(to="approved", roles=frozenset({"hr"})),
    }
    apply_transition(
        db_session, entity=entity, entity_type="fake", table=table, action="submit", actor=actor
    )
    apply_transition(
        db_session, entity=entity, entity_type="fake", table=table, action="approve", actor=actor
    )
    db_session.commit()

    history = transition_history(db_session, entity_type="fake", entity_id=7)
    assert [h.action for h in history] == ["submit", "approve"]
