## 2024-05-15 - Prevent OOM DoS in File Uploads
**Vulnerability:** Unbounded `await file.read()` calls in FastAPI upload endpoints can load excessively large files entirely into memory, leading to Out-Of-Memory (OOM) Denial of Service (DoS) attacks.
**Learning:** Checking file size *after* reading the entire file into memory defeats the purpose of the size limit. FastAPI `UploadFile` endpoints bypass disk spooling if you immediately await read() on the whole file.
**Prevention:** Always validate size first (e.g. `file.size` if available) and bound read calls (e.g., `await file.read(max_upload_bytes + 1)`), then check if the length exceeds the maximum before proceeding.
