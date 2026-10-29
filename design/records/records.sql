BEGIN TRANSACTION;
CREATE TABLE brief_sections (    -- docs/Starting_document.md, verbatim
  heading TEXT PRIMARY KEY,
  position INTEGER NOT NULL,
  text TEXT NOT NULL
);
INSERT INTO "brief_sections" VALUES('Background',1,'A company has years of engineering and infrastructure design information stored in design files and related project documents. Users often do not know which files contain the information they need, and they do not want to learn file formats, schema details, query languages, or system-specific jargon.');
INSERT INTO "brief_sections" VALUES('Constraints',2,'A broader architecture direction already exists, the files live in an existing repository, Connector and APIs can extract metadata/text/properties from supported files, extracted information can be stored in structured and/or semantic stores, and a chat-agent shell can call backend APIs or tools to expose a conversational plane for users.');
INSERT INTO "brief_sections" VALUES('Use Case',3,'We want a selected engineering manager or lead to be able to find a critical engineering parameter (e.g., a load limit, a material specification, or a compliance approval status) across 100+ project documents in under 10 seconds, with 100% confidence in the source, without opening a single design file (CAD) or tool (PDF viewer).');
INSERT INTO "brief_sections" VALUES('Task',4,'As a Ninja developer, your task is to identify, clarify the requirements, any critical gaps or challenges – (5 mins), define the initial phase and create a system design diagram (10 mins), and get a working prototype of an MVP (40 mins).');
INSERT INTO "brief_sections" VALUES('Scope',5,'Initial scope is just an MVP and NOT the final platform or solution.');
CREATE TABLE constraint_files (
  constraint_id TEXT NOT NULL REFERENCES constraints(id),
  path TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('stand-in', 'enforced by', 'measured by', 'delivered by')),
  PRIMARY KEY (constraint_id, path, role)
);
INSERT INTO "constraint_files" VALUES('C1','engineering_search/service.py','stand-in');
INSERT INTO "constraint_files" VALUES('C1','engineering_search/app.py','stand-in');
INSERT INTO "constraint_files" VALUES('C1','engineering_search/mcp_server.py','stand-in');
INSERT INTO "constraint_files" VALUES('C2','test-repository','stand-in');
INSERT INTO "constraint_files" VALUES('C2','engineering_search/access.py','stand-in');
INSERT INTO "constraint_files" VALUES('C3','engineering_search/indexing/readers','stand-in');
INSERT INTO "constraint_files" VALUES('C3','tests/test_indexer.py','enforced by');
INSERT INTO "constraint_files" VALUES('C4','engineering_search/store.py','stand-in');
INSERT INTO "constraint_files" VALUES('C4','engineering_search/sql.py','stand-in');
INSERT INTO "constraint_files" VALUES('C5','engineering_search/mcp_server.py','stand-in');
INSERT INTO "constraint_files" VALUES('C5','tests/test_mcp_stdio.py','enforced by');
INSERT INTO "constraint_files" VALUES('U1','tests/test_use_case.py','enforced by');
INSERT INTO "constraint_files" VALUES('U1','scripts/evaluate.py','measured by');
INSERT INTO "constraint_files" VALUES('U1','evaluation/questions.json','measured by');
INSERT INTO "constraint_files" VALUES('U2','tests/test_use_case.py','enforced by');
INSERT INTO "constraint_files" VALUES('U3','tests/test_use_case.py','enforced by');
INSERT INTO "constraint_files" VALUES('U3','tests/test_admission.py','enforced by');
INSERT INTO "constraint_files" VALUES('U3','scripts/load_test.py','measured by');
INSERT INTO "constraint_files" VALUES('U4','tests/test_use_case.py','enforced by');
INSERT INTO "constraint_files" VALUES('U4','tests/test_binding.py','enforced by');
INSERT INTO "constraint_files" VALUES('U4','scripts/evaluate.py','measured by');
INSERT INTO "constraint_files" VALUES('U5','tests/test_use_case.py','enforced by');
INSERT INTO "constraint_files" VALUES('U6','tests/test_sql_questions.py','enforced by');
INSERT INTO "constraint_files" VALUES('U6','evaluation/sql_questions.json','measured by');
INSERT INTO "constraint_files" VALUES('T1','TODO.md','delivered by');
INSERT INTO "constraint_files" VALUES('T1','docs/README.md','delivered by');
INSERT INTO "constraint_files" VALUES('T2','design/SYSTEM-DESIGN.md','delivered by');
INSERT INTO "constraint_files" VALUES('T2','design/system-design.svg','delivered by');
INSERT INTO "constraint_files" VALUES('T2','ARCHITECTURE.md','delivered by');
INSERT INTO "constraint_files" VALUES('T3','engineering_search','delivered by');
INSERT INTO "constraint_files" VALUES('T3','README.md','delivered by');
INSERT INTO "constraint_files" VALUES('S2','engineering_search/indexing/readers','delivered by');
INSERT INTO "constraint_files" VALUES('S2','tests/test_indexer.py','enforced by');
INSERT INTO "constraint_files" VALUES('S3','test-repository','delivered by');
INSERT INTO "constraint_files" VALUES('S4','engineering_search/indexing/detect.py','delivered by');
INSERT INTO "constraint_files" VALUES('S4','engineering_search/indexing/facts.py','delivered by');
INSERT INTO "constraint_files" VALUES('S4','tests/test_facts.py','enforced by');
INSERT INTO "constraint_files" VALUES('R1','tests/test_no_leaks.py','enforced by');
INSERT INTO "constraint_files" VALUES('R1','tests/test_sql.py','enforced by');
INSERT INTO "constraint_files" VALUES('R1','tests/test_access.py','enforced by');
INSERT INTO "constraint_files" VALUES('R2','tests/test_binding.py','enforced by');
INSERT INTO "constraint_files" VALUES('R2','tests/test_use_case.py','enforced by');
INSERT INTO "constraint_files" VALUES('R3','tests/test_use_case.py','enforced by');
INSERT INTO "constraint_files" VALUES('R3','tests/test_pagination.py','enforced by');
INSERT INTO "constraint_files" VALUES('R4','tests/test_use_case.py','enforced by');
INSERT INTO "constraint_files" VALUES('R4','tests/test_sql_questions.py','enforced by');
INSERT INTO "constraint_files" VALUES('P1','scripts/load_test.py','measured by');
CREATE TABLE constraint_groups (
  code TEXT PRIMARY KEY,         -- the ID prefix
  position INTEGER NOT NULL,
  name TEXT NOT NULL,
  page TEXT NOT NULL,            -- file under docs/constraints/
  summary TEXT NOT NULL,
  intro TEXT NOT NULL
);
INSERT INTO "constraint_groups" VALUES('B',1,'Background','background.md','The problem as the brief states it','The problem, as [the brief](../Starting_document.md) states it. These are facts about the situation, not requirements; the use case and the constraints answer them.');
INSERT INTO "constraint_groups" VALUES('C',2,'Constraints from the brief','environment.md','The environment that already exists: the architecture direction, the repository, connectors, stores and the chat-agent shell. The MVP assumes them and uses stand-ins','The environment that [the brief](../Starting_document.md) says **already exists**. The MVP does not design or build any of it. Where the MVP needs one of these to run end to end, it uses the simplest stand-in that proves the chain from question to cited answer, and names it as a stand-in. For example, connectors already extract metadata, text and properties from supported files (C3), so the MVP''s PDF, Markdown, CSV and XLSX readers are placeholders for them, not a proposal to build extraction ([ADR 0020](../adr/0020-assume-the-environment-and-stand-in-for-it.md)).');
INSERT INTO "constraint_groups" VALUES('U',3,'Use case','use-case.md','Who needs what, how fast and with what confidence. From the brief','The use case in the brief: who needs what, how fast and with what confidence. Each item is quoted or closely paraphrased from [the brief](../Starting_document.md).');
INSERT INTO "constraint_groups" VALUES('T',4,'Task','task.md','What the brief asks to be delivered','What [the brief](../Starting_document.md) asks to be delivered, with its time boxes.');
INSERT INTO "constraint_groups" VALUES('S',5,'Scope','scope.md','What the MVP includes and excludes','What the MVP includes and excludes.');
INSERT INTO "constraint_groups" VALUES('R',6,'Requirements added during the MVP','requirements.md','Permissions, answers, lists and tests','Requirements that the product owner added while the MVP was built.');
INSERT INTO "constraint_groups" VALUES('P',7,'Production requirements','production.md','What a service for the whole organisation needs and **the MVP does not meet**','What a service for a whole organisation needs and **the MVP does not meet**. They are out of scope by [S1](scope.md#s1), and recorded so that no one mistakes the MVP for a platform. [docs/README.md](../README.md#making-it-available-to-an-organisation) explains why each is its own engineering work.');
CREATE TABLE constraints (
  id TEXT PRIMARY KEY,           -- for example U3; never renumbered
  group_code TEXT NOT NULL REFERENCES constraint_groups(code),
  position INTEGER NOT NULL,
  title TEXT NOT NULL,
  statement TEXT NOT NULL,
  source_id TEXT NOT NULL REFERENCES sources(id),
  brief_section TEXT REFERENCES brief_sections(heading),
  source_note TEXT,
  meaning TEXT NOT NULL,         -- what it means for the design
  standing TEXT NOT NULL CHECK (standing IN ('context', 'assumed', 'met', 'partly met', 'not met')),
  mvp TEXT NOT NULL              -- where the MVP stands
);
INSERT INTO "constraints" VALUES('U1','U',1,'Find a critical engineering parameter','A selected engineering manager or lead can find a critical engineering parameter: a load limit, a material specification or a compliance approval status.','brief','Use Case',NULL,'The questions are about specific parameters, not general reading. Values must be bound to the element they describe. *Selected* means the users are known and their access differs.','partly met','Load limits, materials and approval statuses are answered from text (with a binding status) and from table facts through SQL. Only a small, fixed set of parameters is recognised.');
INSERT INTO "constraints" VALUES('U2','U',2,'Across 100+ project documents','The parameter is found across 100 or more project documents.','brief','Use Case',NULL,'Search must not depend on the user knowing which file to open. The system needs an index, not a scan.','met','Met on 148 test files. Not measured on a real repository, which may hold hundreds of thousands of files.');
INSERT INTO "constraints" VALUES('U3','U',3,'In under 10 seconds','The answer comes in under 10 seconds.','brief','Use Case',NULL,'The time includes the network and the chat agent''s language model, not only the search. It must hold for every user, not only for one.','partly met','About 80 ms median per question for one user. Under load, admission control answers within 8 s or refuses at once with a retry time. One process answers about 10 requests a second. Holding 10 s for any number of users is P1.');
INSERT INTO "constraints" VALUES('U4','U',4,'With 100% confidence in the source','The user has 100% confidence in the source of the answer.','brief','Use Case',NULL,'Every answer cites the exact file, location and version, and the cited text must really be in the file. The system must prefer no answer to a wrong one, and say how well the value is bound to the question.','partly met','Every answer and row carries file, page or sheet, lines and SHA-256 version, checked against the files by tests. The source is proven; that the value is the current, approved one is not.');
INSERT INTO "constraints" VALUES('U5','U',5,'Without opening a design file or viewer','The user does not open a single design file (CAD) or tool (PDF viewer).','brief','Use Case',NULL,'The answer must carry its evidence: the exact text or row, with enough context to trust it.','met','The answer shows the exact text or row and its location. There is no viewer for the context around a value, and no CAD content is read.');
INSERT INTO "constraints" VALUES('U6','U',6,'No formats, schema, query languages or jargon','Users do not want to learn file formats, schema details, query languages or system-specific jargon.','brief','Background',NULL,'Questions are in plain language. If a query language is needed, something other than the user writes it.','met','Plain-language questions. For table questions, the chat agent''s language model writes the SQL, not the user.');
INSERT INTO "constraints" VALUES('C1','C',1,'A broader architecture direction already exists','A broader architecture direction already exists.','brief','Constraints',NULL,'This component is a backend that other parts of that architecture call, not a separate product.','assumed','One search service behind an HTTP API, a web page and an MCP server stands in for this component''s place in that architecture. The wider architecture is not known in detail.');
INSERT INTO "constraints" VALUES('C2','C',2,'The files live in an existing repository','The files live in an existing repository.','brief','Constraints',NULL,'The system does not own the files. A real repository holds years of files in many formats and versions, with its own permissions. The service reads what is there and never changes it.','assumed','A local folder of test files stands in for the repository, and folder rules in `access.py` stand in for its permissions. Files are read in place and never changed. Real permissions are P3.');
INSERT INTO "constraints" VALUES('C3','C',3,'Connectors extract metadata, text and properties','Connectors and APIs can extract metadata, text and properties from supported files.','brief','Constraints',NULL,'The connectors exist and are not part of this work. The service consumes what they extract (text, tables and properties, with source locations and versions), and it must know which files were read, by which connector and version, and which were not.','assumed','The MVP''s readers for Markdown, PDF text layer, CSV and XLSX are placeholders for the connectors, written only to prove the chain from file to cited answer. They are not a proposal to build extraction. Each sits behind the reader interface (`ReaderManifest`, `Extraction`), which is where a connector adapter plugs in ([ADR 0020](../adr/0020-assume-the-environment-and-stand-in-for-it.md)). Every file that no reader handles is reported.');
INSERT INTO "constraints" VALUES('C4','C',4,'Structured and/or semantic stores','Extracted information can be stored in structured and/or semantic stores.','brief','Constraints',NULL,'The stores should be chosen from the questions and the data, and both kinds may be needed.','assumed','SQLite stands in for the stores: an FTS5 keyword index for passages, and tables and typed facts for structured questions. No semantic (embedding) store: it is deferred until the questions show a gain.');
INSERT INTO "constraints" VALUES('C5','C',5,'A chat-agent shell calls backend APIs or tools','A chat-agent shell can call backend APIs or tools to expose a conversational plane for users.','brief','Constraints',NULL,'The service exposes tools that a chat agent can call. The agent''s language model is part of the system and must be measured.','assumed','Claude Code, Codex and Pi over a local MCP server stand in for the company''s chat-agent shell. The agent writes the SQL for table questions.');
INSERT INTO "constraints" VALUES('S1','S',1,'An MVP, not the final platform','The initial scope is an MVP, not the final platform or solution.','brief','Scope',NULL,'Take shortcuts where they do not hide a risk, and write each one down. Prove the path from question to cited answer before building the platform.','met','Built in about four to five hours. The shortcuts are listed in [ARCHITECTURE.md](../../ARCHITECTURE.md#mvp-shortcuts-in-the-code) and the production gaps in [production.md](production.md).');
INSERT INTO "constraints" VALUES('S2','S',2,'Markdown and simple PDF, no OCR, no CAD','The first formats for the stand-in readers are Markdown and PDF with a text layer. No OCR. No DXF, DWG, JT or CATIA.','mvp',NULL,'Set at the start; extended by S4','A small format set is enough to prove the chain. Reading more formats is the connectors'' job (C3). Every other file is reported, not hidden.','met','Met, and extended by S4 with CSV and XLSX. CAD stays out of scope.');
INSERT INTO "constraints" VALUES('S3','S',3,'Synthetic or public test documents','The repository will be published, so the test documents must be synthetic or publicly shareable.','mvp',NULL,NULL,'No real engineering documents. Scores on the test data are therefore optimistic.','met','Synthetic Markdown, PDF, CSV and XLSX files, and two public FHWA PDFs.');
INSERT INTO "constraints" VALUES('S4','S',4,'The 29 October design inputs','Add CSV and XLSX, detection of the file type from content, a coverage report, and SQL written by the MCP client over tables. CAD content stays out of scope.','inputs',NULL,'With the [design notes](../../docs/engineering_knowledge_search_design_notes.html); dated inputs, not edited','The MCP client''s language model plans structured questions; the server constrains and runs them. No second language model on the server.','met','Built: CSV and XLSX readers, content detection, reader registry, coverage report, constrained SQL and the structured MCP tools.');
INSERT INTO "constraints" VALUES('R1','R',1,'No information from a forbidden document','A user must never get information from a document that the user is not authorised to read. This is an absolute requirement.','mvp',NULL,NULL,'Information is more than text: a count, a file name, a ranking or a join can leak too. Permissions apply before any limit, ranking, count, join or aggregate.','partly met','Met in the tests on both paths. It rests on pretend sign-in and an unverified MCP user, so it is a demonstration until P2 and P3 are met.');
INSERT INTO "constraints" VALUES('R2','R',2,'An answer, not a list of passages','The service must answer the question. A list of passages is not an answer.','mvp',NULL,NULL,'Select one value with its source, or say clearly that no readable document states it.','met','One sentence or row with a status (found, unverified, partial, not found), or rows from SQL.');
INSERT INTO "constraints" VALUES('R3','R',3,'Lists of documents, with follow-ups','Users can ask for lists of documents: by project, topic, material, approval status, or a value such as a load above 5 kN/m², with follow-up questions about a previous list.','mvp',NULL,NULL,'Lists must be complete within the user''s permissions, paged, and filterable by value with units.','met','Text lists with bound number comparisons and paging; complete filters over tables through SQL.');
INSERT INTO "constraints" VALUES('R4','R',4,'The tests enforce the use case','The tests must enforce the use case.','mvp',NULL,NULL,'Each part of the use case has a test that fails when it breaks. Quality is measured by evaluation, not by eye.','partly met','Acceptance tests, a leak test, SQL and binding tests, a retrieval evaluation and an NL-to-SQL gold set. The live-client SQL evaluation is not built.');
INSERT INTO "constraints" VALUES('P1','P',1,'Any number of users, each answered within 10 seconds','An arbitrary number of people can ask at the same time, and each gets an answer within 10 seconds. The service stays available when a process, a machine or a zone fails.','production',NULL,'Follows from U3 at organisational scale','No single process, lock, connection or machine on the query path. Reads scale out; writes do not block reads; the store is replicated and fails over; capacity is planned and load-tested.','not met','**Not met.** One process, one lock, one SQLite connection, about 10 requests a second, on one machine. Admission control refuses the excess at once rather than answering late. See [ADR 0018](../adr/0018-admission-control-and-the-time-budget.md).');
INSERT INTO "constraints" VALUES('P2','P',2,'Verified identity','The service knows who is asking from the company identity provider. It never takes the user from a flag, a setting or a tool argument.','production',NULL,'Follows from R1','Company sign-in for the web app; a remote MCP server with OAuth, taking the user from the verified token.','not met','**Not met.** Pretend sign-in on the web; the MCP server trusts `--user`. This is a known security hole ([ADR 0012](../adr/0012-mcp-server-for-the-chat-agent.md)).');
INSERT INTO "constraints" VALUES('P3','P',3,'Permissions from the repository','Each user''s file permissions come from the repository itself, current at query time.','production',NULL,'Follows from R1 and C2','Effective permissions (including inheritance and deny entries) synced or queried through the connector.','not met','**Not met.** Path rules in `access.py` ([ADR 0010](../adr/0010-path-based-access-rules.md)).');
INSERT INTO "constraints" VALUES('P4','P',4,'Durable, protected audit','The audit log survives the loss of a machine, is protected against change, and has retention and backup rules.','production',NULL,'Follows from U4 and R1','A managed audit store with retention, tamper evidence and access control.','not met','**Not met.** A local SQLite file ([ADR 0007](../adr/0007-telemetry-and-audit.md)).');
INSERT INTO "constraints" VALUES('P5','P',5,'Approved use of language models','The company approves which document text may be sent to which language model provider.','production',NULL,'Follows from C5','A data-governance decision per repository or classification, enforced by the service.','not met','**Not met.** The chat client sends permitted tool results to its provider ([ADR 0012](../adr/0012-mcp-server-for-the-chat-agent.md)).');
INSERT INTO "constraints" VALUES('P6','P',6,'Quality measured on real questions','Answer quality is measured on real questions from engineering leads, with a held-back set, and releases are gated on it.','production',NULL,'Follows from U4 and R4','Profile the real repository; collect real questions with expected answers and sources; score retrieval, SQL and replies.','not met','**Not met.** Scores come from synthetic data written with the questions ([ADR 0019](../adr/0019-evaluate-retrieval-and-nl-to-sql.md)).');
INSERT INTO "constraints" VALUES('B1','B',1,'Years of design information in files and documents','A company has years of engineering and infrastructure design information stored in design files and related project documents.','brief','Background',NULL,'The information already exists, spread across many files, formats and versions. The service finds it where it is; it does not ask people to enter it again.','context','148 synthetic and public test files stand in for the repository (S3).');
INSERT INTO "constraints" VALUES('B2','B',2,'Users do not know which files hold the answer','Users often do not know which files contain the information they need.','brief','Background',NULL,'Search must work across every file the user may read without the user naming one, and each answer must say where it came from (U2, U4).','context','Each question searches every permitted file, and each answer names its file, location and version.');
INSERT INTO "constraints" VALUES('T1','T',1,'Identify and clarify the requirements, gaps and challenges','Identify and clarify the requirements, and any critical gaps or challenges (5 minutes).','brief','Task',NULL,'Write the requirements down where decisions can cite them, and keep the gaps visible.','met','The requirements are these constraint pages; the gaps are the production requirements (P1–P6) and [TODO.md](../../TODO.md).');
INSERT INTO "constraints" VALUES('T2','T',2,'Define the initial phase and a system design diagram','Define the initial phase and create a system design diagram (10 minutes).','brief','Task',NULL,'Show the parts, the flows and where the MVP stops.','met','The [system design](../../design/SYSTEM-DESIGN.md) and its diagram, and the code architecture in [ARCHITECTURE.md](../../ARCHITECTURE.md).');
INSERT INTO "constraints" VALUES('T3','T',3,'A working prototype of an MVP','Get a working prototype of an MVP (40 minutes).','brief','Task',NULL,'Prove the chain from question to cited answer, running, with tests.','met','Built in about four to five hours rather than 40 minutes, to prove the whole chain with tests and evaluation ([docs/README.md](../README.md)).');
CREATE TABLE decision_constraints (
  number INTEGER NOT NULL REFERENCES decisions(number),
  constraint_id TEXT NOT NULL REFERENCES constraints(id),
  relation TEXT NOT NULL CHECK (relation IN ('serves', 'not met', 'cites')),
  position INTEGER NOT NULL,
  reason TEXT,
  PRIMARY KEY (number, constraint_id, relation)
);
INSERT INTO "decision_constraints" VALUES(1,'S1','serves',1,'MVP only');
INSERT INTO "decision_constraints" VALUES(1,'S2','serves',2,'Markdown and simple PDF, no OCR, no CAD');
INSERT INTO "decision_constraints" VALUES(1,'U5','serves',3,'no CAD file or PDF viewer');
INSERT INTO "decision_constraints" VALUES(1,'C2','cites',4,NULL);
INSERT INTO "decision_constraints" VALUES(1,'U3','cites',5,NULL);
INSERT INTO "decision_constraints" VALUES(1,'U4','cites',6,NULL);
INSERT INTO "decision_constraints" VALUES(2,'S1','serves',1,'MVP only');
INSERT INTO "decision_constraints" VALUES(2,'S3','serves',2,'published repository');
INSERT INTO "decision_constraints" VALUES(2,'C2','serves',3,'files in an existing repository');
INSERT INTO "decision_constraints" VALUES(2,'P1','not met',4,'any number of users, each answered within 10 seconds');
INSERT INTO "decision_constraints" VALUES(3,'C2','serves',1,'years of files in an existing repository');
INSERT INTO "decision_constraints" VALUES(3,'C3','serves',2,'connectors extract from supported files');
INSERT INTO "decision_constraints" VALUES(3,'U4','serves',3,'100% confidence in the source');
INSERT INTO "decision_constraints" VALUES(4,'U3','serves',1,'under 10 seconds');
INSERT INTO "decision_constraints" VALUES(4,'U4','serves',2,'100% confidence in the source');
INSERT INTO "decision_constraints" VALUES(4,'U5','serves',3,'no need to open the file');
INSERT INTO "decision_constraints" VALUES(5,'C2','serves',1,'years of files in an existing repository');
INSERT INTO "decision_constraints" VALUES(5,'C3','serves',2,'supported files only');
INSERT INTO "decision_constraints" VALUES(5,'U4','serves',3,'100% confidence in the source');
INSERT INTO "decision_constraints" VALUES(6,'R1','serves',1,'no information from a document that the user cannot read');
INSERT INTO "decision_constraints" VALUES(6,'U1','serves',2,'a *selected* manager or lead');
INSERT INTO "decision_constraints" VALUES(7,'U3','serves',1,'under 10 seconds');
INSERT INTO "decision_constraints" VALUES(7,'U4','serves',2,'100% confidence in the source');
INSERT INTO "decision_constraints" VALUES(7,'R1','serves',3,'no information from forbidden documents');
INSERT INTO "decision_constraints" VALUES(7,'P4','not met',4,'durable, protected audit');
INSERT INTO "decision_constraints" VALUES(8,'R1','serves',1,'no information from forbidden documents');
INSERT INTO "decision_constraints" VALUES(8,'U1','serves',2,'selected managers and leads search');
INSERT INTO "decision_constraints" VALUES(9,'U1','serves',1,'find a parameter');
INSERT INTO "decision_constraints" VALUES(9,'U2','serves',2,'100+ documents');
INSERT INTO "decision_constraints" VALUES(9,'U3','serves',3,'under 10 seconds');
INSERT INTO "decision_constraints" VALUES(9,'U4','serves',4,'100% confidence in the source');
INSERT INTO "decision_constraints" VALUES(9,'U6','serves',5,'plain language');
INSERT INTO "decision_constraints" VALUES(9,'R2','serves',6,'an answer, not passages');
INSERT INTO "decision_constraints" VALUES(9,'R3','serves',7,'lists of documents');
INSERT INTO "decision_constraints" VALUES(10,'R1','serves',1,'no information from forbidden documents');
INSERT INTO "decision_constraints" VALUES(10,'C2','serves',2,'files in an existing repository');
INSERT INTO "decision_constraints" VALUES(10,'U2','serves',3,'100+ documents');
INSERT INTO "decision_constraints" VALUES(10,'P3','not met',4,'permissions from the repository');
INSERT INTO "decision_constraints" VALUES(11,'C1','serves',1,'a broader architecture exists');
INSERT INTO "decision_constraints" VALUES(11,'C5','serves',2,'a chat-agent shell calls backend APIs and tools');
INSERT INTO "decision_constraints" VALUES(11,'R1','serves',3,'no information from forbidden documents');
INSERT INTO "decision_constraints" VALUES(11,'U4','serves',4,'100% confidence in the source');
INSERT INTO "decision_constraints" VALUES(12,'C5','serves',1,'a chat-agent shell calls backend APIs and tools');
INSERT INTO "decision_constraints" VALUES(12,'U6','serves',2,'no file formats, schema, query languages or jargon');
INSERT INTO "decision_constraints" VALUES(12,'S1','serves',3,'MVP only');
INSERT INTO "decision_constraints" VALUES(12,'R1','serves',4,'no information from forbidden documents');
INSERT INTO "decision_constraints" VALUES(12,'P2','not met',5,'verified identity');
INSERT INTO "decision_constraints" VALUES(12,'P5','not met',6,'approved use of language models');
INSERT INTO "decision_constraints" VALUES(12,'S3','cites',7,NULL);
INSERT INTO "decision_constraints" VALUES(12,'U4','cites',8,NULL);
INSERT INTO "decision_constraints" VALUES(13,'U4','serves',1,'100% confidence in the source');
INSERT INTO "decision_constraints" VALUES(13,'R2','serves',2,'an answer, not passages');
INSERT INTO "decision_constraints" VALUES(13,'R1','serves',3,'no information from forbidden documents');
INSERT INTO "decision_constraints" VALUES(13,'U1','serves',4,'load limit, material or approval status');
INSERT INTO "decision_constraints" VALUES(14,'S1','serves',1,'MVP only');
INSERT INTO "decision_constraints" VALUES(14,'C3','serves',2,'connectors extract metadata, text and properties');
INSERT INTO "decision_constraints" VALUES(14,'C4','serves',3,'structured and/or semantic stores');
INSERT INTO "decision_constraints" VALUES(14,'U1','serves',4,'load limit, material or approval status');
INSERT INTO "decision_constraints" VALUES(14,'U4','cites',5,NULL);
INSERT INTO "decision_constraints" VALUES(15,'R4','serves',1,'tests enforce the use case');
INSERT INTO "decision_constraints" VALUES(15,'U1','serves',2,NULL);
INSERT INTO "decision_constraints" VALUES(15,'U2','serves',3,NULL);
INSERT INTO "decision_constraints" VALUES(15,'U3','serves',4,NULL);
INSERT INTO "decision_constraints" VALUES(15,'U4','serves',5,NULL);
INSERT INTO "decision_constraints" VALUES(15,'U5','serves',6,NULL);
INSERT INTO "decision_constraints" VALUES(15,'R1','serves',7,'no information from forbidden documents');
INSERT INTO "decision_constraints" VALUES(15,'S3','serves',8,'public or synthetic test data');
INSERT INTO "decision_constraints" VALUES(15,'R3','cites',9,NULL);
INSERT INTO "decision_constraints" VALUES(16,'U1','serves',1,'load limit, material or approval status');
INSERT INTO "decision_constraints" VALUES(16,'U2','serves',2,'100+ documents');
INSERT INTO "decision_constraints" VALUES(16,'U4','serves',3,'100% confidence in the source');
INSERT INTO "decision_constraints" VALUES(16,'U6','serves',4,'no query languages for the user');
INSERT INTO "decision_constraints" VALUES(16,'R1','serves',5,'no information from forbidden documents');
INSERT INTO "decision_constraints" VALUES(16,'R3','serves',6,'lists by value');
INSERT INTO "decision_constraints" VALUES(16,'C3','serves',7,'connectors extract properties');
INSERT INTO "decision_constraints" VALUES(16,'C4','serves',8,'structured and/or semantic stores');
INSERT INTO "decision_constraints" VALUES(16,'C5','serves',9,'a chat-agent shell calls tools');
INSERT INTO "decision_constraints" VALUES(16,'S4','serves',10,'the 29 October design inputs');
INSERT INTO "decision_constraints" VALUES(17,'U4','serves',1,'100% confidence in the source');
INSERT INTO "decision_constraints" VALUES(17,'R1','serves',2,'no information from forbidden documents');
INSERT INTO "decision_constraints" VALUES(17,'R2','serves',3,'an answer, not passages');
INSERT INTO "decision_constraints" VALUES(17,'R3','serves',4,'lists by value');
INSERT INTO "decision_constraints" VALUES(18,'U3','serves',1,'under 10 seconds');
INSERT INTO "decision_constraints" VALUES(18,'U4','serves',2,'trust');
INSERT INTO "decision_constraints" VALUES(18,'C5','serves',3,'a chat-agent shell calls the service');
INSERT INTO "decision_constraints" VALUES(18,'S1','serves',4,'MVP only');
INSERT INTO "decision_constraints" VALUES(18,'P1','not met',5,'any number of users, each answered within 10 seconds');
INSERT INTO "decision_constraints" VALUES(19,'U1','serves',1,'find the parameter');
INSERT INTO "decision_constraints" VALUES(19,'U4','serves',2,'100% confidence in the source');
INSERT INTO "decision_constraints" VALUES(19,'U6','serves',3,'plain language');
INSERT INTO "decision_constraints" VALUES(19,'R1','serves',4,'no information from forbidden documents');
INSERT INTO "decision_constraints" VALUES(19,'R4','serves',5,'the tests enforce the use case');
INSERT INTO "decision_constraints" VALUES(19,'P6','not met',6,'quality measured on real, held-back questions');
INSERT INTO "decision_constraints" VALUES(20,'C1','serves',1,'an architecture direction exists');
INSERT INTO "decision_constraints" VALUES(20,'C2','serves',2,'the files live in an existing repository');
INSERT INTO "decision_constraints" VALUES(20,'C3','serves',3,'connectors extract metadata, text and properties');
INSERT INTO "decision_constraints" VALUES(20,'C4','serves',4,'structured and/or semantic stores exist');
INSERT INTO "decision_constraints" VALUES(20,'C5','serves',5,'a chat-agent shell exists');
INSERT INTO "decision_constraints" VALUES(20,'S1','serves',6,'MVP only');
INSERT INTO "decision_constraints" VALUES(20,'S2','cites',7,NULL);
INSERT INTO "decision_constraints" VALUES(21,'T1','serves',1,'clarify the requirements');
INSERT INTO "decision_constraints" VALUES(21,'R4','serves',2,'the tests enforce the use case');
INSERT INTO "decision_constraints" VALUES(21,'R1','cites',3,NULL);
INSERT INTO "decision_constraints" VALUES(21,'S4','cites',4,NULL);
INSERT INTO "decision_constraints" VALUES(1,'C3','cites',7,NULL);
CREATE TABLE decision_files (
  number INTEGER NOT NULL REFERENCES decisions(number),
  path TEXT NOT NULL,            -- repository path
  role TEXT NOT NULL CHECK (role IN ('implements', 'tests', 'measures')),
  PRIMARY KEY (number, path)
);
INSERT INTO "decision_files" VALUES(1,'tests/test_coverage.py','tests');
INSERT INTO "decision_files" VALUES(1,'tests/test_index.py','tests');
INSERT INTO "decision_files" VALUES(1,'tests/test_indexer.py','tests');
INSERT INTO "decision_files" VALUES(1,'tests/test_use_case.py','tests');
INSERT INTO "decision_files" VALUES(2,'engineering_search/runtime.py','implements');
INSERT INTO "decision_files" VALUES(2,'scripts/package_source.py','implements');
INSERT INTO "decision_files" VALUES(3,'engineering_search/indexing/detect.py','implements');
INSERT INTO "decision_files" VALUES(3,'engineering_search/indexing/readers/registry.py','implements');
INSERT INTO "decision_files" VALUES(3,'tests/test_coverage.py','tests');
INSERT INTO "decision_files" VALUES(3,'tests/test_indexer.py','tests');
INSERT INTO "decision_files" VALUES(4,'engineering_search/store.py','implements');
INSERT INTO "decision_files" VALUES(4,'tests/test_coverage.py','tests');
INSERT INTO "decision_files" VALUES(4,'tests/test_index.py','tests');
INSERT INTO "decision_files" VALUES(4,'tests/test_use_case.py','tests');
INSERT INTO "decision_files" VALUES(5,'engineering_search/indexing/coverage.py','implements');
INSERT INTO "decision_files" VALUES(5,'engineering_search/indexing/status.py','implements');
INSERT INTO "decision_files" VALUES(5,'tests/test_coverage.py','tests');
INSERT INTO "decision_files" VALUES(5,'tests/test_indexer.py','tests');
INSERT INTO "decision_files" VALUES(5,'tests/test_startup.py','tests');
INSERT INTO "decision_files" VALUES(6,'engineering_search/access.py','implements');
INSERT INTO "decision_files" VALUES(6,'engineering_search/service.py','implements');
INSERT INTO "decision_files" VALUES(6,'engineering_search/store.py','implements');
INSERT INTO "decision_files" VALUES(6,'tests/test_access.py','tests');
INSERT INTO "decision_files" VALUES(6,'tests/test_binding.py','tests');
INSERT INTO "decision_files" VALUES(6,'tests/test_no_leaks.py','tests');
INSERT INTO "decision_files" VALUES(6,'tests/test_pagination.py','tests');
INSERT INTO "decision_files" VALUES(6,'tests/test_sql.py','tests');
INSERT INTO "decision_files" VALUES(6,'tests/test_use_case.py','tests');
INSERT INTO "decision_files" VALUES(7,'engineering_search/adapters.py','implements');
INSERT INTO "decision_files" VALUES(7,'engineering_search/service.py','implements');
INSERT INTO "decision_files" VALUES(7,'tests/test_audit.py','tests');
INSERT INTO "decision_files" VALUES(8,'engineering_search/access.py','implements');
INSERT INTO "decision_files" VALUES(8,'engineering_search/app.py','implements');
INSERT INTO "decision_files" VALUES(8,'tests/test_access.py','tests');
INSERT INTO "decision_files" VALUES(8,'tests/test_audit.py','tests');
INSERT INTO "decision_files" VALUES(9,'engineering_search/answer.py','implements');
INSERT INTO "decision_files" VALUES(9,'engineering_search/query.py','implements');
INSERT INTO "decision_files" VALUES(9,'engineering_search/store.py','implements');
INSERT INTO "decision_files" VALUES(9,'engineering_search/units.py','implements');
INSERT INTO "decision_files" VALUES(9,'scripts/evaluate.py','measures');
INSERT INTO "decision_files" VALUES(9,'tests/test_binding.py','tests');
INSERT INTO "decision_files" VALUES(9,'tests/test_index.py','tests');
INSERT INTO "decision_files" VALUES(9,'tests/test_use_case.py','tests');
INSERT INTO "decision_files" VALUES(10,'engineering_search/access.py','implements');
INSERT INTO "decision_files" VALUES(10,'tests/test_access.py','tests');
INSERT INTO "decision_files" VALUES(10,'tests/test_no_leaks.py','tests');
INSERT INTO "decision_files" VALUES(10,'tests/test_pagination.py','tests');
INSERT INTO "decision_files" VALUES(11,'engineering_search/app.py','implements');
INSERT INTO "decision_files" VALUES(11,'engineering_search/mcp_server.py','implements');
INSERT INTO "decision_files" VALUES(11,'engineering_search/runtime.py','implements');
INSERT INTO "decision_files" VALUES(11,'engineering_search/service.py','implements');
INSERT INTO "decision_files" VALUES(11,'scripts/check_mcp.py','implements');
INSERT INTO "decision_files" VALUES(11,'tests/test_no_leaks.py','tests');
INSERT INTO "decision_files" VALUES(12,'engineering_search/mcp_server.py','implements');
INSERT INTO "decision_files" VALUES(12,'tests/test_mcp_stdio.py','tests');
INSERT INTO "decision_files" VALUES(13,'engineering_search/answer.py','implements');
INSERT INTO "decision_files" VALUES(13,'scripts/evaluate.py','measures');
INSERT INTO "decision_files" VALUES(13,'tests/test_binding.py','tests');
INSERT INTO "decision_files" VALUES(13,'tests/test_use_case.py','tests');
INSERT INTO "decision_files" VALUES(15,'evaluation/README.md','measures');
INSERT INTO "decision_files" VALUES(15,'evaluation/questions.json','measures');
INSERT INTO "decision_files" VALUES(15,'evaluation/results/answers.json','measures');
INSERT INTO "decision_files" VALUES(15,'scripts/evaluate.py','measures');
INSERT INTO "decision_files" VALUES(15,'tests/test_no_leaks.py','tests');
INSERT INTO "decision_files" VALUES(15,'tests/test_use_case.py','tests');
INSERT INTO "decision_files" VALUES(16,'engineering_search/indexing/facts.py','implements');
INSERT INTO "decision_files" VALUES(16,'engineering_search/indexing/readers/csv.py','implements');
INSERT INTO "decision_files" VALUES(16,'engineering_search/indexing/readers/markdown.py','implements');
INSERT INTO "decision_files" VALUES(16,'engineering_search/indexing/readers/xlsx.py','implements');
INSERT INTO "decision_files" VALUES(16,'engineering_search/mcp_server.py','implements');
INSERT INTO "decision_files" VALUES(16,'engineering_search/service.py','implements');
INSERT INTO "decision_files" VALUES(16,'engineering_search/sql.py','implements');
INSERT INTO "decision_files" VALUES(16,'engineering_search/store.py','implements');
INSERT INTO "decision_files" VALUES(16,'engineering_search/units.py','implements');
INSERT INTO "decision_files" VALUES(16,'tests/test_facts.py','tests');
INSERT INTO "decision_files" VALUES(16,'tests/test_mcp_stdio.py','tests');
INSERT INTO "decision_files" VALUES(16,'tests/test_no_leaks.py','tests');
INSERT INTO "decision_files" VALUES(16,'tests/test_sql.py','tests');
INSERT INTO "decision_files" VALUES(17,'engineering_search/answer.py','implements');
INSERT INTO "decision_files" VALUES(17,'engineering_search/service.py','implements');
INSERT INTO "decision_files" VALUES(17,'engineering_search/store.py','implements');
INSERT INTO "decision_files" VALUES(17,'engineering_search/units.py','implements');
INSERT INTO "decision_files" VALUES(17,'tests/test_binding.py','tests');
INSERT INTO "decision_files" VALUES(17,'tests/test_no_leaks.py','tests');
INSERT INTO "decision_files" VALUES(18,'engineering_search/adapters.py','implements');
INSERT INTO "decision_files" VALUES(18,'engineering_search/app.py','implements');
INSERT INTO "decision_files" VALUES(18,'engineering_search/mcp_server.py','implements');
INSERT INTO "decision_files" VALUES(18,'engineering_search/runtime.py','implements');
INSERT INTO "decision_files" VALUES(18,'engineering_search/service.py','implements');
INSERT INTO "decision_files" VALUES(18,'scripts/load_test.py','measures');
INSERT INTO "decision_files" VALUES(18,'tests/test_admission.py','tests');
INSERT INTO "decision_files" VALUES(19,'evaluation/questions.json','measures');
INSERT INTO "decision_files" VALUES(19,'evaluation/sql_questions.json','measures');
INSERT INTO "decision_files" VALUES(19,'scripts/evaluate.py','measures');
INSERT INTO "decision_files" VALUES(19,'tests/test_no_leaks.py','tests');
INSERT INTO "decision_files" VALUES(19,'tests/test_sql_questions.py','tests');
INSERT INTO "decision_files" VALUES(20,'engineering_search/indexing/readers/__init__.py','implements');
INSERT INTO "decision_files" VALUES(21,'design_records/records.py','implements');
INSERT INTO "decision_files" VALUES(21,'design_records/mcp_server.py','implements');
INSERT INTO "decision_files" VALUES(21,'tests/test_design_records.py','tests');
CREATE TABLE decision_relations (
  number INTEGER NOT NULL REFERENCES decisions(number),
  other INTEGER NOT NULL REFERENCES decisions(number),
  kind TEXT NOT NULL CHECK (kind IN ('supersedes in part', 'amends', 'extends')),
  PRIMARY KEY (number, other, kind)
);
INSERT INTO "decision_relations" VALUES(16,14,'supersedes in part');
INSERT INTO "decision_relations" VALUES(16,12,'supersedes in part');
INSERT INTO "decision_relations" VALUES(16,1,'extends');
INSERT INTO "decision_relations" VALUES(17,13,'supersedes in part');
INSERT INTO "decision_relations" VALUES(17,6,'supersedes in part');
INSERT INTO "decision_relations" VALUES(17,9,'amends');
INSERT INTO "decision_relations" VALUES(18,12,'supersedes in part');
INSERT INTO "decision_relations" VALUES(19,15,'supersedes in part');
INSERT INTO "decision_relations" VALUES(20,1,'amends');
INSERT INTO "decision_relations" VALUES(20,3,'amends');
INSERT INTO "decision_relations" VALUES(20,5,'amends');
CREATE TABLE decision_sections (
  number INTEGER NOT NULL REFERENCES decisions(number),
  position INTEGER NOT NULL,
  heading TEXT NOT NULL,
  body TEXT NOT NULL,
  PRIMARY KEY (number, position)
);
INSERT INTO "decision_sections" VALUES(1,1,'Context','The brief limits the MVP to Markdown and simple PDF (S2). It excludes OCR and the CAD formats DXF, DWG, JT and CATIA. The MVP must prove the full path from a question to an answer with an exact source (U4, U5) before the system takes on complex formats. A real repository holds many formats and versions (C2), so the format boundary must stay open for later readers ([ADR 0003](0003-versioned-reader-selection.md)).');
INSERT INTO "decision_sections" VALUES(1,2,'Decision','- Read UTF-8 Markdown and PDF files that have a text layer.
- "Simple PDF" means text that a library can extract, with the page number as its location. OCR, encrypted files, embedded drawings, complex table reconstruction and layout analysis are out of scope.
- Markdown passages keep line numbers. PDF passages keep the page number and the line numbers in the extracted page text.
- A location proves where the text came from. It does not prove that an engineering value is approved or correct.
- Semantic search, CAD geometry, the decision about which document is the authority, and production distribution are later work.');
INSERT INTO "decision_sections" VALUES(1,3,'Consequences','- The user sees the exact text and its file, page and lines, so the user does not need to open the PDF (U5).
- A PDF with some text does not mean that all its pages, tables or images are searchable. A scanned page gives no text.
- The 10-second target (U3) is measured on the test corpus only. It is not a promise for any file or any computer.');
INSERT INTO "decision_sections" VALUES(1,4,'Implementation','Done, and extended. The [indexing package](../../engineering_search/indexing/) detects the type from the content ([ADR 0003](0003-versioned-reader-selection.md)) and has readers for Markdown (text and pipe tables) and PDF (text layer, page by page with pypdf, at most 15 lines in each passage). [ADR 0016](0016-structured-facts-and-client-written-sql.md) adds CSV and XLSX readers for structured data. No OCR, no Word, no CAD content: scans and CAD files are listed in the coverage report as gaps. A file that cannot be read is skipped and reported ([ADR 0005](0005-coverage-and-reader-gaps.md)). Uploads accept Markdown only. Tests: `tests/test_indexer.py`, `tests/test_coverage.py`, `tests/test_index.py`, `tests/test_use_case.py`.');
INSERT INTO "decision_sections" VALUES(2,1,'Context','The MVP must be easy for other people to download, run and test (S1). The repository will be published (S3), so it must not need a central account, a hosted service or private data. In production the files stay in the existing repository (C2). For the MVP, a local folder stands in for it.');
INSERT INTO "decision_sections" VALUES(2,2,'Decision','- Each person runs an independent copy of the service on a computer that they control: indexing, search, telemetry and audit.
- The document folder and the writable state folder are separate from the code. Both can be set at start.
- Remote use is a copy on a remote machine, reached through an SSH tunnel to a loopback port.
- The source package contains the code and the synthetic and public test documents only. It never contains private documents, uploads or audit databases.');
INSERT INTO "decision_sections" VALUES(2,3,'Consequences','- No account, API key or cloud database is needed. The install needs network access, and search does not.
- Pretend sign-in is acceptable only for trusted testers. Anyone who can reach the service can select any user ([ADR 0008](0008-index-team-and-audit-viewer.md)).
- The documents are on the tester''s computer, so the access rules are a demonstration, not a protection ([ADR 0012](0012-mcp-server-for-the-chat-agent.md)).
- One local instance is not a service for an organisation. Serving any number of users, each within 10 seconds, with no single point of failure (P1), is separate engineering work ([ADR 0018](0018-admission-control-and-the-time-budget.md), [docs/README.md](../README.md#making-it-available-to-an-organisation)).
- A future reader must declare its dependencies, platforms and licence. A vendor reader on the developer''s computer does not mean that a tester can install it.');
INSERT INTO "decision_sections" VALUES(2,4,'Implementation','Done. `python -m engineering_search` starts the web service. [`runtime.py`](../../engineering_search/runtime.py) puts the index, queue and audit files in the state folder (default `.runtime/`). The index persists between runs ([ADR 0004](0004-persistent-evidence.md)). Telemetry resets on restart. `scripts/package_source.py` makes the source ZIP. See [RUNNING.md](../../RUNNING.md).');
INSERT INTO "decision_sections" VALUES(3,1,'Context','The repository holds years of files (C2). One format can have many versions, and an old version can need a different reader. The brief says that connectors and APIs extract from *supported* files (C3), so the system must know which files are supported. To have confidence in the source (U4), the system must also know how each file was read: a new reader can read the same file differently.');
INSERT INTO "decision_sections" VALUES(3,2,'Decision','- Detect the format and version of each file from its content. The file extension and the file date are hints only.
- A registry maps each format and version to a tested reader, with its exact version, its capabilities and the test files that prove it.
- The selection is deterministic. A missing runtime, a missing licence, an unsupported version or an unclear result gives an explicit outcome, never a silent fallback to another reader.
- For each source version, record the detected format and version, the selected reader and its version, and the result of the extraction.
- Never change a reader silently. A new reader gives a new extraction revision, after tests.');
INSERT INTO "decision_sections" VALUES(3,3,'Consequences','- A file that no reader can read becomes visible work, not a hidden gap ([ADR 0005](0005-coverage-and-reader-gaps.md)).
- The repository profile decides which readers come first ([design/DATA-PROFILE.md](../../design/DATA-PROFILE.md)). A viewer that reads the same formats is selected at the same time.
- Normal search reads stored passages and does not open the file again ([ADR 0004](0004-persistent-evidence.md)).');
INSERT INTO "decision_sections" VALUES(3,4,'Implementation','Mostly done. [`indexing/detect.py`](../../engineering_search/indexing/detect.py): `ContentDetector` treats the extension as a hint and checks the first 512 bytes. A PDF header gives the PDF version, a ZIP with `xl/workbook.xml` is XLSX, and a JT file''s 80-character header gives its version (for example JT 10.0). Content that contradicts the extension is `FORMAT_MISMATCH` and is not given to a reader. [`readers/registry.py`](../../engineering_search/indexing/readers/registry.py): `ReaderRegistry` holds several readers for each type, each with a manifest (name, version, formats, format versions, dependencies, capabilities). It picks the first installed reader that supports the format version, and tells `NO_READER`, `UNSUPPORTED_VERSION` and `DEPENDENCY_MISSING` apart. The detector and the registry are injected into `Indexer`. The reader and its version are stored for each file, and a new reader version re-extracts the file. Tests: `tests/test_coverage.py`, `tests/test_indexer.py`.

Not done: detection for formats without a signature (Markdown and CSV are named by extension), and any JT or CATIA reader. The JT probe reads the version string only. CAD stays out of scope ([ADR 0001](0001-mvp-format-scope.md)).');
INSERT INTO "decision_sections" VALUES(4,1,'Context','To answer in under 10 seconds (U3) across many documents, search cannot open every file for each question. To give 100% confidence in the source (U4), each answer must point to an exact, fixed version of the file. The user must not need to open the file to check it (U5).');
INSERT INTO "decision_sections" VALUES(4,2,'Decision','- Extract each file once, and store its passages with the file, the location (lines, and the page for a PDF) and the SHA-256 of the file content.
- Search reads only the stored passages.
- Apply a change to a document as one transaction. A failed update must not leave part of a document in the index.
- Keep three versions separate: the source version (content hash), the format version, and the reader version ([ADR 0003](0003-versioned-reader-selection.md)). A new reader can change the passages of a file whose hash did not change.
- Deleted files leave the index. Permissions apply to all stored passages, every time ([ADR 0006](0006-permissions-before-results.md)).');
INSERT INTO "decision_sections" VALUES(4,3,'Consequences','- Each answer has a file, page, line range and SHA-256 version. A test can check it against the file itself.
- The index survives a restart. A restart reads and hashes every file, and extracts only new and changed files.
- Until the reader version is recorded, a reader change cannot be traced in the stored passages.');
INSERT INTO "decision_sections" VALUES(4,4,'Implementation','Done. [`store.py`](../../engineering_search/store.py): `SQLiteSearchIndex` keeps `documents` (file and SHA-256), `passages` (text, heading, lines, page), the FTS5 index, `files` (type, format version, reader and reader version, status, warnings) and, for tables, `source_tables`, `table_rows` and `facts` ([ADR 0016](0016-structured-facts-and-client-written-sql.md)), in `index-<id>.sqlite3` ([ADR 0009](0009-sqlite-fts5-index-and-answers.md)). `apply` and `upsert` write a document, its tables, facts and file record in one transaction. A new reader version re-extracts the file. Tests: `tests/test_index.py` (persistence and one transaction), `tests/test_coverage.py` (statuses survive a restart), `tests/test_use_case.py` (each answer checked against the file).');
INSERT INTO "decision_sections" VALUES(5,1,'Context','If a search finds nothing, the user must not think that no document states the value when the true reason is that a file could not be read. That would break confidence in the answer (U4). The repository holds years of files (C2), and connectors read only supported files (C3), so some files will not be readable. A 20-year-old drawing is a question of compatibility. Its age does not prove that it is supported or obsolete.');
INSERT INTO "decision_sections" VALUES(5,2,'Decision','- Keep an inventory of all discovered files, with a clear outcome for each: out of scope, unsupported format, unknown version, reader not available, encrypted, damaged, extraction failed, partly extracted, no text, or indexed.
- Discovery and eligibility are separate. List an out-of-scope CAD file without reading it.
- One bad file must not stop the index build.
- Group the report by format, version and reason, with counts, for the index team. Never show an unreadable file as a search result with zero matches. Never show its name to a user who cannot read it ([ADR 0006](0006-permissions-before-results.md)).
- Coverage figures must keep unreadable and unsupported files in the total.');
INSERT INTO "decision_sections" VALUES(5,3,'Consequences','- The team can see which reader to build or buy next, and test it on real old files.
- An unsupported version needs a new reader, not endless retries.');
INSERT INTO "decision_sections" VALUES(5,4,'Implementation','Done. [`indexing/status.py`](../../engineering_search/indexing/status.py) names one status for each file: classification (`CLASSIFIED`, `UNSUPPORTED_FORMAT`, `NO_READER`, `UNSUPPORTED_VERSION`, `DEPENDENCY_MISSING`, `FORMAT_MISMATCH`, `INVALID_HEADER`, `READ_ERROR`) and reading (`INDEXED_FULL`, `INDEXED_PARTIAL`, `NO_TEXT_LAYER`, `NO_EXTRACTABLE_CONTENT`, `MALFORMED`, `ENCRYPTED`, `READER_CRASH`), each with a hint. A PDF without a text layer is `NO_TEXT_LAYER`, not indexed. The inventory is stored in the index (`files` table) with the format version, the reader and the warnings, and survives a restart. [`indexing/coverage.py`](../../engineering_search/indexing/coverage.py) builds the report by type, format version, status, folder and capability. The index team gets it at `GET /index/coverage` and through the MCP tool `get_index_coverage`. Other users do not, because the report names files. Tests: `tests/test_coverage.py`, `tests/test_indexer.py`, `tests/test_startup.py`.');
INSERT INTO "decision_sections" VALUES(6,1,'Context','The use case is for selected users (U1), and documents in the repository have different readers. A user must never get information from a document that the user cannot read (R1). Information is more than text: a count, a file name, an empty result position or a page total can also show that a forbidden document matches. If the service picks a page of results first and removes forbidden passages after, the counts and the gaps leak information, and permitted results can be lost.');
INSERT INTO "decision_sections" VALUES(6,2,'Decision','- After the index lookup and before anything else, decide which matched files the user can read. Everything after that step uses permitted files only: the answer, the "also stated in" list, the document list, the counts, the pages and the file overview.
- Check permissions again on every request, including each page. A page number is not permission to read.
- Reading one file gives the same reply for "does not exist" and "not permitted", so file names do not leak.
- If the permission check fails, return no evidence (fail closed).
- A search match that is excluded by permissions is recorded in the audit log. It is a different event from a deliberate attempt to open a forbidden file.');
INSERT INTO "decision_sections" VALUES(6,3,'Consequences','- Counts and pages are correct for each user and show nothing about forbidden files.
- Pages are live views. If the index or the permissions change between two pages, results can move. The service never freezes permissions to keep pages stable.
- Two exceptions are recorded in [`access.py`](../../engineering_search/access.py): the sign-in screen shows folder counts for each demo user (no names, no text), and the audit log shows file names to the index team ([ADR 0008](0008-index-team-and-audit-viewer.md)).');
INSERT INTO "decision_sections" VALUES(6,4,'Implementation','Done. `SearchService.search` and `SearchService.read` in [`service.py`](../../engineering_search/service.py). The service finds the matching files, evaluates permissions on them, and gives the index lookup the set of permitted files (and `within`). The lookup ([`store.py`](../../engineering_search/store.py)) applies that set inside the FTS5 query, before the 1,000-candidate limit, so forbidden passages cannot push permitted ones out. The SQL path builds a projection of permitted files only ([ADR 0016](0016-structured-facts-and-client-written-sql.md)). `POST /search` takes `page` and `limit` (at most 50). Tests: `tests/test_no_leaks.py` asks every evaluation question, and questions made from the text of each forbidden file, in each mode, for each user, and checks the first five pages and the last page. Also `test_forbidden_passages_cannot_push_a_permitted_passage_past_the_candidate_limit` in `tests/test_binding.py`, `tests/test_sql.py`, `tests/test_access.py`, `tests/test_pagination.py` and `tests/test_use_case.py`.');
INSERT INTO "decision_sections" VALUES(7,1,'Context','The use case sets a time limit (U3), so the time of each stage must be measured from the first version. It also asks for 100% confidence in the source (U4) and strict permissions (R1). The company must be able to show, after the event, which evidence each user got and which matches were withheld. Telemetry (performance) and audit (security) have different purposes and must stay separate.');
INSERT INTO "decision_sections" VALUES(7,2,'Decision','- Measure indexing throughput, query times (median, p95 and others), failures and the time of each search stage: lookup, permissions and audit.
- Before the service returns evidence, write an audit event: the user, the permission version, the decision for each matched file, the source of the answer and of each returned passage. If the write fails, return no evidence.
- Do not record the question text, the passage text or credentials. Record the number of characters in the question only.
- Take the user from the session, never from the question.
- A later event records that the response was sent. It cannot prove that a person read it.');
INSERT INTO "decision_sections" VALUES(7,3,'Consequences','- The audit log shows that permitted evidence reached the user and that excluded matches did not.
- The audit log is a local SQLite file, with no protection against changes and no retention rules. A production audit must be durable and protected (P4).
- File names in the audit log are sensitive. Only the index team can read the log ([ADR 0008](0008-index-team-and-audit-viewer.md)).
- Fast searches alone do not prove a useful or complete index. Coverage ([ADR 0005](0005-coverage-and-reader-gaps.md)) and quality ([ADR 0015](0015-acceptance-tests-enforce-the-use-case.md)) are separate measures.');
INSERT INTO "decision_sections" VALUES(7,4,'Implementation','Done. `SearchService.commit_audit` in [`service.py`](../../engineering_search/service.py) writes to `audit.sqlite3` ([`adapters.py`](../../engineering_search/adapters.py)) and raises `ServiceError(503)` on failure. `Telemetry` keeps the last 10,000 queries and 100 index runs in memory, so it resets on restart. The audit log is durable but not protected against changes, and has no retention rules. Tests: `tests/test_audit.py`.');
INSERT INTO "decision_sections" VALUES(8,1,'Context','The use case is for engineering managers and leads who search (U1). Index operations, uploads, telemetry, the access rules and the audit log are a different job, with sensitive information: the audit log names files that some users cannot read. Permission to search must not give access to these operations (R1).');
INSERT INTO "decision_sections" VALUES(8,2,'Decision','- JP and Kamal can search only.
- Maya represents the index team. Maya can open index operations, uploads, telemetry, the access rules, the API documentation and the audit log.
- The index-team role does not change file permissions. When Maya searches, Maya gets only the files that Maya can read ([ADR 0010](0010-path-based-access-rules.md)).
- The server checks the role on every page and API request. Hidden navigation is not the protection.
- The audit viewer shows pages of events, newest first. A snapshot ID keeps the pages stable while new events arrive. It is a page boundary, not permission to read.');
INSERT INTO "decision_sections" VALUES(8,3,'Consequences','- A search user cannot see the access rules, the audit log or other users'' searches.
- The index team can see file names in permission decisions. That is accepted for this role.
- Sign-in is pretend, so anyone can select Maya. Real identity is required before a shared service ([TODO.md](../../TODO.md#before-use-as-a-shared-service)).');
INSERT INTO "decision_sections" VALUES(8,4,'Implementation','Done. The `backend_boundary` middleware in [`app.py`](../../engineering_search/app.py) protects `/admin`, `/index`, `/scan`, `/uploads`, `/audit`, `/telemetry`, `/health` and the API pages. A denied request is recorded in the audit log. Pages: `static/admin.html` and `static/audit.html`. The demo users are `USERS` in [`access.py`](../../engineering_search/access.py). Tests: `tests/test_access.py`, `tests/test_audit.py`.

The earlier version of this record described per-file grants for ten demonstration files. [ADR 0010](0010-path-based-access-rules.md) replaced those grants with folder and file rules.');
INSERT INTO "decision_sections" VALUES(9,1,'Context','The first prototype kept passages in memory and needed every question word to match exactly. Plain-language questions (U6) found nothing for 76% of the test questions. Search across 100+ documents in under 10 seconds (U2, U3) needs an index, not a scan of the passages, as dtSearch and Lucene do. The first prototype also returned passages. The user asked for an answer (R2), and for lists of documents (R3). Confidence in the source (U4) means that the service must not write or change the answer text.');
INSERT INTO "decision_sections" VALUES(9,2,'Decision','1. Store documents and passages in SQLite, with an FTS5 inverted index over the heading, the text and the words of the file path. Use the `porter unicode61` tokenizer, so "loads" matches "load".
2. Change each question into an index query: remove common words, add a small synonym list, and make words with digits into prefix searches ("S355" finds "S355J2+N"). Show the user what was searched for.
3. Match any word. Rank passages that contain more of the question words first, then by BM25 (heading 3, text 1, file path 0.5).
4. Answer with text copied from a passage: one sentence or table row for a value question, or one line for each document in a list question. Never write or change the answer text.
5. For list questions, find the documents that contain every question word. Apply number comparisons ("greater than 5 kN/m²") at query time, with unit conversion.
6. Update the index incrementally by SHA-256, in one transaction ([ADR 0004](0004-persistent-evidence.md)).');
INSERT INTO "decision_sections" VALUES(9,3,'Consequences','- A question takes about 16 ms on the 138 test files, far below the 10-second limit.
- Each answer has a file, page, line range and version. Tests check it against the file.
- This is a basic method. It finds words, not meanings. It does not know which element a value belongs to, and number filters see only what word search finds. [ADR 0014](0014-defer-facts-store-and-embeddings.md) records why facts and embeddings are deferred.
- At a larger scale, the same design moves to OpenSearch or Elasticsearch ([design/SCALING.md](../../design/SCALING.md)).');
INSERT INTO "decision_sections" VALUES(9,4,'Implementation','Done. [`store.py`](../../engineering_search/store.py) (index, up to 1,000 candidates from permitted files), [`query.py`](../../engineering_search/query.py) (query plan), [`answer.py`](../../engineering_search/answer.py) (answer and list), [`units.py`](../../engineering_search/units.py) (quantities, with sign, in SI units). A list comparison counts a quantity only in a sentence bound to the question words. A list is paged at 200 documents, with the total count. Measured by `scripts/evaluate.py`. Enforced by `tests/test_use_case.py`, `tests/test_index.py` and `tests/test_binding.py`.

Limits: the incremental update reads and hashes every file; only extraction is incremental. Filters over tables now use SQL ([ADR 0016](0016-structured-facts-and-client-written-sql.md)); the text path stays for values in prose.');
INSERT INTO "decision_sections" VALUES(10,1,'Context','The first prototype gave per-file grants to ten demonstration files, and gave all other files to two users only. That made most of the repository look out of scope, and it did not match how the existing repository (C2) controls access. File shares and document systems set permissions on folders, and files inherit them, as in Windows. The search must cover all 100+ documents (U2) and still never give a user information from a document that the user cannot read (R1).');
INSERT INTO "decision_sections" VALUES(10,2,'Decision','- Index every supported file. Permissions decide what a user sees, not what is indexed.
- A rule applies to the whole repository, to a folder or to one file. The most specific rule wins and replaces the inherited one.
- Rules list users directly. There are no groups and no "deny" entries.
- Check the rules on each request, before answers, counts and pages ([ADR 0006](0006-permissions-before-results.md)).

The full list of assumptions is at the top of [`access.py`](../../engineering_search/access.py).');
INSERT INTO "decision_sections" VALUES(10,3,'Consequences','- The rules are simpler than Windows (NTFS) permissions, which merge inherited and explicit entries and have "deny" entries. A production service must get the effective permissions from the repository through its connector, not copy them into a Python file (P3).
- The rules are small and easy to read for a demonstration. The sign-in screen and the README show which folders each user can read.');
INSERT INTO "decision_sections" VALUES(10,4,'Implementation','Done. `ACCESS_RULES`, `governing_rule` and `MockPermissionStore` in [`access.py`](../../engineering_search/access.py). JP reads 138 of 138 files, Kamal 130 and Maya 133. Tests: `tests/test_access.py`, `tests/test_pagination.py`, `tests/test_no_leaks.py` (which also checks each user''s file list against a list written by hand).');
INSERT INTO "decision_sections" VALUES(11,1,'Context','The use case has two front ends: a search bar on a web page, and a chat-agent shell that calls backend APIs and tools (C5). The broader architecture already exists (C1), so this component must be a backend that other parts call, not a closed application. Before this decision, the search, permission and audit logic was in the HTTP routes of `app.py`. The MCP server had to call the web app over HTTP, or copy the logic. A copy can drift: one front end could check permissions (R1) or audit the sources (U4) differently from the other.');
INSERT INTO "decision_sections" VALUES(11,2,'Decision','- [`service.py`](../../engineering_search/service.py) holds all search logic in `SearchService`: search, read one file, permissions, audit, index operations and uploads.
- [`app.py`](../../engineering_search/app.py) is the HTTP layer only. It does sign-in, roles, request checks and the routes. Each route calls the service. The upload routes are an MVP shortcut: they call `service.queue` directly for the job steps.
- [`mcp_server.py`](../../engineering_search/mcp_server.py) calls the same service directly, with the same index, permissions and audit log. It does not start the web app.
- The service raises `ServiceError(status, detail)`. The web app changes it into an HTTP reply. The MCP server returns it as an error result.
- Every import points down: entry points (`__main__.py`, `mcp_server.py`) → [`runtime.py`](../../engineering_search/runtime.py) → `app.py` → `service.py` → the indexer (`indexing/`), domain logic (`answer.py`, `access.py`) and adapters (`store.py`, `adapters.py`, `jobs.py`) → `core.py` and `query.py`. `service.py` does not import `store.py`. `runtime.py` opens the stores and gives them to the service as objects. [design/code-architecture.png](../../design/code-architecture.png) shows each import.');
INSERT INTO "decision_sections" VALUES(11,3,'Consequences','- Both front ends give the same answer, check the same permissions and write the same audit events. One test of the service covers both.
- A new front end (for example a REST client in the existing architecture, C1) needs only a thin layer.
- Each process has its own `SearchService`: the web app in one process, the MCP server in another. Both open the same SQLite files. SQLite allows this, but a shared service needs one backend that many clients call ([design/SCALING.md](../../design/SCALING.md)).
- `SearchService` is a large class. It is acceptable for the MVP. The MVP shortcuts are listed in [ARCHITECTURE.md](../../ARCHITECTURE.md).');
INSERT INTO "decision_sections" VALUES(11,4,'Implementation','Done. Tests go through the web app (`tests/test_*.py`) and through the service directly (`tests/test_no_leaks.py` calls `service.read`). `scripts/check_mcp.py` starts the MCP server as a chat client does and calls its tools.');
INSERT INTO "decision_sections" VALUES(12,1,'Context','The constraints include a chat-agent shell that can call backend APIs and tools (C5). The users do not want to learn file formats, schema, query languages or jargon (U6). A chat agent lets them ask in their own words, and lets the agent ask follow-up questions. The Model Context Protocol (MCP) is the standard way for chat clients (Claude Desktop, Claude Code and others) to call tools. The simplest MCP transport is stdio: the chat client starts the server as a local process. A stdio server has no sign-in. It knows the user only from its start command. R1 is an absolute requirement, so this is a security hole.');
INSERT INTO "decision_sections" VALUES(12,2,'Decision','- Provide an MCP server with two tools:
  - `search_evidence(question, mode, within, limit, page)`: the same search as the search bar.
  - `read_evidence(file_id, page)`: all indexed passages of one readable file.
- Use the stdio transport for the MVP (S1).
- Take the user from the `--user` flag (or `SEARCH_USER`). Nothing verifies it.
- Accept this hole for the MVP only, with public and synthetic test data only (S3). Record it in the module docstring, [docs/MCP.md](../MCP.md), the README and the system design diagram.
- The tool results contain the same permitted evidence as the web page. The agent must quote the answer and its source, not write its own value (U4).');
INSERT INTO "decision_sections" VALUES(12,3,'Consequences','- A person who can change the chat client configuration can read as any user. Do not use the stdio server with real restricted files.
- The fix: run the MCP server remotely over Streamable HTTP, behind the company sign-in (OAuth). Take the user from the verified token on each request. The permissions and audit log then match the real person ([docs/MCP.md](../MCP.md#the-security-hole-the-mcp-user-is-not-verified)).
- Tool results go to the language-model provider of the chat client. The company must approve that provider for the documents.
- The agent can summarise or change the exact text. The tool gives exact text and sources, but the agent''s reply is outside the control of this service.');
INSERT INTO "decision_sections" VALUES(12,4,'Implementation','Done for stdio, with the hole. [`mcp_server.py`](../../engineering_search/mcp_server.py), with `mcp==1.27.2` (FastMCP). [ADR 0016](0016-structured-facts-and-client-written-sql.md) adds the structured tools: `describe_schema`, `list_tables`, `describe_table`, `query_sql` and `get_document_evidence`. The index team also gets `get_index_coverage`. Verified on 29 October 2026 with Claude Code, Codex and Pi over local stdio; the project files `.mcp.json` and `.pi/mcp.json` start the server. Install and test steps: [docs/MCP.md](../MCP.md). Checks: `uv run --frozen python -m scripts.check_mcp` and `tests/test_mcp_stdio.py`, which run the server as a chat client does. The remote server with OAuth is in [TODO.md](../../TODO.md#before-use-as-a-shared-service).');
INSERT INTO "decision_sections" VALUES(13,1,'Context','The user asks for one parameter (U1) and must trust the source 100% (U4). The user also asked for an answer, not a list of passages (R2). Word search always finds something: a question about a project that does not exist still matches "roof" and "load" in other projects. If the service always gives its best match as the answer, a user can get the load limit of the wrong project, with a correct-looking source. That is worse than no answer. Two documents can also state different values for the same parameter, for example a draft and an approved revision.');
INSERT INTO "decision_sections" VALUES(13,2,'Decision','- Each answer has a status:
  - `found`: one sentence or table row states a value, and its document contains every question word.
  - `partial`: the closest sentence states a value, but its document does not contain some question words. `missing_words` names them. The user sees which words were not found, for example the project name.
  - `not_found`: no sentence states a value that matches enough question words (`MIN_COVERAGE`, 50%). The service gives no answer.
- Check the question words against the whole document text, not only the passage. A project name is often in the title, not in the sentence with the value.
- Copy the answer exactly from the document. Never write, round or convert the answer text.
- Show other readable files that also state a value as "also stated in", so the user sees conflicts (at most `MAX_ALSO_STATED`, 5).
- Use only readable files for each of these steps (R1, [ADR 0006](0006-permissions-before-results.md)).');
INSERT INTO "decision_sections" VALUES(13,3,'Consequences','- The service can say "not found" when a person would find the value in a table or a drawing that the readers cannot read. A correct "not found" is better than a wrong answer.
- `partial` is a word check, not an understanding of the question. It does not know that the value belongs to the asked element. [ADR 0014](0014-defer-facts-store-and-embeddings.md) records the facts store that would know this.
- The test questions include a question with no answer, and the acceptance tests check that the service gives none.');
INSERT INTO "decision_sections" VALUES(13,4,'Implementation','Done for the known case. `pick_answer()` in [`answer.py`](../../engineering_search/answer.py) checks that the cited sentence is bound to the question words: through the sentence, its heading, the file path or the document title. If the document has every word but the sentence does not name some of them, the status is `unverified`, with `unbound_words`. "Roof load is not specified. Floor load limit is 5 kN/m²." no longer answers "What is the roof load?" as `found`. The web page and the MCP server show the status and the missing or unbound words. Tests: `tests/test_binding.py`, `test_no_answer_is_given_when_no_document_states_it` and `test_one_value_is_answered_from_its_exact_source` in `tests/test_use_case.py`, and the `answer_correct` metric of `scripts/evaluate.py`.

Limits: binding is a word check. A sentence that names the subject can still state a different parameter. The document-title rule is a heuristic: the first passage counts as the title only if it starts in the first three lines.');
INSERT INTO "decision_sections" VALUES(14,1,'Context','The constraints offer connectors that extract properties (C3), and structured and semantic stores (C4). A structured store of engineering facts (element, parameter, value, unit, status, source) would answer "the roof load limit at Northgate" directly. Embeddings in a semantic store would find passages that use different words from the question. Both need decisions that the MVP cannot make yet:

- Which questions do users ask? Which parameters (U1) and which words?
- Which document types hold the answers, and in which form: sentences, tables, title blocks or drawings?
- Which readers and extractors can get the values reliably, with their source?

There is no one design that suits all repositories. A facts store made without this research extracts the wrong properties. Embeddings without tests can rank a similar but wrong passage first, which breaks U4.');
INSERT INTO "decision_sections" VALUES(14,2,'Decision','- For the MVP (S1), use word search and exact text answers only ([ADR 0009](0009-sqlite-fts5-index-and-answers.md)).
- Do not build a facts store or embeddings yet.
- First, profile the repository and collect real questions and answers ([design/DATA-PROFILE.md](../../design/DATA-PROFILE.md)). Then design the extractors and stores from those questions ([design/EXTRACTION.md](../../design/EXTRACTION.md)).
- Keep the index schema and the source fields (file, page, lines, version) so that a later facts store or embedding index can cite the same sources.');
INSERT INTO "decision_sections" VALUES(14,3,'Consequences','- The MVP finds words, not meanings. Synonyms are a small fixed list. The metrics on the test data are high because the questions, the synonyms and the documents were made together ([docs/METRICS.md](../METRICS.md)).
- Hybrid search (words and embeddings) and the facts store are phase 2 and 3 work ([TODO.md](../../TODO.md#next-phase-2)).
- The question set and the acceptance tests ([ADR 0015](0015-acceptance-tests-enforce-the-use-case.md)) will measure whether the later stores are better.');
INSERT INTO "decision_sections" VALUES(14,4,'Implementation','Superseded in part by [ADR 0016](0016-structured-facts-and-client-written-sql.md): typed facts from tables are implemented, and the MCP client writes constrained SQL over them. Still deferred: facts from prose, and embeddings. The design is in [design/EXTRACTION.md](../../design/EXTRACTION.md) and [design/DATA-PROFILE.md](../../design/DATA-PROFILE.md).');
INSERT INTO "decision_sections" VALUES(15,1,'Context','The use case must be enforced by tests (R4), not only described. The repository will be published, so the test data must be public or synthetic (S3). Real engineering documents cannot be used. The tests need more than 100 documents (U2), questions with known answers and sources (U1, U4), and documents that some users cannot read (R1).');
INSERT INTO "decision_sections" VALUES(15,2,'Decision','- Keep a test repository in `test-repository/` with 138 files: 133 Markdown and 5 PDF.
  - 120 generated project files in `generated-projects/`, so the count is above 100 (U2).
  - Hand-written projects (Northgate, Riverside, Cedar), registers and specifications, with known values, conflicts, drafts and approvals.
  - Two public FHWA steel bridge handbook PDFs. `SOURCES.txt` records where they come from.
- Write one acceptance test for each part of the use case in `tests/test_use_case.py`:
  - more than 100 documents (U2);
  - one value from its exact file, page, lines and version, checked against the file (U1, U4, U5);
  - no answer when no document states it ([ADR 0013](0013-no-answer-before-a-wrong-answer.md));
  - list questions, material, approval status, load comparison and a follow-up (R3);
  - each answer within the 10-second limit (U3);
  - no answer from a file the user cannot read (R1).
- Test R1 more strongly in `tests/test_no_leaks.py`: every question, plus questions made from the text of each forbidden file, in each mode, on the first five result pages of 50 passages, for each user.
- Measure ranking and answers with `scripts/evaluate.py` on 17 questions, 16 of them scored (`evaluation/questions.json`). Save the results in `evaluation/results/answers.json`.');
INSERT INTO "decision_sections" VALUES(15,3,'Consequences','- A change that breaks the use case on these examples fails a test. The tests do not cover every failure: they passed with defects that a later review found, a wrong parameter marked `found` and lost results when forbidden passages filled the retrieval limit, which [ADR 0017](0017-bind-answers-and-permit-before-the-limit.md) fixed with new tests. The open limits are in [TODO.md](../../TODO.md#known-limits-fix-or-decide).
- The test data was made with the questions and the synonyms. The scores are higher than on a real repository. [docs/METRICS.md](../METRICS.md) and [evaluation/README.md](../../evaluation/README.md) explain the limits and the gaps in the tests.
- The tests prove the behaviour on this repository, not on the company''s repository. A real question set, made from real users and real documents, is the next step ([ADR 0014](0014-defer-facts-store-and-embeddings.md)).');
INSERT INTO "decision_sections" VALUES(15,4,'Implementation','Done. Run `uv run --frozen pytest -q` and `uv run --frozen python -m scripts.evaluate`. The current figures are in [docs/METRICS.md](../METRICS.md).');
INSERT INTO "decision_sections" VALUES(16,1,'Context','The text path ([ADR 0009](0009-sqlite-fts5-index-and-answers.md)) answers one value from prose well enough. It answers filter questions badly: "Which S355 components have an allowable load under 5 kN/m²?" needs every matching row, a numeric comparison in one unit, and the difference between what a component can carry (a capacity) and what it must carry (a demand). Word search sees only the passages that it ranks, so the list is not complete, and a number near a keyword can belong to a different element.

Much of the data that leads ask about is already structured: component schedules and registers in CSV and Excel, and tables in Markdown and PDF. The 29 October design inputs ([handoff](../CODEX_ENGINEERING_SEARCH_HANDOFF.md), [design notes](../engineering_knowledge_search_design_notes.html)) ask for these tables to keep their row identity and source location, and for the MCP client''s LLM to plan structured questions. They rule out a second LLM on the server.

The premise is that the indexer is designed from the questions and the data: to build it, you need an idea of the questions; to answer them, you need to know what data you have and what you can extract from it. That gives two kinds of extracted data, unstructured (passages) and structured (tables and facts), and a way in for each.

Who writes the structured query has three options:

1. **The service plans it from the plain-language question.** No LLM, but a rule-based planner for joins and filters is a query language in disguise, and it is brittle.
2. **A server-side LLM writes SQL.** Needs an API key and a provider on the server, and sends questions to it. The design inputs rule it out.
3. **The chat agent that already reads the question writes SQL, and the server constrains it.** The LLM is already in the loop (C5). The user still asks in plain language (U6). The server owns safety and permissions.');
INSERT INTO "decision_sections" VALUES(16,2,'Decision','- **Extract tables and typed facts at index time.** Readers return tables with the source line, page or sheet of each row: Markdown pipe tables, CSV files and XLSX sheets. Fixed rules (`indexing/facts.py`) read the column header, the table name and the cell, and give each cell a parameter, a role (capacity, demand, specification, status, measurement, unknown), the value as written, a number, a unit and an SI value. Facts come only from table cells, never from free text. Capacity and demand are never the same parameter.
- **Publish a small, documented schema** to the client: `documents`, `facts`, `components` (a view with the common parameters as columns), `table_rows` and `source_tables`. `describe_schema`, `list_tables` and `describe_table` describe it. The schema holds no document data.
- **The MCP client''s LLM writes the SQL.** `query_sql` runs one statement. The service does not plan structured questions itself, and the web search bar does not claim to.
- **Constrain the SQL on the server, for each request:**
  - Build an in-memory SQLite projection with only the rows from files the user may read, and every dependent row. Forbidden data is absent, not filtered, so counts, joins and `NOT EXISTS` cannot reveal it. The base index is never exposed to SQL.
  - Accept one `SELECT` or `WITH` statement, at most 4000 characters.
  - Run it with `PRAGMA query_only`, an authoriser that allows reads of the published tables only and a short function allowlist, a budget of 2,000,000 SQLite steps, and at most 500 rows.
  - Audit the SHA-256 and length of the statement, the files in scope and excluded, the row count and the cited files, not the rows.
- **Every row can be cited.** Rows carry `file_id`, `table_no`, `row_no`, `line` and `page`. `get_document_evidence` returns the row''s cells, its facts, the file''s SHA-256 version and the verbatim line.
- **Keep the text path.** `search_evidence` and `read_evidence` are unchanged. The server instructions tell the agent to choose: SQL for filters, joins and counts over tables; text search for values in prose.');
INSERT INTO "decision_sections" VALUES(16,3,'Consequences','- "S355 components under 5 kN/m²" returns every matching row from the files the user may read, with citations: 7 rows for JP, 6 for Kamal. Verified with Claude Code, Codex and Pi ([docs/MCP.md](../MCP.md#what-was-verified)).
- The server makes the SQL safe; it does not make it right. The LLM can write a valid query for the wrong thing. The column names (`allowable_load_kn_m2`, `imposed_load_kn_m2`) and the instructions guide it, and the tool call shows the SQL to the tester.
- A value stated only in prose is not a fact. SQL does not find it; text search does.
- The rules know a small set of parameters and units. A new kind of column becomes a fact with role `unknown` until a rule is added.
- The web page has no structured path. `POST /sql` exists in the HTTP API for a future client-planned flow.
- Building a projection per request is simple and safe, and costs time in proportion to the permitted data. It does not scale to a large repository; a policy-enforced view over the base index is the later design ([design/SCALING.md](../../design/SCALING.md)).
- The safety rests on SQLite''s authoriser and `query_only`, not on a SQL parser. The bypass tests in `tests/test_sql.py` are the check. The MCP tool does not take bound parameters yet.');
INSERT INTO "decision_sections" VALUES(16,4,'Implementation','Done for CSV, XLSX and Markdown tables. Readers: [`readers/csv.py`](../../engineering_search/indexing/readers/csv.py), [`readers/xlsx.py`](../../engineering_search/indexing/readers/xlsx.py) (`openpyxl`; a formula with no cached value is left empty and the file is `INDEXED_PARTIAL`), [`readers/markdown.py`](../../engineering_search/indexing/readers/markdown.py). Facts: [`indexing/facts.py`](../../engineering_search/indexing/facts.py), units in [`units.py`](../../engineering_search/units.py). Store: `source_tables`, `table_rows` and `facts` in [`store.py`](../../engineering_search/store.py). Projection and safety: [`sql.py`](../../engineering_search/sql.py). Service: `query_sql`, `sql_schema`, `table_row_evidence` in [`service.py`](../../engineering_search/service.py). HTTP: `POST /sql`, `GET /sql/schema`, `GET /evidence/{file_id}/tables/{n}/rows/{n}`. MCP tools in [`mcp_server.py`](../../engineering_search/mcp_server.py).

Tests: `tests/test_facts.py` (the rules), `tests/test_sql.py` (expected rows by hand from the fixtures, permissions, refused statements, audit, citations, the example queries in docs/MCP.md), `tests/test_mcp_stdio.py` (a real MCP client over stdio), `tests/test_no_leaks.py` (CSV and XLSX files included). Not done: tables in PDF files, facts from prose, bound parameters in `query_sql`.');
INSERT INTO "decision_sections" VALUES(17,1,'Context','An independent review on 28 October 2026 reproduced four errors in the text path:

1. **A wrong parameter was `found`.** ADR 0013 checked the question words against the whole document. "Roof load is not specified. Floor load limit is 5 kN/m²." answered "What is the roof load?" with the floor load, status `found`. A list comparison could also qualify a document by a floor load for a roof load filter. This is the wrong answer that ADR 0013 exists to prevent (U4).
2. **Forbidden files changed a user''s results.** ADR 0006 checked permissions after the index lookup, and the lookup kept the 1,000 best passages from all files. Forbidden passages that ranked higher pushed permitted ones out. No forbidden text was shown, but a forbidden file changed what a user saw, which breaks R1 in spirit.
3. **Signs were ignored.** "-2 kN/m²" compared as 2 kN/m².
4. **Lists stopped at 200 documents** and `page` did not page them.');
INSERT INTO "decision_sections" VALUES(17,2,'Decision','- **Bind the answer to the question words.** A question word is bound when it is in the selected sentence, its passage heading, the file path, or the document title. The title counts only if the first passage starts in the first three lines of the file or of its first page.
- **Statuses:**
  - `found`: every question word is bound to the sentence.
  - `unverified` (new): the document has every question word, but the sentence does not name some of them (`unbound_words`). The value may be about something else. The user and the chat agent must see the warning.
  - `partial`: some question words are not in the document (`missing_words`).
  - `not_found`: no sentence states a value that matches enough question words.
- **List comparisons need a bound line.** A document qualifies only if one line states a quantity that meets the comparison and every question word is bound to that line.
- **Permissions before the limit.** Find the files that contain a query word, evaluate permissions on them (and apply `within`), and pass the permitted set into the FTS5 query. The 1,000-passage limit applies to permitted passages only.
- **Signed numbers.** A leading minus is a sign. A hyphen inside a code (B-104) or a range (1-2 kN) is not.
- **Page lists** at 200 documents, with the total `count`, `document_pages` and `truncated`.');
INSERT INTO "decision_sections" VALUES(17,3,'Consequences','- Some answers that were `found` are now `unverified`. That costs apparent precision and gains trust: the service no longer presents an unbound value as the answer.
- Binding is a word check. A sentence that names the subject can still state a different parameter. Facts from tables ([ADR 0016](0016-structured-facts-and-client-written-sql.md)) bind value to subject structurally; prose still relies on words.
- The title rule is a heuristic until the readers return a title.
- Adding forbidden files can no longer change a user''s results. The index query is a little more complex (a temporary scope table joined inside the FTS5 query).');
INSERT INTO "decision_sections" VALUES(17,4,'Implementation','Done. `pick_answer()`, `list_documents()` and `title()` in [`answer.py`](../../engineering_search/answer.py); signed numbers in [`units.py`](../../engineering_search/units.py); `document_matches()` and `candidates(query, files)` in [`store.py`](../../engineering_search/store.py); the order of steps in `SearchService.search` ([`service.py`](../../engineering_search/service.py)). Tests: [`tests/test_binding.py`](../../tests/test_binding.py) (floor load not the roof answer, heading binds, list filter, signed values, forbidden passages past the candidate limit, list page 2), [`tests/test_no_leaks.py`](../../tests/test_no_leaks.py) (first five and last pages).');
INSERT INTO "decision_sections" VALUES(18,1,'Context','The use case asks for an answer in under 10 seconds (U3). The MVP was measured with one user at a time. With many users, it fails:

- **One process serves one request at a time.** `SearchService.lock` is held from the file match to the audit write, and the index has one SQLite connection. Throughput is about 10 requests a second on the 148 test files, whatever the load.
- **The constrained SQL path copies data for each request.** [ADR 0016](0016-structured-facts-and-client-written-sql.md) builds an in-memory projection of every permitted fact, then runs the statement. That costs about 2 µs a fact to build and 1 µs a fact to query the `components` view: 0.6 s at 200,000 facts, 3 s at 1,000,000. The build is under the service lock.
- **The SQL step budget does not grow with the data.** At 200,000 facts, the 2,000,000-step budget stops even the standard S355 query, because `components` is a view that groups every fact.

Measured on 29 October 2026 (`scripts/load_test.py` on a macOS laptop, one process, mixed text questions and the S355 SQL query, JP, Kamal and Maya):

| Requests at once | Before: slowest answer | Before: median |
| --- | --- | --- |
| 1 | 0.12 s | 0.12 s |
| 100 | 10.3 s | 5.6 s |
| 1,000 | 102 s | 51 s |

A user who waits 100 s and then gets an answer, or a timeout, loses trust. A user who is told at once "busy, try again in 5 s" can act.

Note that over local stdio ([ADR 0012](0012-mcp-server-for-the-chat-agent.md)) each chat client starts its own server process, so MCP users do not queue behind each other in one process; they share the machine and the SQLite files. The queue matters for the web service and for any shared remote server.');
INSERT INTO "decision_sections" VALUES(18,2,'Decision','- **Admission control.** Before a search, read or SQL query runs, predict its time and refuse it at once if it cannot finish within the budget. With n = requests in flight + 1, the prediction is n × mean + 2 × √n × spread, from moving averages of the measured service time (smoothing 0.05; first guess 0.2 s, deliberately cautious). A request''s own service time runs from the later of its arrival and the previous departure, so waiting is not counted as work.
- **The budget is 8 s** (`SEARCH_BUDGET_SECONDS`), leaving 2 s of the 10 s target for the network, the chat client and the language model.
- **Admit where the request arrives.** The HTTP middleware admits before the route waits for a worker thread, so time in the thread queue counts. Each MCP tool admits before it calls the service. Index operations and uploads are not admission-controlled.
- **Tell the caller.** HTTP: 503 with a `Retry-After` header and `{"busy": true, "retry_after_seconds": n, "message": ...}`, and no evidence. MCP: the same object as the tool error; the server instructions tell the agent to report it and not to retry in a loop. The web page shows the message. `/index/status` shows the learnt service time, spread, requests in flight, refusals and capacity to the index team.
- **Do not hide the limit.** Document the throughput, the SQL cost and the step-budget limit here, in [ARCHITECTURE.md](../../ARCHITECTURE.md) and in [TODO.md](../../TODO.md), until the scaling work below is done.');
INSERT INTO "decision_sections" VALUES(18,3,'Consequences','Measured after the change, budget 8 s:

| Requests at once | Answered | Slowest answer | Refused as busy | Slowest refusal |
| --- | --- | --- | --- | --- |
| 1 | 1 | 0.12 s | 0 | — |
| 10 | 10 | 0.73 s | 0 | — |
| 100 | about 50 | 5.7 s | about 50 | 0.02 s |
| 1,000 | about 47 | 5.5 s | about 953 | 0.24 s |

- Every answered request finished within the budget, and every refusal came back in under 0.25 s, with a retry time.
- **The guarantee is bounded latency, not capacity.** Throughput is unchanged at about 10 a second per process. With 1,000 simultaneous requests, most users are told to retry.
- The prediction is conservative: it admits about 50 per burst where about 75 would fit. That trades capacity for the guarantee. The 2 × √n × spread margin and the smoothing are tunable after measurement on real load.
- A burst of slow requests (large SQL projections) raises the estimate, and the service refuses more until it falls again.
- Admission is per process. Several processes behind a load balancer each admit on their own queue.

### What must change to serve the company

In order of value; each is a milestone in [TODO.md](../../TODO.md):

1. **Concurrent reads in one process.** One read connection per thread, each request in one read transaction (a WAL snapshot), and no global lock for searches. The index lock stays for writers. Python''s GIL still limits the answer rules, so:
2. **Several worker processes** (or machines) reading the same index, behind a load balancer. Sessions and the upload queue move out of process memory. Rough sizing at the test-data cost of 0.1 s a request: 1,000 users asking one question a minute is about 17 requests a second, so 3 to 4 workers at 60% load. The real repository must be measured.
3. **SQL without a copy per request.** Cache projections by (permission-set fingerprint, index version), or enforce permissions inside a server database (row-level security, or views over a permitted-file table) so nothing is copied. Make `components` an indexed table, not a grouping view, and scale the step budget with the data.
4. **A server search engine** (or a server database with full-text search) when one SQLite file is no longer enough.
5. **Load tests in CI** at the expected size and concurrency, with the 10 s target as a gate.');
INSERT INTO "decision_sections" VALUES(18,4,'Implementation','Done for admission control. `Admission` and `Busy` in [`adapters.py`](../../engineering_search/adapters.py); `SearchService.admit()` in [`service.py`](../../engineering_search/service.py); `AdmissionMiddleware` in [`app.py`](../../engineering_search/app.py); `service.admit()` around each MCP tool in [`mcp_server.py`](../../engineering_search/mcp_server.py); `SEARCH_BUDGET_SECONDS` in [`runtime.py`](../../engineering_search/runtime.py). Tests: [`tests/test_admission.py`](../../tests/test_admission.py) (the prediction, worked by hand on a fake clock; 503 with Retry-After and no evidence). Load test: `uv run --frozen python -m scripts.load_test`. The scaling work above is not started.');
INSERT INTO "decision_sections" VALUES(19,1,'Context','Trust fails quickly when search is wrong. A lead who gets one confident wrong load limit stops using the service. The tests prove that the code does what it was written to do, on the documents it was written for. They do not say how good the answers are, or how good they will be on real documents and real questions.

There are now three places where a question can go wrong:

1. **Retrieval and text answers** (the service). Does the index find the right passage, and does the answer step choose the right sentence, with the right status?
2. **Natural language to SQL** (the chat agent). [ADR 0016](0016-structured-facts-and-client-written-sql.md) gives the structured question to the MCP client''s language model. The server makes the SQL safe, not right. A safe query can compare a demand with a capacity, miss S355J2 when asked for S355, read 5 N/m² as 5 kN/m², or drop a project filter. Nothing measured this.
3. **The agent''s reply.** The agent reads the tool result and writes its own words. It can drop a row, change a value, or present an `unverified` value as fact. Nothing checks this either.

What existed on 29 October 2026: `scripts/evaluate.py` scores 16 text questions (Success@1 0.88, Success@5 1.00, MRR@10 0.90, Recall@10 0.90, answer correct 1.00, no leaks). The questions, the synonyms and the documents were written together by the same team, so the scores are optimistic ([docs/METRICS.md](../METRICS.md)). The SQL path had tests, not an evaluation.');
INSERT INTO "decision_sections" VALUES(19,2,'Decision','Evaluate each of the three places separately, so a failure points at its cause.

### 1. Retrieval and text answers

Keep `scripts/evaluate.py` and `evaluation/questions.json`, and extend the set by kind:

- **One value**: the answer comes from an expected file and contains the expected text; its status is the expected one (`found`, `unverified`, `partial`).
- **Not stated**: questions whose correct result is `not_found`. A confident answer is a failure.
- **Lists**: precision and recall of the document set, not only the first result.
- **Paraphrases**: the same question in other words, to measure the synonym gap.
- **Permissions**: the same question for each user; leaks must be 0.

Metrics: Success@1 and @5, MRR@10, Recall@10, answer correct, status correct, not-found precision, list precision and recall, zero-result rate, leaks, latency p50 and p95.

### 2. Natural language to SQL

Use **execution accuracy**, not SQL text: many different statements are correct. A question passes when the client''s result has exactly the expected rows (as `[subject, file_id]` pairs) or the expected value.

- **The gold set**: [`evaluation/sql_questions.json`](../../evaluation/sql_questions.json), 13 questions with expected rows written by hand from the fixtures. Each names its **trap**: grade family, capacity versus demand, units, sign, project filter, a join through `table_rows`, permissions (Kamal), and "no rows is the right answer". Each has one reference SQL, and [`tests/test_sql_questions.py`](../../tests/test_sql_questions.py) checks that it gives the expected rows, so the gold set cannot drift from the extraction.
- **Metrics**: execution accuracy; row precision and recall (partial credit shows what is missed); pass rate by trap; refused statements (the server''s error messages should let the agent correct itself); tool calls and time per question.
- **Repeat each question several times.** A language model does not answer the same way twice. Report pass@1 and the share that pass every time.
- **Pin versions.** Record the client, its version and the model with every result. A model change is a new baseline.
- **Coincidental success.** A wrong query can return the right rows on small data. Use several paraphrases per question and the traps to make that unlikely, and grow the fixtures where a trap is not yet decisive.

### 3. The agent''s reply and its choice of tool

- **Fidelity**: every value and row in the reply appears in a tool result; no expected row is missing; `partial` and `unverified` warnings are passed on; no forbidden content. Check these deterministically first (subjects, numbers and file names in the reply against the tool results). Use a language-model judge only as a second opinion, with people checking a sample.
- **Routing**: does the agent use SQL for filter and count questions, and text search for values in prose? A mixed set of questions, scored by which tools were called.

### 4. The harness

- The MCP server writes an opt-in trace (local file, evaluation only) of each tool call: the tool, the arguments (including the SQL), the row keys returned, any error and the time. It never writes passage text.
- A script runs each client (`claude -p`, `codex exec`, `pi -p`) on each question as its user, reads the trace and the final reply, and scores them. Results go to `evaluation/results/` with the date, the client and model versions, and the per-question details.

### 5. Gates and real questions

- **Every commit** (in the test suite): the gold SQL set is valid, the retrieval evaluation runs, leaks are 0, and answer correct stays at 1.00 on the scored set.
- **Before a release, or a model or client change**: the live-client evaluation for each supported client. No release with a permission leak or a fidelity failure; execution accuracy and the retrieval metrics must not fall below the last accepted baseline without a recorded reason.
- **Real questions**: collect questions from engineering leads, with the answers and sources they expect ([design/DATA-PROFILE.md](../../design/DATA-PROFILE.md)). Keep about a third back from the developers. Only scores on the held-back set predict real use.');
INSERT INTO "decision_sections" VALUES(19,3,'Consequences','- Each failure points at its layer: the index, the answer rules, the schema and its descriptions, the client''s model, or the reply.
- The live evaluation costs money and time per run, so it runs before releases, not on every commit.
- The scores on synthetic data will stay optimistic until real, held-back questions exist. The documents say so ([docs/METRICS.md](../METRICS.md)).
- Schema descriptions and tool instructions become things to tune against the SQL evaluation, like the synonym list for retrieval.');
INSERT INTO "decision_sections" VALUES(19,4,'Implementation','Partial.

- Done: the retrieval evaluation ([`scripts/evaluate.py`](../../scripts/evaluate.py), 16 scored questions); the NL-to-SQL gold set with its validation test; the load test for the time budget ([ADR 0018](0018-admission-control-and-the-time-budget.md)).
- Gates: only the gold-set check runs in the test suite, and `tests/test_no_leaks.py` asks every evaluation question for each user. The retrieval evaluation is run by hand. There is no CI.
- Not done: the MCP trace, the live-client harness and its first baseline for Claude Code, Codex and Pi; not-found, list and paraphrase questions in the retrieval set; the fidelity and routing checks; real held-back questions. Each is a milestone in [TODO.md](../../TODO.md).');
INSERT INTO "decision_sections" VALUES(20,1,'Context','The brief states five things that already exist (C1 to C5). In particular, connectors and APIs already extract metadata, text and properties from supported files (C3).

The MVP still needs files to be read, stored and queried to run end to end, so it has its own readers for Markdown, PDF with a text layer, CSV and XLSX, its own SQLite stores, a local folder for a repository and local chat clients. Earlier records ([ADR 0001](0001-mvp-format-scope.md), [ADR 0003](0003-versioned-reader-selection.md), [ADR 0005](0005-coverage-and-reader-gaps.md)) describe the readers as if extraction were part of this work. Read that way, the MVP appears to ignore the constraint and to propose rebuilding what the company already has.');
INSERT INTO "decision_sections" VALUES(20,2,'Decision','- Treat C1 to C5 as given. The MVP does not design or build them.
- Where the MVP needs one of them to run, use the simplest stand-in that proves the chain from question to cited answer, and name it as a stand-in:

| In the brief | Stand-in in the MVP | In a real deployment |
| --- | --- | --- |
| C1 an architecture direction | One search service behind an HTTP API, a web page and an MCP server | The existing architecture calls the same service |
| C2 an existing repository | A local folder of test files, and folder rules for permissions | The repository, its versions and its permissions, through its connector |
| C3 connectors extract metadata, text and properties | Readers for Markdown, PDF text layer, CSV and XLSX | The existing connectors and APIs, each behind the reader interface |
| C4 structured and semantic stores | SQLite: an FTS5 index, tables and typed facts | The company''s stores |
| C5 a chat-agent shell | Claude Code, Codex and Pi over a local MCP server | The company''s chat-agent shell, over remote MCP or its tool API |

- The work that is the MVP''s own is what sits between these: knowing the questions, what to take from tables and how to type it, permissions before limits, binding an answer to its subject, citations, constrained SQL, the time budget, and the tests and evaluation.
- The reader interface (`ReaderManifest`, `Extraction`) is where a connector plugs in: an adapter returns the same passages and tables, with source locations and a version.');
INSERT INTO "decision_sections" VALUES(20,3,'Consequences','- Better PDF or Markdown parsing is not MVP work. A gap in a stand-in reader is recorded, not fixed, unless it breaks the chain.
- The format scope of [ADR 0001](0001-mvp-format-scope.md) (S2) is the scope of the stand-ins, not of the product.
- Reader selection and coverage ([ADR 0003](0003-versioned-reader-selection.md), [ADR 0005](0005-coverage-and-reader-gaps.md)) stay: the service must still know what read each file, in which version, and which files nothing could read. With real connectors they record the connector''s name and version.
- The quality of real connector output (OCR, tables in PDF files, CAD properties) is unknown, and must be profiled on the real repository ([design/DATA-PROFILE.md](../../design/DATA-PROFILE.md)).');
INSERT INTO "decision_sections" VALUES(20,4,'Implementation','Done in the documents: [docs/README.md](../README.md#what-is-assumed-and-what-stands-in-for-it), the constraint pages (C1 to C5 have the standing *assumed* and list their stand-ins), and the docstring of the reader package, [`engineering_search/indexing/readers/__init__.py`](../../engineering_search/indexing/readers/__init__.py). No behaviour changed.');
INSERT INTO "decision_sections" VALUES(21,1,'Context','The constraints are cited by every decision record and by other documents. The links, the Serves column of the index and the lists of citing records were kept by hand, and they drifted: the index listed R1 for [ADR 0018](0018-admission-control-and-the-time-budget.md) when the record did not, [ADR 0016](0016-structured-facts-and-client-written-sql.md) lacked S4, and a link pointed at a heading that had been removed. Code paths in records go stale when files move. An agent changing the code had no structured way to find the decisions that govern a file.');
INSERT INTO "decision_sections" VALUES(21,2,'Decision','- **One SQLite database**, `design/records/records.sqlite`, holds the brief verbatim by section, the constraint groups and constraints with their standing, the decision records (metadata, notes and sections), and the links between them: which constraints a decision serves, leaves unmet or cites; which decisions supersede, amend or extend which; which files implement, test or measure a decision; and which files stand in for, enforce, measure or deliver a constraint. It is only a tracking database for the design; the product does not read it.
- **It is the source.** `python -m design_records generate` writes every ADR page, the ADR index, the constraint pages and a SQL dump (`records.sql`) for review in diffs. Each generated page says so at the top. docs/README.md and the dated design inputs stay hand-written.
- **A check runs in the suite** ([`tests/test_design_records.py`](../../tests/test_design_records.py)). It fails when a generated page differs from what the database produces; a file named in the database does not exist; a decision mentions a constraint or a code file that it does not link; the brief in the database differs from docs/Starting_document.md; a link or anchor in a generated page is broken; or a foreign key is broken.
- **A read-only MCP server** (`python -m design_records mcp`) gives an agent the records during development: an overview, a constraint or a decision with its links, a search, the decisions and constraints that govern a file, the check, and read-only SQL. AGENTS.md tells agents to consult it before a design change. It is registered for Claude Code in `.mcp.json`.
- **A browser view** (`design/records/index.html`) reads the SQLite file directly with sql.js and shows the brief with its constraints, each constraint and decision with its links and files, and a matrix of constraints against decisions. It changes nothing.');
INSERT INTO "decision_sections" VALUES(21,3,'Consequences','- A change to a decision is an edit to the database, then `generate`. Editing a generated page by hand fails the test. The edit is less convenient than editing Markdown: the `sqlite3` shell''s `edit()` function opens a text field in an editor.
- The database is binary in git. `records.sql` is the form to review; the check keeps it in step.
- Prose stays in text fields. The database checks that the structure, the links and the files are consistent, not that the words are right.
- To be evaluated after a few real changes. If editing prose in SQLite is too awkward, keep the structure in the database and move the prose to files that it references. Write tools for the MCP server are a later option; for now every write goes through `generate` and the check.
- **No history yet.** Rows are updated in place, so the database cannot say what a constraint said when a decision was made, which decisions rest on a constraint that has since changed, or which records are active and which displaced. Before the records become a living spec that features work within, they need append-only versions, links from decisions to the constraint versions they were made under, features as records, and proposals instead of writes for agents. The weaknesses and the design are in [design/records/README.md](../../design/records/README.md#weaknesses-and-what-comes-next).
- **A binary source does not merge.** Two branches that change records conflict on the database file. Making text files the source, with SQLite built from them as an index, is the likely next step and is to be decided before history is built.');
INSERT INTO "decision_sections" VALUES(21,4,'Implementation','Done. Schema, rendering and checks: [`design_records/records.py`](../../design_records/records.py). MCP server: [`design_records/mcp_server.py`](../../design_records/mcp_server.py). Database, dump, view and how to edit: [design/records/](../../design/records/README.md). Tests: [`tests/test_design_records.py`](../../tests/test_design_records.py) (the generated pages match the database, the records are consistent, and each check fails on a broken copy of the database; the MCP tools return the links from the database).');
CREATE TABLE decisions (
  number INTEGER PRIMARY KEY,
  slug TEXT NOT NULL UNIQUE,
  title TEXT NOT NULL,
  summary TEXT NOT NULL,         -- one line for the index
  status TEXT NOT NULL,
  date TEXT NOT NULL,
  notes TEXT NOT NULL DEFAULT '',  -- under the title: supersession and amendment notes
  implementation_summary TEXT NOT NULL
);
INSERT INTO "decisions" VALUES(1,'mvp-format-scope','Start with Markdown and simple text-layer PDF','Markdown and text-layer PDF are the MVP formats','superseded in part by 0016 (CSV and XLSX are read); amended by 0020 (the readers are stand-ins for connectors)','2026-10-28','> **Superseded in part** by [ADR 0016](0016-structured-facts-and-client-written-sql.md): CSV and XLSX are now read, with their tables. The rest of this record stands.

> **Amended** by [ADR 0020](0020-assume-the-environment-and-stand-in-for-it.md): the readers are stand-ins for the connectors that the brief says exist (C3), written to prove the chain, not extraction to be built.','Done. CSV and XLSX added by 0016. The readers are stand-ins (0020)');
INSERT INTO "decisions" VALUES(2,'independent-local-instances','Run independent instances with local data','Each tester runs an independent local instance','accepted','2026-10-28','','Done');
INSERT INTO "decisions" VALUES(3,'versioned-reader-selection','Select a tested reader for each format and version, and record it','Select and record a tested reader for each format and version','accepted, amended by 0020 (the readers are stand-ins for connectors)','2026-10-28','> **Amended** by [ADR 0020](0020-assume-the-environment-and-stand-in-for-it.md): the readers are stand-ins for the connectors that the brief says exist (C3), written to prove the chain, not extraction to be built.','Mostly done. Content detection, reader registry, reader version stored. No CAD reader');
INSERT INTO "decisions" VALUES(4,'persistent-evidence','Store extracted passages with their source version','Store extracted passages with their source version','accepted','2026-10-28','','Done');
INSERT INTO "decisions" VALUES(5,'coverage-and-reader-gaps','Report the files that cannot be read','Report files that cannot be read','accepted, amended by 0020 (the readers are stand-ins for connectors)','2026-10-28','> **Amended** by [ADR 0020](0020-assume-the-environment-and-stand-in-for-it.md): the readers are stand-ins for the connectors that the brief says exist (C3), written to prove the chain, not extraction to be built.','Done. Stored statuses and a coverage report for the index team');
INSERT INTO "decisions" VALUES(6,'permissions-before-results','Check permissions before answers, counts and pages','Check permissions before answers, counts and pages','superseded in part by 0017 (permissions apply inside the lookup, before the limit)','2026-10-28','> **Superseded in part** by [ADR 0017](0017-bind-answers-and-permit-before-the-limit.md): permissions now apply inside the index lookup, before the 1,000-passage limit, not after it. The rest of this record stands.','Done');
INSERT INTO "decisions" VALUES(7,'telemetry-and-audit','Measure from the start, and audit before evidence is released','Telemetry and an audit record before evidence is released','accepted','2026-10-28','','Done');
INSERT INTO "decisions" VALUES(8,'index-team-and-audit-viewer','Keep search users and the index team separate','Search users and the index team are separate roles','accepted','2026-10-28','','Done');
INSERT INTO "decisions" VALUES(9,'sqlite-fts5-index-and-answers','Use a SQLite FTS5 inverted index, and answer with exact text','SQLite FTS5 inverted index. Answers are exact text','accepted, amended by 0017 (bound list comparisons, signed numbers, list paging)','2026-10-28','> **Amended** by [ADR 0017](0017-bind-answers-and-permit-before-the-limit.md): list comparisons need a bound line, numbers keep their sign, and lists are paged. Filters over tables use SQL ([ADR 0016](0016-structured-facts-and-client-written-sql.md)).','Done');
INSERT INTO "decisions" VALUES(10,'path-based-access-rules','Index the whole repository, and control access with folder and file rules','Index the whole repository. Folder and file access rules','accepted','2026-10-28','','Done');
INSERT INTO "decisions" VALUES(11,'one-search-service','Put all search logic in one service, used by the web page and the chat agent','One search service for the web page, the API and the MCP server','accepted','2026-10-28','','Done');
INSERT INTO "decisions" VALUES(12,'mcp-server-for-the-chat-agent','Give the chat agent an MCP server over stdio, and accept an unverified user for the MVP only','A stdio MCP server is the chat-agent interface','superseded in part by 0016 (the tools) and 0018 (admission); stdio and the identity hole stand','2026-10-28','> **Superseded in part** by [ADR 0016](0016-structured-facts-and-client-written-sql.md) (five structured tools and a coverage tool for the index team) and [ADR 0018](0018-admission-control-and-the-time-budget.md) (admission control). The stdio transport and the identity hole stand.','Done. Verified with Claude Code, Codex and Pi. Identity is a known security hole');
INSERT INTO "decisions" VALUES(13,'no-answer-before-a-wrong-answer','Give no answer, or a partial answer, before a wrong answer','Give no answer before a wrong answer','superseded in part by 0017 (binding and the unverified status)','2026-10-28','> **Superseded in part** by [ADR 0017](0017-bind-answers-and-permit-before-the-limit.md): the question words are bound to the sentence, its heading, the file path or the title, not checked against the whole document, and a new status, `unverified`, marks an unbound value. The principle stands.','Done');
INSERT INTO "decisions" VALUES(14,'defer-facts-store-and-embeddings','Defer the facts store and embeddings until the questions and the data are known','Defer the facts store and embeddings','superseded in part by 0016','2026-10-28','> **Superseded in part** by [ADR 0016](0016-structured-facts-and-client-written-sql.md): typed facts from tables are built, and the MCP client writes constrained SQL over them. Embeddings and facts from prose stay deferred.','Embeddings and facts from prose still deferred');
INSERT INTO "decisions" VALUES(15,'acceptance-tests-enforce-the-use-case','Enforce the use case with acceptance tests on a public test repository','Acceptance tests enforce the use case on a public test repository','superseded in part by 0019 (evaluation); the acceptance tests stand','2026-10-28','> **Superseded in part** by [ADR 0019](0019-evaluate-retrieval-and-nl-to-sql.md): evaluation now covers retrieval, natural language to SQL and the agent''s reply. The acceptance tests stand; the test repository now has 148 files.','Done');
INSERT INTO "decisions" VALUES(16,'structured-facts-and-client-written-sql','Read tables into typed facts at index time, and let the MCP client write constrained SQL','Read tables into typed facts at index time. The MCP client writes constrained SQL','accepted','2026-10-29','Supersedes in part [ADR 0014](0014-defer-facts-store-and-embeddings.md): the facts store is no longer deferred for tables. Embeddings stay deferred. Extends the formats of [ADR 0001](0001-mvp-format-scope.md) with CSV and XLSX.','Done for CSV, XLSX and Markdown tables');
INSERT INTO "decisions" VALUES(17,'bind-answers-and-permit-before-the-limit','Bind each answer to its subject, and apply permissions before the retrieval limit','Bind each answer to its subject. Apply permissions before the retrieval limit','accepted','2026-10-29','Supersedes in part [ADR 0013](0013-no-answer-before-a-wrong-answer.md) (the whole-document word check) and [ADR 0006](0006-permissions-before-results.md) (permissions after the lookup). Amends [ADR 0009](0009-sqlite-fts5-index-and-answers.md) (list comparisons and paging).','Done');
INSERT INTO "decisions" VALUES(18,'admission-control-and-the-time-budget','Answer within the time budget or refuse at once, and record what does not scale','Answer within the time budget or refuse at once. Record what does not scale','accepted (MVP; the scaling work is open)','2026-10-29','','Admission control done. Scaling work not started');
INSERT INTO "decisions" VALUES(19,'evaluate-retrieval-and-nl-to-sql','Evaluate retrieval, natural-language-to-SQL and the agent''s reply, and gate releases on the results','Evaluate retrieval, natural language to SQL and the agent''s reply. Gate releases on them','accepted (partly implemented)','2026-10-29','Supersedes in part [ADR 0015](0015-acceptance-tests-enforce-the-use-case.md): its measurement part (17 questions, one script) is extended here. Its acceptance tests stay.','Partial. Retrieval evaluation and the SQL gold set. No live-client harness');
INSERT INTO "decisions" VALUES(20,'assume-the-environment-and-stand-in-for-it','Assume the environment in the brief exists, and use stand-ins only to prove the chain','The environment in the brief exists. The readers, folder, stores and chat clients in the MVP are stand-ins for it','accepted','2026-10-29','Amends [ADR 0001](0001-mvp-format-scope.md), [ADR 0003](0003-versioned-reader-selection.md) and [ADR 0005](0005-coverage-and-reader-gaps.md): their readers and their format scope describe stand-ins for the connectors, not extraction to be built.','Done in the documents. No code change');
INSERT INTO "decisions" VALUES(21,'design-records-in-one-database','Keep the brief, the constraints and the decision records in one SQLite database, and generate their pages from it','The brief, the constraints and the decision records live in one SQLite database. The pages are generated from it, and an MCP server reads it','accepted (to be evaluated after a few changes)','2026-10-29','','Done. Database, generator, check in the suite, read-only MCP server and a browser view');
CREATE TABLE sources (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  path TEXT,                     -- repository path, when the source is a file
  date TEXT
);
INSERT INTO "sources" VALUES('brief','The brief','docs/Starting_document.md',NULL);
INSERT INTO "sources" VALUES('mvp','A decision during the MVP',NULL,'2026-10-28');
INSERT INTO "sources" VALUES('inputs','The 29 October design inputs','docs/CODEX_ENGINEERING_SEARCH_HANDOFF.md','2026-10-29');
INSERT INTO "sources" VALUES('production','Required of a service for the whole organisation',NULL,NULL);
COMMIT;
