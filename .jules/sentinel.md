## 2025-02-26 - Unbounded FastAPI UploadFile Read OOM DoS
**Vulnerability:** FastAPI `await file.read()` loads the entire file into memory as bytes before checking the size, leading to an Out-Of-Memory (OOM) Denial of Service vulnerability on upload endpoints.
**Learning:** FastAPI's `UploadFile` uses SpooledTemporaryFile for disk spooling, but `file.read()` returns all bytes into memory at once. Checking size *after* this read is too late.
**Prevention:** Always check `file.size` first (if provided) and bound the read call using `await file.read(max_bytes + 1)`. If the bounded read returns more than `max_bytes`, throw a 413 error.
