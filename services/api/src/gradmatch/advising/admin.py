from django.contrib import admin

from .models import (
    EligibilityRule,
    EvidenceClaimRevision,
    PublicationEvent,
    ReviewDecision,
    RuleEvidenceUsage,
    RuleSetRevision,
    SourceDocumentRevision,
)

admin.site.register(  # pyright: ignore[reportUnknownMemberType]
    (
        SourceDocumentRevision,
        EvidenceClaimRevision,
        ReviewDecision,
        PublicationEvent,
        RuleSetRevision,
        EligibilityRule,
        RuleEvidenceUsage,
    )
)
