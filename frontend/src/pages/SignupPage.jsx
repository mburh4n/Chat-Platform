import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { signup } from "../api/auth";
import { getErrorMessage, getFieldErrors } from "../api/errors";
import FormField from "../components/FormField";
import {
  onlyErrors,
  validateConfirmPassword,
  validateEmail,
  validateName,
  validateNewPassword,
} from "../utils/validation";

const EMPTY_FORM = { name: "", email: "", password: "", confirmPassword: "" };

function validate(form) {
  return onlyErrors({
    name: validateName(form.name),
    email: validateEmail(form.email),
    password: validateNewPassword(form.password),
    confirmPassword: validateConfirmPassword(form.password, form.confirmPassword),
  });
}

export default function SignupPage() {
  const navigate = useNavigate();
  const [form, setForm] = useState(EMPTY_FORM);
  const [fieldErrors, setFieldErrors] = useState({});
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  function handleChange(event) {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
    // Clear a field's error as soon as the user edits it
    setFieldErrors((current) => ({ ...current, [name]: "" }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");

    const errors = validate(form);
    setFieldErrors(errors);
    if (Object.keys(errors).length > 0) {
      return;
    }

    setIsSubmitting(true);
    try {
      const email = form.email.trim().toLowerCase();
      await signup({ name: form.name.trim(), email, password: form.password });
      // Carry the email to the next page so the user doesn't type it again.
      // codeSent starts the resend countdown there, matching the backend cooldown.
      navigate("/verify-email", { state: { email, codeSent: true } });
    } catch (err) {
      setFieldErrors(getFieldErrors(err));
      setError(getErrorMessage(err));
      setIsSubmitting(false);
    }
  }

  return (
    <div className="card">
      <h1>Create an account</h1>

      {error && (
        <div className="alert alert-error" role="alert">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} noValidate>
        <FormField
          id="name"
          label="Name"
          autoComplete="name"
          value={form.name}
          onChange={handleChange}
          error={fieldErrors.name}
        />
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
          autoComplete="new-password"
          value={form.password}
          onChange={handleChange}
          error={fieldErrors.password}
          hint="At least 8 characters, with a letter and a number."
        />
        <FormField
          id="confirmPassword"
          label="Confirm password"
          type="password"
          autoComplete="new-password"
          value={form.confirmPassword}
          onChange={handleChange}
          error={fieldErrors.confirmPassword}
        />

        <button type="submit" className="btn" disabled={isSubmitting}>
          {isSubmitting ? "Creating account..." : "Sign up"}
        </button>
      </form>

      <p className="form-footer">
        Already have an account? <Link to="/login">Log in</Link>
      </p>
    </div>
  );
}
