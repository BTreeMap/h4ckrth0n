## 2024-09-08 - Centralized Pydantic validation via Annotated types
**Learning:** Duplicate `@field_validator` methods across multiple Pydantic models handling the same logical field type (e.g., `display_name`) risk drift and bloat the schemas with repetitive imperative code.
**Action:** Use `typing.Annotated` combined with `pydantic.Field` (for metadata like max_length) and `pydantic.AfterValidator` (for normalization) to create a single, composable, shared semantic type that automatically handles both validation and OpenAPI schema generation without inline validators.
