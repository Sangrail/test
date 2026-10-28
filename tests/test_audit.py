from fastapi.testclient import TestClient
import pytest

from engineering_search.adapters import SQLiteAuditStore
from engineering_search.app import create_app
from engineering_search.jobs import SQLiteJobQueue


def setup(tmp_path):
    store = SQLiteAuditStore(tmp_path / 'audit.sqlite3')
    for n in range(55):
        store.append({'event': 'test_event', 'sequence': n, 'timestamp': f'2026-10-28T12:00:{n:02d}Z',
                      'file_id': 'sensitive-file.md'})
    app = create_app(root=tmp_path, audit=store, queue=SQLiteJobQueue(tmp_path / 'jobs.sqlite3'), worker_count=0)
    return store, TestClient(app)


@pytest.mark.parametrize('identity', [None, 'jp', 'kamal'])
def test_index_and_audit_access_require_index_team(tmp_path, identity):
    _, client = setup(tmp_path)
    if identity:
        client.post('/auth/login', json={'user_id': identity})
    for path in ('/admin', '/audit', '/docs'):
        assert client.get(path, follow_redirects=False).status_code == 303
    for method, path in [('GET', '/audit/events'), ('GET', '/index/status'), ('POST', '/index'),
                         ('POST', '/scan'), ('GET', '/uploads'), ('GET', '/admin/access'),
                         ('GET', '/telemetry'), ('GET', '/openapi.json')]:
        response = client.request(method, path, headers={'X-User': 'maya'})
        assert response.status_code == (403 if identity else 401)
        assert 'sensitive-file.md' not in response.text
        assert response.headers['cache-control'] == 'no-store'
    assert client.get('/static/audit.html').status_code == 404


def test_maya_reads_newest_first_with_stable_pages_and_refresh(tmp_path):
    store, client = setup(tmp_path)
    client.post('/auth/login', json={'user_id': 'maya'})
    assert client.get('/admin').status_code == 200
    assert client.get('/audit').status_code == 200
    first = client.get('/audit/events?limit=20').json()
    assert first['total_events'] == 55 and first['total_pages'] == 3
    assert [e['id'] for e in first['events']] == list(range(55, 35, -1))
    assert first['sort'] == 'recorded_desc'
    store.append({'event': 'new_event'})
    received = first['events']
    for page in (2, 3):
        response = client.get('/audit/events', params={'limit': 20, 'page': page, 'snapshot_id': first['snapshot_id']})
        assert response.headers['cache-control'] == 'no-store'
        data = response.json()
        assert data['total_events'] == 55
        received += data['events']
    assert [e['id'] for e in received] == list(range(55, 0, -1))
    fresh = client.get('/audit/events').json()
    assert fresh['events'][0]['id'] == 56 and fresh['total_events'] == 56
    for params in ({'page': 0}, {'limit': 101}, {'snapshot_id': -1}):
        assert client.get('/audit/events', params=params).status_code == 422
    assert client.get('/audit/events?page=100').json()['events'] == []
    client.post('/auth/login', json={'user_id': 'jp'})
    assert client.get('/audit/events', params={'snapshot_id': first['snapshot_id'], 'page': 2}).status_code == 403


def test_audit_read_failure_is_not_an_empty_log(tmp_path):
    class FailedReader:
        def read_page(self, *args):
            raise OSError('sensitive-path')
    app = create_app(root=tmp_path, audit=SQLiteAuditStore(tmp_path / 'audit.sqlite3'),
                     audit_reader=FailedReader(), queue=SQLiteJobQueue(tmp_path / 'jobs.sqlite3'), worker_count=0)
    client = TestClient(app)
    client.post('/auth/login', json={'user_id': 'maya'})
    response = client.get('/audit/events')
    assert response.status_code == 503 and 'sensitive-path' not in response.text


def test_empty_audit_snapshot_stays_empty_when_events_arrive(tmp_path):
    store = SQLiteAuditStore(tmp_path / 'audit.sqlite3')
    first = store.read_page(1, 20)
    assert first['snapshot_id'] == first['total_pages'] == 0
    store.append({'event': 'new'})
    assert store.read_page(1, 20, first['snapshot_id'])['events'] == []
    assert len(store.read_page(1, 20)['events']) == 1
