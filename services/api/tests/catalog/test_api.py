from __future__ import annotations

import pytest
from django.test import Client

from gradmatch.catalog.models import AnnualOffering, Institution, TaxonomyNode
from gradmatch.catalog.seed import PILOT_MANIFEST_KEY

PUBLIC_OFFERING_KEYS = {
    "id",
    "target_year",
    "institution_key",
    "institution_name",
    "program_code",
    "title",
    "degree_type",
    "study_mode",
    "admission_pathway",
    "publication_status",
}


@pytest.mark.django_db
def test_pilot_scope_exposes_the_frozen_public_boundary(client: Client) -> None:
    response = client.get("/api/v1/pilot-scope")

    assert response.status_code == 200
    assert response.json() == {
        "key": PILOT_MANIFEST_KEY,
        "version": 1,
        "target_year": 2027,
        "region": "北京",
        "study_mode": "full_time",
        "admission_pathway": "unified_exam",
        "discipline": "computer_related",
        "decision_stage": "shortlist_convergence",
        "offering_count": 10,
        "frozen_at": "2026-09-01T00:00:00Z",
    }


@pytest.mark.django_db
def test_taxonomy_exposes_only_the_frozen_revision(client: Client) -> None:
    response = client.get("/api/v1/taxonomy")

    assert response.status_code == 200
    payload = response.json()
    assert payload["revision"] == {
        "key": "taxonomy_2027_cn_grad_computer_v1",
        "effective_year": 2027,
    }
    assert [(node["code"], node["name"]) for node in payload["nodes"]] == [
        ("081200", "计算机科学与技术"),
        ("083500", "软件工程"),
        ("083900", "网络空间安全"),
        ("085404", "计算机技术"),
        ("085405", "软件工程"),
        ("085410", "人工智能"),
    ]
    assert all(
        set(node) == {"code", "name", "level_type", "parent_code"}
        for node in payload["nodes"]
    )


@pytest.mark.django_db
def test_offering_list_is_manifest_scoped_and_filterable(client: Client) -> None:
    institution = Institution.objects.get(key="bupt")
    taxonomy_node = TaxonomyNode.objects.get(code="081200")
    AnnualOffering.objects.create(
        id="ao_2027_outside_081200_ft_unified_plan01",
        target_year=2027,
        institution=institution,
        taxonomy_node=taxonomy_node,
        title="不在冻结清单中的项目",
        degree_type=AnnualOffering.DegreeType.ACADEMIC,
        study_mode=AnnualOffering.StudyMode.FULL_TIME,
        admission_pathway=AnnualOffering.AdmissionPathway.UNIFIED_EXAM,
        publication_status=AnnualOffering.PublicationStatus.PENDING_PUBLICATION,
    )

    response = client.get("/api/v1/offerings")

    assert response.status_code == 200
    payload = response.json()
    assert payload["manifest_key"] == PILOT_MANIFEST_KEY
    assert payload["count"] == 10
    assert len(payload["items"]) == 10
    assert all(set(item) == PUBLIC_OFFERING_KEYS for item in payload["items"])
    assert all("outside" not in item["id"] for item in payload["items"])

    filtered = client.get("/api/v1/offerings", {"institution": "bupt", "degree_type": "academic"})
    assert filtered.status_code == 200
    filtered_payload = filtered.json()
    assert filtered_payload["count"] == 1
    assert filtered_payload["items"][0]["id"] == "ao_2027_bupt_081200_ft_unified_plan01"


@pytest.mark.django_db
def test_offering_detail_hides_internal_and_fixture_fields(client: Client) -> None:
    offering_id = "ao_2027_bit_085404_ft_unified_plan01"

    response = client.get(f"/api/v1/offerings/{offering_id}")

    assert response.status_code == 200
    assert set(response.json()) == PUBLIC_OFFERING_KEYS
    assert response.json()["id"] == offering_id
    serialized = response.content.decode()
    assert "engineering_slice" not in serialized
    assert "reference_year" not in serialized
    assert "synthetic" not in serialized


@pytest.mark.django_db
def test_offering_detail_returns_not_found_outside_active_manifest(client: Client) -> None:
    institution = Institution.objects.get(key="bit")
    taxonomy_node = TaxonomyNode.objects.get(code="081200")
    outside = AnnualOffering.objects.create(
        id="ao_2027_private_081200_ft_unified_plan01",
        target_year=2027,
        institution=institution,
        taxonomy_node=taxonomy_node,
        title="不在清单中",
        degree_type=AnnualOffering.DegreeType.ACADEMIC,
        study_mode=AnnualOffering.StudyMode.FULL_TIME,
        admission_pathway=AnnualOffering.AdmissionPathway.UNIFIED_EXAM,
        publication_status=AnnualOffering.PublicationStatus.PENDING_PUBLICATION,
    )

    response = client.get(f"/api/v1/offerings/{outside.pk}")

    assert response.status_code == 404
