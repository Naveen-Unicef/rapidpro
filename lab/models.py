# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from django.db import transaction
from django.utils import timezone

from temba.channels.models import Channel
from temba.contacts.models import Contact
from temba.orgs.models import Org


class ContactSecondaryOrg(models.Model):
    contact = models.OneToOneField(Contact, on_delete=models.CASCADE, related_name='secondary_org')
    org = models.ForeignKey(Org, on_delete=models.CASCADE, related_name='contact_secondary_org')

    def __str__(self):
        return '{}.{}'.format(self.contact, self.org)


def move_contact_to_org(contact, new_org):
    import uuid
    with transaction.atomic():
        original_org = contact.org
        ContactSecondaryOrg.objects.create(contact=contact, org=new_org)
        for channel in original_org.channels.all():
            channel_name = '{} - {}'.format(channel.name, new_org.name)
            if not Channel.objects.filter(name=channel_name, org=new_org).exists():
                channel.pk = None
                channel.uuid = uuid.uuid4()
                channel.org = new_org
                channel.name = channel_name
                channel.created_at = timezone.datetime.now()
                channel.modified_at = timezone.datetime.now()
                channel.save()
            # new_org.channels.add(channel)
        for contact_group in contact.all_groups.filter(org=original_org):
            contact_group.contacts.remove(contact)
        all_contacts_group = new_org.all_groups.get(name__icontains='all')
        all_contacts_group.contacts.add(contact)
        contact.org = new_org
        contact.save()
