## 2024-05-24 - [Fix Memory Exhaustion DoS in File Uploads]
**Vulnerability:** Unbounded `await file.read()` loaded the entire uploaded file into RAM before checking size against `max_upload_bytes`, allowing an attacker to cause an Out-Of-Memory (OOM) crash by uploading a massive file.
**Learning:** FastAPI `UploadFile` handles large files by spooled temporary files on disk, but calling `.read()` without arguments pulls the entire contents into a `bytes` string in memory.
**Prevention:** Always check `file.size` first if available, and bound the `.read(limit)` call to `max_upload_bytes + 1` to gracefully reject oversized files without exhausting server RAM.
