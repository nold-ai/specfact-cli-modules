## Validation Summary

- OpenSpec strict validation passes for `fix-backlog-provider-required-field-mappings`.
- The implemented code path now covers `backlog add` create payload assembly for both:
  - ADO required mapped provider fields resolved from persisted `backlog map-fields` metadata plus explicit overrides
  - GitHub persisted provider metadata overrides for `github_issue_types` and `github_project_v2`
- The worktree analysis of the core adapters shows:
  - ADO create is the direct provider-field HTTP 400 risk path because it serializes `provider_fields.fields` into the create patch document.
  - ADO update and GitHub update paths patch selected fields and generally preserve untouched provider metadata server-side.
  - GitHub create already consumes persisted provider config for issue type / ProjectV2 metadata, so this change adds explicit override support on top of that config-first behavior.

## Consistency Notes

- The new change proposal/design describe a broader config-first provider-field contract across backlog write commands.
- The implementation now covers the backlog command path in this repo that assembles create payloads directly (`backlog add`) and confirms via adapter-path analysis that backlog writeback commands do not need full required-field resend because they patch selected fields only.
- Existing canonical CLI flags remain supported and now act as higher-priority overrides over resolved config defaults for the ADO create flow.

## Remaining Gaps

- PR creation and end-to-end gate execution remain pending.
