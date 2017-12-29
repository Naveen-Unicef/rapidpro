import logging

from celery.task import task

from .models import Migration


@task(track_started=True, name='fire_data_migration')
def fire_data_migration(migration_id):
    migration = Migration.objects.get(pk=migration_id)

    logging.warning('Migrating contacts...')
    migration.migrate_contacts()

    logging.warning('---------------------')
    logging.warning('Migrating groups...')
    migration.migrate_groups()

    logging.warning('---------------------')
    logging.warning('Migrating flows...')
    migration.migrate_flows()

    logging.warning('---------------------')
    logging.warning('Migrating campaigns...')
    migration.migrate_campaigns()

    logging.warning('---------------------')
    logging.warning('Migrating flow starts...')
    migration.migrate_flow_starts()

    logging.warning('---------------------')
    logging.warning('Migrating flow runs...')
    migration.migrate_flow_runs()

    logging.warning('---------------------')
    logging.warning('Migrating broadcasts...')
    migration.migrate_broadcasts()

    logging.warning('---------------------')
    logging.warning('Migrating messages...')
    migration.migrate_messages()

    logging.warning('---------------------')
    logging.warning('Migrating labels...')
    migration.migrate_labels()

    logging.warning('---------------------')
    logging.warning('Migration completed!')

    return migration
