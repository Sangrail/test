# From local uploads to hundreds of thousands of documents

Document count alone does not establish a need for distributed storage. Measure total bytes, passage count, extraction cost, arrival rate, query load and required recovery time. Folder layout can partition discovery; it should not dictate one independent search index per folder. Use one logical search service that can shard internally as capacity requires.

```mermaid
flowchart LR
    Upload["Upload API"] --> Store["Shared source storage<br/>Immutable document versions"]
    Existing["Existing folders or repositories"] --> Discover["Partitioned discovery / change feed"]
    Discover --> Manifest["Document manifest<br/>Document ID, location, version, state"]
    Store --> Manifest
    Manifest --> Queue["Durable work queue<br/>Document ID + version + storage URI"]
    Queue --> W1["Indexer 1"]
    Queue --> W2["Indexer 2"]
    Queue --> WN["Indexer N"]
    Store --> W1
    Store --> W2
    Store --> WN
    W1 --> Search["One logical search service<br/>Batched, version-aware writes"]
    W2 --> Search
    WN --> Search
    Search --> Ready["Confirm search visibility<br/>Mark version ready; acknowledge job"]
    Ready --> Manifest
    Manifest --> Dashboard["Dashboard<br/>Uploading, queued, indexing, ready, failed"]
    Queue --> Dashboard
```

## The MVP today

The MVP runs on one machine: one web process (plus one MCP process for each chat client), SQLite files, a local upload queue with worker threads, one lock and one SQLite connection in each process, and a file lock that lets one process at a time publish index changes. [ARCHITECTURE.md](../ARCHITECTURE.md#mvp-shortcuts-in-the-code) lists these shortcuts.

**Measured concurrency (29 October 2026, 148 files, one process).** One process answers about 10 requests a second, whatever the load: with 1,000 simultaneous requests the last waited 102 s. Admission control now answers each request within the 8 s budget or refuses it at once with 503 and a retry time; at 1,000 simultaneous requests about 47 are answered and the rest are told to retry within 0.25 s. The constrained SQL path copies every permitted fact into memory for each request (about 3 µs a fact, 3 s at a million facts), and its step budget stops queries above about 200,000 facts. [ADR 0018](../docs/adr/0018-admission-control-and-the-time-budget.md) gives the numbers and the order of work: concurrent reads, several worker processes, SQL without a copy per request, a server search engine, and load tests in CI. It has not been tested with hundreds of thousands of files. [docs/README.md](../docs/README.md#making-it-available-to-an-organisation) explains what high availability for the organisation needs: a stateless query tier, a replicated store with failover, permissions in the store, a separate indexing pipeline, quotas, SLOs and load tests in CI.

## Changes required for multiple machines

1. **Shared sources and a persistent manifest.** Workers need a resolvable source URI. Object storage or an existing shared repository is generally simpler than copying all files to every machine. If files remain on different hosts, run discovery agents there and enqueue accessible versioned references. Separate upload progress from saved/validated content and index visibility. Use a transactional outbox (or equivalent reconciliation) to close the gap between a committed document version and a queued message.
2. **A shared broker with leases.** A worker claims a job, renews its lease while working, and acknowledges after the result is safely committed. Expired claims become available again. Treat delivery as at least once; duplicate processing remains possible, so writes must be idempotent. AWS's [visibility timeout documentation](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-visibility-timeout.html) describes this lease/redelivery model. The local SQLite startup recovery is not a distributed lease mechanism.
3. **Idempotency and ordering.** Identify work by document ID, source version and extractor version. Reject an older version if a newer version has already been indexed. Represent deletion as a versioned tombstone so a late worker cannot resurrect removed content. The MVP avoids overwrite conflicts by assigning each upload a new identity; replacing an existing uploaded document is a separate future operation.
4. **One logical, persistent search index.** Scale extraction workers separately from search shards. Batch index writes, watch backpressure and keep commits atomic per document version. An accepted write is not always searchable immediately: Elasticsearch's [refresh documentation](https://www.elastic.co/docs/reference/elasticsearch/rest-apis/refresh-parameter) distinguishes those states and supports waiting for visibility. Only then advertise the version as ready. Adding workers does not help if storage, the broker or index commits are the bottleneck.
5. **Incremental discovery and paginated operations.** Partition a large initial crawl by stable directory ranges or hashed document IDs. Stream jobs instead of loading the corpus at once. Use change notifications plus periodic reconciliation, enqueue only changed versions, and paginate the inventory server-side. Folder boundaries are discovery partitions, not exclusive ownership of documents by long-lived workers.
6. **Operational controls.** Use bounded retries with backoff for transient failures, a dead-letter state for persistent failures, upload quotas and admission control. Show total state counts, oldest job age, queue-wait and upload-to-searchable p50/p95/p99, worker utilisation, files/bytes/passages per second, failures, retries and query latency under ingestion load. A stopped or failed worker must not remain indefinitely active on the dashboard.
7. **Security before shared deployment.** Replace selectable demo identities with authoritative identity verification and the mock permissions database with the existing permissions service. Keep the enforced file checks, backend-role boundary and protected decision audit. Preserve permissions and source versions through every queue stage. Never expose forbidden candidate IDs through consumer search, the dashboard or audit-reading APIs.

## Capacity experiment

Benchmark representative file sizes and tables with 1, 2, 4 and 8 workers. Measure both initial backfill and steady arrivals while representative searches run. A rough starting point for extraction capacity is `workers × measured documents/second/worker`, reduced for shared-storage and index contention. To avoid an ever-growing backlog, sustained completion rate must exceed arrival rate. Scale based on queue age and target upload-to-searchable latency, not merely folder count. The ten-second search target remains separate from indexing freshness.
