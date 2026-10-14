## Scoped implementation
- [x] Read approved design, scope and repository rules.
- [x] Create independent spec before tests/source.
- [x] Freeze original output and provenance literals.
- [x] Capture actual forbidden-build assertion RED (10 versus 4).
- [x] Add minimal predicate and candidate-search guard.
- [x] Run focused tests and available source quality gates; record existing lint failures without claiming PASS.
- [ ] Independent patch review (root-owned).
- [ ] Full mandatory repository/native gates and trusted signing (root-owned).

Throughput checkpoint: one writer, no parallel mutations, <=30-second capture, <=256 cases with <=32 lines/8 findings except explicitly cheap bound checks. Tasks here replace an out-of-scope todo file. Prior independent design review is supplied; further fan-out is root-owned. No Git mutation, installation, signing or CI dispatch belongs to this worker.

- [x] Correct sibling test import after review; verify 227 tests under normal parallel and serial importlib configuration, preserving frozen fixtures and original production RED.
- [ ] Independent affected-scope closure of import correction (root-owned).
