## Why

The customer capsule jobs cannot start the published SpecFact CLI 0.55.4 with Typer 0.29.1. The Docs Review Hatch environment also fails to generate command documentation from Typer 0.29.1 arguments.

## What Changes

- Constrain Typer in the two capsule installation steps to preserve the released CLI startup path.
- Read the declared argument name when rendering the default docs label. Keep explicit metavars unchanged.

## Impact

Only the capsule job environments and docs generator change. The signed module, cutoff, published payloads, verification steps, and publisher state are unchanged.
