# Architecture decisions

This document records the core design decisions made for the Digital ID register, focusing on
trade-offs, security, and traceability rules.

---

## 1. Domain model separate from application services

### Context
The application must handle complex rules like role permissions, unique citizen keys, status
lifecycles, and tax period date logic, while logging all events. The CLI needs to stay clean and
independent of backend adjustments.

### Decision
The system is split into three layers:
1. Domain model (`src/digital_id/domain`): Contains pure business entities (`DigitalId` aggregate,
   `Restriction`, `Status`) and internal validators. It does not depend on database adapters or
   logging frameworks.
2. Application services (`src/digital_id/services`): Coordinates workflows (`IdentityService`,
   `VerificationService`, `AuditLog`). Services check user roles, fetch records from storage, and
   trigger logging.
3. CLI presentation layer (`src/digital_id/cli` & `src/digital_id/demo`): Handles terminal prompts,
   box drawing, and automated runs.

### Rationale
Separating the domain layer ensures that business rules are isolated. The domain model focuses
solely on what makes an identity state valid, while services manage how records change during a
transaction. This structure prevents the presentation layer from bypassing system checks, since
every command must go through services that enforce authorization and validation.

### Alternatives
- Fat Domain Model: An alternative was making the `DigitalId` entity write to the database and logs
  directly. This was rejected because it makes testing the domain model difficult without setting
  up mock databases and log files.
- Fat CLI: The orchestration logic could have been placed directly in the CLI. This was rejected
  because it leaks security policies into the UI, making it hard to share logic between the
  interactive menu and the scripted demo.

---

## 2. Defensive copying at repository boundaries

### Context
Repositories load and save the `DigitalId` aggregate. If the repository returns a direct reference
to a stored object, calling code could change attributes (like the status history or location)
directly in memory, bypassing the service checks.

### Decision
Both `InMemoryRepository` and `JsonBackedRepository` return deep copies of the `DigitalId` aggregate
on every retrieve and list operation (using Python's `copy.deepcopy`).

### Rationale
Defensive copying keeps the stored state safe. If calling code edits a retrieved record, the change
remains local. To make the change permanent, the caller must pass the modified aggregate or DTO
back through the `IdentityService` update methods, which triggers permission checks, validation
rules, and audit logs.

### Alternatives
- Relying on developer discipline: This was rejected. In security systems, state boundaries must be
  enforced by the code, not by guidelines.
- Frozen domain objects: The option of making all domain classes immutable was considered but rejected
  because writing copy-on-write modifications for every small field edit in Python creates a lot
  of repetitive code, which makes the codebase harder to maintain.

---

## 3. Storage abstraction with pluggable adapters

### Context
The system needs a deterministic scripted demo (which must run fast and leave no file side effects for
easy testing) and a durable interactive menu (which must save records across runs).

### Decision
A repository interface (`DigitalIdRepository`) is used, and the storage adapter is injected at startup
based on CLI arguments:
1. `InMemoryRepository`: A volatile dictionary store used for tests and the scripted demo.
2. `JsonBackedRepository`: A file store that serializes records to a JSON file on every update.

### Rationale
Injecting repository adapters allows using the exact same service and domain code for both modes.
The core logic does not need to know how or where the data is stored, which keeps tests fast and
isolated.

### Alternatives
- SQLite and SQLAlchemy ORM: Using a local SQLite database was considered but rejected because a
  relational database introduces external dependencies and migration scripts. For a coursework
  project, JSON serialization is simple to read, easy for markers to inspect on disk, and fully
  handles database persistence.

---

## 4. Synchronous audit logs

### Context
The system must log all operations, including successful edits and unauthorized/denied checks. If
the system crashes, no recent security logs should be lost.

### Decision
The `AuditLog` service appends entries to the target JSON file synchronously before a service transaction
completes and returns.

### Rationale
Synchronous file updates make the audit trail crash resilient. A security event (like a blocked
access attempt) is saved to disk before the method returns. Although synchronous file writing is a
minor performance bottleneck, the interactive console volume is very low, making data safety far
more important than raw I/O speed.

### Alternatives
- Asynchronous batching: Buffering logs in memory and writing them to disk periodically was considered.
  This was rejected because an unexpected crash or process exit would lose the last security events,
  which ruins system audit accountability.

---

## 5. Read-only DTO snapshots for presentation

### Context
Exposing the mutable domain aggregate `DigitalId` to the CLI leaks internal mutating methods (like
`change_status` or `update_mutable`) directly to the presentation code.

### Decision
The `IdentityService` never returns domain aggregates to the presentation layer. Instead, it maps
records to read-only `IdentitySnapshot` DTOs before returning them.

### Rationale
Using read-only DTOs protects the domain layer. The CLI receives exactly the values it needs to
render tables and inputs, but holds no references to mutating domain methods, preventing UI bugs
from corrupting database records.

### Alternatives
- Returning aggregates directly: This option was rejected to maintain a clean boundary between UI display logic
  and core state mutation.

---

## 6. Minimal verification responses for privacy

### Context
External organizations need to verify citizen status. However, returning a full profile (Name, DOB,
address, restrictions) leaks private information, violating privacy requirements.

### Decision
The `VerificationService` never returns aggregates or snapshots to external checkers. Instead, it
evaluates business rules internally and returns a simple `VerificationResult` containing:
1. `eligible`: A true-or-false flag.
2. `reason`: A short, non-detailed explanation (for example, `"Active restriction blocks driving"`).

For the commercial Bank/Employer verifier, the service hides the reason string entirely, returning
only the boolean eligibility flag.

### Rationale
This architecture implements data minimization. Third parties get only the yes-or-no answer they need,
keeping personal information safe inside the central registry.

### Alternatives
- Exposing the full record: Allowing external services to retrieve full profiles was rejected.
  It creates unnecessary security risks and leaks personal data to unauthorized parties.

---

## 7. Irreversible revocation and idempotent status changes

### Context
The system must handle repetitive status changes and modifications to terminated profiles in a safe,
predictable way without crashing the system.

### Decision
1. Irreversible revocation: Once an identity is set to `REVOKED`, it is locked. Any attempt to
   reactivate the record, edit its profile, or add restrictions throws a domain exception.
2. Safe no-ops: Attempting to set an identity status to its current status (such as active to
   active) is handled as a safe no-op. The system logs the attempt and returns successfully.

### Rationale
A revoked account represents a permanently compromised or retired credential. Locking it permanently
guarantees that revoked records cannot be manipulated. Handling duplicate status changes as safe
no-ops simplifies the client code, removing the need for pre-checks and preventing race conditions.

### Alternatives
- Throwing exceptions on duplicate status changes: This was rejected because it forces the caller
  to use fragile "check-then-act" patterns that are prone to errors in concurrent environments.
