import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { forgotPassword, resetPassword } from "../api/auth";
import { getErrorMessage, getFieldErrors } from "../api/errors";
import FormField from "../components/FormField";
import { useCountdown } from "../hooks/useCountdown";
import {
  cleanOtpInput,
  onlyErrors,
  validateConfirmPassword,
  validateEmail,
  validateNewPassword,
  validateOtp,
} from "../utils/validation";

const RESEND_COOLDOWN_SECONDS = 60;

export default function ResetPasswordPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const emailFromState = location.state?.email ?? "";

  const [form, setForm] = useState({
    email: emailFromState,
    otp: "",
    newPassword: "",
    confirmPassword: "",
  });
  const [fieldErrors, setFieldErrors] = useState({});
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(location.state?.message ?? "");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isResending, setIsResending] = useState(false);
  const [secondsLeft, startCountdown] = useCountdown(
    location.state?.codeSent ? RESEND_COOLDOWN_SECONDS : 0,
  );

  function setField(name, value) {
    setForm((current) => ({ ...current, [name]: value }));
    setFieldErrors((current) => ({ ...current, [name]: "" }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setSuccess("");

    const errors = onlyErrors({
      email: validateEmail(form.email),
      otp: validateOtp(form.otp),
      newPassword: validateNewPassword(form.newPassword),
      confirmPassword: validateConfirmPassword(form.newPassword, form.confirmPassword),
    });
    setFieldErrors(errors);
    if (Object.keys(errors).length > 0) {
      return;
    }

    setIsSubmitting(true);
    try {
      const email = form.email.trim().toLowerCase();
      const data = await resetPassword({ email, otp: form.otp, newPassword: form.newPassword });
      navigate("/login", { replace: true, state: { email, message: data.message } });
    } catch (err) {
      // The backend calls the field "new_password"
      const apiErrors = getFieldErrors(err);
      if (apiErrors.new_password) {
        apiErrors.newPassword = apiErrors.new_password;
      }
      setFieldErrors(apiErrors);
      setError(getErrorMessage(err));
      setIsSubmitting(false);
    }
  }

  async function handleResend() {
    setError("");
    setSuccess("");
    const emailError = validateEmail(form.email);
    if (emailError) {
      setFieldErrors({ email: emailError });
      return;
    }

    setIsResending(true);
    try {
      const data = await forgotPassword({ email: form.email.trim().toLowerCase() });
      setSuccess(data.message);
      setField("otp", "");
      startCountdown(RESEND_COOLDOWN_SECONDS);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsResending(false);
    }
  }

  return (
    <div className="card">
      <h1>Reset your password</h1>

      {success && (
        <div className="alert alert-success" role="status">
          {success}
        </div>
      )}
      {error && (
        <div className="alert alert-error" role="alert">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} noValidate>
        <FormField
          id="email"
          label="Email"
          type="email"
          autoComplete="email"
          value={form.email}
          onChange={(e) => setField("email", e.target.value)}
          error={fieldErrors.email}
        />
        <FormField
          id="otp"
          label="Reset code"
          className="otp-input"
          inputMode="numeric"
          autoComplete="one-time-code"
          maxLength={6}
          placeholder="123456"
          value={form.otp}
          onChange={(e) => setField("otp", cleanOtpInput(e.target.value))}
          error={fieldErrors.otp}
        />
        <FormField
          id="newPassword"
          label="New password"
          type="password"
          autoComplete="new-password"
          value={form.newPassword}
          onChange={(e) => setField("newPassword", e.target.value)}
          error={fieldErrors.newPassword}
          hint="At least 8 characters, with a letter and a number."
        />
        <FormField
          id="confirmPassword"
          label="Confirm new password"
          type="password"
          autoComplete="new-password"
          value={form.confirmPassword}
          onChange={(e) => setField("confirmPassword", e.target.value)}
          error={fieldErrors.confirmPassword}
        />

        <button type="submit" className="btn" disabled={isSubmitting}>
          {isSubmitting ? "Resetting..." : "Reset password"}
        </button>
      </form>

      <p className="form-footer">
        Didn&apos;t get a code?{" "}
        <button
          type="button"
          className="btn-link"
          onClick={handleResend}
          disabled={isResending || secondsLeft > 0}
        >
          {isResending
            ? "Sending..."
            : secondsLeft > 0
              ? `Resend code in ${secondsLeft}s`
              : "Resend code"}
        </button>
      </p>
      <p className="form-footer">
        <Link to="/login">Back to log in</Link>
      </p>
    </div>
  );
}
