# Task (T)

> As a Ninja developer, your task is to identify, clarify the requirements, any critical gaps or challenges – (5 mins), define the initial phase and create a system design diagram (10 mins), and get a working prototype of an MVP (40 mins).

The time boxes are not targets; the goal is the outcome, the MVP ([K2](clarifications.md#k2)).

| ID | Item | Standing | Delivered by |
| --- | --- | --- | --- |
| [T1](#t1) | Identify and clarify the requirements | met | these pages and [clarifications](clarifications.md) |
| [T2](#t2) | Identify any critical gaps or challenges | met | [gaps and challenges](gaps.md) |
| [T3](#t3) | Define the initial phase | met | [design/SYSTEM-DESIGN.md](../../design/SYSTEM-DESIGN.md) |
| [T4](#t4) | Create a system design diagram | met | [design/system-design.svg](../../design/system-design.svg) |
| [T5](#t5) | Get a working prototype of an MVP | met | the code, with [the acceptance tests](../../tests/test_use_case.py) |

<a id="t1"></a>

## T1. Identify and clarify the requirements

**Delivered:** the brief split into B, C, U, T and S items (these pages), and the product owner's answers where it is open ([clarifications](clarifications.md)).

<a id="t2"></a>

## T2. Identify any critical gaps or challenges

**Delivered:** [gaps and challenges](gaps.md): identity, audit, approved model use, retrieval quality, scale and the ontology problem. The coverage report lists, file by file, what the stand-in readers could not read.

<a id="t3"></a>

## T3. Define the initial phase

**For the design:** a potential solution, given the background, the use case and the constraints ([K11](clarifications.md#k11)).

**Delivered:** [design/SYSTEM-DESIGN.md](../../design/SYSTEM-DESIGN.md) and the [decision records](../adr/README.md).

<a id="t4"></a>

## T4. Create a system design diagram

**Delivered:** [design/system-design.svg](../../design/system-design.svg), drawn from the initial phase by [`design/make_diagram.py`](../../design/make_diagram.py). It marks what already exists, what the MVP stands in for, and what is out of scope.

<a id="t5"></a>

## T5. Get a working prototype of an MVP

**Delivered:** the service, the MCP server and the web test page. [`tests/test_use_case.py`](../../tests/test_use_case.py) asks the use-case questions through the HTTP API and checks every answer against the files ([ADR 0009](../adr/0009-acceptance-tests-and-evaluation-sets.md)). How to run it: [RUNNING.md](../../RUNNING.md).
