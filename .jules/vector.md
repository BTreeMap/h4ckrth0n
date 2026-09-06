## 2024-05-18 - Repeated Pydantic Validators
**Learning:** We saw identical `_clean_display_name` validators duplicated across `h4ckath0n/auth/schemas.py` and `h4ckath0n/auth/passkeys/schemas.py` calling the same `normalize_display_name` helper.
**Action:** Extracting a Pydantic `Annotated` type or centralizing the validator logic into a base class/mixin can reduce this duplication and make the semantics of a valid display name explicit and reusable.
