from django.contrib import admin

from .models import (
    ComparisonAssessmentUsage,
    ComparisonRun,
    ComparisonRunResult,
    DecisionSnapshot,
    EligibilityAssessment,
    EligibilityRule,
    EvidenceClaimRevision,
    FactSet,
    FactSetRevision,
    GuestSession,
    PublicationEvent,
    ReviewDecision,
    RuleEvidenceUsage,
    RuleSetRevision,
    SourceDocumentRevision,
)

admin.site.register(  # pyright: ignore[reportUnknownMemberType]
    (
        SourceDocumentRevision,
        GuestSession,
        EvidenceClaimRevision,
        FactSet,
        FactSetRevision,
        EligibilityAssessment,
        ComparisonRun,
        ComparisonRunResult,
        ComparisonAssessmentUsage,
        DecisionSnapshot,
        ReviewDecision,
        PublicationEvent,
        RuleSetRevision,
        EligibilityRule,
        RuleEvidenceUsage,
    )
)
