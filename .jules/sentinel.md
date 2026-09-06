## 2024-05-18 - Unbounded File Read OOM DoS
**Vulnerability:** Calling `await file.read()` on FastAPI `UploadFile` objects without a size limit reads the entire file into memory, causing OOM DoS.
**Learning:** Validation via `len(data) > max_bytes` after reading is too late, because the unbounded read has already occurred.
**Prevention:** Always check `file.size` first (if available) and bound the read using `await file.read(max_upload_bytes + 1)` before validating the length of the read chunk.
