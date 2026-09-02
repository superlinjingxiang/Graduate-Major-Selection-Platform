from __future__ import annotations

from .models import CoverageManifest

PILOT_MANIFEST_KEY = "coverage_2027_beijing_cs_ft_unified_v1"
PILOT_OFFERING_IDS = (
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
ENGINEERING_SLICE_OFFERING_IDS = frozenset(
    {
        "ao_2027_bupt_081200_ft_unified_plan01",
        "ao_2027_bit_085404_ft_unified_plan01",
        "ao_2027_bjut_085410_ft_unified_plan01",
    }
)


def get_pilot_manifest() -> CoverageManifest:
    return CoverageManifest.objects.get(key=PILOT_MANIFEST_KEY)
