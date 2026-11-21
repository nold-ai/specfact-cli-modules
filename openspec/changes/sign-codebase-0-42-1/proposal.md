# Sign the exact Codebase 0.42.1 candidate

PR #524 needs a Codebase manifest signature under the replacement key. The maintainer authorized signing this exact payload on protected `dev` and will approve the signing environment run. Extend the existing replacement-key preflight with a single-payload job triggered when the reviewed payload file lands on dev. Keep current signature verification, signature reproduction, environment protection, and the publication pause in force.

Source tracking: [modules #513](https://github.com/nold-ai/specfact-cli-modules/issues/513) and [PR #524](https://github.com/nold-ai/specfact-cli-modules/pull/524). This change provides the one-time signing prerequisite. The operation does not publish a bundle or close the runtime story.
