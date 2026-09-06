## 2024-05-18 - Device JWT Authorization bypass
**Vulnerability:** The device JWT verification did not ensure that the user ID specified in the subject (`sub`) matches the user ID associated with the device's public key (`device.user_id`).
**Learning:** In device-bound JWT architectures, signing a token only proves possession of the device key. Without verifying the `sub` claim against the device's true owner in the database, a user can forge tokens for any other user on the system by simply changing the `sub` claim while signing with their own valid device key.
**Prevention:** Always validate that the identity asserted in a cryptographically bound token matches the authoritative identity linked to that cryptographic material in the database.
