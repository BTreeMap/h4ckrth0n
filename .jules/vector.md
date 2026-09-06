## 2024-05-24 - Centralize Pydantic Validation with Annotated
**Learning:** Shared field validation (like max_length and custom normalizers for `display_name`) was duplicated across multiple models using `@field_validator`.
**Action:** Use `typing.Annotated` combined with `pydantic.Field` (for metadata) and `pydantic.AfterValidator` (for functions) to create reusable, composable types that centralize semantics and prevent drift.
