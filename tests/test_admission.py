"""Admission control: a request is answered within the time budget, or refused at once.

One process serves requests one at a time, so a new request waits for every
request ahead of it. The expected values below are worked out by hand from
that rule; the clock is fake, so the tests do not depend on machine speed."""
from fastapi.testclient import TestClient
import pytest

from engineering_search.adapters import Admission, Busy, SQLiteAuditStore
from engineering_search.app import create_app
from helpers import TEST_REPOSITORY


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def test_a_request_that_would_wait_past_the_budget_is_refused_with_a_retry_time():
    admission = Admission(budget_seconds=1.0, initial_service_seconds=0.1, clock=Clock())
    held = [admission.admit() for _ in range(10)]  # The 10th expects (9 + 1) x 0.1 s = 1.0 s: on budget.
    with pytest.raises(Busy) as refused:
        admission.admit()  # The 11th expects 1.1 s.
    assert refused.value.retry_after_seconds == 1 and refused.value.waiting == 10
    with held[0]:
        pass  # One leaves, so the next one fits again.
    with admission.admit():
        pass
    assert admission.snapshot()["refused_total"] == 1


def test_the_service_time_and_its_spread_are_learnt_from_departures():
    clock = Clock()
    admission = Admission(budget_seconds=3.0, initial_service_seconds=0.1, clock=clock, smoothing=0.2)
    with admission.admit():
        clock.now = 2.0  # One slow request.
    learnt = admission.snapshot()
    assert learnt["service_seconds"] == pytest.approx(0.8 * 0.1 + 0.2 * 2.0)  # 0.48 s
    assert learnt["spread_seconds"] == pytest.approx(0.2 * (2.0 - 0.1))  # 0.38 s
    # The n-th request in the queue expects n x 0.48 + 2 x sqrt(n) x 0.38 seconds:
    # 1.24, 2.03, 2.76 (admitted), then 3.44 (over 3 s, refused).
    held = [admission.admit() for _ in range(3)]
    with pytest.raises(Busy) as refused:
        admission.admit()
    assert refused.value.retry_after_seconds == 1  # ceil(3.44 - 3.0)
    for ticket in held:
        ticket.__exit__(None, None, None)


def test_a_queued_request_is_charged_only_for_its_own_turn():
    clock = Clock()
    admission = Admission(budget_seconds=10.0, initial_service_seconds=0.1, clock=clock, smoothing=1.0)
    first, second = admission.admit(), admission.admit()  # Both arrive at 0 s.
    clock.now = 1.0
    first.__exit__(None, None, None)
    clock.now = 2.0
    second.__exit__(None, None, None)
    # The second waited 1 s for the first; its own service time is 1 s, not 2 s.
    assert admission.snapshot()["service_seconds"] == pytest.approx(1.0)


def test_a_busy_service_answers_503_with_retry_after_and_withholds_evidence(tmp_path):
    full = Admission(budget_seconds=0.0)  # Every request expects more than no time at all.
    app = create_app(root=TEST_REPOSITORY, audit=SQLiteAuditStore(tmp_path / "audit.sqlite3"), admission=full)
    with TestClient(app) as client:
        client.post("/auth/login", json={"user_id": "maya"})
        assert client.post("/index").status_code == 200  # Index operations are not admission-controlled.
        response = client.post("/search", json={"query": "What is the roof load limit at Northgate?"})
        assert response.status_code == 503
        assert response.headers["Retry-After"] == "1"
        detail = response.json()["detail"]
        assert detail["busy"] is True and detail["retry_after_seconds"] == 1
        assert "evidence" not in response.json() and "answer" not in response.json()
        assert client.post("/sql", json={"sql": "SELECT 1"}).status_code == 503
