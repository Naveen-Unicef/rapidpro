# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.views.generic import TemplateView


class CoreView(TemplateView):
    template_name = 'core.html'
