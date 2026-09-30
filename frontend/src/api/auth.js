import { api } from "./client";

// One function per backend auth endpoint. Each returns the response body.

export async function signup({ name, email, password }) {
  const response = await api.post("/api/auth/signup", { name, email, password });
  return response.data;
}

// otp stays a string: "012345" must not lose its leading zero
export async function verifyEmail({ email, otp }) {
  const response = await api.post("/api/auth/verify-email", { email, otp });
  return response.data;
}

export async function resendVerification({ email }) {
  const response = await api.post("/api/auth/resend-verification", { email });
  return response.data;
}

export async function login({ email, password }) {
  const response = await api.post("/api/auth/login", { email, password });
  return response.data;
}
