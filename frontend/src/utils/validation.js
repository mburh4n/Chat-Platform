// Client-side checks that mirror the backend rules in core/fields.py.
// Each returns an error message, or "" when the value is valid.
// The backend always validates again: these only give faster feedback.

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function validateName(name) {
  const cleaned = name.trim().split(/\s+/).join(" ");
  if (!cleaned) return "Name is required.";
  if (cleaned.length < 2) return "Name must be at least 2 characters.";
  if (cleaned.length > 100) return "Name must be at most 100 characters.";
  return "";
}

export function validateEmail(email) {
  const trimmed = email.trim();
  if (!trimmed) return "Email is required.";
  if (!EMAIL_PATTERN.test(trimmed)) return "Enter a valid email address.";
  return "";
}

// For choosing a new password (sign-up, change, reset)
export function validateNewPassword(password) {
  if (!password) return "Password is required.";
  if (password.length < 8) return "Password must be at least 8 characters.";
  if (password.length > 128) return "Password must be at most 128 characters.";
  if (!/\p{L}/u.test(password)) return "Password must contain at least one letter.";
  if (!/[0-9]/.test(password)) return "Password must contain at least one number.";
  return "";
}

export function validateConfirmPassword(password, confirmPassword) {
  if (!confirmPassword) return "Please confirm your password.";
  if (password !== confirmPassword) return "Passwords do not match.";
  return "";
}

// For logging in: only "not empty", so older passwords keep working
export function validateLoginPassword(password) {
  if (!password) return "Password is required.";
  if (password.length > 128) return "Password must be at most 128 characters.";
  return "";
}

export function validateOtp(otp) {
  if (!otp) return "Enter the 6-digit code.";
  if (!/^[0-9]{6}$/.test(otp)) return "The code must be exactly 6 digits.";
  return "";
}

// Keep only the first 6 digits of whatever was typed or pasted.
// Stays a string, so "012345" keeps its leading zero.
export function cleanOtpInput(value) {
  return value.replace(/[^0-9]/g, "").slice(0, 6);
}

// Remove empty messages: { email: "", password: "Too short" } -> { password: "Too short" }
export function onlyErrors(errors) {
  return Object.fromEntries(Object.entries(errors).filter(([, message]) => message));
}
