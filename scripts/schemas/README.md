# OCI metadata schemas

`oci-config-v1.1.1.json` derives from the Apache-2.0 licensed
[OCI image-spec v1.1.1](https://github.com/opencontainers/image-spec/tree/v1.1.1/schema),
accessed 2026-09-30. The two referenced map definitions are inlined into
`definitions`, and their references are rewritten locally. No validation performs
network schema resolution. All other configuration constraints are preserved.
Upstream license: `OCI-LICENSE`.

Source SHA-256 values:

- `schema/config-schema.json`: `089fcf3cf65a378873ffd5bdf450098de95a0a52def0ef41a57ae33275654ba8`
- `schema/defs.json`: `23b4abe55230e4bc7f521dc08e5261e9f1aece585059d6581300e9c56eb1420e`
- `LICENSE`: `b0a3f39513927db306adabea11d14c23f079d4febcea241d123a68d1a0d45418`

The index, manifest and descriptor schemas use the same pinned release. All
references are expanded inline and schema `id` annotations removed to prevent
remote resolution; validation constraints are preserved. Source SHA-256 values:

- `schema/image-manifest-schema.json`: `040ba9c116f1013175f5be6eb2620d87ca98cd90edc74548ee98ee89394aa4a2`
- `schema/image-index-schema.json`: `1a4641a610933fac77db9af7a83664d54883efac180f8867efd0497048e1a82e`
- `schema/content-descriptor.json`: `d7838a1fd129ff35f2d6461bfd8424e783c1e0185473d2547c09f2d5e8bb4ad4`
- `schema/defs.json`: `23b4abe55230e4bc7f521dc08e5261e9f1aece585059d6581300e9c56eb1420e`
- `schema/defs-descriptor.json`: `00d6be02b7a6661c5e7e8e50afa0a2926a092f4ba8ecedb5d8c29a4b372a927b`
