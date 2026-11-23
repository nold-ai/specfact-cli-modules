## Project delivery after Codebase Repro

1. Capture request and asserted response examples through the existing Project
   import paths. Exercise sequential and worker extraction with a local
   Semgrep configuration present. Verify Spec-Kit protocol and workflow
   artifacts through its normal command.
2. Replace Project's example converter with source extraction that associates
   requests and assertions within a Python test. Remove the Spec-Kit preset
   writer. Preserve existing user configuration and generated artifacts.
3. Migrate Project feature and code-quality evidence and verify its rule IDs,
   findings, confidence, and reports against the accepted core semantics.
4. Refresh the Project payload version and checksum. Run the local and hosted
   checks without waivers. Signed external acceptance remains tracked in #516.

Project ships with a broad supported core range. Calling the core converter
unconditionally would reach Semgrep on earlier core versions. Raising the
bundle's minimum would affect unrelated commands. The Project converter
therefore keeps its existing `OpenAPITestConverter(repo_path, semgrep_config)`
entry point and `extract_examples_from_tests(test_files)` output shape. It
adopts the fixture-backed source semantics from core #799 while keeping the
implementation in the Project bundle. Both extraction paths already call
this converter. A legacy test policy yields migration guidance. It is read
only for presence and never executed.

The command and generated workflow are owned by Project. A successful Spec-Kit
import writes the existing plan, protocol, and validation workflow. The
retired preset writer is removed in the same change as its callers.

For Project feature analysis, reuse the core rule implementation and its
normalized findings shape. Project owns the snapshot so findings do not
depend on the core version or a third-party executable. Reuse the current
plan enrichment and confidence contracts. Show migration guidance in the
existing analysis status output when legacy feature or quality rules exist.
Parse each source file once and pass the same tree to the pattern engine.
