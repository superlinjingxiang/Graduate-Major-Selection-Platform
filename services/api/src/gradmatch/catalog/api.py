from __future__ import annotations

from datetime import datetime

from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from ninja import Router, Schema

from .models import AnnualOffering, ManifestEntry, TaxonomyNode
from .seed import PILOT_MANIFEST_KEY, get_pilot_manifest

router = Router(tags=["catalog"])


class PilotScopeResponse(Schema):
    key: str
    version: int
    target_year: int
    region: str
    study_mode: str
    admission_pathway: str
    discipline: str
    decision_stage: str
    offering_count: int
    frozen_at: datetime


class TaxonomyRevisionResponse(Schema):
    key: str
    effective_year: int


class TaxonomyNodeResponse(Schema):
    code: str
    name: str
    level_type: str
    parent_code: str | None


class TaxonomyResponse(Schema):
    revision: TaxonomyRevisionResponse
    nodes: list[TaxonomyNodeResponse]


class OfferingResponse(Schema):
    id: str
    target_year: int
    institution_key: str
    institution_name: str
    program_code: str
    title: str
    degree_type: str
    study_mode: str
    admission_pathway: str
    publication_status: str


class OfferingListResponse(Schema):
    manifest_key: str
    count: int
    items: list[OfferingResponse]


@router.get("/pilot-scope", response=PilotScopeResponse, operation_id="get_pilot_scope")
def get_pilot_scope(request: HttpRequest) -> PilotScopeResponse:
    del request
    manifest = get_pilot_manifest()
    scope = manifest.scope
    return PilotScopeResponse(
        key=manifest.key,
        version=manifest.version,
        target_year=manifest.target_year,
        region=_scope_value(scope, "region"),
        study_mode=_scope_value(scope, "study_mode"),
        admission_pathway=_scope_value(scope, "admission_pathway"),
        discipline=_scope_value(scope, "discipline"),
        decision_stage=_scope_value(scope, "decision_stage"),
        offering_count=ManifestEntry.objects.filter(manifest=manifest).count(),
        frozen_at=manifest.frozen_at,
    )


@router.get("/taxonomy", response=TaxonomyResponse, operation_id="get_taxonomy")
def get_taxonomy(request: HttpRequest) -> TaxonomyResponse:
    del request
    manifest = get_pilot_manifest()
    nodes = list(
        TaxonomyNode.objects.filter(
            annual_offerings__manifest_entries__manifest=manifest
        )
        .select_related("revision", "parent")
        .distinct()
        .order_by("code")
    )
    revision = nodes[0].revision
    return TaxonomyResponse(
        revision=TaxonomyRevisionResponse(
            key=revision.key,
            effective_year=revision.effective_year,
        ),
        nodes=[
            TaxonomyNodeResponse(
                code=node.code,
                name=node.name,
                level_type=node.level_type,
                parent_code=node.parent.code if node.parent is not None else None,
            )
            for node in nodes
        ],
    )


@router.get("/offerings", response=OfferingListResponse, operation_id="list_offerings")
def list_offerings(
    request: HttpRequest,
    institution: str | None = None,
    degree_type: str | None = None,
) -> OfferingListResponse:
    del request
    queryset = _pilot_offerings()
    if institution is not None:
        queryset = queryset.filter(institution__key=institution)
    if degree_type is not None:
        queryset = queryset.filter(degree_type=degree_type)
    items = [_serialize_offering(offering) for offering in queryset]
    return OfferingListResponse(
        manifest_key=PILOT_MANIFEST_KEY,
        count=len(items),
        items=items,
    )


@router.get(
    "/offerings/{offering_id}",
    response=OfferingResponse,
    operation_id="get_offering",
)
def get_offering(request: HttpRequest, offering_id: str) -> OfferingResponse:
    del request
    offering = get_object_or_404(_pilot_offerings(), pk=offering_id)
    return _serialize_offering(offering)


def _pilot_offerings():  # pyright: ignore[reportUnknownParameterType, reportMissingParameterType]
    return (
        AnnualOffering.objects.filter(manifest_entries__manifest__key=PILOT_MANIFEST_KEY)
        .select_related("institution", "taxonomy_node")
        .order_by("manifest_entries__position")
    )


def _serialize_offering(offering: AnnualOffering) -> OfferingResponse:
    return OfferingResponse(
        id=offering.pk,
        target_year=offering.target_year,
        institution_key=offering.institution.key,
        institution_name=offering.institution.name,
        program_code=offering.taxonomy_node.code,
        title=offering.title,
        degree_type=offering.degree_type,
        study_mode=offering.study_mode,
        admission_pathway=offering.admission_pathway,
        publication_status=offering.publication_status,
    )


def _scope_value(scope: dict[str, object], key: str) -> str:
    value = scope.get(key)
    if not isinstance(value, str):
        raise RuntimeError(f"Pilot manifest scope is missing string field '{key}'.")
    return value
