from __future__ import unicode_literals

from django.conf.urls import url
from rest_framework.urlpatterns import format_suffix_patterns

from lab.views import CoreView
from lab.views import OrgView

urlpatterns = [
    url(r'^orgs$', OrgView.as_view(), name='lab.orgs'),
    url(r'^$', CoreView.as_view(), name='lab.core'),
]
urlpatterns = format_suffix_patterns(urlpatterns, allowed=['json', 'api'])
