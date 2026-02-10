import { SignJWT } from "jose";
import { getPrivateKey, getDeviceIdentity } from "./deviceKey";

let cachedToken: string | null = null;
let cachedExp: number = 0;

const TOKEN_LIFETIME = 900; // 15 minutes in seconds
const RENEWAL_BUFFER = 60; // renew 60s before expiry

export function isTokenValid(): boolean {
  if (!cachedToken) return false;
  const now = Math.floor(Date.now() / 1000);
  return now < cachedExp - RENEWAL_BUFFER;
}

export async function getOrMintToken(aud?: string): Promise<string> {
  if (isTokenValid() && cachedToken) return cachedToken;
  return mintToken(aud);
}

export async function mintToken(aud?: string): Promise<string> {
  const privateKey = await getPrivateKey();
  const identity = await getDeviceIdentity();
  if (!privateKey || !identity) {
    throw new Error("No device key material or identity found");
  }

  const now = Math.floor(Date.now() / 1000);
  const exp = now + TOKEN_LIFETIME;

  let builder = new SignJWT({ sub: identity.userId })
    .setProtectedHeader({
      alg: "ES256",
      typ: "JWT",
      kid: identity.deviceId,
    })
    .setIssuedAt(now)
    .setExpirationTime(exp);

  if (aud) {
    builder = builder.setAudience(aud);
  }

  const token = await builder.sign(privateKey);
  cachedToken = token;
  cachedExp = exp;
  return token;
}

export function clearCachedToken(): void {
  cachedToken = null;
  cachedExp = 0;
}

export function shouldRenewToken(): boolean {
  if (!cachedToken) return true;
  const now = Math.floor(Date.now() / 1000);
  return now >= cachedExp - RENEWAL_BUFFER;
}
