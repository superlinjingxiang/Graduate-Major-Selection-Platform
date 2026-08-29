from django.contrib import admin

from .models import DataSource, IngestionRun, RawArtifact


@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):  # pyright: ignore[reportMissingTypeArgument]
    list_display = ("key", "name", "enabled", "rate_limit_per_minute", "updated_at")
    list_filter = ("enabled",)
    search_fields = ("key", "name", "base_url")


@admin.register(IngestionRun)
class IngestionRunAdmin(admin.ModelAdmin):  # pyright: ignore[reportMissingTypeArgument]
    list_display = ("id", "source", "status", "records_seen", "records_accepted", "started_at")
    list_filter = ("status", "source")
    search_fields = ("source__key", "error_summary")
    readonly_fields = ("started_at", "finished_at")


@admin.register(RawArtifact)
class RawArtifactAdmin(admin.ModelAdmin):  # pyright: ignore[reportMissingTypeArgument]
    list_display = ("content_hash", "source", "content_type", "fetched_at")
    list_filter = ("source", "content_type")
    search_fields = ("content_hash", "storage_key", "source_url")
