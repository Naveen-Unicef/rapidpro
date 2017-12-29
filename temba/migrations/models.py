# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import six
import requests
import logging
import json
import datetime

from django.db import models
from django.utils.translation import ugettext_lazy as _

from smartmin.models import SmartModel

# from temba.channels.models import TEMBA_HEADERS
from temba.orgs.models import Org
from temba.contacts.models import Contact, ContactURN, URN, ContactGroup, ContactField
from temba.flows.models import Flow, RuleSet, ActionSet, FlowStep, FlowLabel, FlowStart, FlowRun
from temba.campaigns.models import Campaign, CampaignEvent
from temba.values.models import Value
from temba.channels.models import Channel
from temba.msgs.models import Msg, Broadcast, Label
from temba.locations.models import AdminBoundary
from temba.utils.models import generate_uuid
from temba.msgs.models import INITIALIZING, PENDING, QUEUED, WIRED, SENT, DELIVERED, HANDLED, ERRORED, FAILED
from temba.msgs.models import RESENT, INBOX, FLOW, IVR, USSD, INCOMING, OUTGOING
from temba.utils.http import http_headers

TEMBA_HEADERS = http_headers()


@six.python_2_unicode_compatible
class Migration(SmartModel):
    org = models.ForeignKey(Org, verbose_name=_('Org'), )

    api_host = models.CharField(verbose_name='API host', max_length=255, )

    api_token = models.CharField(verbose_name='API token', max_length=255, )

    channels = models.TextField(verbose_name='Channels', null=True, )

    def __str__(self):
        return '%s - %s' % (self.pk, self.created_on)

    def get_channels_as_json(self):
        if self.channels:
            return json.loads(self.channels)
        else:
            return {}

    def get_related_channel(self, channel_uuid):
        if self.channels:
            channels_json = self.get_channels_as_json()
            return Channel.objects.filter(uuid=channels_json.get(channel_uuid)).first()
        else:
            return None

    @classmethod
    def create(cls, org, user, api_host, api_token, channels, **kwargs):
        create_args = dict(created_by=user,
                           modified_by=user,
                           org=org,
                           api_host=api_host,
                           api_token=api_token,
                           channels=channels)
        create_args.update(kwargs)
        migration = cls.objects.create(**create_args)
        return migration

    def get_headers(self):
        headers = TEMBA_HEADERS.copy()
        headers.update({
            'Authorization': self.api_token,
            'Content-Type': 'application/json'
        })
        return headers

    def get_request_url(self, api_version, api_name):
        return '%s/api/v%s/%s.json' % (self.api_host, api_version, api_name)

    @classmethod
    def get_all_results(cls, headers, next_call):
        while next_call is not None:
            response = requests.get(next_call, headers=headers)
            response_json = response.json()
            next_call = response_json.get('next')
            yield response_json.get('results', None)

    def migrate_contacts(self):
        headers = self.get_headers()
        api_url = self.get_request_url(api_version=2, api_name='contacts')
        results = self.get_all_results(headers=headers, next_call=api_url)
        for result in results:
            for item in result:
                name = item.get('name', None)
                urns = item.get('urns', None)
                language = item.get('language', None)
                groups = item.get('groups', None)
                fields = item.get('fields', None)
                uuid = item.get('uuid', None)
                is_blocked = item.get('blocked', None)
                is_stopped = item.get('stopped', None)

                contact_existing = Contact.objects.filter(org=self.org, uuid=uuid).first()
                if not contact_existing:
                    logging.warning('Contact: %s' % name or uuid)
                    contact_args = dict(org=self.org,
                                        name=name,
                                        language=language,
                                        uuid=uuid,
                                        is_blocked=is_blocked,
                                        is_stopped=is_stopped,
                                        created_by=self.created_by,
                                        modified_by=self.created_by)
                    try:
                        contact_existing = Contact.objects.create(**contact_args)
                    except Exception as e:
                        logging.error(e.args)
                else:
                    logging.warning('Skipping contact: %s' % name or uuid)

                for urn in urns:
                    try:
                        urn_existing = ContactURN.lookup(self.org, urn)
                        if urn_existing:
                            urn_existing.contact = contact_existing
                            urn_existing.save()
                        else:
                            (scheme, path, display) = URN.to_parts(urn)
                            contact_urn_args = dict(contact=contact_existing,
                                                    identity=urn,
                                                    path=path,
                                                    display=display,
                                                    scheme=scheme,
                                                    org=self.org)
                            ContactURN.objects.create(**contact_urn_args)
                    except Exception as e:
                        logging.error('Skipping contact URN: %s [error: %s]' % (name or uuid, e.args))

                for group in groups:
                    group_uuid = group.get('uuid')
                    group_name = group.get('name')

                    group_existing = ContactGroup.user_groups.filter(org=self.org, uuid=group_uuid).first()
                    if not is_blocked and not is_stopped:
                        if group_existing:
                            group_existing.update_contacts(user=self.created_by, contacts=[contact_existing], add=True)
                        else:
                            group_args = dict(name=group_name,
                                              uuid=group_uuid,
                                              org=self.org,
                                              created_by=self.created_by,
                                              modified_by=self.created_by)
                            try:
                                ContactGroup.user_groups.create(**group_args)
                            except Exception as e:
                                logging.error(e.args)

                for field in fields.keys():
                    contact_existing.set_field(user=self.created_by, key=field, value=fields[field])

        return results

    def migrate_groups(self):
        headers = self.get_headers()
        api_url = self.get_request_url(api_version=2, api_name='groups')
        results = self.get_all_results(headers=headers, next_call=api_url)
        for result in results:
            for item in result:
                name = item.get('name', None)
                uuid = item.get('uuid', None)
                query = item.get('query', None)

                group_existing = ContactGroup.user_groups.filter(org=self.org, uuid=uuid).first()
                if not group_existing:
                    logging.warning('Group: %s' % name or uuid)
                    group_args = dict(name=name,
                                      uuid=uuid,
                                      org=self.org,
                                      query=query,
                                      created_by=self.created_by,
                                      modified_by=self.created_by)
                    try:
                        ContactGroup.user_groups.create(**group_args)
                    except Exception as e:
                        logging.error(e.args)
                else:
                    logging.warning('Skipping group: %s' % name or uuid)

    def migrate_flows(self):
        headers = self.get_headers()
        api_url = self.get_request_url(api_version=2, api_name='flows')
        results = self.get_all_results(headers=headers, next_call=api_url)

        for result in results:
            for item in result:
                flow_name = item.get('name', None)
                flow_uuid = item.get('uuid', None)
                flow_labels = item.get('labels', None)
                flow_expires = item.get('expires', None)
                flow_created_on = item.get('created_on', None)
                flow_archived = item.get('archived', None)

                try:
                    flow_definitions_url = '%s?flow=%s&dependencies=none' % (
                        self.get_request_url(api_version=2, api_name='definitions'), flow_uuid)
                    response_definitions = requests.get(flow_definitions_url, headers=headers)
                    response_definitions_json = response_definitions.json()
                    flows = response_definitions_json.get('flows', None)

                    existing_flow = Flow.objects.filter(uuid=flow_uuid).first()

                    for flow in flows:
                        flow_base_language = flow.get('base_language')
                        flow_action_sets = flow.get('action_sets')
                        flow_type = flow.get('flow_type')
                        flow_version = flow.get('version')
                        flow_entry = flow.get('entry')
                        flow_rule_sets = flow.get('rule_sets')
                        flow_metadata = flow.get('metadata')

                        if not existing_flow and flow_entry:
                            logging.warning('Flow: %s' % flow_name or flow_uuid)
                            try:
                                flow_args = dict(name=flow_name,
                                                 org=self.org,
                                                 flow_type=flow_type,
                                                 metadata=json.dumps(flow_metadata),
                                                 saved_by=self.created_by,
                                                 base_language=flow_base_language,
                                                 version_number=int(float(flow_version)),
                                                 entry_uuid=flow_entry,
                                                 uuid=flow_uuid,
                                                 expires_after_minutes=flow_expires,
                                                 created_on=flow_created_on,
                                                 is_archived=flow_archived,
                                                 created_by=self.created_by,
                                                 modified_by=self.created_by)
                                existing_flow = Flow.objects.create(**flow_args)
                            except Exception as e:
                                logging.error('Flow: %s' % e.args)
                        else:
                            logging.warning('Skipping flow: %s' % flow_name or flow_uuid)

                        for rules_set in flow_rule_sets:
                            rule_uuid = rules_set.get('uuid')
                            rule_x = rules_set.get('x')
                            rule_y = rules_set.get('y')
                            rule_rules = rules_set.get('rules')
                            rule_ruleset_type = rules_set.get('ruleset_type')
                            rule_label = rules_set.get('label')
                            rule_finished_key = rules_set.get('finished_key')
                            rule_operand = rules_set.get('operand')
                            rule_response_type = rules_set.get('response_type')
                            rule_config = rules_set.get('config')

                            existing_rule_set = RuleSet.objects.filter(uuid=rule_uuid).first()
                            if not existing_rule_set:
                                try:
                                    logging.warning('RuleSet: %s' % rule_uuid)
                                    rule_set_args = dict(uuid=rule_uuid,
                                                         flow=existing_flow,
                                                         label=rule_label,
                                                         operand=rule_operand,
                                                         rules=json.dumps(rule_rules),
                                                         x=rule_x,
                                                         y=rule_y,
                                                         finished_key=rule_finished_key,
                                                         ruleset_type=rule_ruleset_type,
                                                         config=json.dumps(rule_config),
                                                         response_type=rule_response_type)
                                    existing_rule_set = RuleSet.objects.create(**rule_set_args)
                                    existing_rule_set.value_type = existing_rule_set.get_value_type()
                                    existing_rule_set.save(update_fields=['value_type'])
                                except Exception as e:
                                    logging.error('RuleSet: %s' % e.args)
                            else:
                                logging.warning('Skipping ruleset: %s' % rule_uuid)

                        for action_set in flow_action_sets:
                            action_x = action_set.get('x')
                            action_y = action_set.get('y')
                            action_destination = action_set.get('destination')
                            action_uuid = action_set.get('uuid')
                            action_actions = action_set.get('actions')

                            if RuleSet.objects.filter(uuid=action_destination).first():
                                action_destination_type = FlowStep.TYPE_RULE_SET
                            elif ActionSet.objects.filter(uuid=action_destination).first():
                                action_destination_type = FlowStep.TYPE_ACTION_SET
                            else:
                                action_destination_type = None

                            existing_action_set = ActionSet.objects.filter(uuid=action_uuid).first()
                            if not existing_action_set:
                                try:
                                    logging.warning('ActionSet: %s' % action_uuid)
                                    action_set_args = dict(uuid=action_uuid,
                                                           flow=existing_flow,
                                                           destination=action_destination,
                                                           x=action_x,
                                                           y=action_y,
                                                           destination_type=action_destination_type,
                                                           actions=json.dumps(action_actions))
                                    ActionSet.objects.create(**action_set_args)
                                except Exception as e:
                                    logging.error('ActionSet: %s' % e.args)
                            else:
                                logging.warning('Skipping actionset: %s' % action_uuid)

                        if ActionSet.objects.filter(uuid=flow_entry).first():
                            existing_flow.entry_type = Flow.ACTIONS_ENTRY
                        elif RuleSet.objects.filter(uuid=flow_entry).first():
                            existing_flow.entry_type = Flow.RULES_ENTRY

                        existing_flow.save(update_fields=['entry_type'])

                    for label in flow_labels:
                        label_uuid = label.get('uuid')
                        label_name = label.get('name')

                        existing_label = FlowLabel.objects.filter(uuid=label_uuid).first()
                        if not existing_label:
                            try:
                                logging.warning('Flow Label: %s' % label_name)
                                label_args = dict(org=self.org,
                                                  uuid=label_uuid,
                                                  name=label_name)
                                existing_flow.labels.create(**label_args)
                            except Exception as e:
                                logging.error('Flow Label: %s' % e.args)
                        else:
                            logging.warning('Flow Label: %s' % label_name)
                            existing_flow.labels.add(existing_label)

                except Exception as e:
                    logging.error('Flow: %s' % e.args)

    def migrate_campaigns(self):
        headers = self.get_headers()
        api_url = self.get_request_url(api_version=2, api_name='campaigns')
        results = self.get_all_results(headers=headers, next_call=api_url)

        for result in results:
            for item in result:
                campaign_uuid = item.get('uuid')
                campaign_name = item.get('name')
                campaign_group_uuid = item.get('group').get('uuid') if item.get('group') is not None else None
                campaign_group_name = item.get('group').get('name') if item.get('group') is not None else None
                campaign_created_on = item.get('created_on')

                existing_campaign = Campaign.objects.filter(uuid=campaign_uuid).first()
                if not existing_campaign and campaign_group_uuid and campaign_group_name:
                    group_existing = ContactGroup.user_groups.filter(uuid=campaign_group_uuid).first()

                    if not group_existing:
                        try:
                            logging.warning('Campaign Group: %s' % campaign_group_name)
                            group_args = dict(name=campaign_group_name,
                                              uuid=campaign_group_uuid,
                                              org=self.org,
                                              query=None,
                                              created_by=self.created_by,
                                              modified_by=self.created_by)
                            logging.warning('Group: %s' % campaign_group_name)
                            group_existing = ContactGroup.user_groups.create(**group_args)
                        except Exception as e:
                            logging.error('Campaign Group: %s' % e.args)

                    try:
                        logging.warning('Campaign: %s' % campaign_name)
                        campaign_args = dict(name=campaign_name,
                                             group=group_existing,
                                             org=self.org,
                                             uuid=campaign_uuid,
                                             created_by=self.created_by,
                                             modified_by=self.created_by,
                                             created_on=campaign_created_on)

                        existing_campaign = Campaign.objects.create(**campaign_args)
                    except Exception as e:
                        logging.error('Campaign: %s' % e.args)

                events_api_url = '%s?campaign=%s' % (self.get_request_url(api_version=2, api_name='campaign_events'),
                                                     campaign_uuid)
                events_results = self.get_all_results(headers=headers, next_call=events_api_url)

                for event_result in events_results:
                    for event in event_result:
                        event_uuid = event.get('uuid')
                        event_unit = event.get('unit')
                        event_offset = event.get('offset')
                        event_message = event.get('message')
                        event_delivery_hour = event.get('delivery_hour')
                        event_relative_to_label = event.get('relative_to').get('label')
                        event_flow_uuid = event.get('flow').get('uuid') if event.get('flow') is not None else None
                        event_created_on = event.get('created_on')
                        event_type = CampaignEvent.TYPE_FLOW if event.get('flow') is not None \
                            else CampaignEvent.TYPE_MESSAGE

                        event_unit_choices = dict(minutes=CampaignEvent.UNIT_MINUTES,
                                                  hours=CampaignEvent.UNIT_HOURS,
                                                  days=CampaignEvent.UNIT_DAYS,
                                                  weeks=CampaignEvent.UNIT_WEEKS)

                        event_relative_to = ContactField.get_by_label(org=self.org,
                                                                      label=event_relative_to_label)

                        event_flow = Flow.objects.filter(uuid=event_flow_uuid).first() if event_flow_uuid else None

                        if not event_flow:
                            actionset_uuid = generate_uuid()
                            flow_args = dict(name='Single Message (%s)' % actionset_uuid,
                                             org=self.org,
                                             flow_type=Flow.MESSAGE,
                                             saved_by=self.created_by,
                                             created_by=self.created_by,
                                             modified_by=self.created_by)
                            event_flow = Flow.objects.create(**flow_args)

                            action_actions = [dict(msg=json.dumps(event_message),
                                                   media=dict(),
                                                   send_all=False,
                                                   type='reply')]

                            action_set_args = dict(uuid=actionset_uuid,
                                                   flow=event_flow,
                                                   x=100,
                                                   y=0,
                                                   actions=json.dumps(action_actions))

                            ActionSet.objects.create(**action_set_args)
                            event_flow.entry_uuid = actionset_uuid
                            event_flow.save(update_fields=['entry_uuid'])

                        existing_event = CampaignEvent.objects.filter(uuid=event_uuid).first()

                        if not existing_event and existing_campaign:
                            try:
                                logging.warning('Campaign Event: %s' % event_uuid)
                                event_args = dict(uuid=event_uuid,
                                                  campaign=existing_campaign,
                                                  offset=event_offset,
                                                  unit=event_unit_choices.get(event_unit),
                                                  flow=event_flow,
                                                  relative_to=event_relative_to,
                                                  message=event_message,
                                                  event_type=event_type,
                                                  delivery_hour=event_delivery_hour,
                                                  created_by=self.created_by,
                                                  modified_by=self.created_by,
                                                  created_on=event_created_on)
                                CampaignEvent.objects.create(**event_args)
                            except Exception as e:
                                logging.error('Campaign Event: %s' % e.args)
                        else:
                            logging.warning('Skipping campaign event: %s' % event_uuid)

    def migrate_flow_starts(self):
        headers = self.get_headers()
        api_url = self.get_request_url(api_version=2, api_name='flow_starts')
        results = self.get_all_results(headers=headers, next_call=api_url)

        for result in results:
            for item in result:
                flow_start_uuid = item.get('uuid')
                flow_start_flow_uuid = item.get('flow').get('uuid')
                flow_start_flow_name = item.get('flow').get('name')
                flow_start_status = item.get('status')
                flow_start_groups = item.get('groups')
                flow_start_contacts = item.get('contacts')
                flow_start_restart = item.get('restart_participants')
                flow_start_extra = item.get('extra')
                flow_start_created_on = item.get('created_on')

                flow_start_flow = Flow.objects.filter(uuid=flow_start_flow_uuid).first()

                existing_flow_start = FlowStart.objects.filter(uuid=flow_start_uuid).first()

                if flow_start_flow and not existing_flow_start:
                    try:
                        status_choices = dict(pending='P', starting='S', complete='C', failed='F')
                        logging.warning('Flow Start: %s' % flow_start_flow_name)
                        flow_start_args = dict(uuid=flow_start_uuid,
                                               flow=flow_start_flow,
                                               restart_participants=flow_start_restart,
                                               contact_count=len(flow_start_contacts),
                                               status=status_choices.get(flow_start_status),
                                               extra=json.dumps(flow_start_extra),
                                               created_by=self.created_by,
                                               modified_by=self.created_by,
                                               created_on=flow_start_created_on)
                        existing_flow_start = FlowStart.objects.create(**flow_start_args)

                        contacts_uuid = []
                        for contact in flow_start_contacts:
                            contacts_uuid.append(contact.get('uuid'))

                        groups_uuid = []
                        for group in flow_start_groups:
                            groups_uuid.append(group.get('uuid'))

                        if contacts_uuid:
                            existing_flow_start.contacts.add(*Contact.objects.filter(uuid__in=contacts_uuid))
                        elif groups_uuid:
                            existing_flow_start.groups.add(*ContactGroup.user_groups.filter(uuid__in=groups_uuid))

                    except Exception as e:
                        logging.error('Flow Start: %s' % e.args)
                else:
                    logging.warning('Skipping flow start: %s' % flow_start_flow_name)

    def migrate_flow_runs(self):
        headers = self.get_headers()
        api_url = self.get_request_url(api_version=2, api_name='runs')
        results = self.get_all_results(headers=headers, next_call=api_url)

        for result in results:
            for item in result:
                run_created_on = item.get('created_on')
                run_modified_on = item.get('modified_on')
                run_exited_on = item.get('exited_on')
                run_exit_type = item.get('exit_type')
                run_values = item.get('values')
                run_paths = item.get('path')
                run_responded = item.get('responded')
                run_contact_uuid = item.get('contact').get('uuid') if item.get('contact') is not None else None
                run_start_uuid = item.get('start').get('uuid') if item.get('start') is not None else None
                run_flow_uuid = item.get('flow').get('uuid') if item.get('flow') is not None else None
                run_is_active = False if run_exited_on is not None else True
                run_id = item.get('id')

                existing_flow = Flow.objects.filter(uuid=run_flow_uuid).first()
                existing_contact = Contact.objects.filter(uuid=run_contact_uuid).first()

                existing_migrationrel = MigrationRelationship.objects.filter(
                    reference=MigrationRelationship.REFERENCE_FLOWRUN, source_value=run_id).first()

                if existing_flow and existing_contact and not existing_migrationrel:
                    try:
                        logging.warning('Flow Run: %s' % run_id)
                        existing_flow_start = FlowStart.objects.filter(uuid=run_start_uuid).first()

                        run_created_on_dt = datetime.datetime.strptime(run_created_on, '%Y-%m-%dT%H:%M:%S.%fZ')
                        run_expires_on = run_created_on_dt + datetime.timedelta(
                            minutes=existing_flow.expires_after_minutes)

                        run_expires_on = run_expires_on.strftime('%Y-%m-%dT%H:%M:%S.%fZ')

                        exit_type_choices = dict(completed=FlowRun.EXIT_TYPE_COMPLETED,
                                                 interrupted=FlowRun.EXIT_TYPE_INTERRUPTED,
                                                 expired=FlowRun.EXIT_TYPE_EXPIRED)

                        run_args = dict(org=self.org,
                                        flow=existing_flow,
                                        contact=existing_contact,
                                        is_active=run_is_active,
                                        created_on=run_created_on,
                                        modified_on=run_modified_on,
                                        exited_on=run_exited_on,
                                        exit_type=exit_type_choices.get(run_exit_type),
                                        expires_on=run_expires_on,
                                        responded=run_responded,
                                        start=existing_flow_start,
                                        submitted_by=self.created_by)

                        flow_run = FlowRun.objects.create(**run_args)

                        migrationrel_args = dict(migration=self,
                                                 reference=MigrationRelationship.REFERENCE_FLOWRUN,
                                                 source_value=run_id,
                                                 destination_value=flow_run.pk)
                        MigrationRelationship.objects.create(**migrationrel_args)

                        if run_values:
                            for run_key in run_values.keys():
                                values = run_values.get(run_key)
                                value_category = values.get('category')
                                value_ruleset_uuid = values.get('node')
                                value_value = values.get('value')
                                value_time = values.get('time')

                                (new_value, location_value, dec_value, dt_value,
                                 media_value) = Migration.get_all_values_type(value_value, flow_run)

                                flow_ruleset = RuleSet.objects.filter(uuid=value_ruleset_uuid).first()
                                selected_rule = None
                                rule_category = None
                                if flow_ruleset:
                                    ruleset_rules = flow_ruleset.get_rules()
                                    for rule in ruleset_rules:
                                        if rule.get_category_name(existing_flow.base_language) == value_category:
                                            selected_rule = rule
                                            rule_category = rule.get_category_name(existing_flow.base_language)
                                            break

                                if selected_rule:
                                    try:
                                        logging.warning('Flow Step - RuleSet: %s' % selected_rule.uuid)
                                        flow_step_rule_args = dict(run=flow_run,
                                                                   contact=existing_contact,
                                                                   step_type=FlowStep.TYPE_RULE_SET,
                                                                   step_uuid=value_ruleset_uuid,
                                                                   rule_uuid=selected_rule.uuid,
                                                                   rule_category=rule_category,
                                                                   rule_value=new_value,
                                                                   rule_decimal_value=dec_value,
                                                                   next_uuid=selected_rule.destination,
                                                                   arrived_on=value_time)

                                        flow_ruleset.save_run_value(flow_run, selected_rule, value_value)
                                        Migration.save_run_value(ruleset=flow_ruleset, run=flow_run, rule=selected_rule,
                                                                 value=value_value)

                                        FlowStep.objects.create(**flow_step_rule_args)

                                    except Exception as e:
                                        logging.error('Flow Step - RuleSet: %s' % e.args)

                        if run_paths:
                            for path in run_paths:
                                path_uuid = path.get('node')
                                path_time = path.get('time')

                                existing_actionset = ActionSet.objects.filter(uuid=path_uuid).first()
                                if existing_actionset:
                                    try:
                                        logging.warning('Flow Step - ActionSet: %s' % path_uuid)
                                        flow_step_rule_args = dict(run=flow_run,
                                                                   contact=existing_contact,
                                                                   step_type=FlowStep.TYPE_ACTION_SET,
                                                                   step_uuid=path_uuid,
                                                                   next_uuid=existing_actionset.destination,
                                                                   arrived_on=path_time)

                                        FlowStep.objects.create(**flow_step_rule_args)
                                    except Exception as e:
                                        logging.error('Flow Step - ActionSet: %s' % e.args)

                    except Exception as e:
                        logging.error('Flow Run: %s' % e.args)

                else:
                    logging.warning('Skipping flow run: %s' % run_id)

    def migrate_broadcasts(self):
        headers = self.get_headers()
        api_url = self.get_request_url(api_version=2, api_name='broadcasts')
        results = self.get_all_results(headers=headers, next_call=api_url)

        for result in results:
            for item in result:
                broadcast_id = item.get('id')
                broadcast_urns = item.get('urns')
                broadcast_contacts = item.get('contacts')
                broadcast_groups = item.get('groups')
                broadcast_text = item.get('text')
                broadcast_created_on = item.get('created_on')

                existing_migrationrel = MigrationRelationship.objects.filter(
                    reference=MigrationRelationship.REFERENCE_MSGBROADCAST, source_value=broadcast_id).first()

                if not existing_migrationrel:
                    try:
                        logging.warning('Broadcast: %s' % broadcast_id)

                        # Groups
                        groups_uuid = [item.get('uuid') for item in broadcast_groups]
                        existing_groups = ContactGroup.user_groups.filter(uuid__in=groups_uuid)

                        # Contacts
                        contacts_uuid = [item.get('uuid') for item in broadcast_contacts]
                        existing_contacts = Contact.objects.filter(uuid__in=contacts_uuid)

                        broadcast_args = dict(org=self.org,
                                              recipient_count=existing_contacts.count(),
                                              status=SENT,
                                              text=broadcast_text,
                                              base_language=self.org.primary_language or 'base',
                                              is_active=True,
                                              created_by=self.created_by,
                                              modified_by=self.created_by,
                                              created_on=broadcast_created_on)
                        existing_broadcast = Broadcast.objects.create(**broadcast_args)

                        for urn in broadcast_urns:
                            existing_urn = ContactURN.lookup(self.org, urn)
                            existing_broadcast.urns.add(existing_urn)

                        if existing_groups:
                            existing_broadcast.groups.add(*existing_groups)

                        if existing_contacts:
                            existing_broadcast.contacts.add(*existing_contacts)

                            for contact in existing_contacts:
                                broadcast_recipient_args = dict(broadcast=existing_broadcast,
                                                                contact=contact)
                                existing_broadcast.broadcastrecipient_set.create(**broadcast_recipient_args)

                        if existing_broadcast:
                            migrationrel_args = dict(migration=self,
                                                     reference=MigrationRelationship.REFERENCE_MSGBROADCAST,
                                                     source_value=broadcast_id,
                                                     destination_value=existing_broadcast.pk)
                            MigrationRelationship.objects.create(**migrationrel_args)

                    except Exception as e:
                        logging.error('Broadcast: %s' % e.args)

                else:
                    logging.warning('Skipping broadcast: %s' % broadcast_id)

    def migrate_messages(self):
        headers = self.get_headers()

        folders = ['inbox', 'flows', 'archived', 'outbox', 'sent', 'incoming']

        for folder in folders:
            api_url = '%s?folder=%s' % (self.get_request_url(api_version=2, api_name='messages'), folder)
            results = self.get_all_results(headers=headers, next_call=api_url)

            for result in results:
                for item in result:
                    message_id = item.get('id')
                    message_broadcast = item.get('broadcast')
                    message_contact_uuid = item.get('contact').get('uuid')
                    message_contact_urn = item.get('urn')
                    message_channel_uuid = item.get('channel').get('uuid')
                    message_direction = item.get('direction')
                    message_type = item.get('type')
                    message_status = item.get('status')
                    message_archived = item.get('archived')
                    message_visibility = item.get('visibility')
                    message_text = item.get('text')
                    message_labels = item.get('labels')
                    message_media = item.get('media')
                    message_created_on = item.get('created_on')
                    message_modified_on = item.get('modified_on')

                    destination_broadcast = MigrationRelationship.objects.filter(
                        reference=MigrationRelationship.REFERENCE_MSGBROADCAST, source_value=message_broadcast).first()

                    message_channel = self.get_related_channel(message_channel_uuid)

                    if destination_broadcast:
                        existing_broadcast = Broadcast.objects.filter(
                            id=destination_broadcast.destination_value).first()
                    else:
                        existing_broadcast = None

                    msg_status_choices = dict(initializing=INITIALIZING,
                                              pending=PENDING,
                                              queued=QUEUED,
                                              wired=WIRED,
                                              sent=SENT,
                                              delived=DELIVERED,
                                              handled=HANDLED,
                                              errored=ERRORED,
                                              falied=FAILED,
                                              resent=RESENT)

                    msg_visibility_choices = dict(visible=Msg.VISIBILITY_VISIBLE,
                                                  archived=Msg.VISIBILITY_ARCHIVED,
                                                  deleted=Msg.VISIBILITY_DELETED)

                    msg_type_choices = dict(flow=FLOW,
                                            inbox=INBOX,
                                            ivr=IVR,
                                            ussd=USSD)

                    msg_direction_choices = {'in': INCOMING,
                                             'out': OUTGOING}

                    if message_archived:
                        message_status = Msg.VISIBILITY_ARCHIVED

                    existing_msg_rel = MigrationRelationship.objects.filter(
                        reference=MigrationRelationship.REFERENCE_MSG, source_value=message_id).first()

                    if existing_msg_rel:
                        existing_msg = Msg.objects.filter(id=existing_msg_rel.destination_value).first()
                    else:
                        existing_msg = None

                    existing_contact = Contact.objects.filter(uuid=message_contact_uuid).first()

                    try:
                        message_contact_urn = ContactURN.lookup(self.org, message_contact_urn)
                    except:
                        message_contact_urn = None

                    if not existing_msg and existing_contact and message_channel and message_contact_urn:
                        try:
                            if msg_direction_choices.get(message_direction) == INCOMING:
                                msg_status = HANDLED
                            else:
                                msg_status = msg_status_choices.get(message_status) or SENT

                            logging.warning('Msg: %s' % message_id)
                            msg_args = dict(org=self.org,
                                            channel=message_channel,
                                            contact=existing_contact,
                                            contact_urn=message_contact_urn,
                                            broadcast=existing_broadcast,
                                            text=message_text,
                                            created_on=message_created_on,
                                            modified_on=message_modified_on,
                                            direction=msg_direction_choices.get(message_direction),
                                            status=msg_status,
                                            visibility=msg_visibility_choices.get(message_visibility),
                                            msg_type=msg_type_choices.get(message_type),
                                            attachments=[message_media] if message_media else None)

                            existing_msg = Msg.objects.create(**msg_args)

                            for label in message_labels:
                                label_name = label.get('name')
                                label_uuid = label.get('uuid')

                                existing_label = Label.label_objects.filter(uuid=label_uuid).first()

                                if not existing_label:
                                    label_args = dict(org=self.org,
                                                      uuid=label_uuid,
                                                      name=label_name,
                                                      created_by=self.created_by,
                                                      modified_by=self.created_by)
                                    existing_msg.labels.create(**label_args)
                                else:
                                    existing_msg.labels.add(existing_label)

                            migrationrel_args = dict(migration=self,
                                                     reference=MigrationRelationship.REFERENCE_MSG,
                                                     source_value=message_id,
                                                     destination_value=existing_msg.pk)
                            MigrationRelationship.objects.create(**migrationrel_args)

                        except Exception as e:
                            logging.error('Msg: %s' % e.args)
                    else:
                        logging.warning('Skipping msg: %s' % message_id)

    def migrate_labels(self):
        headers = self.get_headers()
        api_url = self.get_request_url(api_version=2, api_name='labels')
        results = self.get_all_results(headers=headers, next_call=api_url)

        for result in results:
            for item in result:
                label_uuid = item.get('uuid')
                label_name = item.get('name')

                existing_label = Label.label_objects.filter(uuid=label_uuid).first()

                if not existing_label:
                    try:
                        logging.warning('Label: %s' % label_uuid)
                        label_args = dict(org=self.org,
                                          uuid=label_uuid,
                                          name=label_name,
                                          created_by=self.created_by,
                                          modified_by=self.created_by)
                        Label.label_objects.create(**label_args)
                    except Exception as e:
                        logging.error('Label: %s' % e.args)
                else:
                    logging.warning('Skipping label: %s' % label_uuid)


    @staticmethod
    def save_run_value(ruleset, run, rule, value):
        (new_value, location_value, dec_value, dt_value, media_value) = Migration.get_all_values_type(value, run)

        # delete any existing values for this ruleset, run and contact, we only store the latest
        Value.objects.filter(contact=run.contact, run=run, ruleset=ruleset).delete()

        Value.objects.create(contact=run.contact, run=run, ruleset=ruleset,
                             category=rule.get_category_name(run.flow.base_language), rule_uuid=rule.uuid,
                             string_value=new_value, decimal_value=dec_value, datetime_value=dt_value,
                             location_value=location_value, media_value=media_value, org=run.flow.org)

        # invalidate any cache on this ruleset
        Value.invalidate_cache(ruleset=ruleset)

    @staticmethod
    def get_all_values_type(value, run):
        value = six.text_type(value)[:Value.MAX_VALUE_LEN]
        location_value = None
        dec_value = None
        dt_value = None
        media_value = None

        if isinstance(value, AdminBoundary):  # pragma: needs cover
            location_value = value
        else:
            dt_value = run.flow.org.parse_date(value)
            dec_value = run.flow.org.parse_decimal(value)

        # if its a media value, only store the path as the value
        if ':' in value:
            (media_type, media_path) = value.split(':', 1)
            if media_type in Msg.MEDIA_TYPES:  # pragma: needs cover
                media_value = value
                value = media_path

        return value, location_value, dec_value, dt_value, media_value


class MigrationRelationship(models.Model):
    REFERENCE_CONTACT = 'contact'
    REFERENCE_CONTACTGROUP = 'contact_group'
    REFERENCE_FLOW = 'flow'
    REFERENCE_FLOWSTART = 'flow_start'
    REFERENCE_FLOWRUN = 'flow_run'
    REFERENCE_CAMPAIGN = 'campaign'
    REFERENCE_MSG = 'msg'
    REFERENCE_MSGLABEL = 'msg_label'
    REFERENCE_MSGBROADCAST = 'msg_broadcast'

    REFERENCE_CHOICES = (
        (REFERENCE_CONTACT, 'Contact'),
        (REFERENCE_CONTACTGROUP, 'Contact Groups'),
        (REFERENCE_FLOW, 'Flows'),
        (REFERENCE_FLOWSTART, 'Flow Starts'),
        (REFERENCE_FLOWRUN, 'Flow Runs'),
        (REFERENCE_CAMPAIGN, 'Campaigns'),
        (REFERENCE_MSG, 'Messages'),
        (REFERENCE_MSGLABEL, 'Message Labels'),
        (REFERENCE_MSGBROADCAST, 'Message Broadcast'),
    )

    migration = models.ForeignKey(Migration, verbose_name='Migration', )

    reference = models.CharField(help_text='The module reference like flow_run, contact, flow, contacts_group...',
                                 max_length=100, choices=REFERENCE_CHOICES, )

    source_value = models.CharField(help_text='The original value from other host', max_length=100, )

    destination_value = models.CharField(help_text='The value related on our host', max_length=100, )

    def __str__(self):
        return '%s - %s - %s' % (self.migration.pk, self.source_value, self.destination_value)
