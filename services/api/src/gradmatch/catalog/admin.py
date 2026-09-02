from django.contrib import admin

from .models import (
    AnnualOffering,
    CoverageManifest,
    Institution,
    ManifestEntry,
    TaxonomyNode,
    TaxonomyRevision,
)


@admin.register(CoverageManifest)
class CoverageManifestAdmin(admin.ModelAdmin):  # pyright: ignore[reportMissingTypeArgument]
    list_display = ("key", "version", "target_year", "frozen_at")
    search_fields = ("key",)
    readonly_fields = ("key", "version", "target_year", "scope", "frozen_at")


@admin.register(Institution)
class InstitutionAdmin(admin.ModelAdmin):  # pyright: ignore[reportMissingTypeArgument]
    list_display = ("key", "name")
    search_fields = ("key", "name")


@admin.register(TaxonomyRevision)
class TaxonomyRevisionAdmin(admin.ModelAdmin):  # pyright: ignore[reportMissingTypeArgument]
    list_display = ("key", "effective_year")
    search_fields = ("key",)


@admin.register(TaxonomyNode)
class TaxonomyNodeAdmin(admin.ModelAdmin):  # pyright: ignore[reportMissingTypeArgument]
    list_display = ("code", "name", "level_type", "revision")
    list_filter = ("revision", "level_type")
    search_fields = ("code", "name")


@admin.register(AnnualOffering)
class AnnualOfferingAdmin(admin.ModelAdmin):  # pyright: ignore[reportMissingTypeArgument]
    list_display = (
        "id",
        "institution",
        "taxonomy_node",
        "degree_type",
        "publication_status",
    )
    list_filter = ("target_year", "institution", "degree_type", "publication_status")
    search_fields = ("id", "title", "institution__name", "taxonomy_node__code")


@admin.register(ManifestEntry)
class ManifestEntryAdmin(admin.ModelAdmin):  # pyright: ignore[reportMissingTypeArgument]
    list_display = ("manifest", "position", "offering", "engineering_slice")
    list_filter = ("manifest", "engineering_slice")
    search_fields = ("offering__id", "offering__title")
