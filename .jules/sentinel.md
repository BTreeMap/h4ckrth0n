
## 2026-07-24 - Unbounded File Read in Uploads
**Vulnerability:** Unbounded `await file.read()` calls bypassing disk spooling and loading entire files into memory.
**Learning:** FastAPI's `UploadFile.read()` without a size limit can cause Out-Of-Memory (OOM) Denial of Service (DoS) attacks when processing large files.
**Prevention:** Always check `file.size` if available, and bound `file.read()` calls to `max_upload_bytes + 1` to strictly enforce memory usage limits.
