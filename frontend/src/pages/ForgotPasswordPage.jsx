import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { forgotPassword } from "../api/auth";
import { getErrorMessage, getFieldErrors } from "../api/errors";
import FormField from "../components/FormField";
import { validateEmail } from "../utils/validation";

export default function ForgotPasswordPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [fieldErrors, setFieldErrors] = useState({});
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");

    const emailError = validateEmail(email);
    setFieldErrors(emailError ? { email: emailError } : {});
    if (emailError) {
      return;
    }

    setIsSubmitting(true);
    try {
      const normalizedEmail = email.trim().toLowerCase();
      const data = await forgotPassword({ email: normalizedEmail });
      // The message is the same whether or not the account exists
      navigate("/reset-password", {
        state: { email: normalizedEmail, codeSent: true, message: data.message },
      });
    } catch (err) {
      setFieldErrors(getFieldErrors(err));
      setError(getErrorMessage(err));
      setIsSubmitting(false);
    }
  }

  return (
    <div className="card">
      <h1>Forgot your password?</h1>
      <p>Enter your account email and we&apos;ll send you a 6-digit reset code.</p>

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
          value={email}
          onChange={(e) => {
            setEmail(e.target.value);
            setFieldErrors({});
          }}
          error={fieldErrors.email}
        />
        <button type="submit" className="btn" disabled={isSubmitting}>
          {isSubmitting ? "Sending code..." : "Send reset code"}
        </button>
      </form>

      <p className="form-footer">
        Already have a code? <Link to="/reset-password">Enter it here</Link>
      </p>
      <p className="form-footer">
        <Link to="/login">Back to log in</Link>
      </p>
    </div>
  );
}
