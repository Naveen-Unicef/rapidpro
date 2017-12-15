# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.apps import AppConfig
from django.apps import apps
from django.db.models import Manager


class LabConfig(AppConfig):
    name = 'lab'

    def ready(self):
        """
        Dynamic injection of our custom model(BlackMage).
        """
        class BlackMage(Manager):

            def get_queryset(self):
                model_name = '%s.%s' % (self.model._meta.app_label, self.model.__name__)
                print('BlackMage.get_queryset for %s' % model_name)
                qs = super(BlackMage, self).get_queryset()
                return qs

        models = (model for model in apps.get_models(True) if 'temba.' in model.__module__)
        for model in models:
            manager = BlackMage()
            manager.model = model
            model.objects = manager
