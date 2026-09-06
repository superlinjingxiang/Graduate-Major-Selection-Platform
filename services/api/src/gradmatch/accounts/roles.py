from __future__ import annotations

from django.db.models import Q

from gradmatch.accounts.models import User

VIEWER_ROLE = "viewer"
EDITOR_ROLE = "editor"
REVIEWER_ROLE = "reviewer"
ADMINISTRATOR_ROLE = "administrator"


def has_staff_role(user: User, role: str) -> bool:
    return User.objects.filter(
        pk=user.pk,
        is_active=True,
        is_staff=True,
    ).filter(
        Q(is_superuser=True) | Q(groups__name=role)
    ).exists()
