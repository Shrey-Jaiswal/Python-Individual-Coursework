# Architecture Decisions

## 1. Services own business workflows
Domain objects hold core invariants such as immutable identity attributes, restriction
validity, and status transition rules. Application services own use-case workflows such as
creation, updates, status changes, restriction management, verification, authorisation, and
audit recording. This keeps the console layer thin and prevents callers from bypassing
business rules.

## 2. Repositories protect aggregate state
Repositories return defensive copies of `DigitalId` aggregates. Service methods update and
save a copy through the repository, so external callers cannot mutate stored identity state
without passing through validation, authorisation, and audit logging.

## 3. Runtime persistence is adapter-based
The repository interface is implemented by both an in-memory adapter and a JSON-backed
adapter. The scripted demo uses in-memory storage so it stays deterministic and repeatable.
The interactive runtime can use `JsonBackedRepository` through `--store-path`, which reloads
existing identities and persists every mutation.

## 4. Audit logging is durable when configured
`AuditLog` can run in memory for deterministic tests and scripted demos, or with a file path
for runtime use. When configured with a path, it reloads existing entries and persists every
new successful, failed, or denied action immediately.

## 5. Services return DTOs, not mutable aggregates
Identity management methods return immutable `IdentitySnapshot` records rather than
`DigitalId` aggregates. This gives the console and tests enough information to display
outcomes while keeping mutable domain objects behind the service boundary.

## 6. Verification exposes limited results
Consuming organisations submit only a `digital_id` and receive a `VerificationResult`.
Verification services resolve the identity internally and do not return identity attributes
to banks or employers, matching the scenario requirement for controlled information use.

## 7. Deterministic conflict handling
Repeated status changes to the current status are explicit no-ops. Revoked identities are
terminal, and updates or restriction changes after revocation are rejected and audited.
