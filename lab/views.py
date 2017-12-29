# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db.models import Q
from django.views.generic import TemplateView
from rest_framework import status
from rest_framework.response import Response

from temba.api.v2.views import BaseAPIView
from temba.orgs.models import Org


class CoreView(TemplateView):
    template_name = 'core.html'


class OrgView(BaseAPIView):
    """
    Return the orgs that can be used by action MoveToOrg.
    """
    permission = 'orgs.org_api'

    def get(self, request, *args, **kwargs):
        org = request.user.get_org()
        parent_org = org if org.parent is None else org.parent
        orgs = Org.objects.filter(Q(id=parent_org.pk) | Q(parent=parent_org)).values('id', 'name')
        data = []

        for org in orgs:
            item = {}
            for k, v in org.items():
                item['uuid' if k == 'id' else k] = v
            data.append(item)

        return Response(data, status=status.HTTP_200_OK)

    @classmethod
    def get_read_explorer(cls):
        return {
            'method': "GET",
            'title': "View Current Org",
            'url': reverse('api.v2.org'),
            'slug': 'org-read'
        }
