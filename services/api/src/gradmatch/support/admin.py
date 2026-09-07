from django.contrib import admin

from gradmatch.system.admin import ReadOnlyHistoryAdmin

from .models import (
    AuditEvent,
    CorrectionCase,
    JobExecution,
    OutboxEvent,
    SnapshotUpdate,
    SnapshotUpdateNotification,
)

admin.site.register(  # pyright: ignore[reportUnknownMemberType]
    (
        CorrectionCase,
        AuditEvent,
        OutboxEvent,
        JobExecution,
        SnapshotUpdate,
        SnapshotUpdateNotification,
    ),
    ReadOnlyHistoryAdmin,
)
