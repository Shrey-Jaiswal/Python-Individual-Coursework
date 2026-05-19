# Architecture Decision Records (ADR)

This document provides a deep, professional trace of the core architectural and software design
decisions made during the development of the Digital Identity Control System (DICS). 

Each decision represents an evaluative trade-off analysis balancing security, performance,
maintainability, and compliance with the coursework specification.

---

## 1. Separation of Concerns: Domain Model Layer vs. Application Services Layer

### Context & Requirements
The application must govern critical business rules (e.g., role authorization, unique keys, valid
status transitions, and complex date-sequence checking for tax periods) and preserve absolute
traceability via audit logs. The interaction interface is a terminal CLI which must remain highly
responsive, clean, and completely isolated from backend modifications.

### Decision
We partition the core system into three strictly decoupled layers, following the Clean Architecture
and Domain-Driven Design (DDD) patterns:
1. **Domain Model Layer (`src/digital_id/domain`)**: House of pure enterprise business rules.
   Contains the `DigitalId` aggregate root, value objects (`Restriction`, `Status`), and status
   history lists. It holds no dependencies on external persistence libraries, input parsers, or
   audit logging files.
2. **Application Services Layer (`src/digital_id/services`)**: Business orchestrator boundary.
   Houses core services (`IdentityService`, `VerificationService`, `AuthorizationService`,
   `ValidationService`, `AuditLog`). Services check user roles, fetch records from repositories,
   invoke domain mutations, and trigger synchronous auditing.
3. **Interface / Adapter Layer (`src/digital_id/cli` & `src/digital_id/demo`)**: Thin boundary
   handling console box-drawing UI elements, terminal prompt loops, and scripted executions.

### Rationale & Design Trade-offs
Separating the Domain Model from Application Services guarantees that core business invariants are
physically isolated. The domain model focuses purely on *what* constitutes a valid identity state.
The services focus on *how* that identity is manipulated within the context of a transaction.
This prevents the presentation layer (CLI) from ever bypassing system policies, as every CLI
interaction must route through services that enforce authorization, parameter validation, and
audit side effects.

### Alternatives Considered & Rejected
- **Fat Domain Model (Active Record Pattern)**: We considered having `DigitalId` handle its own
  repository saving and log file writing. We rejected this because it violates the Single
  Responsibility Principle and makes the domain aggregate extremely difficult to isolate and test
  without mocking database connections and log files.
- **Fat Controllers (Transaction Script in CLI)**: We considered letting the CLI handle the
  orchestration. We rejected this because it leaks security policies and authorization checks into
  the presentation layer, risking bypass vulnerabilities and duplicating business logic between the
  interactive CLI and the scripted demo.

---

## 2. Integrity Protection: Defensive Copying at Repository Boundaries

### Context & Requirements
Repositories are responsible for the lifecycle retrieval and persistence of the `DigitalId`
aggregate. If a repository returns a direct reference to an object stored in its internal memory,
any calling layer (including the CLI) could directly modify the aggregate's attributes (e.g.,
writing to its address or status history list) without invoking the service layer.

### Decision
Both the `InMemoryRepository` and `JsonBackedRepository` are designed to return deep, defensive
copies of the `DigitalId` aggregate on every `get_by_id`, `get_by_national_id`, and `list_all`
operation (using Python's standard `copy.deepcopy`).

### Rationale & Design Trade-offs
By forcing repositories to return deep copies, we establish a strict barrier protecting the active
aggregate state. If calling code attempts to mutate attributes on a retrieved aggregate, those
mutations remain local to that thread's copy. To make the changes permanent in the database, the
caller must pass the modified aggregate or DTO explicitly back through the `IdentityService`
update boundaries, triggering:
1. Role-based authorization checks (RBAC).
2. Domain validation checks (immutable field blocks, valid status transitions).
3. Synchronous audit log records.

### Alternatives Considered & Rejected
- **Pass-by-Reference with Developer Discipline**: We rejected relying on code discipline to
  prevent unauthorized direct mutations. In high-assurance environments (like digital identity
  registers), system boundaries must be enforced programmatically rather than socially.
- **Fully Frozen Dataclasses**: We considered making all domain classes completely frozen
  (immutable). We rejected this because modeling legitimate lifecycle mutations (e.g., status
  changes and restriction additions) using copy-on-write models in standard Python introduces
  significant boilerplate and memory overhead, reducing codebase maintainability.

---

## 3. Persistence Flexibility: Adapter-Based Port & Adapter Pattern

### Context & Requirements
The specification demands a deterministic scripted demo (which must run instantly, cleanly, and
with zero disk write side effects to enable repeatable testing) and a fully functioning
persistent interactive menu (which must preserve registered identities across sessions).

### Decision
We implement the Repository Pattern using an abstract port interface (`DigitalIdRepository`) and
inject concrete adapters dynamically at application startup based on runtime arguments:
1. `InMemoryRepository`: A volatile, in-memory dictionary-backed store used for unit tests and the
   scripted demo.
2. `JsonBackedRepository`: A file-backed document store adapter that serializes identities to a
   specified JSON file upon transaction completion, ensuring persistence.

### Rationale & Design Trade-offs
Using dependency injection to swap repository adapters allows us to maintain a completely unified
service and domain layer. The core application logic does not know or care whether it is writing
to volatile memory or a disk-backed JSON database. This simplifies unit testing, keeps tests
blazing fast (no file I/O operations in tests), and guarantees a clean state on every demo execution.

### Alternatives Considered & Rejected
- **SQLite Database with SQLAlchemy ORM**: We considered using SQLite. We rejected this because a
  relational database introduces heavy external dependencies and database migration overhead. For a
  coursework submission, standard JSON serialization provides a highly readable, human-inspectable
  file format that simplifies marker assessment while perfectly fulfilling database durability.

---

## 4. Crash Resilience: Synchronous Audit Logging

### Context & Requirements
Coursework guidelines require strict traceability. Both successful actions and denied/unauthorized
actions must be recorded. If a system failure or power interruption occurs, the audit log must not
lose records of recent operations.

### Decision
The `AuditLog` service appends entries synchronously to its target JSON file immediately upon the
successful or rejected completion of any service transaction.

### Rationale & Design Trade-offs
Writing to the disk synchronously ensures that audit logging is completely crash-resilient. A
security event (like a denied access attempt or a terminal revocation) is guaranteed to be saved
to disk before the service method returns. While synchronous file operations introduce a minor I/O
bottleneck, the volume of transactions in a console-based control system is extremely small,
making safety and durability far more valuable than microsecond throughput optimizations.

### Alternatives Considered & Rejected
- **Asynchronous / Batch Logging**: We considered buffering audit logs in memory and flushing them
  to disk in batches or upon application shutdown. We rejected this because a sudden program crash,
  process termination, or unhandled exception would lose the most critical audit trails (e.g., the
  events leading up to the crash), undermining security accountability.

---

## 5. Information Hiding: Returning Read-Only DTOs (IdentitySnapshots)

### Context & Requirements
Exposing the mutable domain aggregate `DigitalId` to the CLI presentation layer leaks private domain
methods (like `change_status` or `update_mutable`) directly to the console boundary.

### Decision
The `IdentityService` completely hides the domain aggregate from the presentation layer. Service methods
like `create_identity`, `update_mutable`, and `list_identities` map internally-retrieved
aggregates into read-only `IdentitySnapshot` Data Transfer Objects (DTOs) before returning them to
the CLI.

### Rationale & Design Trade-offs
By using read-only snapshots, we achieve strict encapsulation and information hiding. The CLI holds
exactly what it needs to render tables and screens, and holds zero references or access to mutable
domain methods. This prevents presentation-layer bugs from ever directly corrupting database state.

### Alternatives Considered & Rejected
- **Exposing Domain Aggregates Directly**: We rejected this to maintain a clean architectural boundary
  between presentation elements and core domain objects, adhering to the principle of least privilege.

---

## 6. Privacy Protection: Data Minimization in Verification Results

### Context & Requirements
External organizations (e.g., banks checking job applicants, local authorities checking locality,
or tax authorities checking records) require identity verification. Returning a citizen's full
profile (Name, DOB, Address, Restrictions) leaks highly sensitive Personally Identifiable
Information (PII), violating standard privacy and compliance rules.

### Decision
The `VerificationService` never returns `IdentitySnapshot` DTOs or aggregates to calling verifiers.
Instead, it evaluates internal rules and returns a specialized, compact `VerificationResult`
containing:
1. `eligible`: A simple boolean flag (true/false).
2. `reason`: A short, high-level string explaining the classification (e.g., `"Active restriction
   'driving_suspension' prevents driving eligibility"`).

For the commercial Bank/Employer verifier, the system goes a step further: it enforces zero data
leakage by hiding even the specific reason string, returning *only* the boolean eligibility flag.

### Rationale & Design Trade-offs
This architecture implements **Data Minimization by Design**. Third parties receive the absolute
minimum amount of data necessary to satisfy their administrative check, keeping citizen PII entirely
secure within the central sovereign register.

### Alternatives Considered & Rejected
- **Exposing the Full Record**: We rejected allowing external organizations to fetch the full citizen
  record and perform their own eligibility checks. This leaks highly sensitive PII, creating severe
  security risks and violating modern privacy engineering best practices.

---

## 7. Operational Safety: Deterministic Lifecycle Transitions and Safe No-Ops

### Context & Requirements
Handling repetitive administration commands or mutations on revoked records requires consistent,
predictable outcomes without triggering system crashes.

### Decision
1. **Irreversible Revocation**: Once an identity's status is set to `REVOKED`, it enters a terminal
   state. Any subsequent attempt to reactivate the account, update its attributes, or add a
   restriction immediately throws a dedicated domain exception.
2. **Safe Idempotent No-Ops**: Attempting to transition an identity to its current status (e.g.,
   suspending an already suspended account) does not throw errors. The system logs the attempt as a
   no-op and returns gracefully.

### Rationale & Design Trade-offs
A revoked account represents a permanently retired or compromised credential. Blocking all future
mutations guarantees that revoked identities cannot be retroactively manipulated or reactivated,
securing the integrity of the register. Handling repetitive status changes as safe no-ops
simplifies interface code, eliminating complex pre-checks and preventing race conditions.

### Alternatives Considered & Rejected
- **Throwing Errors on Repetitive Status Changes**: We rejected throwing exceptions for duplicate
  states because it forces CLI or client layers into fragile "check-before-act" patterns that are
  vulnerable to race conditions in multi-user environments.
