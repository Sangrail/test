# The brief, item by item

A forensic reading of [the brief](../Starting_document.md). Each pillar of the brief is split into items with one ID each, and every item says what it means for the design, where the MVP stands, and which files and [decisions](../adr/README.md) serve it. The product owner's answers to the questions the brief leaves open are the clarifications (K). What the MVP does not solve is on the gaps page (G).

| Page | IDs | What it holds |
| --- | --- | --- |
| [Background](background.md) | [B1](background.md#b1)–[B4](background.md#b4) | The problem as the brief states it |
| [Constraints](constraints.md) | [C1](constraints.md#c1)–[C5](constraints.md#c5) | What already exists in the company. The MVP assumes it and uses labelled stand-ins |
| [Use case](use-case.md) | [U1](use-case.md#u1)–[U6](use-case.md#u6) | Who needs what, how fast and with what confidence |
| [Task](task.md) | [T1](task.md#t1)–[T5](task.md#t5) | What the brief asks to be delivered |
| [Scope](scope.md) | [S1](scope.md#s1)–[S2](scope.md#s2) | An MVP, not the platform. Lists the features that go beyond the brief |
| [Clarifications](clarifications.md) | [K1](clarifications.md#k1)–[K16](clarifications.md#k16) | The product owner's answers where the brief is open |
| [Gaps and challenges](gaps.md) | [G1](gaps.md#g1)–[G8](gaps.md#g8), [O1](gaps.md#o1)–[O2](gaps.md#o2) | What the MVP leaves unsolved, and what is out of scope but recorded |

**Standing** of an item:

- *context*: a fact about the problem, not something to meet.
- *assumed*: the brief says it already exists. The MVP does not build it; a minimal, labelled stand-in shows the flow.
- *met*: met by the MVP on the test repository.
- *partly met*: met in part; the item says what is missing and which gap holds it.

**Rules:**

- Every decision record cites the IDs it serves. A decision that cites none does not belong in this MVP.
- A change that steps outside an item is flagged in its commit message (`Constraints:` line, see [AGENTS.md](../../AGENTS.md)), not hidden.
- IDs are not renumbered. A withdrawn item stays, marked withdrawn, with the reason.
- The pages are written by hand. The brief itself is never edited.
