from django.contrib import admin

from .models import (
    EligibilityAssessment,
    EligibilityRule,
    EvidenceClaimRevision,
    FactSet,
    FactSetRevision,
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
        FactSet,
        FactSetRevision,
        EligibilityAssessment,
        ReviewDecision,
        PublicationEvent,
        RuleSetRevision,
        EligibilityRule,
        RuleEvidenceUsage,
    )
)
