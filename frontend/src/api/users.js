import { api } from "./client";

export async function getMe() {
  const response = await api.get("/api/users/me");
  return response.data;
}

export async function updateMe({ name }) {
  const response = await api.patch("/api/users/me", { name });
  return response.data;
}

// Returns a NEW access token: the old one stops working
export async function changePassword({ currentPassword, newPassword }) {
  const response = await api.post("/api/users/me/change-password", {
    current_password: currentPassword,
    new_password: newPassword,
  });
  return response.data;
}
