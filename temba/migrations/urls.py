from __future__ import absolute_import, unicode_literals

from .views import MigrationCRUDL

urlpatterns = MigrationCRUDL().as_urlpatterns()
