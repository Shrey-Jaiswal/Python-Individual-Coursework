# Architecture Decisions

This document outlines the core architectural and design decisions made for the Digital ID lifecycle management system, focusing on the trade-offs considered and the rationale behind the chosen approaches to satisfy the strict requirements of robustness, security, and traceability.

## 1. Application Services Own Business Workflows

**Decision:** The application is split into a Domain Model layer (handling core invariants like immutable identity attributes, valid status transitions, and restriction date validations) and an Application Services layer (owning use-case workflows like creation, updates, authorization, and audit recording).

**Rationale:** This strict separation of concerns keeps the console/CLI layer extremely thin, ensuring that presentation logic cannot accidentally bypass business rules or authorization checks. 

**Alternative Considered:** Fat Domain Models (where the domain object itself handles saving to the repository and writing to the audit log) or Fat Controllers (where the CLI handles orchestration). We rejected these because they tightly couple persistence and side-effects with core logic, making the system harder to test deterministically and violating the Single Responsibility Principle.

## 2. Repositories Return Defensive Copies to Protect Aggregate State

**Decision:** Repositories are designed to return deep or defensive copies of the `DigitalId` aggregate root, rather than returning references to the stored instances.

**Rationale:** If a repository returns a reference to the mutable object stored in memory, calling code could theoretically mutate the `DigitalId` state directly without going through the Application Services. By returning copies, we enforce that all state mutations must be pushed back through the `IdentityService` using proper update methods. This guarantees that authorization checks and audit logging cannot be bypassed.

**Alternative Considered:** Relying on developer discipline to not mutate returned aggregates, or using frozen dataclasses for the entire aggregate. We rejected the frozen approach as it makes legitimate mutations overly complex, and rejected developer discipline as inadequate for a high-security context like Digital ID management.

## 3. Runtime Persistence is Adapter-Based

**Decision:** The persistence layer is abstracted behind a Repository interface, with two implementations: `InMemoryRepository` and `JsonBackedRepository`. The CLI dynamically selects the adapter based on startup flags.

**Rationale:** The coursework requirements stipulate both a deterministically testable scripted demo (which needs clean state) and persistent functionality. By injecting an in-memory repository for tests and scripted demos, we guarantee fast, repeatable runs without file I/O side effects. The JSON adapter is used for persistent interactive runs.

**Alternative Considered:** Using an ORM and a SQLite database. We rejected this because a relational database introduces unnecessary external dependencies for a coursework submission that can be adequately modeled using JSON, and an ORM would over-complicate the simple document-like structure of the `DigitalId` aggregate.

## 4. Audit Logging is Durable When Configured

**Decision:** The `AuditLog` acts as an injected dependency that can either store records in memory or append them to a JSON file immediately upon action completion.

**Rationale:** The requirement for strict traceability means that both successful and denied operations must be recorded reliably. Writing to the file synchronously upon the completion of a service operation ensures that audit trails are preserved even if the application crashes.

**Alternative Considered:** Batch writing the audit log at the end of the application run. This was rejected because a system crash or unexpected exit would result in the loss of critical security events (like denied authorization attempts).

## 5. Services Return Immutable DTOs (IdentitySnapshots)

**Decision:** Instead of returning the full `DigitalId` domain aggregate to the CLI or calling services, the `IdentityService` explicitly constructs and returns immutable `IdentitySnapshot` Data Transfer Objects (DTOs).

**Rationale:** Returning the domain aggregate exposes mutable methods (like `change_status`) to the presentation layer. By mapping the aggregate to a read-only snapshot, we implement strict Information Hiding. The CLI receives exactly what it needs to render output, and absolutely nothing more.

**Alternative Considered:** Returning the Domain Aggregate and trusting the presentation layer to treat it as read-only. This was rejected because it violates the principle of least privilege.

## 6. Verification Services Expose Limited Results

**Decision:** Consuming organizations (e.g., banks, local authorities) submit only a `digital_id` and receive a simplified `VerificationResult` containing a boolean `eligible` flag and an optional reason string. The verification service never returns the `IdentitySnapshot`.

**Rationale:** This decision aligns with the principle of data minimization and the specific scenario requirements. A bank checking employment validity only needs to know if the ID is active; they do not need the citizen's date of birth or address.

**Alternative Considered:** Returning the full `IdentitySnapshot` and allowing the consuming organization to write their own eligibility checks. This was rejected because it leaks PII (Personally Identifiable Information) to organizations that do not have the authorization to view it, violating core security requirements.

## 7. Deterministic Conflict Handling and Terminal States

**Decision:** Repeated operations (like setting the status to ACTIVE when it is already ACTIVE) are treated as deterministic no-ops. Revocation is modeled as a strict terminal state where any subsequent mutation throws an exception.

**Rationale:** Deterministic no-ops simplify the client code, as they do not need to pre-check status before requesting a change. Strict terminal states ensure that compromised or permanently invalidated identities cannot be surreptitiously reactivated or modified, protecting system integrity.

**Alternative Considered:** Throwing errors on repeated operations (e.g., throwing an error if trying to suspend an already suspended account). This was rejected as it forces the client into a "check-then-act" pattern, which is prone to race conditions in concurrent environments.
