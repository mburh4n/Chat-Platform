import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { resendVerification, verifyEmail } from "../api/auth";
import { getErrorMessage, getFieldErrors } from "../api/errors";
import FormField from "../components/FormField";
import { useCountdown } from "../hooks/useCountdown";
import { cleanOtpInput, onlyErrors, validateEmail, validateOtp } from "../utils/validation";

// Matches OTP_RESEND_COOLDOWN_SECONDS on the backend
const RESEND_COOLDOWN_SECONDS = 60;

export default function VerifyEmailPage() {
  const navigate = useNavigate();
  const location = useLocation();

  // Sign-up and login pass the email in router state. If the page is opened
  // directly (or refreshed after state is lost), the user types it instead.
  const emailFromState = location.state?.email ?? "";
  const codeJustSent = Boolean(location.state?.codeSent);

  const [email, setEmail] = useState(emailFromState);
  const [otp, setOtp] = useState("");
  const [fieldErrors, setFieldErrors] = useState({});
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isResending, setIsResending] = useState(false);
  const [secondsLeft, startCountdown] = useCountdown(codeJustSent ? RESEND_COOLDOWN_SECONDS : 0);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setSuccess("");

    const errors = onlyErrors({ email: validateEmail(email), otp: validateOtp(otp) });
    setFieldErrors(errors);
    if (Object.keys(errors).length > 0) {
      return;
    }

    setIsSubmitting(true);
    try {
      const normalizedEmail = email.trim().toLowerCase();
      const data = await verifyEmail({ email: normalizedEmail, otp });
      navigate("/login", { replace: true, state: { email: normalizedEmail, message: data.message } });
    } catch (err) {
      setFieldErrors(getFieldErrors(err));
      setError(getErrorMessage(err));
      setIsSubmitting(false);
    }
  }

  async function handleResend() {
    setError("");
    setSuccess("");

    const emailError = validateEmail(email);
    if (emailError) {
      setFieldErrors({ email: emailError });
      return;
    }

    setIsResending(true);
    try {
      const data = await resendVerification({ email: email.trim().toLowerCase() });
      setSuccess(data.message);
      setOtp("");
      startCountdown(RESEND_COOLDOWN_SECONDS);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsResending(false);
    }
  }

  return (
    <div className="card">
      <h1>Verify your email</h1>

      <p>
        {emailFromState
          ? `Enter the 6-digit code we sent to ${emailFromState}.`
          : "Enter your email and the 6-digit code we sent you."}
      </p>

      {error && (
        <div className="alert alert-error" role="alert">
          {error}
        </div>
      )}
      {success && (
        <div className="alert alert-success" role="status">
          {success}
        </div>
      )}

      <form onSubmit={handleSubmit} noValidate>
        {!emailFromState && (
          <FormField
            id="email"
            label="Email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => {
              setEmail(e.target.value);
              setFieldErrors((current) => ({ ...current, email: "" }));
            }}
            error={fieldErrors.email}
          />
        )}

        <FormField
          id="otp"
          label="Verification code"
          className="otp-input"
          inputMode="numeric"
          autoComplete="one-time-code"
          maxLength={6}
          placeholder="123456"
          value={otp}
          onChange={(e) => {
            setOtp(cleanOtpInput(e.target.value));
            setFieldErrors((current) => ({ ...current, otp: "" }));
          }}
          error={fieldErrors.otp}
        />

        <button type="submit" className="btn" disabled={isSubmitting}>
          {isSubmitting ? "Verifying..." : "Verify email"}
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
