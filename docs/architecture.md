# System architecture and data flow

Status: Week 1 proposal, 2026-11-06. Baseline: upstream main at `8abd5ec`.

## Existing components

The repository has specification scrapers, retailer specification CSVs, PostgreSQL migrations and a migration runner. Daily price CSVs are produced externally. The [FastAPI backend](../Database%20%26%20Backend%20Development%20Team/backend/API.md) reads PostgreSQL. Its demo loader uses Pozitif, Samsung and Beymen price files and specification CSVs. Production ingestion, matching-team output integration and the frontend remain future work.

## Proposed boundaries

The integration stages below are responsibilities to agree, not new implemented services. They may eventually run in one process; this diagram does not prescribe microservices, frameworks, queues or hosting.

```mermaid
flowchart LR
    subgraph External["External sources"]
        D["Inflation study daily price CSVs"]
        R["Retailer APIs and pages"]
    end
    subgraph Existing["Existing repository components"]
        S["Specification scrapers"]
        C["Retailer specification CSVs"]
        M["SQL migrations and runner"]
        DB[("PostgreSQL schema")]
        L["Electronics demo loader"]
        A["FastAPI v1 read API"]
    end
    subgraph Future["Proposed / future integration"]
        V["Validate and normalize"]
        J["Resolve retailer listing"]
        Q["Rejected or ambiguous records with reasons"]
        P["Canonical product assignment: matching-team boundary"]
        I["Transactional repeatable import"]
        F["Frontend"]
    end
    R --> S
    D -->|"Beymen reads existing names"| S
    S --> C
    D -.-> V
    C -.-> V
    V --> J
    V --> Q
    J -->|"Missing or ambiguous"| Q
    J -->|"Resolved"| P
    P -->|"Approved assignment"| I
    D --> L
    C --> L
    L --> DB
    M --> DB
    I --> DB
    DB --> A
    A -.-> F
```

Solid connections inside the existing group describe available component relationships; all connections involving future components are proposed. The schema exists as SQL; this does not assert a deployed database.

The demo loader groups listings using model code and condition as a baseline. It covers three electronics retailers and does not establish a production import or an approved matching policy.

## Proposed end-to-end sequence

```mermaid
sequenceDiagram
    participant Source as Daily prices and specifications
    participant Integration as Future integration layer
    participant Matching as Future matching boundary
    participant DB as PostgreSQL
    participant API as Existing FastAPI v1
    participant User as Future frontend
    Source->>Integration: Source records and observation dates
    Integration->>Integration: Validate fields, identifiers, prices and currency
    Integration->>Integration: Join by retailer ID or unique grocery name
    alt Invalid, missing or ambiguous
        Integration->>Integration: Record reason and retain provenance
    else Resolved listing
        Integration->>Matching: Request canonical product assignment
        Matching-->>Integration: Assignment or unresolved result
        opt Assignment approved under agreed contract
            Integration->>DB: Transactional offer and history write
            Note over Integration,DB: Deduplication and stale-update policy require team agreement
            DB-->>Integration: Commit result
        end
    end
    User->>API: Search, comparison or history request
    API->>DB: Query comparable products and offers
    DB-->>API: Results
    API-->>User: Offers, history and freshness
```

## Existing database relationships

```mermaid
erDiagram
    categories o|--o{ categories : parent
    categories ||--o{ products : contains
    brands o|--o{ products : labels
    products ||--o{ offers : has
    retailers ||--o{ offers : publishes
    offers ||--o{ price_history : records
```

The schema also has `schema_migrations`. Category self-parenting is prohibited, but longer cycles are not prevented by that check.

## Ownership boundaries to confirm

Data collection owns source extraction and source-format documentation; matching owns canonical product and hierarchy decisions; database/backend owns persistence and API contracts; system integration coordinates contracts, environment setup, test evidence and deployment planning. These are proposed responsibility boundaries, not assignments of unapproved work.

See [open decisions](integration-contract.md). The existing API is available for future frontend integration. The diagram's write path describes proposed production ingestion.
