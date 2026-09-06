## 2024-05-24 - Fix unbounded memory read DoS in FastAPI uploads
**Vulnerability:** Unbounded `await file.read()` calls bypassing disk spooling and loading the entire file into memory.
**Learning:** OOM DoS vulnerabilities occur because FastAPI `UploadFile` endpoints using unbounded reads can be abused to load massive payloads into memory, crashing the app.
**Prevention:** Always validate size first (using `file.size` if available) and bound read calls (e.g., `await file.read(max_upload_bytes + 1)`).
