from typing import Any

from django.db import migrations

ROLE_NAMES = ("viewer", "editor", "reviewer", "administrator")


def seed_staff_roles(apps: Any, schema_editor: Any) -> None:
    del schema_editor
    Group = apps.get_model("auth", "Group")
    for name in ROLE_NAMES:
        Group.objects.get_or_create(name=name)


def remove_staff_roles(apps: Any, schema_editor: Any) -> None:
    del schema_editor
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name__in=ROLE_NAMES).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [migrations.RunPython(seed_staff_roles, remove_staff_roles)]
