# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django.db import models
from django.db.models.signals import post_delete, post_save
from django.dispatch.dispatcher import receiver

from temba.flows.models import Flow
from temba.orgs.models import Org

INDIA_STATES = (('AP', 'Andhra Pradesh'),
                ('AR', 'Arunachal Pradesh'),
                ('AS', 'Assam'),
                ('BR', 'Bihar'),
                ('CG', 'Chhattisgarh'),
                ('GA', 'Goa'),
                ('GJ', 'Gujarat'),
                ('HR', 'Haryana'),
                ('HP', 'Himachal Pradesh'),
                ('JK', 'Jammu and Kashmir'),
                ('JH', 'Jharkhand'),
                ('KA', 'Karnataka'),
                ('KL', 'Kerala'),
                ('MP', 'Madhya Pradesh'),
                ('MH', 'Maharashtra'),
                ('MN', 'Manipur'),
                ('ML', 'Meghalaya'),
                ('MZ', 'Mizoram'),
                ('NL', 'Nagaland'),
                ('OR', 'Orissa'),
                ('PB', 'Punjab'),
                ('RJ', 'Rajasthan'),
                ('SK', 'Sikkim'),
                ('TN', 'Tamil Nadu'),
                ('TR', 'Tripura'),
                ('UK', 'Uttarakhand'),
                ('UP', 'Uttar Pradesh'),
                ('WB', 'West Bengal'),
                ('TN', 'Tamil Nadu'),
                ('TR', 'Tripura'),
                ('AN', 'Andaman and Nicobar Islands'),
                ('CH', 'Chandigarh'),
                ('DH', 'Dadra and Nagar Haveli'),
                ('DD', 'Daman and Diu'),
                ('DL', 'Delhi'),
                ('LD', 'Lakshadweep'),
                ('PY', 'Pondicherry'),
                )

class UserState(models.Model):
    """
    Essa classe precisa ser reformulada.

    Um usuário pode ser associado a mais de um estado.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='state')
    state = models.CharField(choices=INDIA_STATES, max_length=2)

    def __str__(self):
        return '{}({})'.format(self.get_state_display(), self.state)


class GroupAssociation(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    content_type = models.ForeignKey(ContentType,
                                     on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey()

    def __str__(self):
        return '{}({})'.format(self.group.name, self.content_type.model)


###################################################################################################
# Signals
###################################################################################################

@receiver(post_save, sender=Org)
@receiver(post_save, sender=Flow)
def create_group(sender, instance, **kwargs):
    ct = ContentType.objects.get_for_model(sender)
    state = instance.created_by.state
    group_name = str(state)
    group, _ = Group.objects.get_or_create(name=group_name,
                                           defaults={'name': group_name})
    GroupAssociation.objects.get_or_create(group=group,
                                           content_type=ct,
                                           object_id=instance.id,
                                           defaults={
                                               'group': group,
                                               'content_object': instance
                                           })

def username_to_database(username):
    """
    Convert username to format accepted by database username.

    The database cannot accept username in email format, because that we change some characters:
    @ => __at__
    . => __dot__
    foo@bar.com => foo__at__bar__dot__com
    """
    return username.replace('@', '__at__').replace('.', '__dot__')

def database_user_exists(username):
    """
    Check if postgres database user exists.
    """
    with connection.cursor() as cursor:
        select_user_sql = "SELECT COUNT(*) FROM pg_catalog.pg_user WHERE usename = %s"
        cursor.execute(select_user_sql, [username, ])
        return cursor.fetchone()[0] > 0


@receiver(post_save, sender=User)
def create_database_role(instance, **kwargs):
    """
    Create a new postgres rule for Django user.
    """
    database_username = username_to_database(instance.username)
    print('creating database role: %s' % database_username)

    username, password = database_username, settings.DATABASES['default']['PASSWORD']

    grant_commands = (
        "GRANT ALL ON ALL TABLES IN SCHEMA public TO %s",
        "GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO %s"
    )
    if not database_user_exists(username):
        with connection.cursor() as cursor:
            create_user_sql = "CREATE USER %s WITH ENCRYPTED PASSWORD %%s" % username
            cursor.execute(create_user_sql, [password, ])
            for grant_sql in grant_commands:
                grant_sql = grant_sql % username
                cursor.execute(grant_sql)

@receiver(post_delete, sender=User)
def drop_database_role(instance, **kwargs):
    """
    Drop postgres rule when Django user is delete.
    """
    print('drop user %s' % instance.username)
    database_username = username_to_database(instance.username)
    if database_user_exists(database_username):
        with connection.cursor() as cursor:
            sql = "DROP USER %s" % database_username
            cursor.execute(sql)
