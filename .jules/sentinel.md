## 2026-07-20 - [Fix OOM DoS via unbounded file read]
**Vulnerability:** FastAPIs `UploadFile.read()` without bounds allows users to exhaust server memory, leading to an Out-Of-Memory (OOM) DoS.
**Learning:** The memory limit check `len(data) > limit` occurred *after* the entire file was loaded into memory.
**Prevention:** Use `file.size` to fail early, and strictly bound the read operation with `await file.read(max_upload_bytes + 1)` so that large files cannot exhaust memory.
