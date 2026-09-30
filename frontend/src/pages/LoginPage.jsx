import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { getErrorMessage, getFieldErrors } from "../api/errors";
import FormField from "../components/FormField";
import { useAuth } from "../hooks/useAuth";
import { onlyErrors, validateEmail, validateLoginPassword } from "../utils/validation";

export default function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { login, notice, clearNotice } = useAuth();

  // Other pages can hand over an email and a success message
  // (e.g. "Email verified successfully. You can now log in.")
  const [form, setForm] = useState({ email: location.state?.email ?? "", password: "" });
  const [fieldErrors, setFieldErrors] = useState({});
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const successMessage = location.state?.message;

  function handleChange(event) {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
    setFieldErrors((current) => ({ ...current, [name]: "" }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    clearNotice();

    const errors = onlyErrors({
      email: validateEmail(form.email),
      password: validateLoginPassword(form.password),
    });
    setFieldErrors(errors);
    if (Object.keys(errors).length > 0) {
      return;
    }

    setIsSubmitting(true);
    const email = form.email.trim().toLowerCase();
    try {
      // On success the token is stored, isAuthenticated becomes true and
      // PublicOnlyRoute redirects to the page the user originally wanted.
      await login({ email, password: form.password });
    } catch (err) {
      setIsSubmitting(false);

      // Correct password but email not verified yet: send them to verify it
      if (err.response?.status === 403) {
        navigate("/verify-email", { state: { email } });
        return;
      }
      setFieldErrors(getFieldErrors(err));
      setError(getErrorMessage(err));
    }
  }

  return (
    <div className="card">
      <h1>Log in</h1>

      {notice && (
        <div className="alert alert-info" role="status">
          {notice}
        </div>
      )}
      {successMessage && !error && (
        <div className="alert alert-success" role="status">
          {successMessage}
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
          onChange={handleChange}
          error={fieldErrors.email}
        />
        <FormField
          id="password"
          label="Password"
          type="password"
          autoComplete="current-password"
          value={form.password}
          onChange={handleChange}
          error={fieldErrors.password}
        />

        <button type="submit" className="btn" disabled={isSubmitting}>
          {isSubmitting ? "Logging in..." : "Log in"}
        </button>
      </form>

      <p className="form-footer">
        <Link to="/forgot-password">Forgot your password?</Link>
      </p>
      <p className="form-footer">
        New here? <Link to="/signup">Create an account</Link>
      </p>
    </div>
  );
}
