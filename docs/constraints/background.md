# Background (B)

<!-- Generated from docs/records/design.sqlite. Do not edit: change the database, then run `uv run --frozen python -m design_records generate` (the pre-commit hook runs it). -->

The problem, as [the brief](../Starting_document.md) states it. These are facts about the situation, not requirements; the use case and the constraints answer them.

| ID | Item | Pillar | Standing | Version |
| --- | --- | --- | --- | --- |
| [B1](#b1) | Years of design information in files and documents | intent | context | 1 |
| [B2](#b2) | Users do not know which files hold the answer | intent | context | 1 |

<a id="b1"></a>

## B1. Years of design information in files and documents

> A company has years of engineering and infrastructure design information stored in design files and related project documents.

**Pillar:** intent. **Source:** [The brief](../../docs/Starting_document.md), background.

**Standing:** *context*. A fact about the problem, not a requirement to meet.

**What it means for the design:** The information already exists, spread across many files, formats and versions. The service finds it where it is; it does not ask people to enter it again.

**Where the MVP stands:** 148 synthetic and public test files stand in for the repository ([S3](scope.md#s3)).

**Decisions:** none yet.

**History:**

- Version 1, from 2026-10-29, active. Recorded from the background of the brief.

<a id="b2"></a>

## B2. Users do not know which files hold the answer

> Users often do not know which files contain the information they need.

**Pillar:** intent. **Source:** [The brief](../../docs/Starting_document.md), background.

**Standing:** *context*. A fact about the problem, not a requirement to meet.

**What it means for the design:** Search must work across every file the user may read without the user naming one, and each answer must say where it came from ([U2](use-case.md#u2), [U4](use-case.md#u4)).

**Where the MVP stands:** Each question searches every permitted file, and each answer names its file, location and version.

**Decisions:** none yet.

**History:**

- Version 1, from 2026-10-29, active. Recorded from the background of the brief.
