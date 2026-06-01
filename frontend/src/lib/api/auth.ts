import { apiFetch } from "@/lib/api/client";

export interface SendCodeResponse {
  sent: boolean;
  dev_code: string | null;
}

export interface AuthToken {
  access_token: string;
  token_type: "bearer";
}

export interface UserIdentity {
  email: string;
}

export async function sendCode(email: string): Promise<SendCodeResponse> {
  const response = await apiFetch("/api/auth/send-code", {
    method: "POST",
    body: JSON.stringify({ email }),
  });
  if (!response.ok) throw new Error(`sendCode ${response.status}`);
  return response.json() as Promise<SendCodeResponse>;
}

export async function verifyCode(email: string, code: string): Promise<AuthToken> {
  const response = await apiFetch("/api/auth/verify", {
    method: "POST",
    body: JSON.stringify({ email, code }),
  });
  if (!response.ok) throw new Error(`verifyCode ${response.status}`);
  return response.json() as Promise<AuthToken>;
}

export async function getMe(): Promise<UserIdentity> {
  const response = await apiFetch("/api/auth/me", { cache: "no-store" });
  if (!response.ok) throw new Error(`getMe ${response.status}`);
  return response.json() as Promise<UserIdentity>;
}

export async function logout(): Promise<void> {
  const response = await apiFetch("/api/auth/logout", { method: "POST" });
  if (!response.ok) throw new Error(`logout ${response.status}`);
}
