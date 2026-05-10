import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('subscriptions', '0002_remove_locationsubscription_address_text_and_more'),
        ('incidents', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='LGASubscription',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('lga', models.CharField(help_text='Lagos Local Government Area name', max_length=50)),
                ('whatsapp_number', models.CharField(blank=True, help_text='WhatsApp number for alerts (e.g. +2348012345678)', max_length=20)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='lga_subscriptions',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': 'LGA Subscription',
                'verbose_name_plural': 'LGA Subscriptions',
                'db_table': 'subscriptions_lgasubscription',
                'unique_together': {('user', 'lga')},
            },
        ),
        migrations.AddIndex(
            model_name='lgasubscription',
            index=models.Index(fields=['lga', 'is_active'], name='sub_lga_active_idx'),
        ),
        migrations.AddIndex(
            model_name='lgasubscription',
            index=models.Index(fields=['user', 'is_active'], name='sub_user_active_idx'),
        ),
        migrations.CreateModel(
            name='LGASubscriptionAlert',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sent_at', models.DateTimeField(auto_now_add=True)),
                ('subscription', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='alerts',
                    to='subscriptions.lgasubscription',
                )),
                ('incident', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    to='incidents.incident',
                )),
            ],
            options={
                'db_table': 'subscriptions_lgasubscriptionalert',
                'unique_together': {('subscription', 'incident')},
            },
        ),
    ]
