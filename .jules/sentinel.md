## 2024-05-24 - Unbounded FastAPI UploadFile Read OOM DoS
**Vulnerability:** Calling `await file.read()` on FastAPI `UploadFile` objects without a size limit or size check first.
**Learning:** This bypasses FastAPI's disk spooling, loads the entire file into memory regardless of size, and causes Out-Of-Memory (OOM) Denial of Service (DoS) vulnerabilities if an attacker uploads a massive file.
**Prevention:** Always validate size first using `file.size` if available, and bound `file.read()` calls (e.g., `await file.read(max_upload_bytes + 1)`) to enforce size limits before reading the entire content into memory.
