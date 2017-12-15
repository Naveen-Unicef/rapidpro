from __future__ import unicode_literals

from django.conf.urls import url

from lab.views import CoreView

urlpatterns = [
    url(r'^$', CoreView.as_view(), name='lab.core'),
]
