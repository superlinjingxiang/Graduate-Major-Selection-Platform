from django.contrib import admin

from .models import DataSource, IngestionRun, RawBlob, SourceFetch


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


@admin.register(RawBlob)
class RawBlobAdmin(admin.ModelAdmin):  # pyright: ignore[reportMissingTypeArgument]
    list_display = ("content_hash", "byte_size", "content_type", "created_at")
    list_filter = ("content_type",)
    search_fields = ("content_hash", "storage_key")
    readonly_fields = ("content_hash", "storage_key", "byte_size", "content_type", "created_at")


@admin.register(SourceFetch)
class SourceFetchAdmin(admin.ModelAdmin):  # pyright: ignore[reportMissingTypeArgument]
    list_display = ("id", "source", "status", "http_status", "requested_at", "fetched_at")
    list_filter = ("status", "source", "http_status")
    search_fields = ("source__key", "source_url", "etag", "last_modified", "error_summary")
    readonly_fields = (
        "source",
        "run",
        "source_url",
        "requested_at",
        "fetched_at",
        "http_status",
        "etag",
        "last_modified",
        "status",
        "blob",
        "error_summary",
    )
