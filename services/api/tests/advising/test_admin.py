from __future__ import annotations

from typing import cast

import pytest
from django.contrib import admin
from django.db.models import Model
from django.test import RequestFactory

from gradmatch.accounts.models import User
from gradmatch.advising.models import (
    EligibilityRule,
    EvidenceClaimRevision,
    PublicationEvent,
    ReviewDecision,
    RuleEvidenceUsage,
    RuleSetRevision,
    SourceDocumentRevision,
)
from gradmatch.support.models import AuditEvent, JobExecution, OutboxEvent, SnapshotUpdate
from gradmatch.system.admin import ReadOnlyHistoryAdmin


@pytest.mark.django_db
@pytest.mark.parametrize(
    "model",
    [
        SourceDocumentRevision,
        EvidenceClaimRevision,
        ReviewDecision,
        PublicationEvent,
        RuleSetRevision,
        EligibilityRule,
        RuleEvidenceUsage,
        AuditEvent,
        OutboxEvent,
        JobExecution,
        SnapshotUpdate,
    ],
)
def test_workflow_history_is_read_only_even_for_admin_users(model: type[Model]) -> None:
    operator = User.objects.create_superuser(
        email="admin@example.test",
        password="strong-password-123",
    )
    request = RequestFactory().get("/admin/")
    request.user = operator
    registry = cast(
        dict[type[Model], ReadOnlyHistoryAdmin],
        admin.site._registry,  # pyright: ignore[reportUnknownMemberType]
    )
    model_admin = registry[model]

    assert model_admin.has_add_permission(request) is False
    assert model_admin.has_change_permission(request) is False
    assert model_admin.has_delete_permission(request) is False
