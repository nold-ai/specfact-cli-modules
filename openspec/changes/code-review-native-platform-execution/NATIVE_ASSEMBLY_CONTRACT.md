# Native macOS capsule assembly contract

## Purpose

`scripts/assemble_macos_native_capsule.py` is a maintainer-only, copy-only
boundary between already validated Darwin/ARM64 inputs and the immutable root
consumed by `build_macos_native_capsule.py`. It does not compile, sign,
download, execute, or repair an input. Customer machines never run it.
The documented CLI locates its repository modules from the script's own path,
independently of the working directory or a supplied PYTHONPATH.

## Inputs

The analyzer input is the parent of `payload/` and `candidate.json` produced by
the native analyzer preparation. Assembly requires a supported CPython 3.11,
3.12, or 3.13 ABI, an exact complete file/directory inventory, Darwin/ARM64
platform evidence, matching native-image and signed-image inventories, trusted
worker bytes, and observed ad-hoc hardened-runtime ARM64 signatures.

The native component input contains only `component.json`, the three declared
broker/bootstrap/self-test binaries, and `policy/profile.sb`. Its hashes,
platform, protocol, bounded plan IDs, and ad-hoc hardened-runtime signing mode
must match the observed files. Generated build intermediates are undeclared and
therefore rejected; release assembly uses a staged component export.

Both trees must be canonical ordinary directories. Symlinks, special files,
case-insensitive aliases, missing files, extra files, modified digests, partial
components, incompatible ABIs, and architecture/signature mismatches fail
closed.

## Output

Concurrent assemblies must never delete another invocation's runtime or closure.
Failure cleanup removes only output identities created by the failing invocation;
an output appearing after the initial absence check remains owned by its creator.

Assembly creates a fresh mode-0700 runtime root atomically. It streams regular
files through no-follow descriptors into exclusive destinations and verifies
their digests after copying. It preserves native signatures because it copies
image bytes and never invokes signing tools.

The fixed layout includes:

- `python/bin/python3` for the selected ABI interpreter;
- `bin/specfact-native-{broker,bootstrap,self-test}`;
- `policy/profile.sb`;
- the complete analyzer, Node, fixture, manager, wheelhouse, Python library,
  and site-package closure below `python/`;
- analyzer packages and trusted `specfact_code_review` sources under
  `python/lib/pythonX.Y/site-packages`, including fixed
  `specfact_code_review.run.native_worker`,
  `specfact_code_review.run.native_tool_worker` and
  `specfact_code_review.run.native_project_manager` bindings;
- generated, host-path-free provenance below `provenance/`; and
- a digest inventory of included license bytes below `licenses/`.

The external `<runtime>.closure.json` assigns every output file to exactly one
non-empty builder closure component. It is canonical JSON accepted by the
artifact builder's closure validator. Output remains candidate-only until the
subsequent artifact, acquisition, boundary, analyzer, project, and customer
installation gates pass.

The broker executes fixed capsule CPython with `-I -m` and one closed trusted
runtime module selected by its plan. CPython therefore ignores `PYTHONHOME`,
`PYTHONPATH`, user site packages, and startup overrides while retaining the
relocated standard `site` initialization that admits only the capsule's
`python/lib/pythonX.Y/site-packages`. The assembler models that closed getpath
without launching unsigned input and requires the fixed worker to resolve from
exactly one modeled capsule path.

## Current real-input integration finding

The existing CPython 3.12 analyzer candidate predates
`specfact_code_review.run.native_worker`, the managed tool and project-manager
workers, and the sealed manager directory, so
the complete assembly input check rejects it before copying. It must be
regenerated from the current trusted package and manager closure.

An independent path-profile scan found a second integration issue: the current
artifact builder grammar rejects the first runtime-preserving path,
`python/node/basedpyright/LICENSE.txt`. There are 1,567 mixed-case paths, plus
ordinary Python names such as `__init__.py` whose leading underscore also
violates that grammar. Renaming these files would break package metadata,
package imports, and typeshed lookup, so assembly fails closed. The artifact
path grammar must be widened without losing traversal, Unicode-alias, depth,
length, or case-collision protections before a real root can be emitted. No
staged native component export is present yet.
