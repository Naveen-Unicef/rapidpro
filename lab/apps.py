# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.apps import AppConfig
from django.db import models
from django.utils.datastructures import ImmutableList


class LabConfig(AppConfig):
    name = 'lab'

    def ready(self):
        from temba.orgs.models import Org

        class BlackMage(models.Manager):

            def get_queryset(self):
                print('BlackMage.get_queryset')
                qs = super(BlackMage, self).get_queryset()
                return qs

        manager = BlackMage()
        manager.model = Org
        Org.objects = manager
