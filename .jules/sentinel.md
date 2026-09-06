
## 2024-07-21 - [Prevent OOM DoS in File Uploads]
 **Vulnerability:** Unbounded `await file.read()` calls in FastAPI load entire files into memory, causing OOM DoS vulnerabilities.
 **Learning:** FastAPI's `UploadFile` bypasses disk spooling when read completely at once if no bounds are enforced.
 **Prevention:** Always validate size first (using `file.size`) and bound read calls (e.g., `await file.read(max_upload_bytes + 1)`).
