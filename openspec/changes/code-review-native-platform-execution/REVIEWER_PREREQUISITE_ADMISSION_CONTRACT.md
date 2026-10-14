# Reviewer prerequisite admission contract

Human authorization on 2026-10-14 (Europe/Berlin), relayed by the coordinating
agent, permits CI activation of the reviewed frozen signed reviewer 0.51.5 from
commit `a785ef4da8ea74f67f8ffa41f458c025cbfba4b1`. It does not authorize release
or publication. Existing deadlines, blocking gates and review prerequisites remain.

The user outcome is to let the existing CI review workflow install that frozen
reviewer through the already reviewed bootstrap and ordinary installer. Reuse the
existing complete parsed workflow comparison and its two observer exceptions.
The smallest adaptation admits only the two complete installation run bodies
below. Retaining the unmodified checker rejects the approved transition; custom
admission infrastructure would add maintenance without improving this outcome.

## Exact admission boundary

Only `jobs.independent-review.steps`, at the uniquely named step
`Install trusted reviewer in its own ordinary-user environment`, receives the
installation-body admission. Its position and every non-run metadata field must
match the integrated baseline. Both candidate and baseline raw UTF-8 run bodies
must match an approved SHA-256, including when their bytes equal each other.
Normalize only that candidate run to the baseline run after validation. The
existing complete workflow comparison then rejects other execution changes.

| Inert fixture | Complete run SHA-256 |
| --- | --- |
| `REVIEWER_INSTALL_OLD.txt` | `fcdf9ce7746ec559c420f96205487508a16c0445576e06775bb2deca3f6f2b98` |
| `REVIEWER_INSTALL_NEW.txt` | `ceab0c17724c56da6cb89f634eb94d39f66e54bc993fd3973e6a5aa74c08c434` |

These 0644 text fixtures are data for the canonical host proof, never programs
invoked by CI. OLD preserves the exact current workflow body at preparation;
NEW preserves the independently reviewed bootstrap proposal body. Exact OLD/OLD,
NEW/OLD activation, OLD/NEW rollback and NEW/NEW merged-baseline admission are
required. Unknown bodies must fail even on both identical sides. Renamed, moved,
duplicated or reassigned steps and modified metadata fail. The two existing
observer exceptions, budget adaptation, parser, caller and surrounding workflow
authority remain unchanged. No prefix, path or partial-body allowance is added.

## Frozen trust and installation evidence

The reviewed source tree is `9cc469a6a4a0cc74bed564e315eadd58e0b57020`.
The signed reviewer payload is
`5c538655ddd1e24977b41a979d6b01fbbdac0b4f3bfe7ceb6fc3b5c1bfd9041f`.
Bootstrap source SHA-256 is
`59dc43177e31a9f5e4e9b40b30d3246c8b8caa29c8cbb73ed4c98eb65da25c2a`.
Trust uses core 0.55.4 and bundled public-key SHA-256
`4e54ffb02307e1a85c166c40aba6d1bc40fbb9a8ef40bf756f8870e5bb08d1c8`.
Dependencies bind to baseline `209b4ed835187ea857d1fa847abdd351f6f6232a`.
Strict signature verification must precede installation and remain strict after
installation. The reviewed bootstrap checks all 117 installed source inventory
entries for bytes and Git-derived 0644/0755 modes. This contract preserves that
reviewed identity; the checker proof does not independently prove installation.

## Acceptance, limits and rollback

The canonical host proof imports the actual checker and parses the actual complete
current workflow with its duplicate-rejecting YAML loader. It substitutes only
Git workflow-document selection while exercising the real reusable-review
validator. Golden bodies must have the exact hashes above and normalized complete
workflows must differ only in the install run. Preserve all existing proof cases
and all 68 reviewed semantic validator calls across five new test methods.

Sequence is contract, tests, recorded RED against the old canonical checker,
then independently reviewed checker implementation and GREEN. Report activation
and rollback failures separately from unknown-equals-unknown guard failures.
No workflow shell body executes in this proof. A passing matrix does not establish
Linux execution, signing, publication or independent installed acceptance.

Failure modes are drifted bytes, expanded step metadata, and surrounding authority
changes. Exact hashes, identity/metadata validation and complete workflow equality
respectively reject them. Rollback uses the preserved exact OLD body. This bounded
local proof adds no paid service operation; full ordinary gates and exact-head CI
remain separate obligations owned by the coordinating task. Confidence is high for
the specified comparison behavior, conditional on unchanged frozen identities.

## Approved quality follow-up (2026-10-14, Europe/Berlin)

The public nesting gate rejects the newly appended admission test loops. Flatten
only these five methods into pytest-parameterized cases: one fixture identity,
four exact transitions, eight unknown-body/baseline combinations, 22 metadata
combinations and 18 surrounding-workflow combinations. These 53 pytest items
preserve all 68 actual validator calls, including candidate-only, baseline-only
and identical unknown bodies. Preserve every fixture identity and mutation,
reader-only substitution, and all 43 pre-existing proof definitions. The checker,
workflow, gates and signed assets remain unchanged. Acceptance requires recorded
public Radon, AST clean-code and AI-bloat RED/GREEN evidence with no new findings,
the focused proof, and an actual-validator call profile totaling 68.

The fixture ownership correction places the exact 0644 golden bodies at
`tests/support/reviewer_prerequisite/REVIEWER_INSTALL_OLD.txt` and
`tests/support/reviewer_prerequisite/REVIEWER_INSTALL_NEW.txt`. The proof reads
these stable paths so archiving this OpenSpec change cannot remove its fixtures.
The hashes and all acceptance behavior above remain the same.
