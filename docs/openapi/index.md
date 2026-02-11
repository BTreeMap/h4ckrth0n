# OpenAPI generation and client types

The full stack template ships a checked in OpenAPI schema and generated TypeScript types. This
keeps backend and frontend types in sync.

## Artifacts

- `packages/create-h4ckath0n/templates/fullstack/api/openapi.json`
- `packages/create-h4ckath0n/templates/fullstack/web/src/api/openapi.ts`

## Regenerating OpenAPI JSON

From the template web directory, the generator runs the backend script using uv:

```bash
cd packages/create-h4ckath0n/templates/fullstack/web
npm run gen
```

Under the hood this executes:

- `uv --project <api> run --locked python -m scripts.dump_openapi --out <api>/openapi.json`

The backend schema is built from `app.main:app`, which already includes the h4ckath0n auth routes.

## Generating TypeScript types

The same `npm run gen` command runs `openapi-typescript` and writes:

- `packages/create-h4ckath0n/templates/fullstack/web/src/api/openapi.ts`

The generator is invoked with `npm exec --no` to ensure the pinned version in
`package-lock.json` is used.

## Keeping client code aligned

The web template imports the generated types in `src/api/client.ts` and `src/api/types.ts`. If the
schema drifts, TypeScript will fail during `npm run typecheck`.

## Inline docs

FastAPI route metadata and Pydantic field descriptions are the source of truth for the OpenAPI
schema. Update route summaries, descriptions, and response models whenever the API changes.
