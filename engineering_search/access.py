"""Pretend users and file permissions: a stand-in (U1, K13) for the company's identity
provider and the repository's own access controls (gap G1).

Access-control assumptions for the MVP
--------------------------------------
1. Every file in the repository is indexed. Permissions decide what a user
   sees in results; they do not decide what is indexed.
2. Permission is "read" only. A user who may read a file sees all of its
   passages; there is no page- or section-level permission.
3. A rule can be set on the whole repository, on a folder, or on one file.
   Files inherit the rule of the nearest folder above them, like folder
   permissions in Windows.
4. The most specific rule wins and replaces the inherited one. Unlike
   Windows (NTFS), rules are not merged and there are no "deny" entries.
5. Rules name users directly. There are no groups or roles in file rules.
6. Permissions are checked on every search, after matching and before
   counting and paging. A change takes effect on the next request; the index
   is not rebuilt.
7. If the permission check fails, no evidence is returned (fail closed).
8. Login is pretend: anyone can pick a user. Index-team access (Maya) is a
   separate role and does not grant file access. The MCP server takes its
   user from the --user flag and does not verify it. This is a security
   hole: the person who uses the chat client is not matched to the file
   permissions. See docs/MCP.md.
9. A user never gets text, file names or counts from a file that they cannot
   read. The one exception is a demo aid: the sign-in screen shows, for each
   demo user, how many files of each top-level folder they can read. It shows
   no file names and no content. A real system must not show this.
   The audit log (index team only) records file names and line numbers of
   each permission decision. It never records document text.
   tests/test_no_leaks.py checks this for each user.

In production these rules would come from the existing repository's own
permissions (for example the file server or document system) through a
connector, not from this file.
"""
from dataclasses import dataclass
import secrets
from threading import RLock
from time import monotonic
from typing import Protocol

# "can" and "try" are shown on the sign-in screen so a demo shows the differences.
USERS = (
    {"id": "jp", "subject": "demo-user-001", "name": "JP", "title": "Engineering lead", "role": "reader",
     "can": ["Read every file in the repository."],
     "try": "Ask \u201cWhat is the roof load limit?\u201d Results come from Project Cedar, "
            "the specifications and the Northgate PDF."},
    {"id": "kamal", "subject": "demo-user-002", "name": "Kamal", "title": "Structural engineer", "role": "reader",
     "can": ["Read most files. The folder list below shows which."],
     "try": "Ask the same roof load question as JP. The specification and Northgate results do not show."},
    {"id": "maya", "subject": "demo-user-003", "name": "Maya", "title": "Index team", "role": "index_team",
     "can": ["Read most files. The folder list below shows which.",
             "Index documents (Index operations).",
             "Read the audit log, which records each search and its permission decisions."],
     "try": "Search for anything, then open Audit log to see the record of that search."},
)

WHOLE_REPOSITORY = ""
EVERYONE = {"jp", "kamal", "maya"}
JP_AND_KAMAL = {"jp", "kamal"}
JP_AND_MAYA = {"jp", "maya"}
JP_ONLY = {"jp"}

# Path -> users who may read it. A path ending in "/" is a folder.
ACCESS_RULES: dict[str, set[str]] = {
    WHOLE_REPOSITORY:                             EVERYONE,
    "specifications/":                            JP_AND_MAYA,
    "project-northgate/":                         JP_AND_MAYA,
    # project-cedar/ has a rule per file. Files 01 and 02 have none, so
    # they inherit WHOLE_REPOSITORY.
    "project-cedar/03-roof-load.md":              JP_AND_KAMAL,
    "project-cedar/04-beam-capacity.md":          JP_AND_KAMAL,
    "project-cedar/05-foundation.md":             JP_AND_KAMAL,
    "project-cedar/06-material-certificate.md":   JP_AND_MAYA,
    "project-cedar/07-compliance-approval.md":    JP_AND_MAYA,
    "project-cedar/08-environmental-review.md":   JP_AND_MAYA,
    "project-cedar/09-bridge-load.md":            JP_AND_KAMAL,
    "project-cedar/10-restricted-incident.md":    JP_ONLY,
    # project-harbour/ inherits WHOLE_REPOSITORY, except the roof schedule.
    "project-harbour/harbour-roof-schedule.xlsx": JP_AND_MAYA,
}


def folder_access(file_ids: set[str], readable: set[str]) -> list[dict]:
    """For each top-level folder: its file count and how many of them a user can read."""
    counts: dict[str, list[int]] = {}
    for file_id in file_ids:
        folder = file_id.split("/")[0] + "/" if "/" in file_id else "(top level)"
        files, can_read = counts.setdefault(folder, [0, 0]), file_id in readable
        files[0] += 1
        files[1] += can_read
    return [{"folder": folder, "files": files, "readable": can_read,
             "access": "all" if can_read == files else "none" if can_read == 0 else "some"}
            for folder, (files, can_read) in sorted(counts.items())]


def governing_rule(rules: dict[str, set[str]], file_id: str) -> str:
    """Return the most specific rule path that covers file_id."""
    def covers(path: str) -> bool:
        return path in (WHOLE_REPOSITORY, file_id) or (path.endswith("/") and file_id.startswith(path))
    return max(filter(covers, rules), key=len)


@dataclass(frozen=True)
class PermissionSnapshot:
    version: str
    allowed: frozenset[str]
    reasons: dict[str, str]


class PermissionStore(Protocol):
    def evaluate(self, subject: str, file_ids: set[str]) -> PermissionSnapshot: ...


class MockPermissionStore:
    """Path rules, checked on every request. Separate from index-team access."""
    version = "path-rules-v1"

    def __init__(self, rules: dict[str, set[str]] | None = None):
        self.rules = dict(ACCESS_RULES if rules is None else rules)
        self.subjects = {u["id"]: u["subject"] for u in USERS}

    def readers(self, file_id: str) -> set[str]:
        return self.rules[governing_rule(self.rules, file_id)]

    def evaluate(self, subject, file_ids):
        allowed = set()
        reasons = {}
        for file_id in file_ids:
            rule = governing_rule(self.rules, file_id)
            permit = subject in {self.subjects[user] for user in self.rules[rule]}
            reasons[file_id] = f"{'allowed' if permit else 'denied'} by rule '{rule or '(whole repository)'}'"
            if permit:
                allowed.add(file_id)
        return PermissionSnapshot(self.version, frozenset(allowed), reasons)


class DemoSessions:
    """Anyone can select a demo user. The opaque cookie only binds that selection.

    This is not identity verification. Replace it with a real identity provider
    before treating role or file restrictions as a production security boundary.
    """
    cookie = "engineering_demo_session"
    ttl = 8 * 60 * 60

    def __init__(self):
        self.lock = RLock()
        self.sessions = {}

    def create(self, user_id):
        user = next((u for u in USERS if u["id"] == user_id), None)
        if user is None:
            raise ValueError("Unknown demo user")
        token = secrets.token_urlsafe(32)
        with self.lock:
            self.sessions = {key: value for key, value in self.sessions.items() if value[1] > monotonic()}
            self.sessions[token] = (user, monotonic()+self.ttl)
        return token, user

    def resolve(self, token):
        with self.lock:
            entry = self.sessions.get(token)
            if not entry or entry[1] <= monotonic():
                return None
            return entry[0]

    def revoke(self, token):
        with self.lock:
            self.sessions.pop(token, None)

