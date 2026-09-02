from datetime import UTC, datetime
from typing import Any

from django.db import migrations


MANIFEST_KEY = "coverage_2027_beijing_cs_ft_unified_v1"
TAXONOMY_KEY = "taxonomy_2027_cn_grad_computer_v1"
ENGINEERING_IDS = {
    "ao_2027_bupt_081200_ft_unified_plan01",
    "ao_2027_bit_085404_ft_unified_plan01",
    "ao_2027_bjut_085410_ft_unified_plan01",
}
INSTITUTIONS = (
    ("bupt", "北京邮电大学"),
    ("bit", "北京理工大学"),
    ("bjut", "北京工业大学"),
)
TAXONOMY_NODES = (
    ("081200", "计算机科学与技术", "academic_discipline"),
    ("083500", "软件工程", "academic_discipline"),
    ("083900", "网络空间安全", "academic_discipline"),
    ("085404", "计算机技术", "professional_field"),
    ("085405", "软件工程", "professional_field"),
    ("085410", "人工智能", "professional_field"),
)
OFFERINGS = (
    (
        "ao_2027_bupt_081200_ft_unified_plan01",
        "bupt",
        "081200",
        "计算机科学与技术",
        "academic",
    ),
    (
        "ao_2027_bupt_085404_ft_unified_plan01",
        "bupt",
        "085404",
        "计算机技术",
        "professional",
    ),
    (
        "ao_2027_bupt_085405_ft_unified_plan01",
        "bupt",
        "085405",
        "软件工程",
        "professional",
    ),
    (
        "ao_2027_bit_081200_ft_unified_plan01",
        "bit",
        "081200",
        "计算机科学与技术",
        "academic",
    ),
    (
        "ao_2027_bit_085404_ft_unified_plan01",
        "bit",
        "085404",
        "计算机技术",
        "professional",
    ),
    (
        "ao_2027_bjut_081200_ft_unified_plan01",
        "bjut",
        "081200",
        "计算机科学与技术",
        "academic",
    ),
    (
        "ao_2027_bjut_083500_ft_unified_plan01",
        "bjut",
        "083500",
        "软件工程",
        "academic",
    ),
    (
        "ao_2027_bjut_083900_ft_unified_plan01",
        "bjut",
        "083900",
        "网络空间安全",
        "academic",
    ),
    (
        "ao_2027_bjut_085404_ft_unified_plan01",
        "bjut",
        "085404",
        "计算机技术",
        "professional",
    ),
    (
        "ao_2027_bjut_085410_ft_unified_plan01",
        "bjut",
        "085410",
        "人工智能",
        "professional",
    ),
)


def seed_pilot_manifest(apps: Any, schema_editor: Any) -> None:
    del schema_editor
    coverage_manifest = apps.get_model("catalog", "CoverageManifest")
    institution_model = apps.get_model("catalog", "Institution")
    taxonomy_revision = apps.get_model("catalog", "TaxonomyRevision")
    taxonomy_node = apps.get_model("catalog", "TaxonomyNode")
    annual_offering = apps.get_model("catalog", "AnnualOffering")
    manifest_entry = apps.get_model("catalog", "ManifestEntry")

    manifest = coverage_manifest.objects.create(
        key=MANIFEST_KEY,
        version=1,
        target_year=2027,
        scope={
            "region": "北京",
            "study_mode": "full_time",
            "admission_pathway": "unified_exam",
            "discipline": "computer_related",
            "decision_stage": "shortlist_convergence",
        },
        frozen_at=datetime(2026, 9, 1, tzinfo=UTC),
    )
    institutions = {
        key: institution_model.objects.create(key=key, name=name)
        for key, name in INSTITUTIONS
    }
    revision = taxonomy_revision.objects.create(key=TAXONOMY_KEY, effective_year=2027)
    nodes = {
        code: taxonomy_node.objects.create(
            revision=revision,
            code=code,
            name=name,
            level_type=level_type,
        )
        for code, name, level_type in TAXONOMY_NODES
    }

    for position, (offering_id, institution_key, code, title, degree_type) in enumerate(
        OFFERINGS,
        start=1,
    ):
        offering = annual_offering.objects.create(
            id=offering_id,
            target_year=2027,
            institution=institutions[institution_key],
            taxonomy_node=nodes[code],
            title=title,
            degree_type=degree_type,
            study_mode="full_time",
            admission_pathway="unified_exam",
            publication_status="pending_publication",
        )
        manifest_entry.objects.create(
            manifest=manifest,
            offering=offering,
            position=position,
            engineering_slice=offering_id in ENGINEERING_IDS,
        )


def remove_pilot_manifest(apps: Any, schema_editor: Any) -> None:
    del schema_editor
    manifest_entry = apps.get_model("catalog", "ManifestEntry")
    annual_offering = apps.get_model("catalog", "AnnualOffering")
    coverage_manifest = apps.get_model("catalog", "CoverageManifest")
    taxonomy_node = apps.get_model("catalog", "TaxonomyNode")
    taxonomy_revision = apps.get_model("catalog", "TaxonomyRevision")
    institution_model = apps.get_model("catalog", "Institution")

    offering_ids = tuple(offering[0] for offering in OFFERINGS)
    manifest_entry.objects.filter(manifest__key=MANIFEST_KEY).delete()
    annual_offering.objects.filter(pk__in=offering_ids).delete()
    coverage_manifest.objects.filter(key=MANIFEST_KEY).delete()
    taxonomy_node.objects.filter(revision__key=TAXONOMY_KEY).delete()
    taxonomy_revision.objects.filter(key=TAXONOMY_KEY).delete()
    institution_model.objects.filter(key__in=tuple(item[0] for item in INSTITUTIONS)).delete()


class Migration(migrations.Migration):
    dependencies = [("catalog", "0001_initial")]

    operations = [migrations.RunPython(seed_pilot_manifest, remove_pilot_manifest)]
