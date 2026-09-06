import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_seed_staff_roles"),
        ("advising", "0003_comparisonrun_comparisonrunresult_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="sourcedocumentrevision",
            name="created_by",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="created_source_document_revisions",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="evidenceclaimrevision",
            name="created_by",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="created_evidence_claim_revisions",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="rulesetrevision",
            name="created_by",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="created_rule_set_revisions",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
