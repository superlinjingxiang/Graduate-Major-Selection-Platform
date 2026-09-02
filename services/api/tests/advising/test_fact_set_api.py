from __future__ import annotations

import pytest
from django.test import Client

from gradmatch.advising.models import EligibilityAssessment, FactSet, FactSetRevision
from gradmatch.catalog.models import AnnualOffering, Institution, TaxonomyNode

VALID_FACTS = {
    "target_year": 2027,
    "region": "北京",
    "study_mode": "full_time",
    "admission_pathway": "unified_exam",
    "education_level": "bachelor",
    "undergraduate_major": "software_engineering",
    "cross_discipline": False,
}


@pytest.mark.django_db
def test_fact_set_api_persists_only_confirmed_allowlisted_facts(client: Client) -> None:
    response = client.post(
        "/api/v1/fact-sets",
        data={"confirmed_facts": VALID_FACTS},
        content_type="application/json",
    )

    assert response.status_code == 201
    payload = response.json()
    assert set(payload) == {
        "fact_set_id",
        "version",
        "confirmed_facts",
        "input_hash",
    }
    assert payload["version"] == 1
    assert payload["confirmed_facts"] == VALID_FACTS
    fact_set = FactSet.objects.get(pk=payload["fact_set_id"])
    revision = FactSetRevision.objects.get(fact_set=fact_set, version=1)
    assert revision.confirmed_facts == VALID_FACTS
    assert revision.input_hash == payload["input_hash"]


@pytest.mark.django_db
def test_fact_set_api_rejects_unknown_fact_keys(client: Client) -> None:
    response = client.post(
        "/api/v1/fact-sets",
        data={"confirmed_facts": {"target_year": 2027, "secret_score": 99}},
        content_type="application/json",
    )

    assert response.status_code == 422
    assert "secret_score" in response.json()["detail"]
    assert FactSet.objects.count() == 0


@pytest.mark.django_db
def test_production_assessment_api_never_exposes_fixture_controls(client: Client) -> None:
    fact_response = client.post(
        "/api/v1/fact-sets",
        data={"confirmed_facts": VALID_FACTS},
        content_type="application/json",
    )
    fact_set_id = fact_response.json()["fact_set_id"]

    response = client.post(
        "/api/v1/eligibility-assessments",
        data={
            "offering_id": "ao_2027_bupt_081200_ft_unified_plan01",
            "fact_set_id": fact_set_id,
            "fact_revision": 1,
        },
        content_type="application/json",
    )

    assert response.status_code == 201
    assert response.json()["status"] == EligibilityAssessment.Status.NEEDS_CONFIRMATION.value
    assert response.json()["reasons"] == [
        {"code": "rule_unpublished", "fact_key": None, "rule_key": None}
    ]
    serialized = response.content.decode()
    assert "test_fixture" not in serialized
    assert "synthetic" not in serialized
    assert "reference_year" not in serialized

    forbidden_switch = client.post(
        "/api/v1/eligibility-assessments",
        data={
            "offering_id": "ao_2027_bupt_081200_ft_unified_plan01",
            "fact_set_id": fact_set_id,
            "fact_revision": 1,
            "allow_test_fixture": True,
        },
        content_type="application/json",
    )
    assert forbidden_switch.status_code == 422


@pytest.mark.django_db
def test_assessment_api_rejects_off_manifest_offerings(client: Client) -> None:
    fact_response = client.post(
        "/api/v1/fact-sets",
        data={"confirmed_facts": VALID_FACTS},
        content_type="application/json",
    )
    institution = Institution.objects.get(key="bupt")
    taxonomy_node = TaxonomyNode.objects.get(code="081200")
    outside = AnnualOffering.objects.create(
        id="ao_2027_outside_assessment_plan01",
        target_year=2027,
        institution=institution,
        taxonomy_node=taxonomy_node,
        title="Outside assessment",
        degree_type=AnnualOffering.DegreeType.ACADEMIC,
        study_mode=AnnualOffering.StudyMode.FULL_TIME,
        admission_pathway=AnnualOffering.AdmissionPathway.UNIFIED_EXAM,
        publication_status=AnnualOffering.PublicationStatus.PENDING_PUBLICATION,
    )

    response = client.post(
        "/api/v1/eligibility-assessments",
        data={
            "offering_id": outside.pk,
            "fact_set_id": fact_response.json()["fact_set_id"],
            "fact_revision": 1,
        },
        content_type="application/json",
    )

    assert response.status_code == 404
