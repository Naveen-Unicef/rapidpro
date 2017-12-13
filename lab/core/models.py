# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth.models import AbstractUser, Group, Permission
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models.signals import post_save
from django.dispatch.dispatcher import receiver
from django.utils.translation import gettext_lazy as _

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


class CustomUser(AbstractUser):
    estate = models.CharField(choices=INDIA_STATES, max_length=2)
    groups = models.ManyToManyField(
            Group,
            verbose_name=_('groups'),
            blank=True,
            help_text=_(
                    'The groups this user belongs to. A user will get all permissions '
                    'granted to each of their groups.'
            ),
            related_name="users",
            related_query_name="user",
    )
    user_permissions = models.ManyToManyField(
            Permission,
            verbose_name=_('user permissions'),
            blank=True,
            help_text=_('Specific permissions for this user.'),
            related_name="users",
            related_query_name="user",
    )


class GroupAssociation(models.Model):
    group = models.ForeignKey(Group)
    content_type = models.ForeignKey(ContentType,
                                     on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey()

    def __str__(self):
        return '{}({})'.format(self.group.name, self.content_type.model)


'''
Create GA when flow is created.
Update GA when flow is updated.
Drop GA when flow is droped.
'''


@receiver(post_save, sender=Flow)
def create_group(sender, instance, **kwargs):
    ct = ContentType.objects.get_for_model(sender)
    group, _ = Group.objects.get_or_create(name=instance.name,
                                           defaults={'name': instance.name})
    GroupAssociation.objects.get_or_create(group=group,
                                           content_type=ct,
                                           object_id=instance.id,
                                           defaults={
                                               'group': group,
                                               'content_object': instance
                                           })
