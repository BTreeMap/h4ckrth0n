
## 2024-05-24 - Centralize Pydantic Validation with Annotated Types
**Learning:** Duplicated `@field_validator` and `Field` constraints across multiple Pydantic V2 models for identical fields (like `display_name`) create drift risk and boilerplate.
**Action:** Use `typing.Annotated` combined with `pydantic.Field` and `pydantic.AfterValidator` to create reusable, self-validating custom types (e.g., `DisplayNameField`), replacing repeated inline validation logic.
