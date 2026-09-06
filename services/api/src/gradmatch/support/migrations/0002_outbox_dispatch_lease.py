from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("support", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="outboxevent",
            name="dispatch_attempts",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="outboxevent",
            name="last_dispatch_attempt_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
