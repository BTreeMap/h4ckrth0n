
## 2024-07-26 - OOM DoS Vulnerability in File Uploads
**Vulnerability:** Unbounded `await file.read()` in `src/h4ckath0n/uploads/router.py` loads the entire uploaded file into memory.
**Learning:** By bypassing disk spooling and reading unconditionally, attackers can cause OOM crashes (DoS) by sending excessively large files.
**Prevention:** Always validate size first (using `file.size`) and bound read calls (e.g., `await file.read(max_upload_bytes + 1)`).
