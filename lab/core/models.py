# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth.models import Group
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models.signals import post_save
from django.dispatch.dispatcher import receiver

from temba.flows.models import Flow


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
                                               'content_type': ct,
                                               'object_id': instance.id
                                           })
