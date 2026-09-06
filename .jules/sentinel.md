## 2026-07-16 - OOM DoS via Unbounded UploadFile Read
**Vulnerability:** Unbounded `await file.read()` in FastAPI `UploadFile` endpoint loaded the entire file into memory before checking its size, creating a Denial of Service (OOM) risk.
**Learning:** FastAPI's `UploadFile` caches uploads in memory or spools to disk, but `await file.read()` reads everything into the application's RAM at once, bypassing the spooling protection.
**Prevention:** Always check `file.size` first if available, and use bounded reads like `await file.read(max_bytes + 1)` when reading file contents into memory, raising an error if the bound is exceeded.
