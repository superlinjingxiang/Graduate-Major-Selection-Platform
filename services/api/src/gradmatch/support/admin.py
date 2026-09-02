from django.contrib import admin

from .models import AuditEvent, CorrectionCase, JobExecution, OutboxEvent, SnapshotUpdate

admin.site.register(  # pyright: ignore[reportUnknownMemberType]
    (CorrectionCase, AuditEvent, OutboxEvent, JobExecution, SnapshotUpdate)
)
