from django.core.management.base import BaseCommand
from django.apps import apps
from django.db import connections
from django.db import transaction


class Command(BaseCommand):
    help = 'Migrate all data from database 1 to database 2'

    def handle(self, *args, **options):
        # ignore_models = ['Session', 'PostGISGeometryColumns', 'PostGISSpatialRefSys', 'Token']
        ignore_models = ['PostGISGeometryColumns', 'PostGISSpatialRefSys']
        # Some models don't use id as pk field.
        differente_pk_name = {
            'Token': 'key',
            'APIToken': 'key',
            'Session': 'session_key',
        }
        migrate_to = connections['rp2']
        migrate_to.set_autocommit(False)
        with migrate_to.cursor() as cursor:
            filtered_models = [model for model in apps.get_models() if model.__name__ not in ignore_models]

            print('Disable all triggers')
            for model in filtered_models:
                sql = 'ALTER TABLE {} DISABLE TRIGGER ALL;'
                sql = sql.format(model._meta.db_table)
                cursor.execute(sql)

            for model in filtered_models:
                print('Migrating data from model {}.{}'.format(model._meta.app_label, model.__name__))
                pk_field = differente_pk_name.get(model.__name__, 'id')
                # We need to ignore all values that has been exist.
                filter_by = {
                    '{}__in'.format(pk_field): list(model._meta.default_manager.using('rp2').values_list(pk_field, flat=True))
                }
                objs = list(model._meta.default_manager.exclude(**filter_by).values())
                model._meta.default_manager.using('rp2').bulk_create([model(**kwargs) for kwargs in objs])

            print('Enable all triggers')
            for model in filtered_models:
                sql = 'ALTER TABLE {} ENABLE TRIGGER ALL;'
                sql = sql.format(model._meta.db_table)
                cursor.execute(sql)
            print('Reset all sequences')
            reset_sequences = '''
                SELECT 'SELECT SETVAL(' ||
                       quote_literal(quote_ident(PGT.schemaname) || '.' || quote_ident(S.relname)) ||
                       ', COALESCE(MAX(' ||quote_ident(C.attname)|| '), 1) ) FROM ' ||
                       quote_ident(PGT.schemaname)|| '.'||quote_ident(T.relname)|| ';'
                FROM pg_class AS S,
                     pg_depend AS D,
                     pg_class AS T,
                     pg_attribute AS C,
                     pg_tables AS PGT
                WHERE S.relkind = 'S'
                    AND S.oid = D.objid
                    AND D.refobjid = T.oid
                    AND D.refobjid = C.attrelid
                    AND D.refobjsubid = C.attnum
                    AND T.relname = PGT.tablename
                ORDER BY S.relname;
            '''
            cursor.execute(reset_sequences)
            transaction.commit(using='rp2')