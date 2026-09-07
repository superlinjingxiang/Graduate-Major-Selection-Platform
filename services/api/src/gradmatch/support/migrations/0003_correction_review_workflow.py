import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("support", "0002_outbox_dispatch_lease"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="correctioncase",
            name="review_started_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="correctioncase",
            name="reviewer",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="assigned_correction_cases",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="correctioncase",
            name="status",
            field=models.CharField(
                choices=[
                    ("submitted", "Submitted"),
                    ("reviewing", "Reviewing"),
                    ("accepted", "Accepted"),
                    ("published", "Published"),
                    ("rejected", "Rejected"),
                ],
                default="submitted",
                max_length=24,
            ),
        ),
        migrations.CreateModel(
            name="SnapshotUpdateNotification",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "recipient",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="snapshot_update_notifications",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "snapshot_update",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="notification",
                        to="support.snapshotupdate",
                    ),
                ),
            ],
            options={"ordering": ["created_at", "id"]},
        ),
    ]
