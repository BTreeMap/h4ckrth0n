## 2024-08-28 - Centralize Pydantic Validation Logic
**Learning:** Pydantic schema validation using repeated `@field_validator` methods scatters the normalization and transformation pipeline across multiple models, creating code drift and semantic duplication.
**Action:** Always prefer centralizing repeated normalization logic into reusable `typing.Annotated` types paired with `pydantic.AfterValidator`. This ensures a single source of truth for the type and its validation.
