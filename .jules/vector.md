## 2025-03-05 - Centralize Pydantic Validation via Annotated
**Learning:** Pydantic validation rules (`@field_validator` and `max_length` in `Field`) duplicated across multiple API models (like standard register vs. passkey register) are bug-prone.
**Action:** Extracted repeated display name validation logic into a centralized, reusable `typing.Annotated` type (`DisplayName = Annotated[str, Field(max_length=...), AfterValidator(normalize)]`), as suggested by the project conventions for FP-style semantics.
