-- Design records: the source of truth for the brief, the constraints and the
-- architecture decision records. docs/adr/, docs/constraints/ and
-- docs/records/index.html are generated from this database.
--
-- Records are versioned and append-only. A version is 'proposed' (a draft, which
-- can be edited), 'active' (the current one, at most one per record), 'displaced'
-- (replaced by a newer version) or 'withdrawn' (the record no longer applies).
-- Active and past versions cannot be edited or deleted: triggers refuse it.
--
-- Change records through the views at the end of this file (constraint_current,
-- decision_current, decision_section_current, drafts, reviews). See
-- docs/records/README.md for examples.

CREATE TABLE sources (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  path TEXT,                     -- repository path, when the source is a file
  date TEXT
);

CREATE TABLE brief_sections (    -- docs/Starting_document.md, verbatim
  heading TEXT PRIMARY KEY,
  position INTEGER NOT NULL,
  text TEXT NOT NULL
);

CREATE TABLE constraint_groups (
  code TEXT PRIMARY KEY,         -- the ID prefix: B C U T S R P
  position INTEGER NOT NULL,
  name TEXT NOT NULL,
  page TEXT NOT NULL,            -- file under docs/constraints/
  summary TEXT NOT NULL,
  intro TEXT NOT NULL
);

-- Items of intent, constraint and scope: a stable identity, and its versions. The
-- table is called constraints because the IDs (U3, C3, S2) are constraint IDs
-- throughout the documents; pillar says which of the three an item is.

CREATE TABLE constraints (
  id TEXT PRIMARY KEY,           -- for example U3; never renumbered or reused
  group_code TEXT NOT NULL REFERENCES constraint_groups(code),
  position INTEGER NOT NULL
);

CREATE TABLE constraint_versions (
  constraint_id TEXT NOT NULL REFERENCES constraints(id),
  version INTEGER NOT NULL,
  lifecycle TEXT NOT NULL DEFAULT 'proposed' CHECK (lifecycle IN ('proposed', 'active', 'displaced', 'withdrawn')),
  pillar TEXT NOT NULL CHECK (pillar IN ('intent', 'constraint', 'scope')),
  title TEXT NOT NULL,
  statement TEXT NOT NULL,
  source_id TEXT NOT NULL REFERENCES sources(id),
  brief_section TEXT REFERENCES brief_sections(heading),
  source_note TEXT,
  meaning TEXT NOT NULL,         -- what it means for the design
  standing TEXT NOT NULL CHECK (standing IN ('context', 'assumed', 'met', 'partly met', 'not met', 'exceeded')),
  mvp TEXT NOT NULL,             -- where the MVP stands
  change_reason TEXT NOT NULL,   -- why this version exists
  changed_by TEXT NOT NULL DEFAULT 'unknown',
  valid_from TEXT,               -- when it became active
  valid_to TEXT,                 -- when it was displaced or withdrawn
  end_reason TEXT,
  PRIMARY KEY (constraint_id, version)
);
CREATE UNIQUE INDEX one_active_constraint_version ON constraint_versions(constraint_id) WHERE lifecycle = 'active';
CREATE UNIQUE INDEX one_draft_constraint_version ON constraint_versions(constraint_id) WHERE lifecycle = 'proposed';

CREATE TABLE constraint_files (
  constraint_id TEXT NOT NULL,
  version INTEGER NOT NULL,
  path TEXT NOT NULL,            -- repository path
  role TEXT NOT NULL CHECK (role IN ('stand-in', 'enforced by', 'measured by', 'delivered by')),
  PRIMARY KEY (constraint_id, version, path, role)
);

-- Decision records: a stable number, and its versions.

CREATE TABLE decisions (
  number INTEGER PRIMARY KEY,
  slug TEXT NOT NULL UNIQUE      -- the page is docs/adr/NNNN-slug.md
);

CREATE TABLE decision_versions (
  number INTEGER NOT NULL REFERENCES decisions(number),
  version INTEGER NOT NULL,
  lifecycle TEXT NOT NULL DEFAULT 'proposed' CHECK (lifecycle IN ('proposed', 'active', 'displaced', 'withdrawn')),
  title TEXT NOT NULL,
  summary TEXT NOT NULL,         -- one line for the index
  status TEXT NOT NULL,          -- the ADR status: accepted, amended by ..., superseded in part by ...
  date TEXT NOT NULL,            -- the date of the decision
  notes TEXT NOT NULL DEFAULT '',  -- under the title: supersession and amendment notes
  implementation_summary TEXT NOT NULL,
  change_reason TEXT NOT NULL,
  changed_by TEXT NOT NULL DEFAULT 'unknown',
  valid_from TEXT,
  valid_to TEXT,
  end_reason TEXT,
  PRIMARY KEY (number, version)
);
CREATE UNIQUE INDEX one_active_decision_version ON decision_versions(number) WHERE lifecycle = 'active';
CREATE UNIQUE INDEX one_draft_decision_version ON decision_versions(number) WHERE lifecycle = 'proposed';

CREATE TABLE decision_sections (
  number INTEGER NOT NULL,
  version INTEGER NOT NULL,
  position INTEGER NOT NULL,
  heading TEXT NOT NULL,         -- Context, Decision, Consequences, Implementation
  body TEXT NOT NULL,
  PRIMARY KEY (number, version, position)
);

CREATE TABLE decision_constraints (
  number INTEGER NOT NULL,
  version INTEGER NOT NULL,
  constraint_id TEXT NOT NULL REFERENCES constraints(id),
  relation TEXT NOT NULL CHECK (relation IN ('serves', 'not met', 'exceeds', 'cites')),
  position INTEGER NOT NULL,
  reason TEXT,
  constraint_version INTEGER,    -- the version the decision was made under; filled in on insert
  PRIMARY KEY (number, version, constraint_id, relation)
);

CREATE TABLE decision_relations (
  number INTEGER NOT NULL,
  version INTEGER NOT NULL,
  other INTEGER NOT NULL REFERENCES decisions(number),
  kind TEXT NOT NULL CHECK (kind IN ('supersedes in part', 'amends', 'extends')),
  PRIMARY KEY (number, version, other, kind)
);

CREATE TABLE decision_files (
  number INTEGER NOT NULL,
  version INTEGER NOT NULL,
  path TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('implements', 'tests', 'measures')),
  PRIMARY KEY (number, version, path)
);

-- A review confirms that an active decision still holds under a newer version of
-- a constraint it links. Reviews are never changed or deleted.
CREATE TABLE decision_reviews (
  number INTEGER NOT NULL,
  version INTEGER NOT NULL,      -- the decision version reviewed
  constraint_id TEXT NOT NULL,
  constraint_version INTEGER NOT NULL,
  note TEXT NOT NULL,
  reviewed_by TEXT NOT NULL DEFAULT 'unknown',
  reviewed_at TEXT NOT NULL,
  PRIMARY KEY (number, version, constraint_id, constraint_version)
);

-- Append-only guards ---------------------------------------------------------------

-- A new version starts as a draft.
CREATE TRIGGER constraint_version_insert BEFORE INSERT ON constraint_versions WHEN NEW.lifecycle IS NOT 'proposed'
BEGIN SELECT RAISE(ABORT, 'insert a version as proposed (or use the drafts view), then activate it'); END;
CREATE TRIGGER decision_version_insert BEFORE INSERT ON decision_versions WHEN NEW.lifecycle IS NOT 'proposed'
BEGIN SELECT RAISE(ABORT, 'insert a version as proposed (or use the drafts view), then activate it'); END;

-- Only a draft can be deleted (discarded).
CREATE TRIGGER constraint_version_delete BEFORE DELETE ON constraint_versions WHEN OLD.lifecycle IS NOT 'proposed'
BEGIN SELECT RAISE(ABORT, 'active and past versions are kept: withdraw the record instead'); END;
CREATE TRIGGER decision_version_delete BEFORE DELETE ON decision_versions WHEN OLD.lifecycle IS NOT 'proposed'
BEGIN SELECT RAISE(ABORT, 'active and past versions are kept: withdraw the record instead'); END;

-- A draft can be edited and activated. An active version can only be displaced or
-- withdrawn, and its dates and end reason set once. Nothing else changes.
CREATE TRIGGER constraint_version_update BEFORE UPDATE ON constraint_versions
WHEN NOT (
  NEW.constraint_id IS OLD.constraint_id AND NEW.version IS OLD.version AND (
    (OLD.lifecycle = 'proposed' AND NEW.lifecycle IN ('proposed', 'active'))
    OR (NEW.pillar IS OLD.pillar AND NEW.title IS OLD.title AND NEW.statement IS OLD.statement AND NEW.source_id IS OLD.source_id
        AND NEW.brief_section IS OLD.brief_section AND NEW.source_note IS OLD.source_note AND NEW.meaning IS OLD.meaning
        AND NEW.standing IS OLD.standing AND NEW.mvp IS OLD.mvp AND NEW.change_reason IS OLD.change_reason
        AND NEW.changed_by IS OLD.changed_by
        AND (NEW.valid_from IS OLD.valid_from OR (OLD.valid_from IS NULL AND NEW.lifecycle = 'active'))
        AND (NEW.valid_to IS OLD.valid_to OR (OLD.valid_to IS NULL AND NEW.lifecycle IN ('displaced', 'withdrawn')))
        AND (NEW.end_reason IS OLD.end_reason OR (OLD.end_reason IS NULL AND NEW.lifecycle IN ('displaced', 'withdrawn')))
        AND (NEW.lifecycle = OLD.lifecycle OR (OLD.lifecycle = 'active' AND NEW.lifecycle IN ('displaced', 'withdrawn')))))
)
BEGIN SELECT RAISE(ABORT, 'active and past versions cannot be edited: make a new version (drafts, or constraint_current)'); END;

CREATE TRIGGER decision_version_update BEFORE UPDATE ON decision_versions
WHEN NOT (
  NEW.number IS OLD.number AND NEW.version IS OLD.version AND (
    (OLD.lifecycle = 'proposed' AND NEW.lifecycle IN ('proposed', 'active'))
    OR (NEW.title IS OLD.title AND NEW.summary IS OLD.summary AND NEW.status IS OLD.status AND NEW.date IS OLD.date
        AND NEW.notes IS OLD.notes AND NEW.implementation_summary IS OLD.implementation_summary
        AND NEW.change_reason IS OLD.change_reason AND NEW.changed_by IS OLD.changed_by
        AND (NEW.valid_from IS OLD.valid_from OR (OLD.valid_from IS NULL AND NEW.lifecycle = 'active'))
        AND (NEW.valid_to IS OLD.valid_to OR (OLD.valid_to IS NULL AND NEW.lifecycle IN ('displaced', 'withdrawn')))
        AND (NEW.end_reason IS OLD.end_reason OR (OLD.end_reason IS NULL AND NEW.lifecycle IN ('displaced', 'withdrawn')))
        AND (NEW.lifecycle = OLD.lifecycle OR (OLD.lifecycle = 'active' AND NEW.lifecycle IN ('displaced', 'withdrawn')))))
)
BEGIN SELECT RAISE(ABORT, 'active and past versions cannot be edited: make a new version (drafts, or decision_current)'); END;

-- Rows that belong to a version can be changed only while the version is a draft.
CREATE TRIGGER constraint_files_insert BEFORE INSERT ON constraint_files
WHEN (SELECT lifecycle FROM constraint_versions WHERE constraint_id = NEW.constraint_id AND version = NEW.version) IS NOT 'proposed'
BEGIN SELECT RAISE(ABORT, 'constraint_files: change a draft only (insert into drafts first)'); END;
CREATE TRIGGER constraint_files_update BEFORE UPDATE ON constraint_files
WHEN (SELECT lifecycle FROM constraint_versions WHERE constraint_id = OLD.constraint_id AND version = OLD.version) IS NOT 'proposed'
  OR (SELECT lifecycle FROM constraint_versions WHERE constraint_id = NEW.constraint_id AND version = NEW.version) IS NOT 'proposed'
BEGIN SELECT RAISE(ABORT, 'constraint_files: change a draft only (insert into drafts first)'); END;
CREATE TRIGGER constraint_files_delete BEFORE DELETE ON constraint_files
WHEN (SELECT lifecycle FROM constraint_versions WHERE constraint_id = OLD.constraint_id AND version = OLD.version) IN ('active', 'displaced', 'withdrawn')
BEGIN SELECT RAISE(ABORT, 'constraint_files: change a draft only (insert into drafts first)'); END;

CREATE TRIGGER decision_sections_insert BEFORE INSERT ON decision_sections
WHEN (SELECT lifecycle FROM decision_versions WHERE number = NEW.number AND version = NEW.version) IS NOT 'proposed'
BEGIN SELECT RAISE(ABORT, 'decision_sections: change a draft only (insert into drafts first)'); END;
CREATE TRIGGER decision_sections_update BEFORE UPDATE ON decision_sections
WHEN (SELECT lifecycle FROM decision_versions WHERE number = OLD.number AND version = OLD.version) IS NOT 'proposed'
  OR (SELECT lifecycle FROM decision_versions WHERE number = NEW.number AND version = NEW.version) IS NOT 'proposed'
BEGIN SELECT RAISE(ABORT, 'decision_sections: change a draft only (insert into drafts first)'); END;
CREATE TRIGGER decision_sections_delete BEFORE DELETE ON decision_sections
WHEN (SELECT lifecycle FROM decision_versions WHERE number = OLD.number AND version = OLD.version) IN ('active', 'displaced', 'withdrawn')
BEGIN SELECT RAISE(ABORT, 'decision_sections: change a draft only (insert into drafts first)'); END;

CREATE TRIGGER decision_constraints_insert BEFORE INSERT ON decision_constraints
WHEN (SELECT lifecycle FROM decision_versions WHERE number = NEW.number AND version = NEW.version) IS NOT 'proposed'
BEGIN SELECT RAISE(ABORT, 'decision_constraints: change a draft only (insert into drafts first)'); END;
CREATE TRIGGER decision_constraints_update BEFORE UPDATE ON decision_constraints
WHEN (SELECT lifecycle FROM decision_versions WHERE number = OLD.number AND version = OLD.version) IS NOT 'proposed'
  OR (SELECT lifecycle FROM decision_versions WHERE number = NEW.number AND version = NEW.version) IS NOT 'proposed'
BEGIN SELECT RAISE(ABORT, 'decision_constraints: change a draft only (insert into drafts first)'); END;
CREATE TRIGGER decision_constraints_delete BEFORE DELETE ON decision_constraints
WHEN (SELECT lifecycle FROM decision_versions WHERE number = OLD.number AND version = OLD.version) IN ('active', 'displaced', 'withdrawn')
BEGIN SELECT RAISE(ABORT, 'decision_constraints: change a draft only (insert into drafts first)'); END;

CREATE TRIGGER decision_relations_insert BEFORE INSERT ON decision_relations
WHEN (SELECT lifecycle FROM decision_versions WHERE number = NEW.number AND version = NEW.version) IS NOT 'proposed'
BEGIN SELECT RAISE(ABORT, 'decision_relations: change a draft only (insert into drafts first)'); END;
CREATE TRIGGER decision_relations_update BEFORE UPDATE ON decision_relations
WHEN (SELECT lifecycle FROM decision_versions WHERE number = OLD.number AND version = OLD.version) IS NOT 'proposed'
  OR (SELECT lifecycle FROM decision_versions WHERE number = NEW.number AND version = NEW.version) IS NOT 'proposed'
BEGIN SELECT RAISE(ABORT, 'decision_relations: change a draft only (insert into drafts first)'); END;
CREATE TRIGGER decision_relations_delete BEFORE DELETE ON decision_relations
WHEN (SELECT lifecycle FROM decision_versions WHERE number = OLD.number AND version = OLD.version) IN ('active', 'displaced', 'withdrawn')
BEGIN SELECT RAISE(ABORT, 'decision_relations: change a draft only (insert into drafts first)'); END;

CREATE TRIGGER decision_files_insert BEFORE INSERT ON decision_files
WHEN (SELECT lifecycle FROM decision_versions WHERE number = NEW.number AND version = NEW.version) IS NOT 'proposed'
BEGIN SELECT RAISE(ABORT, 'decision_files: change a draft only (insert into drafts first)'); END;
CREATE TRIGGER decision_files_update BEFORE UPDATE ON decision_files
WHEN (SELECT lifecycle FROM decision_versions WHERE number = OLD.number AND version = OLD.version) IS NOT 'proposed'
  OR (SELECT lifecycle FROM decision_versions WHERE number = NEW.number AND version = NEW.version) IS NOT 'proposed'
BEGIN SELECT RAISE(ABORT, 'decision_files: change a draft only (insert into drafts first)'); END;
CREATE TRIGGER decision_files_delete BEFORE DELETE ON decision_files
WHEN (SELECT lifecycle FROM decision_versions WHERE number = OLD.number AND version = OLD.version) IN ('active', 'displaced', 'withdrawn')
BEGIN SELECT RAISE(ABORT, 'decision_files: change a draft only (insert into drafts first)'); END;

CREATE TRIGGER decision_reviews_update BEFORE UPDATE ON decision_reviews
BEGIN SELECT RAISE(ABORT, 'reviews are kept as they were made'); END;
CREATE TRIGGER decision_reviews_delete BEFORE DELETE ON decision_reviews
BEGIN SELECT RAISE(ABORT, 'reviews are kept as they were made'); END;

-- Lifecycle ------------------------------------------------------------------------

-- Activating a draft displaces the active version, at the time the draft takes effect.
CREATE TRIGGER constraint_version_activate BEFORE UPDATE OF lifecycle ON constraint_versions
WHEN OLD.lifecycle = 'proposed' AND NEW.lifecycle = 'active'
BEGIN
  UPDATE constraint_versions
     SET lifecycle = 'displaced', valid_to = coalesce(NEW.valid_from, strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
         end_reason = 'Displaced by version ' || NEW.version
   WHERE constraint_id = NEW.constraint_id AND lifecycle = 'active';
END;
CREATE TRIGGER constraint_version_activated AFTER UPDATE OF lifecycle ON constraint_versions
WHEN OLD.lifecycle = 'proposed' AND NEW.lifecycle = 'active' AND NEW.valid_from IS NULL
BEGIN
  UPDATE constraint_versions SET valid_from = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
   WHERE constraint_id = NEW.constraint_id AND version = NEW.version;
END;
CREATE TRIGGER constraint_version_withdrawn AFTER UPDATE OF lifecycle ON constraint_versions
WHEN OLD.lifecycle = 'active' AND NEW.lifecycle = 'withdrawn' AND NEW.valid_to IS NULL
BEGIN
  UPDATE constraint_versions SET valid_to = strftime('%Y-%m-%dT%H:%M:%SZ', 'now'), end_reason = coalesce(end_reason, 'Withdrawn')
   WHERE constraint_id = NEW.constraint_id AND version = NEW.version;
END;

CREATE TRIGGER decision_version_activate BEFORE UPDATE OF lifecycle ON decision_versions
WHEN OLD.lifecycle = 'proposed' AND NEW.lifecycle = 'active'
BEGIN
  SELECT RAISE(ABORT, 'a decision needs its four sections written before it is activated') WHERE EXISTS
    (SELECT 1 FROM decision_sections WHERE number = NEW.number AND version = NEW.version AND trim(body) = '');
  SELECT RAISE(ABORT, 'a decision must serve at least one item of intent, constraint or scope') WHERE NOT EXISTS
    (SELECT 1 FROM decision_constraints WHERE number = NEW.number AND version = NEW.version AND relation = 'serves');
  UPDATE decision_versions
     SET lifecycle = 'displaced', valid_to = coalesce(NEW.valid_from, strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
         end_reason = 'Displaced by version ' || NEW.version
   WHERE number = NEW.number AND lifecycle = 'active';
END;
CREATE TRIGGER decision_version_activated AFTER UPDATE OF lifecycle ON decision_versions
WHEN OLD.lifecycle = 'proposed' AND NEW.lifecycle = 'active' AND NEW.valid_from IS NULL
BEGIN
  UPDATE decision_versions SET valid_from = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
   WHERE number = NEW.number AND version = NEW.version;
END;
CREATE TRIGGER decision_version_withdrawn AFTER UPDATE OF lifecycle ON decision_versions
WHEN OLD.lifecycle = 'active' AND NEW.lifecycle = 'withdrawn' AND NEW.valid_to IS NULL
BEGIN
  UPDATE decision_versions SET valid_to = strftime('%Y-%m-%dT%H:%M:%SZ', 'now'), end_reason = coalesce(end_reason, 'Withdrawn')
   WHERE number = NEW.number AND version = NEW.version;
END;

-- Discarding a draft discards its rows.
CREATE TRIGGER constraint_draft_discarded AFTER DELETE ON constraint_versions
BEGIN DELETE FROM constraint_files WHERE constraint_id = OLD.constraint_id AND version = OLD.version; END;
CREATE TRIGGER decision_draft_discarded AFTER DELETE ON decision_versions
BEGIN
  DELETE FROM decision_sections WHERE number = OLD.number AND version = OLD.version;
  DELETE FROM decision_constraints WHERE number = OLD.number AND version = OLD.version;
  DELETE FROM decision_relations WHERE number = OLD.number AND version = OLD.version;
  DELETE FROM decision_files WHERE number = OLD.number AND version = OLD.version;
END;

-- A link records the version of the constraint that is active when the link is made.
CREATE TRIGGER decision_constraint_pin AFTER INSERT ON decision_constraints WHEN NEW.constraint_version IS NULL
BEGIN
  UPDATE decision_constraints
     SET constraint_version = (SELECT version FROM constraint_versions WHERE constraint_id = NEW.constraint_id AND lifecycle = 'active')
   WHERE number = NEW.number AND version = NEW.version AND constraint_id = NEW.constraint_id AND relation = NEW.relation;
END;

-- Reading the current records ------------------------------------------------------

CREATE VIEW constraint_current AS
SELECT c.id, c.group_code, c.position, v.version, v.pillar, v.title, v.statement, v.source_id, v.brief_section, v.source_note,
       v.meaning, v.standing, v.mvp, v.change_reason, v.changed_by, v.valid_from
  FROM constraints c JOIN constraint_versions v ON v.constraint_id = c.id AND v.lifecycle = 'active';

CREATE VIEW constraint_file_current AS
SELECT f.constraint_id, f.path, f.role
  FROM constraint_files f JOIN constraint_versions v
    ON v.constraint_id = f.constraint_id AND v.version = f.version AND v.lifecycle = 'active';

CREATE VIEW decision_current AS
SELECT d.number, d.slug, v.version, v.title, v.summary, v.status, v.date, v.notes, v.implementation_summary,
       v.change_reason, v.changed_by, v.valid_from
  FROM decisions d JOIN decision_versions v ON v.number = d.number AND v.lifecycle = 'active';

CREATE VIEW decision_section_current AS
SELECT s.number, s.position, s.heading, s.body, NULL AS change_reason, NULL AS changed_by
  FROM decision_sections s JOIN decision_versions v ON v.number = s.number AND v.version = s.version AND v.lifecycle = 'active';

CREATE VIEW decision_constraint_current AS
SELECT l.number, l.constraint_id, l.relation, l.position, l.reason, l.constraint_version
  FROM decision_constraints l JOIN decision_versions v ON v.number = l.number AND v.version = l.version AND v.lifecycle = 'active';

CREATE VIEW decision_relation_current AS
SELECT r.number, r.other, r.kind
  FROM decision_relations r JOIN decision_versions v ON v.number = r.number AND v.version = r.version AND v.lifecycle = 'active';

CREATE VIEW decision_file_current AS
SELECT f.number, f.path, f.role
  FROM decision_files f JOIN decision_versions v ON v.number = f.number AND v.version = f.version AND v.lifecycle = 'active';

-- Every version of every record, oldest first.
CREATE VIEW history AS
SELECT 'constraint' AS kind, constraint_id AS id, version, lifecycle, title, change_reason, changed_by, valid_from, valid_to, end_reason
  FROM constraint_versions
UNION ALL
SELECT 'decision', printf('%04d', number), version, lifecycle, title, change_reason, changed_by, valid_from, valid_to, end_reason
  FROM decision_versions;

-- Active decisions that link a constraint whose wording or meaning (title, statement,
-- pillar, meaning) has changed since the decision was made, or that has been
-- withdrawn, and that no review of this decision has confirmed against the change.
-- A new assessment (standing, where the MVP stands) does not need a review.
CREATE VIEW needs_review AS
SELECT l.number, l.version AS decision_version, l.constraint_id, l.relation, l.constraint_version AS made_under,
       c.version AS current_version, CASE WHEN c.version IS NULL THEN 'withdrawn' ELSE 'changed' END AS change
  FROM decision_constraints l
  JOIN decision_versions d ON d.number = l.number AND d.version = l.version AND d.lifecycle = 'active'
  JOIN constraint_versions m ON m.constraint_id = l.constraint_id AND m.version = l.constraint_version
  LEFT JOIN constraint_versions c ON c.constraint_id = l.constraint_id AND c.lifecycle = 'active'
 WHERE (c.version IS NULL OR (c.version IS NOT m.version AND (c.title IS NOT m.title OR c.statement IS NOT m.statement
        OR c.pillar IS NOT m.pillar OR c.meaning IS NOT m.meaning)))
   AND NOT EXISTS (SELECT 1 FROM decision_reviews r WHERE r.number = l.number
                      AND r.constraint_id = l.constraint_id AND r.constraint_version IS c.version);

CREATE VIEW drafts AS
SELECT 'constraint' AS kind, constraint_id AS id, version, change_reason, changed_by
  FROM constraint_versions WHERE lifecycle = 'proposed'
UNION ALL
SELECT 'decision', CAST(number AS TEXT), version, change_reason, changed_by
  FROM decision_versions WHERE lifecycle = 'proposed';

CREATE VIEW reviews AS
SELECT number, version, constraint_id, constraint_version, note, reviewed_by, reviewed_at FROM decision_reviews;

-- Changing records -----------------------------------------------------------------

-- INSERT INTO drafts (kind, id, change_reason, changed_by): copy the active version
-- of a record into a new draft, to edit and then activate with
-- UPDATE constraint_versions SET lifecycle = 'active' WHERE ... AND lifecycle = 'proposed'.
CREATE TRIGGER drafts_insert_constraint INSTEAD OF INSERT ON drafts WHEN NEW.kind = 'constraint'
BEGIN
  SELECT RAISE(ABORT, 'drafts: say why in change_reason') WHERE NEW.change_reason IS NULL OR trim(NEW.change_reason) = '';
  SELECT RAISE(ABORT, 'drafts: this constraint already has a draft') WHERE EXISTS
    (SELECT 1 FROM constraint_versions WHERE constraint_id = NEW.id AND lifecycle = 'proposed');
  SELECT RAISE(ABORT, 'drafts: no active version; add a new constraint through constraint_current') WHERE NOT EXISTS
    (SELECT 1 FROM constraint_versions WHERE constraint_id = NEW.id AND lifecycle = 'active');
  INSERT INTO constraint_versions (constraint_id, version, pillar, title, statement, source_id, brief_section, source_note,
                                   meaning, standing, mvp, change_reason, changed_by)
  SELECT constraint_id, (SELECT max(version) + 1 FROM constraint_versions WHERE constraint_id = NEW.id), pillar, title, statement,
         source_id, brief_section, source_note, meaning, standing, mvp, NEW.change_reason, coalesce(NEW.changed_by, 'unknown')
    FROM constraint_versions WHERE constraint_id = NEW.id AND lifecycle = 'active';
  INSERT INTO constraint_files (constraint_id, version, path, role)
  SELECT constraint_id, (SELECT version FROM constraint_versions WHERE constraint_id = NEW.id AND lifecycle = 'proposed'), path, role
    FROM constraint_file_current WHERE constraint_id = NEW.id;
END;

CREATE TRIGGER drafts_insert_decision INSTEAD OF INSERT ON drafts WHEN NEW.kind = 'decision'
BEGIN
  SELECT RAISE(ABORT, 'drafts: say why in change_reason') WHERE NEW.change_reason IS NULL OR trim(NEW.change_reason) = '';
  SELECT RAISE(ABORT, 'drafts: this decision already has a draft') WHERE EXISTS
    (SELECT 1 FROM decision_versions WHERE number = CAST(NEW.id AS INTEGER) AND lifecycle = 'proposed');
  SELECT RAISE(ABORT, 'drafts: no active version; add a new decision through decision_current') WHERE NOT EXISTS
    (SELECT 1 FROM decision_versions WHERE number = CAST(NEW.id AS INTEGER) AND lifecycle = 'active');
  INSERT INTO decision_versions (number, version, title, summary, status, date, notes, implementation_summary, change_reason, changed_by)
  SELECT number, (SELECT max(version) + 1 FROM decision_versions WHERE number = CAST(NEW.id AS INTEGER)), title, summary, status,
         date, notes, implementation_summary, NEW.change_reason, coalesce(NEW.changed_by, 'unknown')
    FROM decision_versions WHERE number = CAST(NEW.id AS INTEGER) AND lifecycle = 'active';
  INSERT INTO decision_sections (number, version, position, heading, body)
  SELECT number, (SELECT version FROM decision_versions WHERE number = CAST(NEW.id AS INTEGER) AND lifecycle = 'proposed'),
         position, heading, body FROM decision_section_current WHERE number = CAST(NEW.id AS INTEGER);
  INSERT INTO decision_constraints (number, version, constraint_id, relation, position, reason, constraint_version)
  SELECT number, (SELECT version FROM decision_versions WHERE number = CAST(NEW.id AS INTEGER) AND lifecycle = 'proposed'),
         constraint_id, relation, position, reason, constraint_version FROM decision_constraint_current WHERE number = CAST(NEW.id AS INTEGER);
  INSERT INTO decision_relations (number, version, other, kind)
  SELECT number, (SELECT version FROM decision_versions WHERE number = CAST(NEW.id AS INTEGER) AND lifecycle = 'proposed'),
         other, kind FROM decision_relation_current WHERE number = CAST(NEW.id AS INTEGER);
  INSERT INTO decision_files (number, version, path, role)
  SELECT number, (SELECT version FROM decision_versions WHERE number = CAST(NEW.id AS INTEGER) AND lifecycle = 'proposed'),
         path, role FROM decision_file_current WHERE number = CAST(NEW.id AS INTEGER);
END;

-- DELETE FROM drafts WHERE kind = ... AND id = ...: discard a draft.
CREATE TRIGGER drafts_delete INSTEAD OF DELETE ON drafts
BEGIN
  DELETE FROM constraint_versions WHERE OLD.kind = 'constraint' AND constraint_id = OLD.id AND lifecycle = 'proposed';
  DELETE FROM decision_versions WHERE OLD.kind = 'decision' AND number = CAST(OLD.id AS INTEGER) AND lifecycle = 'proposed';
END;

-- UPDATE constraint_current SET ..., change_reason = '...' WHERE id = 'U3':
-- make, fill and activate a new version in one statement.
CREATE TRIGGER constraint_current_update INSTEAD OF UPDATE ON constraint_current
BEGIN
  SELECT RAISE(ABORT, 'constraint_current: set change_reason to say why') WHERE NEW.change_reason IS OLD.change_reason
    OR NEW.change_reason IS NULL OR trim(NEW.change_reason) = '';
  SELECT RAISE(ABORT, 'constraint_current: the ID and group cannot change') WHERE NEW.id IS NOT OLD.id OR NEW.group_code IS NOT OLD.group_code;
  INSERT INTO drafts (kind, id, change_reason, changed_by) VALUES ('constraint', OLD.id, NEW.change_reason, NEW.changed_by);
  UPDATE constraint_versions
     SET pillar = NEW.pillar, title = NEW.title, statement = NEW.statement, source_id = NEW.source_id, brief_section = NEW.brief_section,
         source_note = NEW.source_note, meaning = NEW.meaning, standing = NEW.standing, mvp = NEW.mvp
   WHERE constraint_id = OLD.id AND lifecycle = 'proposed';
  UPDATE constraint_versions SET lifecycle = 'active' WHERE constraint_id = OLD.id AND lifecycle = 'proposed';
  UPDATE constraints SET position = NEW.position WHERE id = OLD.id AND NEW.position IS NOT OLD.position;
END;

-- INSERT INTO constraint_current (id, group_code, pillar, title, statement, source_id, meaning, standing, mvp, change_reason):
-- add a constraint, active at once.
CREATE TRIGGER constraint_current_insert INSTEAD OF INSERT ON constraint_current
BEGIN
  SELECT RAISE(ABORT, 'constraint_current: the ID must start with its group code') WHERE substr(NEW.id, 1, 1) IS NOT NEW.group_code;
  INSERT INTO constraints (id, group_code, position)
  VALUES (NEW.id, NEW.group_code, coalesce(NEW.position, (SELECT coalesce(max(position), 0) + 1 FROM constraints WHERE group_code = NEW.group_code)));
  INSERT INTO constraint_versions (constraint_id, version, pillar, title, statement, source_id, brief_section, source_note, meaning,
                                   standing, mvp, change_reason, changed_by)
  VALUES (NEW.id, 1, NEW.pillar, NEW.title, NEW.statement, NEW.source_id, NEW.brief_section, NEW.source_note, NEW.meaning, NEW.standing,
          NEW.mvp, coalesce(NEW.change_reason, 'New constraint'), coalesce(NEW.changed_by, 'unknown'));
  UPDATE constraint_versions SET lifecycle = 'active' WHERE constraint_id = NEW.id AND version = 1;
END;

-- DELETE FROM constraint_current WHERE id = ...: withdraw. The versions are kept.
CREATE TRIGGER constraint_current_delete INSTEAD OF DELETE ON constraint_current
BEGIN
  UPDATE constraint_versions SET lifecycle = 'withdrawn' WHERE constraint_id = OLD.id AND lifecycle = 'active';
END;

-- UPDATE decision_current SET status = ..., change_reason = ... WHERE number = 18:
-- a new version with the changed header fields, active at once.
CREATE TRIGGER decision_current_update INSTEAD OF UPDATE ON decision_current
BEGIN
  SELECT RAISE(ABORT, 'decision_current: set change_reason to say why') WHERE NEW.change_reason IS OLD.change_reason
    OR NEW.change_reason IS NULL OR trim(NEW.change_reason) = '';
  SELECT RAISE(ABORT, 'decision_current: the number and slug cannot change') WHERE NEW.number IS NOT OLD.number OR NEW.slug IS NOT OLD.slug;
  INSERT INTO drafts (kind, id, change_reason, changed_by) VALUES ('decision', CAST(OLD.number AS TEXT), NEW.change_reason, NEW.changed_by);
  UPDATE decision_versions
     SET title = NEW.title, summary = NEW.summary, status = NEW.status, date = NEW.date, notes = NEW.notes,
         implementation_summary = NEW.implementation_summary
   WHERE number = OLD.number AND lifecycle = 'proposed';
  UPDATE decision_versions SET lifecycle = 'active' WHERE number = OLD.number AND lifecycle = 'proposed';
END;

-- INSERT INTO decision_current (number, slug, title, summary, status, date, implementation_summary, change_reason):
-- a new decision as a draft, with four empty sections. Fill the sections and links,
-- then activate it.
CREATE TRIGGER decision_current_insert INSTEAD OF INSERT ON decision_current
BEGIN
  INSERT INTO decisions (number, slug) VALUES (NEW.number, NEW.slug);
  INSERT INTO decision_versions (number, version, title, summary, status, date, notes, implementation_summary, change_reason, changed_by)
  VALUES (NEW.number, 1, NEW.title, NEW.summary, coalesce(NEW.status, 'proposed'), coalesce(NEW.date, date('now')),
          coalesce(NEW.notes, ''), coalesce(NEW.implementation_summary, 'Not started'), coalesce(NEW.change_reason, 'New decision'),
          coalesce(NEW.changed_by, 'unknown'));
  INSERT INTO decision_sections (number, version, position, heading, body)
  VALUES (NEW.number, 1, 1, 'Context', ''), (NEW.number, 1, 2, 'Decision', ''),
         (NEW.number, 1, 3, 'Consequences', ''), (NEW.number, 1, 4, 'Implementation', '');
END;

-- DELETE FROM decision_current WHERE number = ...: withdraw. The versions are kept.
CREATE TRIGGER decision_current_delete INSTEAD OF DELETE ON decision_current
BEGIN
  UPDATE decision_versions SET lifecycle = 'withdrawn' WHERE number = OLD.number AND lifecycle = 'active';
END;

-- UPDATE decision_section_current SET body = ..., change_reason = ... WHERE number = 18 AND heading = 'Consequences':
-- a new version with the changed section, active at once. Change one section per statement: each row
-- changed makes its own version.
CREATE TRIGGER decision_section_current_update INSTEAD OF UPDATE ON decision_section_current
BEGIN
  SELECT RAISE(ABORT, 'decision_section_current: set change_reason to say why') WHERE NEW.change_reason IS NULL OR trim(NEW.change_reason) = '';
  INSERT INTO drafts (kind, id, change_reason, changed_by) VALUES ('decision', CAST(OLD.number AS TEXT), NEW.change_reason, NEW.changed_by);
  UPDATE decision_sections SET body = NEW.body, heading = NEW.heading
   WHERE number = OLD.number AND position = OLD.position
     AND version = (SELECT version FROM decision_versions WHERE number = OLD.number AND lifecycle = 'proposed');
  UPDATE decision_versions SET lifecycle = 'active' WHERE number = OLD.number AND lifecycle = 'proposed';
END;

-- INSERT INTO reviews (number, constraint_id, note, reviewed_by): confirm that the
-- active decision still holds under the active version of the constraint.
CREATE TRIGGER reviews_insert INSTEAD OF INSERT ON reviews
BEGIN
  SELECT RAISE(ABORT, 'reviews: say what was checked in note') WHERE NEW.note IS NULL OR trim(NEW.note) = '';
  INSERT INTO decision_reviews (number, version, constraint_id, constraint_version, note, reviewed_by, reviewed_at)
  SELECT NEW.number, d.version, NEW.constraint_id, c.version, NEW.note, coalesce(NEW.reviewed_by, 'unknown'),
         coalesce(NEW.reviewed_at, strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
    FROM decision_versions d, constraint_versions c
   WHERE d.number = NEW.number AND d.lifecycle = 'active' AND c.constraint_id = NEW.constraint_id AND c.lifecycle = 'active';
END;
