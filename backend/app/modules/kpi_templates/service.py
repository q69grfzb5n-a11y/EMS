from datetime import date

from sqlalchemy import Select, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.common.audit import write_audit
from app.common.enums import TemplateVersionStatus
from app.common.errors import bad_request, conflict, not_found
from app.modules.auth.models import User
from app.modules.kpi_templates.models import (
    KpiCriterion,
    KpiTemplate,
    KpiTemplateAssignment,
    KpiTemplateVersion,
)
from app.modules.org.service import get_position


def list_templates(db: Session) -> list[KpiTemplate]:
    return list(db.scalars(select(KpiTemplate).order_by(KpiTemplate.code)))


def get_template(db: Session, template_id: int) -> KpiTemplate:
    template = db.get(KpiTemplate, template_id)
    if template is None:
        raise not_found("KPI template not found")
    return template


def create_template(
    db: Session, actor: User, *, code: str, name_en: str, name_ar: str
) -> KpiTemplate:
    if db.scalars(select(KpiTemplate).where(KpiTemplate.code == code)).first() is not None:
        raise conflict("A template with this code already exists", code="template_code_taken")

    template = KpiTemplate(code=code, name_en=name_en, name_ar=name_ar)
    db.add(template)
    db.flush()
    db.add(KpiTemplateVersion(template_id=template.id, version_no=1))
    write_audit(
        db,
        actor_user_id=actor.id,
        action="create_kpi_template",
        entity_type="kpi_template",
        entity_id=template.id,
        after={"code": code, "name_en": name_en, "name_ar": name_ar},
    )
    db.commit()
    return get_template(db, template.id)


def _version_query() -> Select[tuple[KpiTemplateVersion]]:
    return select(KpiTemplateVersion).options(selectinload(KpiTemplateVersion.criteria))


def list_versions(db: Session, template_id: int) -> list[KpiTemplateVersion]:
    get_template(db, template_id)  # 404 if missing
    stmt = (
        _version_query()
        .where(KpiTemplateVersion.template_id == template_id)
        .order_by(KpiTemplateVersion.version_no.desc())
    )
    return list(db.scalars(stmt))


def get_version(db: Session, version_id: int) -> KpiTemplateVersion:
    stmt = _version_query().where(KpiTemplateVersion.id == version_id)
    version = db.scalars(stmt).first()
    if version is None:
        raise not_found("KPI template version not found")
    return version


def get_active_version(db: Session, template_id: int) -> KpiTemplateVersion | None:
    stmt = _version_query().where(
        KpiTemplateVersion.template_id == template_id,
        KpiTemplateVersion.status == TemplateVersionStatus.ACTIVE.value,
    )
    return db.scalars(stmt).first()


def clone_version(
    db: Session, actor: User, template_id: int, *, source_version_id: int | None
) -> KpiTemplateVersion:
    """Clones a version's criteria into a new draft version — the demo-gate flow
    (open v1 -> clone to v2 -> edit -> publish, v1 stays frozen forever)."""
    template = get_template(db, template_id)

    source: KpiTemplateVersion | None
    if source_version_id is not None:
        source = get_version(db, source_version_id)
        if source.template_id != template_id:
            raise bad_request("Source version does not belong to this template")
    else:
        source = get_active_version(db, template_id)
        if source is None:
            existing = list_versions(db, template_id)
            source = existing[0] if existing else None

    latest_no = db.scalar(
        select(KpiTemplateVersion.version_no)
        .where(KpiTemplateVersion.template_id == template_id)
        .order_by(KpiTemplateVersion.version_no.desc())
        .limit(1)
    )
    new_version = KpiTemplateVersion(template_id=template.id, version_no=(latest_no or 0) + 1)
    db.add(new_version)
    db.flush()

    if source is not None:
        for criterion in source.criteria:
            db.add(
                KpiCriterion(
                    template_version_id=new_version.id,
                    name_en=criterion.name_en,
                    name_ar=criterion.name_ar,
                    guidance_en=criterion.guidance_en,
                    guidance_ar=criterion.guidance_ar,
                    max_marks=criterion.max_marks,
                    input_mode=criterion.input_mode,
                    allow_negative=criterion.allow_negative,
                    auto_source=criterion.auto_source,
                    auto_params=criterion.auto_params,
                    sort_order=criterion.sort_order,
                )
            )

    write_audit(
        db,
        actor_user_id=actor.id,
        action="clone_kpi_template_version",
        entity_type="kpi_template_version",
        entity_id=new_version.id,
        before={"source_version_id": source.id if source else None},
        after={"template_id": template_id, "version_no": new_version.version_no},
    )
    db.commit()
    return get_version(db, new_version.id)


def _require_draft(version: KpiTemplateVersion) -> None:
    if version.status != TemplateVersionStatus.DRAFT.value:
        raise bad_request(
            "Criteria can only be edited while the version is a draft", code="version_not_draft"
        )


def create_criterion(
    db: Session,
    actor: User,
    version_id: int,
    *,
    name_en: str,
    name_ar: str,
    guidance_en: str | None,
    guidance_ar: str | None,
    max_marks: int,
    input_mode: str,
    allow_negative: bool,
    auto_source: str,
    auto_params: dict[str, object] | None,
    sort_order: int,
) -> KpiCriterion:
    version = get_version(db, version_id)
    _require_draft(version)

    criterion = KpiCriterion(
        template_version_id=version.id,
        name_en=name_en,
        name_ar=name_ar,
        guidance_en=guidance_en,
        guidance_ar=guidance_ar,
        max_marks=max_marks,
        input_mode=input_mode,
        allow_negative=allow_negative,
        auto_source=auto_source,
        auto_params=auto_params,
        sort_order=sort_order,
    )
    db.add(criterion)
    db.flush()
    write_audit(
        db,
        actor_user_id=actor.id,
        action="create_kpi_criterion",
        entity_type="kpi_criterion",
        entity_id=criterion.id,
        after={"template_version_id": version_id, "name_en": name_en, "max_marks": max_marks},
    )
    db.commit()
    return criterion


def patch_criterion(db: Session, actor: User, criterion_id: int, **fields: object) -> KpiCriterion:
    criterion = db.get(KpiCriterion, criterion_id)
    if criterion is None:
        raise not_found("KPI criterion not found")
    _require_draft(criterion.version)

    before = {k: getattr(criterion, k) for k in fields if fields[k] is not None}
    for key, value in fields.items():
        if value is not None:
            setattr(criterion, key, value)

    write_audit(
        db,
        actor_user_id=actor.id,
        action="patch_kpi_criterion",
        entity_type="kpi_criterion",
        entity_id=criterion.id,
        before={k: str(v) for k, v in before.items()},
        after={k: str(getattr(criterion, k)) for k in before},
    )
    db.commit()
    return criterion


def delete_criterion(db: Session, actor: User, criterion_id: int) -> None:
    criterion = db.get(KpiCriterion, criterion_id)
    if criterion is None:
        raise not_found("KPI criterion not found")
    _require_draft(criterion.version)

    write_audit(
        db,
        actor_user_id=actor.id,
        action="delete_kpi_criterion",
        entity_type="kpi_criterion",
        entity_id=criterion.id,
        before={"name_en": criterion.name_en, "max_marks": criterion.max_marks},
    )
    db.delete(criterion)
    db.commit()


def activate_version(db: Session, actor: User, version_id: int) -> KpiTemplateVersion:
    version = get_version(db, version_id)
    _require_draft(version)

    total = sum(c.max_marks for c in version.criteria)
    if not version.criteria or total != 100:
        raise bad_request(
            f"Criteria max_marks must sum to exactly 100 (got {total})",
            code="criteria_sum_invalid",
        )

    previous_active = get_active_version(db, version.template_id)
    if previous_active is not None:
        previous_active.status = TemplateVersionStatus.ARCHIVED.value
        db.flush()

    version.status = TemplateVersionStatus.ACTIVE.value
    write_audit(
        db,
        actor_user_id=actor.id,
        action="activate_kpi_template_version",
        entity_type="kpi_template_version",
        entity_id=version.id,
        before={"previous_active_version_id": previous_active.id if previous_active else None},
        after={"version_no": version.version_no},
    )
    db.commit()
    return get_version(db, version.id)


def resolve_template_for_position(db: Session, position_id: int, as_of: date) -> KpiTemplate | None:
    """First-day-of-month rule: caller passes the first day of the relevant month."""
    stmt = select(KpiTemplateAssignment).where(
        KpiTemplateAssignment.position_id == position_id,
        KpiTemplateAssignment.effective_from <= as_of,
        (KpiTemplateAssignment.effective_to.is_(None))
        | (KpiTemplateAssignment.effective_to > as_of),
    )
    assignment = db.scalars(stmt).first()
    return assignment.template if assignment is not None else None


def list_assignments(db: Session, position_id: int) -> list[KpiTemplateAssignment]:
    get_position(db, position_id)  # 404 if missing
    stmt = (
        select(KpiTemplateAssignment)
        .where(KpiTemplateAssignment.position_id == position_id)
        .order_by(KpiTemplateAssignment.effective_from.desc())
    )
    return list(db.scalars(stmt))


def create_assignment(
    db: Session,
    actor: User,
    position_id: int,
    *,
    template_id: int,
    effective_from: date,
    effective_to: date | None,
) -> KpiTemplateAssignment:
    get_position(db, position_id)  # 404 if missing
    get_template(db, template_id)  # 404 if missing
    if effective_to is not None and effective_to <= effective_from:
        raise bad_request("effective_to must be after effective_from", code="invalid_date_range")

    assignment = KpiTemplateAssignment(
        position_id=position_id,
        template_id=template_id,
        effective_from=effective_from,
        effective_to=effective_to,
    )
    db.add(assignment)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise conflict(
            "This date range overlaps an existing KPI template assignment for the position",
            code="assignment_overlap",
        ) from exc

    write_audit(
        db,
        actor_user_id=actor.id,
        action="create_kpi_template_assignment",
        entity_type="kpi_template_assignment",
        entity_id=assignment.id,
        after={
            "position_id": position_id,
            "template_id": template_id,
            "effective_from": str(effective_from),
            "effective_to": str(effective_to) if effective_to else None,
        },
    )
    db.commit()
    return assignment
