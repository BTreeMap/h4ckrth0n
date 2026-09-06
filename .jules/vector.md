## 2024-05-23 - JWT Device Binding Vulnerability
**Learning:** In a device-bound JWT architecture where the device public key is used to verify the signature (via `kid` header), it is CRITICAL to enforce that the subject claim (`sub`) matches the user ID associated with the device record. Otherwise, any user with a valid device can forge a JWT for any other user (like an admin).
**Action:** Always verify `claims.sub == device.user_id` during device-JWT verification, not just the cryptographic signature.
