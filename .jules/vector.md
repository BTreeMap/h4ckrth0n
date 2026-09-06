## 2024-07-18 - Centralize Pydantic Validation with Annotated types
**Learning:** Using `@field_validator` across multiple models leads to duplicated boilerplate for common fields like `display_name`.
**Action:** Use Pydantic V2's `typing.Annotated` combined with `Field` and `AfterValidator` to create reusable, self-validating custom types that centralize both schema constraints and normalisation logic.
