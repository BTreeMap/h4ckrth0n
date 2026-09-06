## 2024-05-19 - Initial
**Learning:** Nothing yet.
**Action:** Nothing yet.
## 2024-10-24 - Extract Reusable Pydantic Type for Display Names
**Learning:** The project uses `@field_validator` extensively for request normalization (e.g. `display_name`). When this logic needs to be shared across multiple routers (like password auth and passkey auth), it creates duplicated validation logic across models.
**Action:** Prefer centralizing the logic into reusable `typing.Annotated` types combined with `pydantic.AfterValidator` (e.g., `Annotated[str, Field(...), AfterValidator(func)]`) rather than duplicating `@field_validator` methods across multiple models.
