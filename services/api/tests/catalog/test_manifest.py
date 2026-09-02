from __future__ import annotations

import pytest

from gradmatch.catalog.models import AnnualOffering, CoverageManifest, ManifestEntry
from gradmatch.catalog.seed import (
    ENGINEERING_SLICE_OFFERING_IDS,
    PILOT_MANIFEST_KEY,
    PILOT_OFFERING_IDS,
)

EXPECTED_OFFERING_IDS = (
    "ao_2027_bupt_081200_ft_unified_plan01",
    "ao_2027_bupt_085404_ft_unified_plan01",
    "ao_2027_bupt_085405_ft_unified_plan01",
    "ao_2027_bit_081200_ft_unified_plan01",
    "ao_2027_bit_085404_ft_unified_plan01",
    "ao_2027_bjut_081200_ft_unified_plan01",
    "ao_2027_bjut_083500_ft_unified_plan01",
    "ao_2027_bjut_083900_ft_unified_plan01",
    "ao_2027_bjut_085404_ft_unified_plan01",
    "ao_2027_bjut_085410_ft_unified_plan01",
)

EXPECTED_ENGINEERING_IDS = frozenset(
    {
        "ao_2027_bupt_081200_ft_unified_plan01",
        "ao_2027_bit_085404_ft_unified_plan01",
        "ao_2027_bjut_085410_ft_unified_plan01",
    }
)


@pytest.mark.django_db
def test_frozen_manifest_contains_the_exact_ten_planned_offerings() -> None:
    manifest = CoverageManifest.objects.get(key=PILOT_MANIFEST_KEY)
    entries = list(
        ManifestEntry.objects.filter(manifest=manifest)
        .select_related("offering")
        .order_by("position")
    )

    assert manifest.version == 1
    assert manifest.target_year == 2027
    assert tuple(entry.offering.pk for entry in entries) == EXPECTED_OFFERING_IDS
    assert PILOT_OFFERING_IDS == EXPECTED_OFFERING_IDS
    assert ENGINEERING_SLICE_OFFERING_IDS == EXPECTED_ENGINEERING_IDS
    assert {entry.offering.pk for entry in entries if entry.engineering_slice} == (
        EXPECTED_ENGINEERING_IDS
    )


@pytest.mark.django_db
def test_every_pilot_offering_starts_pending_and_in_scope() -> None:
    offerings = AnnualOffering.objects.filter(
        manifest_entries__manifest__key=PILOT_MANIFEST_KEY
    ).order_by("id")

    assert offerings.count() == 10
    for offering in offerings:
        assert offering.target_year == 2027
        assert offering.study_mode == AnnualOffering.StudyMode.FULL_TIME
        assert offering.admission_pathway == AnnualOffering.AdmissionPathway.UNIFIED_EXAM
        assert offering.publication_status == AnnualOffering.PublicationStatus.PENDING_PUBLICATION
        assert offering.institution.key in {"bupt", "bit", "bjut"}
        assert offering.taxonomy_node.revision.effective_year == 2027
