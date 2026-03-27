# Generated migration for ingest-time rate limiting

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ingest', '0018_merge_webhook_timeout_and_eventdedup'),
    ]

    operations = [
        migrations.AddField(
            model_name='trackedcontract',
            name='max_events_per_minute',
            field=models.IntegerField(blank=True, help_text='Max events per minute for ingest-time rate limiting (None = unlimited)', null=True),
        ),
    ]
