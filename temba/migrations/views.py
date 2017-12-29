# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import requests
from django import forms
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.forms import Form
from django.utils.translation import ugettext_lazy as _
from smartmin.views import SmartCRUDL, SmartFormView

from temba.orgs.views import InferOrgMixin, OrgPermsMixin
from temba.utils import on_transaction_commit
from temba.utils.http import http_headers
from .models import Migration
from .tasks import fire_data_migration

TEMBA_HEADERS = http_headers()


class MigrationCRUDL(SmartCRUDL):
    actions = ('import', )

    model = Migration

    class Import(InferOrgMixin, OrgPermsMixin, SmartFormView):
        title = _('Import data from other host')
        submit_button_name = _('Get data')

        class DataImportForm(Form):
            api_host = forms.CharField(label=_('API Host'), help_text=_('API host (e.g. https://app.rapidpro.io)'))

            api_token = forms.CharField(label=_('API Token'),
                                        help_text=_('API token (e.g. e674fa1230ee81045199d1c549f000000c3b7296)'))

            channels = forms.CharField(label=_('Channels'),
                                       help_text=_('JSON with the channels related (e.g. {"source_channel_uuid": '
                                                   '"destination_channel_uuid"}). Remember to migrate the '
                                                   'channels before this step.'),
                                       widget=forms.Textarea(attrs={'style': 'height: 150px'}))

            def __init__(self, *args, **kwargs):
                self.org = kwargs['org']
                del kwargs['org']
                super(MigrationCRUDL.Import.DataImportForm, self).__init__(*args, **kwargs)

            def clean(self):
                # make sure they are in the proper tier
                if not self.org.is_import_flows_tier():
                    raise ValidationError("Sorry, import is a premium feature")

                api_host = self.cleaned_data.get('api_host')
                api_token = self.cleaned_data.get('api_token')
                channels = self.cleaned_data.get('channels')

                if not api_host or not api_token:
                    raise ValidationError("Sorry, fill API host and API token fields")

                if not api_host.startswith('http'):
                    api_host = 'https://%s' % api_host

                if api_host.endswith('/'):
                    api_host = api_host[:-1]

                if not api_token.startswith('Token'):
                    self.cleaned_data['api_token'] = 'Token %s' % api_token

                self.cleaned_data['api_host'] = api_host

                headers = TEMBA_HEADERS.copy()
                headers.update({
                    'Authorization': 'Token %s' % api_token,
                    'Content-Type': 'application/json'
                })
                response = requests.get('%s/api/v2/org.json' % api_host, headers=headers)
                if response.status_code != 200:
                    raise ValidationError(_('API host unreached, check the credentials, please.'))

                if channels:
                    try:
                        self.cleaned_data['channels'] = self.cleaned_data['channels']
                    except:
                        raise ValidationError(_('JSON is not valid on channels field.'))

                return self.cleaned_data

        success_message = _("Import successful")
        form_class = DataImportForm

        def get_success_url(self):  # pragma: needs cover
            return reverse('migrations.migration_import')

        def get_form_kwargs(self):
            kwargs = super(MigrationCRUDL.Import, self).get_form_kwargs()
            kwargs['org'] = self.request.user.get_org()
            return kwargs

        def form_valid(self, form):
            migration = Migration.create(org=self.org, user=self.request.user, api_host=form.cleaned_data['api_host'],
                                         api_token=form.cleaned_data['api_token'],
                                         channels=form.cleaned_data['channels'])
            on_transaction_commit(lambda: fire_data_migration.delay(migration.id))
            return super(MigrationCRUDL.Import, self).form_valid(form)
