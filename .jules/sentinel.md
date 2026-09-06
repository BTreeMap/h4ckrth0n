
## 2026-07-17 - Prevent OOM DoS in File Uploads
**Vulnerability:** Unbounded `await file.read()` in `upload_file` could lead to OOM DoS attacks by loading massive files entirely into memory before size validation.
**Learning:** Checking `len(data) > max_bytes` after reading the whole file is too late. The file content is already in RAM.
**Prevention:** Use `file.size` for early rejection and bound the `read` call (e.g. `await file.read(max_bytes + 1)`) to avoid loading arbitrarily large amounts of data.
