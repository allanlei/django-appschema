from django.core.management import call_command
from django.db.backends import signals
from django.db import transaction
from django.conf import settings

from south.models import MigrationHistory
from south.management.commands import syncdb

from appschema import schema


def set_schema(*args, **kwargs):
    schema.schema_store.set_schema(schema.schema_store.current_schema())

signals.connection_created.connect(set_schema)


def schema_post_save(sender, instance, created=False, *args, **kwargs):
    if created:
        try:
            schema.create(instance.name)
            call_command('syncdb', interactive=False, hostname=instance.public_name)
            try:
                migration = MigrationHistory.objects.latest('applied')
            except MigrationHistory.DoesNotExist:
                migration = None
            if migration:
                call_command('migrate', migration.app_name, migration.migration, hostname=instance.public_name)
            else:
                call_command('migrate', hostname=instance.public_name)
        except Exception, err:
            print err
            instance.delete()
            raise err
        
def schema_post_delete(sender, instance, *args, **kwargs):
    try:
        schema.drop(instance.name)
    except Exception, err:
        raise err

def schema_post_init(sender, instance, *args, **kwargs):
    if getattr(settings, 'APPSCHEMA_ENSURE_SCHEMA', False) and instance.pk and not instance.exists():
        print 'Recreating...'
        schema_post_save(sender=sender, instance=instance, created=True)
        instance.recreated = True
