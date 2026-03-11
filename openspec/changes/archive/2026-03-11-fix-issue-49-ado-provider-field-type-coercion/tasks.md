## 1. OpenSpec Change Setup

- [x] 1.1 Create change folder linked to issue #49
- [x] 1.2 Add proposal/design/spec delta for typed ADO mapped provider fields

## 2. Failing Coverage

- [x] 2.1 Add regression tests proving typed metadata persistence in `map-fields`
- [x] 2.2 Add regression tests proving `backlog add` coerces typed mapped provider fields and rejects invalid values

## 3. Implementation

- [x] 3.1 Persist required-field type metadata from `map-fields`
- [x] 3.2 Apply type-aware conversion in ADO provider field resolution for `backlog add`
- [x] 3.3 Keep existing required-field and override behavior intact

## 4. Validation

- [x] 4.1 Run required gates and record evidence in `TDD_EVIDENCE.md`
