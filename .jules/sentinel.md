## 2024-08-28 - Insecure JWT subject validation
**Vulnerability:** JWT authentication allowed an attacker to issue a valid JWT for any user by modifying the `sub` claim. The device's public key was correctly used to verify the signature (bound to the attacker's device), but there was no check ensuring the requested user ID in `sub` matched the device's actual `user_id`.
**Learning:** In device-bound JWT architectures, signature verification only proves possession of the device key. It does not prove the device is authorized to act on behalf of the arbitrary user specified in the `sub` claim.
**Prevention:** Always enforce that the user ID requested in the token (`claims.sub`) matches the user ID associated with the device record used to sign it (`device.user_id`).
