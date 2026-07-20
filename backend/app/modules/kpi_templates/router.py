from typing import Annotated

from fastapi import APIRouter, Depends

from app.common.enums import RoleCode
from app.core.deps import CurrentUser, DbSession, require_roles
from app.modules.auth.models import User
from app.modules.kpi_templates import service
from app.modules.kpi_templates.models import (
    KpiCriterion,
    KpiTemplate,
    KpiTemplateAssignment,
    KpiTemplateVersion,
)
from app.modules.kpi_templates.schemas import (
    CloneVersionRequest,
    KpiCriterionCreateRequest,
    KpiCriterionOut,
    KpiCriterionPatchRequest,
    KpiTemplateAssignmentCreateRequest,
    KpiTemplateAssignmentOut,
    KpiTemplateCreateRequest,
    KpiTemplateOut,
    KpiTemplateVersionOut,
    KpiTemplateVersionSummary,
)

TemplateWriters = Annotated[User, Depends(require_roles(RoleCode.PMO, RoleCode.ADMIN))]
AssignmentWriters = Annotated[User, Depends(require_roles(RoleCode.PMO, RoleCode.HR))]

router = APIRouter(prefix="/kpi-templates", tags=["kpi-templates"])
positions_router = APIRouter(prefix="/positions", tags=["kpi-templates"])


def _criterion_to_out(criterion: KpiCriterion) -> KpiCriterionOut:
    return KpiCriterionOut(
        id=criterion.id,
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


def _version_to_out(version: KpiTemplateVersion) -> KpiTemplateVersionOut:
    return KpiTemplateVersionOut(
        id=version.id,
        template_id=version.template_id,
        version_no=version.version_no,
        status=version.status,
        criteria=[_criterion_to_out(c) for c in version.criteria],
        total_marks=sum(c.max_marks for c in version.criteria),
    )


def _version_to_summary(version: KpiTemplateVersion) -> KpiTemplateVersionSummary:
    return KpiTemplateVersionSummary(
        id=version.id,
        version_no=version.version_no,
        status=version.status,
        total_marks=sum(c.max_marks for c in version.criteria),
    )


def _template_to_out(db: DbSession, template: KpiTemplate) -> KpiTemplateOut:
    active = service.get_active_version(db, template.id)
    return KpiTemplateOut(
        id=template.id,
        code=template.code,
        name_en=template.name_en,
        name_ar=template.name_ar,
        active_version=_version_to_summary(active) if active is not None else None,
    )


def _assignment_to_out(assignment: KpiTemplateAssignment) -> KpiTemplateAssignmentOut:
    return KpiTemplateAssignmentOut(
        id=assignment.id,
        position_id=assignment.position_id,
        template_id=assignment.template_id,
        effective_from=assignment.effective_from,
        effective_to=assignment.effective_to,
    )


@router.get("", response_model=list[KpiTemplateOut])
def list_templates_endpoint(_user: CurrentUser, db: DbSession) -> list[KpiTemplateOut]:
    return [_template_to_out(db, t) for t in service.list_templates(db)]


@router.post("", response_model=KpiTemplateOut, status_code=201)
def create_template_endpoint(
    payload: KpiTemplateCreateRequest, actor: TemplateWriters, db: DbSession
) -> KpiTemplateOut:
    template = service.create_template(
        db, actor, code=payload.code, name_en=payload.name_en, name_ar=payload.name_ar
    )
    return _template_to_out(db, template)


@router.get("/{template_id}", response_model=KpiTemplateOut)
def get_template_endpoint(template_id: int, _user: CurrentUser, db: DbSession) -> KpiTemplateOut:
    return _template_to_out(db, service.get_template(db, template_id))


@router.get("/{template_id}/versions", response_model=list[KpiTemplateVersionOut])
def list_versions_endpoint(
    template_id: int, _user: CurrentUser, db: DbSession
) -> list[KpiTemplateVersionOut]:
    return [_version_to_out(v) for v in service.list_versions(db, template_id)]


@router.post("/{template_id}/versions", response_model=KpiTemplateVersionOut, status_code=201)
def clone_version_endpoint(
    template_id: int, payload: CloneVersionRequest, actor: TemplateWriters, db: DbSession
) -> KpiTemplateVersionOut:
    version = service.clone_version(
        db, actor, template_id, source_version_id=payload.source_version_id
    )
    return _version_to_out(version)


@router.get("/versions/{version_id}", response_model=KpiTemplateVersionOut)
def get_version_endpoint(
    version_id: int, _user: CurrentUser, db: DbSession
) -> KpiTemplateVersionOut:
    return _version_to_out(service.get_version(db, version_id))


@router.post("/versions/{version_id}/activate", response_model=KpiTemplateVersionOut)
def activate_version_endpoint(
    version_id: int, actor: TemplateWriters, db: DbSession
) -> KpiTemplateVersionOut:
    return _version_to_out(service.activate_version(db, actor, version_id))


@router.post("/versions/{version_id}/criteria", response_model=KpiCriterionOut, status_code=201)
def create_criterion_endpoint(
    version_id: int, payload: KpiCriterionCreateRequest, actor: TemplateWriters, db: DbSession
) -> KpiCriterionOut:
    criterion = service.create_criterion(
        db,
        actor,
        version_id,
        name_en=payload.name_en,
        name_ar=payload.name_ar,
        guidance_en=payload.guidance_en,
        guidance_ar=payload.guidance_ar,
        max_marks=payload.max_marks,
        input_mode=payload.input_mode.value,
        allow_negative=payload.allow_negative,
        auto_source=payload.auto_source.value,
        auto_params=payload.auto_params,
        sort_order=payload.sort_order,
    )
    return _criterion_to_out(criterion)


@router.patch("/criteria/{criterion_id}", response_model=KpiCriterionOut)
def patch_criterion_endpoint(
    criterion_id: int, payload: KpiCriterionPatchRequest, actor: TemplateWriters, db: DbSession
) -> KpiCriterionOut:
    fields = payload.model_dump()
    if payload.input_mode is not None:
        fields["input_mode"] = payload.input_mode.value
    if payload.auto_source is not None:
        fields["auto_source"] = payload.auto_source.value
    criterion = service.patch_criterion(db, actor, criterion_id, **fields)
    return _criterion_to_out(criterion)


@router.delete("/criteria/{criterion_id}", status_code=204)
def delete_criterion_endpoint(criterion_id: int, actor: TemplateWriters, db: DbSession) -> None:
    service.delete_criterion(db, actor, criterion_id)


@positions_router.get(
    "/{position_id}/kpi-template-assignments", response_model=list[KpiTemplateAssignmentOut]
)
def list_assignments_endpoint(
    position_id: int, _user: CurrentUser, db: DbSession
) -> list[KpiTemplateAssignmentOut]:
    return [_assignment_to_out(a) for a in service.list_assignments(db, position_id)]


@positions_router.post(
    "/{position_id}/kpi-template-assignments",
    response_model=KpiTemplateAssignmentOut,
    status_code=201,
)
def create_assignment_endpoint(
    position_id: int,
    payload: KpiTemplateAssignmentCreateRequest,
    actor: AssignmentWriters,
    db: DbSession,
) -> KpiTemplateAssignmentOut:
    assignment = service.create_assignment(
        db,
        actor,
        position_id,
        template_id=payload.template_id,
        effective_from=payload.effective_from,
        effective_to=payload.effective_to,
    )
    return _assignment_to_out(assignment)
