# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = 'lab.core'

    def ready(self):
        from django.conf import settings
        settings.AUTH_USER_MODEL = 'core.CustomUser'
