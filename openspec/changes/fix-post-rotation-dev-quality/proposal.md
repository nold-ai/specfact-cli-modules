## Why

After the module-signing rotation merged, the quality workflow supplied the current modules checkout to a smoke script that requires a reviewed fixture. The open-ended Ruff dependency also resolved to a release that flags unchanged frozen module source and the paired core checkout.

## What changes

- Match the paired core's reviewed Ruff 0.16.0 pin and retain the full lint rules.
- Check out the reviewed modules fixture separately for the existing runtime discovery matrix. Warm the artifact cache from the paired core lock.
- Preserve the existing 0.55.4 cutoff, signature verification, and publisher pause.
