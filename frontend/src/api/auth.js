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

// The token is passed explicitly because AuthProvider clears it from storage
// first. skipAuthRedirect: a 401 here only means "already logged out".
export async function logout(token) {
  const response = await api.post("/api/auth/logout", null, {
    headers: { Authorization: `Bearer ${token}` },
    skipAuthRedirect: true,
  });
  return response.data;
}

export async function forgotPassword({ email }) {
  const response = await api.post("/api/auth/forgot-password", { email });
  return response.data;
}

export async function resetPassword({ email, otp, newPassword }) {
  const response = await api.post("/api/auth/reset-password", {
    email,
    otp,
    new_password: newPassword,
  });
  return response.data;
}
