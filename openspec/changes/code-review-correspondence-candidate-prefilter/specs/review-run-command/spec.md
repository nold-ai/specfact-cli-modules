## ADDED Requirements

### Requirement: Necessary-condition candidate pruning

Candidate search SHALL skip full continuity evaluation only when existing source context, physical current-line uniqueness or exact three-line byte anchor equality rules out unchanged continuity. Final pair classification SHALL retain full continuity evidence and existing bounds.

#### Scenario: Distinct unique anchors reduce redundant work
- **WHEN** four findings with distinct unique anchors share an identity in identical 32-line sources
- **THEN** public classification computes four forbidden matrices and two shared matrices, preserving complete original results

#### Scenario: Whole classification and consumer preservation
- **WHEN** small fixtures exercise multiplicity, ordering, ambiguity, fallback, invalid anchors, byte boundaries, severity, identities, renames, missing sources and source bounds
- **THEN** complete public classification and representative actual range-consumer results equal immutable original literals

#### Scenario: Passing anchors still require optimal correspondence
- **WHEN** equal unique anchors have an alternate optimum or a forced cost above the global cost
- **THEN** full continuity determines the original unknown or introduced disposition

#### Scenario: Rejected search candidates retain final evidence
- **WHEN** no unchanged candidate qualifies and fallback pairs findings
- **THEN** final classification retains all original costs, reasons and digests, and suppression behavior remains unchanged
