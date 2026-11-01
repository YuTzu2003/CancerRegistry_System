import json
from datetime import datetime, timedelta
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from flask import Flask

import modules.services.indicators as service
import modules.blueprint.auth.key_access as key_access
from modules.services.auth import auth_bp
from modules.blueprint.indicators.catalog import CANCER_SPECS
from modules.blueprint.indicators.rule_versions import default_rules


class MemoryDatabase:
    def __init__(self):
        self.records = []
        self.history = []
        self.revision = 0

    def touch(self, row):
        self.revision += 1
        row['updated_at'] = datetime(2026, 1, 1) + timedelta(microseconds=self.revision)

    def cursor(self):
        return MemoryCursor(self)

    def commit(self):
        pass

    def close(self):
        pass

    def rollback(self):
        pass


class MemoryCursor:
    def __init__(self, database):
        self.database = database
        self.rows = []

    def execute(self, query, *params):
        params = params[0] if len(params) == 1 and isinstance(params[0], tuple) else params
        self.rows = []
        records = self.database.records
        compact = ' '.join(query.split())
        if compact.startswith('SELECT TOP 1 1 FROM dbo.User_applications'):
            self.rows = [(1,)] if params == ('test-user', 'valid-key') else []
        elif compact.startswith('SELECT v.version_id, v.version_name, v.definition_year, v.rules_json'):
            self.rows = [(
                row['id'], row['name'], row.get('definition_year'), row['json'], row.get('description', ''), row.get('status', 'DRAFT'),
                row.get('created_by', ''), None, row.get('updated_by', ''), row.get('updated_at'), row.get('published_by', ''), None,
                row.get('created_by', ''),
            ) for row in reversed(records)]
        elif compact.startswith('SELECT version_name, definition_year, rules_json, version_description, status'):
            self.rows = [(
                row['name'], row.get('definition_year'), row['json'], row.get('description', ''), row.get('status', 'DRAFT'),
                row.get('created_by', ''), None, row.get('updated_by', ''), row.get('updated_at'), row.get('published_by', ''), None,
            ) for row in records if row['id'] == params[0]]
        elif compact.startswith('SELECT rules_json, status, version_description, version_name, definition_year, updated_at FROM dbo.IndicatorDefinitionVersion WITH'):
            self.rows = [(row['json'], row.get('status', 'DRAFT'), row.get('description', ''), row['name'], row.get('definition_year'), row.get('updated_at'))
                         for row in records if row['id'] == params[0]]
        elif compact.startswith('SELECT version_name, rules_json, status FROM dbo.IndicatorDefinitionVersion WITH'):
            self.rows = [(row['name'], row['json'], row.get('status', 'DRAFT'))
                         for row in records if row['id'] == params[0]]
        elif compact.startswith('UPDATE dbo.IndicatorDefinitionVersion SET rules_json'):
            for row in records:
                if row['id'] == params[4]:
                    row['json'] = params[0]
                    row['description'] = params[1]
                    row['updated_by'] = params[2]
                    row['status'] = params[3]
                    self.database.touch(row)
        elif compact.startswith('UPDATE dbo.IndicatorDefinitionVersion SET version_name'):
            for row in records:
                if row['id'] == params[3]:
                    row['name'] = params[0]
                    row['updated_by'] = params[1]
                    row['status'] = params[2]
                    self.database.touch(row)
        elif compact.startswith('UPDATE dbo.IndicatorDefinitionVersion SET status'):
            for row in records:
                if row['id'] == params[-1]:
                    row['status'] = params[0]
                    row['updated_by'] = params[1]
                    self.database.touch(row)
                    if params[0] == 'PUBLISHED':
                        row['published_by'] = params[2]
        elif compact.startswith('SELECT version_name FROM dbo.IndicatorDefinitionVersion WITH'):
            self.rows = [(row['name'],) for row in records]
        elif compact.startswith('SELECT history_id, action'):
            self.rows = [(
                item['id'], item['action'], item.get('status_before'), item.get('status_after'),
                item.get('rules_before'), item.get('rules_after'), item.get('reason'), item.get('actor'), None,
            ) for item in reversed(self.database.history) if item['version_id'] == params[0]]
        elif compact.startswith('SELECT 1'):
            self.rows = [(1,) for row in records if row['name'] == params[0]]
        elif compact.startswith('INSERT INTO dbo.IndicatorDefinitionVersionHistory'):
            number = max((item['id'] for item in self.database.history), default=0) + 1
            self.database.history.append({
                'id': number, 'version_id': params[0], 'action': params[1], 'status_before': params[2],
                'status_after': params[3], 'rules_before': params[4], 'rules_after': params[5],
                'reason': params[6], 'actor': params[7],
            })
        elif compact.startswith('INSERT INTO dbo.IndicatorDefinitionVersion'):
            number = max((row['id'] for row in records), default=0) + 1
            records.append({'id': number, 'name': params[0], 'definition_year': params[1], 'description': params[2], 'status': 'PENDING',
                            'json': params[3], 'created_by': params[4]})
            self.rows = [(number,)]
        elif compact.startswith('DELETE FROM dbo.IndicatorDefinitionVersion'):
            records[:] = [row for row in records if row['id'] != params[0]]
        else:
            raise AssertionError(f'Unexpected query: {query}')
        return self

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def fetchall(self):
        return self.rows


class IndicatorVersionApiTests(unittest.TestCase):
    def setUp(self):
        app = Flask(__name__)
        app.secret_key = 'test-key'
        app.register_blueprint(service.indicators_bp)
        app.register_blueprint(auth_bp)
        self.client = app.test_client()
        self.database = MemoryDatabase()
        self.user = SimpleNamespace(Position='Ctr')
        with self.client.session_transaction() as session:
            session['userid'] = 'test-user'
            session['position'] = 'Ctr'
            session[key_access.DATA_UPDATE_ACCESS_USER] = 'test-user'
            session[key_access.DATA_UPDATE_ACCESS_TOKEN] = 'verified'
        for patcher in (patch.object(service, 'get_conn', return_value=self.database),
                        patch.object(key_access, 'get_conn', return_value=self.database),
                        patch.object(service, 'write_audit_log'),
                        patch.object(service, 'get_indicator_metadata', return_value=[]),
                        patch('modules.services.auth.current_session_user', side_effect=lambda: self.user)):
            patcher.start()
            self.addCleanup(patcher.stop)

    def create(self, cancer='Oral_Cavity', name='Annual definition'):
        rules = default_rules(cancer)
        return self.client.post('/api/indicators/definition-versions', json={
            'name': name, 'base_version': 'default', 'cancer_key': cancer, 'changes': [],
            'description': 'Test definition',
            'descriptions': [{'id': number, 'name': rule['name'],
                              'numerator_definition': 'Test numerator', 'denominator_definition': 'Test denominator'}
                             for number, rule in sorted(rules.items())],
        })

    def revision_payload(self, version_id, cancer):
        details = self.client.get(f'/api/indicators/definition-versions/{version_id}/cancers/{cancer}').get_json()
        for item in details['descriptions']:
            item['numerator_definition'] = item['numerator_definition'] or 'Test numerator'
            item['denominator_definition'] = item['denominator_definition'] or 'Test denominator'
        return {'cancer_key': cancer, 'changes': [], 'descriptions': details['descriptions'],
                'description': 'Updated test definition', 'reason': 'Test update'}

    def publish(self, version_id, reason='Test publication'):
        self.user.Position = 'Admin'
        with self.client.session_transaction() as session:
            session['position'] = 'Admin'
        return self.client.post(f'/api/indicators/definition-versions/{version_id}/status', json={
            'status': 'PUBLISHED', 'reason': reason,
        })

    def test_one_created_version_includes_all_cancers(self):
        response = self.create()
        self.assertEqual(response.status_code, 200)
        version_id = response.get_json()['id']
        for cancer in CANCER_SPECS:
            with self.subTest(cancer=cancer):
                loaded = self.client.get(f'/api/indicators/definition-versions/{version_id}/cancers/{cancer}')
                self.assertEqual(loaded.status_code, 200)
                self.assertEqual(loaded.get_json()['version']['id'], version_id)
                self.assertTrue(loaded.get_json()['included'])
                self.assertEqual(len(loaded.get_json()['descriptions']), len(CANCER_SPECS[cancer].rules))
        listed = self.client.get('/api/indicators/definition-versions').get_json()['versions']
        self.assertEqual(len(listed), 1)
        managed = self.client.get('/api/indicators/definition-versions?include_all=1').get_json()['versions']
        self.assertEqual(len(managed), 2)
        self.assertEqual(managed[1]['status'], 'PENDING')
        self.assertEqual(managed[1]['created_by_key'], 'test-user')
        self.assertTrue(all(set(version['cancers']) == set(CANCER_SPECS) for version in managed))
        self.assertEqual(self.publish(version_id).status_code, 200)
        public = self.client.get('/api/indicators/definition-versions').get_json()['versions']
        self.assertNotIn('created_by_key', public[1])

    def test_definition_names_are_unique_across_cancers(self):
        self.assertEqual(self.create('Oral_Cavity').status_code, 200)
        self.assertEqual(self.create('Breast').status_code, 400)

    def test_revision_saves_date_rule_tree_and_keeps_other_rules(self):
        created = self.create().get_json()['id']
        detail = self.client.get(f'/api/indicators/definition-versions/{created}/cancers/Oral_Cavity').get_json()
        tree = detail['rule_trees']['1']['numerator']
        self.assertEqual(tree['max_days'], 42)
        tree['max_days'] = 60
        payload = self.revision_payload(created, 'Oral_Cavity')
        payload['rule_trees'] = {'1': {'numerator': tree}}
        response = self.client.put(f'/api/indicators/definition-versions/{created}', json={
            'fingerprint': detail['version']['fingerprint'], 'reason': 'Update day limit',
            'cancer_edits': {'Oral_Cavity': payload},
        })
        self.assertEqual(response.status_code, 200, response.get_json())
        saved = json.loads(self.database.records[0]['json'])['Oral_Cavity']
        self.assertEqual(saved['1']['numerator']['max_days'], 60)
        self.assertEqual(saved['1']['denominator'], default_rules('Oral_Cavity')[1]['denominator'])

    def test_rule_fields_are_available_and_editable_for_ovary_and_lung(self):
        version_id = self.create().get_json()['id']
        for cancer, number, key in [('Ovary', 3, 'value'), ('Lung', 1, 'min')]:
            detail = self.client.get(f'/api/indicators/definition-versions/{version_id}/cancers/{cancer}').get_json()
            tree = detail['rule_trees'][str(number)]['numerator']
            self.assertIn(tree['field'], detail['field_labels'])
            old = tree[key]
            tree[key] += 1
            edit = self.revision_payload(version_id, cancer)
            edit['rule_trees'] = {str(number): {'numerator': tree}}
            response = self.client.put(f'/api/indicators/definition-versions/{version_id}', json={
                'fingerprint': detail['version']['fingerprint'], 'reason': 'Update field rule',
                'cancer_edits': {cancer: edit},
            })
            self.assertEqual(response.status_code, 200, response.get_json())
            saved = json.loads(self.database.records[0]['json'])[cancer][str(number)]['numerator']
            self.assertEqual(saved[key], old + 1)

    def test_definition_year_is_saved_as_an_annual_label(self):
        rules = default_rules('Oral_Cavity')
        response = self.client.post('/api/indicators/definition-versions', json={
            'definition_year': 2026, 'base_version': 'default', 'cancer_key': 'Oral_Cavity', 'changes': [],
            'description': 'Annual definition',
            'descriptions': [{'id': number, 'name': rule['name'],
                              'numerator_definition': 'Test numerator', 'denominator_definition': 'Test denominator'}
                             for number, rule in sorted(rules.items())],
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()['name'].startswith('2026 '))
        self.assertEqual(response.get_json()['definition_year'], 2026)
        self.assertEqual(self.database.records[0]['definition_year'], 2026)
        listed = self.client.get('/api/indicators/definition-versions?include_all=1').get_json()['versions']
        self.assertEqual(listed[-1]['definition_year'], 2026)

    def test_multiple_cancers_are_saved_in_one_snapshot(self):
        edits = {key: self.revision_payload('default', key) for key in ('Oral_Cavity', 'Breast')}
        for key, edit in edits.items():
            edit['descriptions'][0]['name'] = f'Updated {key}'
        response = self.client.post('/api/indicators/definition-versions', json={
            'name': 'Combined', 'base_version': 'default', 'cancer_edits': edits,
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(self.database.records), 1)
        definition = json.loads(self.database.records[0]['json'])
        for key in edits:
            number = edits[key]['descriptions'][0]['id']
            self.assertEqual(definition[key][str(number)]['name'], f'Updated {key}')
        self.assertEqual(definition['Esophagus']['1']['name'], default_rules('Esophagus')[1]['name'])

    def test_invalid_one_of_multiple_edits_does_not_save_any(self):
        edits = {key: self.revision_payload('default', key) for key in ('Oral_Cavity', 'Breast')}
        edits['Breast']['descriptions'][0]['name'] = ''
        response = self.client.post('/api/indicators/definition-versions', json={
            'name': 'Invalid combined', 'base_version': 'default', 'cancer_edits': edits,
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.database.records, [])

    def test_remove_indicator_in_new_snapshot_and_keep_original(self):
        edit = self.revision_payload('default', 'Breast')
        removed = edit['descriptions'][0]['id']
        edit['removed_indicators'] = [removed]
        edit['descriptions'] = [item for item in edit['descriptions'] if item['id'] != removed]
        response = self.client.post('/api/indicators/definition-versions', json={
            'name': 'Removed indicator', 'base_version': 'default', 'cancer_edits': {'Breast': edit},
        })
        self.assertEqual(response.status_code, 200)
        saved = self.client.get(f"/api/indicators/definition-versions/{response.get_json()['id']}/cancers/Breast").get_json()
        self.assertNotIn(removed, [item['id'] for item in saved['descriptions']])
        self.assertIn(removed, default_rules('Breast'))

    def test_delete_created_version_but_not_default(self):
        self.assertEqual(self.create().status_code, 200)
        self.assertEqual(self.client.delete('/api/indicators/definition-versions/default').status_code, 400)
        self.assertEqual(self.client.delete('/api/indicators/definition-versions/1').status_code, 200)
        self.assertEqual(self.database.records, [])

    def test_inactive_version_can_be_deleted_but_published_version_cannot(self):
        version_id = self.create().get_json()['id']
        self.assertEqual(self.publish(version_id).status_code, 200)
        self.assertEqual(self.client.delete(f'/api/indicators/definition-versions/{version_id}').status_code, 409)
        self.assertEqual(self.client.post(
            f'/api/indicators/definition-versions/{version_id}/status', json={'status': 'INACTIVE'}
        ).status_code, 200)
        self.assertEqual(self.client.delete(f'/api/indicators/definition-versions/{version_id}').status_code, 200)
        self.assertEqual(self.database.records, [])

    def test_update_changes_same_version_and_rejects_stale_edit(self):
        version_id = self.create().get_json()['id']
        details = self.client.get(f'/api/indicators/definition-versions/{version_id}/cancers/Breast').get_json()
        payload = self.revision_payload(version_id, 'Breast')
        payload['fingerprint'] = details['version']['fingerprint']
        payload['descriptions'][0]['name'] = 'Updated breast indicator'
        response = self.client.put(f'/api/indicators/definition-versions/{version_id}', json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['id'], version_id)
        self.assertEqual(len(self.database.records), 1)
        updated = self.client.get(f'/api/indicators/definition-versions/{version_id}/cancers/Breast').get_json()
        self.assertEqual(updated['descriptions'][0]['name'], 'Updated breast indicator')
        self.assertEqual(self.client.put(f'/api/indicators/definition-versions/{version_id}', json=payload).status_code, 409)
        self.assertEqual(self.client.put('/api/indicators/definition-versions/default', json=payload).status_code, 400)

    def test_published_version_is_immutable_and_has_history(self):
        version_id = self.create().get_json()['id']
        self.assertEqual(self.publish(version_id).status_code, 200)
        payload = self.revision_payload(version_id, 'Breast')
        details = self.client.get(f'/api/indicators/definition-versions/{version_id}/cancers/Breast').get_json()
        payload['fingerprint'] = details['version']['fingerprint']
        self.assertEqual(self.client.put(f'/api/indicators/definition-versions/{version_id}', json=payload).status_code, 409)
        self.assertEqual(self.client.delete(f'/api/indicators/definition-versions/{version_id}').status_code, 409)
        history = self.client.get(f'/api/indicators/definition-versions/{version_id}/history').get_json()['history']
        self.assertEqual([item['action'] for item in history], ['STATUS_CHANGED', 'CREATED'])

    def test_published_version_can_be_disabled_and_reenabled_without_a_reason(self):
        version_id = self.create().get_json()['id']
        self.assertEqual(self.publish(version_id).status_code, 200)
        disabled = self.client.post(f'/api/indicators/definition-versions/{version_id}/status', json={'status': 'INACTIVE'})
        self.assertEqual(disabled.status_code, 200)
        self.assertEqual(disabled.get_json()['status'], 'INACTIVE')
        reenabled = self.client.post(f'/api/indicators/definition-versions/{version_id}/status', json={'status': 'PUBLISHED'})
        self.assertEqual(reenabled.status_code, 200)
        self.assertEqual(reenabled.get_json()['status'], 'PUBLISHED')

    def test_inactive_version_can_be_edited_and_must_be_approved_again(self):
        version_id = self.create().get_json()['id']
        self.assertEqual(self.publish(version_id).status_code, 200)

        self.assertEqual(self.client.post(f'/api/indicators/definition-versions/{version_id}/status', json={'status': 'INACTIVE'}).status_code, 200)
        before = self.database.records[0]['json']
        details = self.client.get(f'/api/indicators/definition-versions/{version_id}/cancers/Breast').get_json()
        edit = self.revision_payload(version_id, 'Breast')
        edit['descriptions'][0]['name'] = 'Updated inactive indicator'
        with self.client.session_transaction() as session:
            session['position'] = 'Ctr'
        self.user.Position = 'Ctr'
        response = self.client.put(f'/api/indicators/definition-versions/{version_id}', json={
            'fingerprint': details['version']['fingerprint'], 'reason': 'Update inactive version',
            'cancer_edits': {'Breast': edit},
        })
        self.assertEqual(response.status_code, 200, response.get_json())
        self.assertEqual(response.get_json()['status'], 'PENDING')
        self.assertEqual(self.database.records[0]['status'], 'PENDING')
        self.assertEqual(len(self.database.records), 1)
        self.assertEqual(self.database.history[-1]['status_before'], 'INACTIVE')
        self.assertEqual(self.database.history[-1]['status_after'], 'PENDING')
        self.assertEqual(self.database.history[-1]['rules_before'], before)
        public = self.client.get('/api/indicators/definition-versions').get_json()['versions']
        self.assertNotIn(version_id, [item['id'] for item in public])
        self.assertEqual(self.client.post(f'/api/indicators/definition-versions/{version_id}/status', json={'status': 'PUBLISHED'}).status_code, 403)
        self.assertEqual(self.publish(version_id).status_code, 200)
        public = self.client.get('/api/indicators/definition-versions').get_json()['versions']
        self.assertIn(version_id, [item['id'] for item in public])

    def test_only_inactive_version_can_be_renamed_after_publication(self):
        version_id = self.create().get_json()['id']
        self.assertEqual(self.publish(version_id).status_code, 200)
        url = f'/api/indicators/definition-versions/{version_id}/rename'
        fingerprint = self.client.get(f'/api/indicators/definition-versions/{version_id}/cancers/Breast').get_json()['version']['fingerprint']
        self.assertEqual(self.client.post(url, json={'name': 'Renamed', 'fingerprint': fingerprint}).status_code, 409)
        self.assertEqual(self.client.post(f'/api/indicators/definition-versions/{version_id}/status', json={'status': 'INACTIVE'}).status_code, 200)
        fingerprint = self.client.get(f'/api/indicators/definition-versions/{version_id}/cancers/Breast').get_json()['version']['fingerprint']
        result = self.client.post(url, json={'name': 'Renamed', 'fingerprint': fingerprint})
        self.assertEqual(result.status_code, 200, result.get_json())
        self.assertEqual(result.get_json()['status'], 'PENDING')
        self.assertEqual(self.database.records[0]['status'], 'PENDING')

    def test_stale_description_and_name_edits_cannot_overwrite_newer_changes(self):
        version_id = self.create().get_json()['id']
        url = f'/api/indicators/definition-versions/{version_id}'
        detail = self.client.get(url + '/cancers/Breast').get_json()
        old_fingerprint = detail['version']['fingerprint']
        edit = self.revision_payload(version_id, 'Breast')
        edit['fingerprint'] = old_fingerprint
        edit['description'] = 'First editor description'
        self.assertEqual(self.client.put(url, json=edit).status_code, 200)
        edit['description'] = 'Second editor description'
        self.assertEqual(self.client.put(url, json=edit).status_code, 409)
        self.assertEqual(self.database.records[0]['description'], 'First editor description')
        self.assertEqual(self.client.post(url + '/rename', json={'name': 'Stale rename', 'fingerprint': old_fingerprint}).status_code, 409)
        current = self.client.get(url + '/cancers/Breast').get_json()['version']['fingerprint']
        self.assertEqual(self.client.post(url + '/rename', json={'name': 'New name', 'fingerprint': current}).status_code, 200)
        edit['fingerprint'] = current
        self.assertEqual(self.client.put(url, json=edit).status_code, 409)
        self.assertEqual(self.database.records[0]['name'], 'New name')

    def test_restore_endpoint_is_removed_but_history_is_available(self):
        version_id = self.create().get_json()['id']
        url = f'/api/indicators/definition-versions/{version_id}'
        self.assertEqual(self.client.post(url + '/restore').status_code, 404)
        self.assertEqual(self.client.get(url + '/history').status_code, 200)

    def test_concurrent_description_change_between_read_and_lock_is_rejected(self):
        version_id = self.create().get_json()['id']
        url = f'/api/indicators/definition-versions/{version_id}'
        detail = self.client.get(url + '/cancers/Breast').get_json()
        edit = self.revision_payload(version_id, 'Breast')
        edit['fingerprint'] = detail['version']['fingerprint']
        edit['description'] = 'Stale editor description'
        execute = MemoryCursor.execute
        changed = []

        def concurrent_change(cursor, query, *params):
            if query.startswith('SELECT rules_json, status, version_description, version_name') and not changed:
                row = cursor.database.records[0]
                row['description'] = 'Other editor description'
                cursor.database.touch(row)
                changed.append(True)
            return execute(cursor, query, *params)

        with patch.object(MemoryCursor, 'execute', concurrent_change):
            response = self.client.put(url, json=edit)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.database.records[0]['description'], 'Other editor description')

    def test_maintainer_submits_but_only_admin_can_approve(self):
        version_id = self.create().get_json()['id']
        self.assertEqual(self.database.records[0]['status'], 'PENDING')
        forbidden = self.client.post(
            f'/api/indicators/definition-versions/{version_id}/status',
            json={'status': 'PUBLISHED'},
        )
        self.assertEqual(forbidden.status_code, 403)
        self.user.Position = 'Admin'
        with self.client.session_transaction() as session:
            session['position'] = 'Admin'
        approved = self.client.post(
            f'/api/indicators/definition-versions/{version_id}/status',
            json={'status': 'PUBLISHED'},
        )
        self.assertEqual(approved.status_code, 200)
        self.assertEqual(approved.get_json()['status'], 'PUBLISHED')

    def test_user_without_key_cannot_open_details_publish_or_revise(self):
        self.user.Position = 'User'
        with self.client.session_transaction() as session:
            session['position'] = 'User'
            session.pop(key_access.DATA_UPDATE_ACCESS_TOKEN)
            session.pop(key_access.DATA_UPDATE_ACCESS_USER)
        self.assertEqual(self.client.get('/api/indicators/definition-versions/default/cancers/Oral_Cavity').status_code, 403)
        self.assertEqual(self.client.get('/api/indicators/definition-versions').status_code, 200)
        self.assertEqual(self.create().status_code, 403)
        self.assertEqual(self.client.post('/api/indicators/definition-versions/default/revisions', json={}).status_code, 403)
        self.assertEqual(self.database.records, [])

    def test_user_with_key_and_admin_without_key_can_publish(self):
        self.user.Position = 'User'
        with self.client.session_transaction() as session:
            session['position'] = 'User'
        self.assertEqual(self.create(name='Authorized user').status_code, 200)
        self.user.Position = 'Admin'
        with self.client.session_transaction() as session:
            session['position'] = 'Admin'
            session.pop(key_access.DATA_UPDATE_ACCESS_TOKEN)
            session.pop(key_access.DATA_UPDATE_ACCESS_USER)
        self.assertEqual(self.create(name='Administrator').status_code, 200)

    def test_key_verification_returns_to_selected_indicator_version(self):
        self.assertEqual(self.create(name='Selected version').status_code, 200)
        with self.client.session_transaction() as session:
            session.pop(key_access.DATA_UPDATE_ACCESS_TOKEN)
            session.pop(key_access.DATA_UPDATE_ACCESS_USER)
        destination = '/indicators/definitions?cancer=Breast&version=1'
        response = self.client.get(destination)
        self.assertEqual(response.status_code, 302)
        self.assertIn('next=indicator_definitions', response.location)
        self.assertIn('cancer=Breast', response.location)
        self.assertIn('version=1', response.location)
        with patch.object(key_access, 'render_template', return_value='key page') as render:
            self.assertEqual(self.client.get(response.location).status_code, 200)
            self.assertEqual(render.call_args.kwargs['access_destination'], {
                'next': 'indicator_definitions', 'cancer': 'Breast', 'version': '1',
            })
        invalid = self.client.post('/dashboard/data-update/access', data={
            'next': 'indicator_definitions', 'cancer': 'Breast', 'version': '1', 'api_key': 'invalid',
        })
        self.assertEqual(invalid.status_code, 302)
        self.assertIn('next=indicator_definitions', invalid.location)
        verified = self.client.post('/dashboard/data-update/access', data={
            'next': 'indicator_definitions', 'cancer': 'Breast', 'version': '1', 'api_key': 'valid-key',
        })
        self.assertEqual(verified.status_code, 302)
        self.assertEqual(verified.location, destination)
        with patch.object(service, 'render_template', return_value='indicator page'):
            self.assertEqual(self.client.get(destination).status_code, 200)
        self.assertEqual(self.client.get('/api/indicators/definition-versions/1/cancers/Breast').status_code, 200)

    def test_signed_out_user_is_rejected_before_key_checks(self):
        self.user = None
        self.assertEqual(self.client.get('/api/indicators/definition-versions').status_code, 401)
        self.assertEqual(self.create().status_code, 401)

    def test_key_for_another_user_does_not_grant_access(self):
        with self.client.session_transaction() as session:
            session[key_access.DATA_UPDATE_ACCESS_USER] = 'another-user'
        self.assertEqual(self.client.get('/api/indicators/definition-versions/default/cancers/Breast').status_code, 403)
        self.assertEqual(self.create().status_code, 403)

    def test_key_verification_does_not_redirect_to_arbitrary_urls(self):
        with self.client.session_transaction() as session:
            session.pop(key_access.DATA_UPDATE_ACCESS_TOKEN)
            session.pop(key_access.DATA_UPDATE_ACCESS_USER)
        response = self.client.post('/dashboard/data-update/access', data={
            'next': 'https://example.invalid', 'api_key': 'valid-key',
        })
        self.assertEqual(response.location, '/dashboard/data-update/select')

    def test_reporting_maintenance_key_can_be_reused_for_indicators(self):
        with self.client.session_transaction() as session:
            session.pop(key_access.DATA_UPDATE_ACCESS_TOKEN)
            session.pop(key_access.DATA_UPDATE_ACCESS_USER)
        self.assertEqual(self.client.get('/dashboard/data-update/select').location, '/dashboard/data-update')
        verified = self.client.post('/dashboard/data-update/access', data={'api_key': 'valid-key'})
        self.assertEqual(verified.location, '/dashboard/data-update/select')
        self.assertEqual(self.client.get('/api/indicators/definition-versions/default/cancers/Breast').status_code, 200)

    def test_updates_clone_the_whole_version_and_keep_originals(self):
        source_id = self.create().get_json()['id']
        original_json = self.database.records[0]['json']
        original = json.loads(original_json)
        payload = self.revision_payload(source_id, 'Oral_Cavity')
        condition = self.client.get(f'/api/indicators/definition-versions/{source_id}/cancers/Oral_Cavity').get_json()['conditions'][0]
        payload['changes'] = [{**condition, 'min': 40, 'max': 90}]
        revised = self.client.post(f'/api/indicators/definition-versions/{source_id}/revisions', json=payload)
        self.assertEqual(revised.status_code, 200)
        self.assertTrue(revised.get_json()['name'].startswith('Annual definition'))
        revision_id = revised.get_json()['id']
        self.assertNotEqual(revision_id, source_id)
        self.assertEqual(self.database.records[0]['json'], original_json)
        updated = json.loads(self.database.records[1]['json'])
        self.assertEqual(updated['Oral_Cavity']['1']['denominator']['rules'][0]['min'], 40)
        for cancer in CANCER_SPECS:
            if cancer != 'Oral_Cavity':
                self.assertEqual(updated[cancer], original[cancer])
        second = self.client.post(f'/api/indicators/definition-versions/{revision_id}/revisions',
                                  json=self.revision_payload(revision_id, 'Breast'))
        self.assertTrue(second.get_json()['name'].startswith('Annual definition'))
        self.assertEqual(json.loads(self.database.records[2]['json'])['Oral_Cavity'], updated['Oral_Cavity'])

    def test_partial_legacy_versions_cannot_create_an_incomplete_revision(self):
        self.database.records.append({'id': 1, 'name': 'Legacy oral',
                                      'json': json.dumps({'Oral_Cavity': default_rules('Oral_Cavity')})})
        with self.assertRaises(ValueError):
            service._selected_rule_versions({'definition_version': '1'}, ['Oral_Cavity', 'Breast'])
        details = self.client.get('/api/indicators/definition-versions/1/cancers/Breast').get_json()
        self.assertFalse(details['included'])
        response = self.client.post('/api/indicators/definition-versions/1/revisions', json=self.revision_payload('1', 'Breast'))
        self.assertEqual(response.status_code, 400)
        self.assertTrue(response.get_json()['error'])
        self.assertEqual(len(self.database.records), 1)

    def test_partial_legacy_versions_cannot_be_used_for_analysis(self):
        self.database.records.append({'id': 1, 'name': 'Legacy oral',
                                      'json': json.dumps({'Oral_Cavity': default_rules('Oral_Cavity')})})
        with self.assertRaises(ValueError):
            service._selected_rule_versions({'definition_version': '1'}, ['Oral_Cavity'])

    def test_old_mixed_cancer_requests_are_rejected(self):
        with self.assertRaises(ValueError):
            service._selected_rule_versions({'rule_versions': {'Oral_Cavity': '1', 'Breast': '2'}}, ['Oral_Cavity', 'Breast'])


if __name__ == '__main__':
    unittest.main()

