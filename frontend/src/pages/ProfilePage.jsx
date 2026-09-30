import { useState } from "react";
import { getErrorMessage, getFieldErrors } from "../api/errors";
import { changePassword, updateMe } from "../api/users";
import FormField from "../components/FormField";
import { useAuth } from "../hooks/useAuth";
import {
  onlyErrors,
  validateConfirmPassword,
  validateLoginPassword,
  validateName,
  validateNewPassword,
} from "../utils/validation";

function ProfileForm({ user, onUpdated }) {
  const [name, setName] = useState(user.name);
  const [fieldErrors, setFieldErrors] = useState({});
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setSuccess("");

    const nameError = validateName(name);
    setFieldErrors(nameError ? { name: nameError } : {});
    if (nameError) {
      return;
    }

    setIsSubmitting(true);
    try {
      const updated = await updateMe({ name: name.trim() });
      onUpdated(updated);
      setName(updated.name);
      setSuccess("Profile updated.");
    } catch (err) {
      setFieldErrors(getFieldErrors(err));
      setError(getErrorMessage(err));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} noValidate>
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
      <FormField id="profile-email" label="Email" type="email" value={user.email} disabled readOnly />
      <FormField
        id="name"
        label="Name"
        autoComplete="name"
        value={name}
        onChange={(e) => {
          setName(e.target.value);
          setFieldErrors({});
        }}
        error={fieldErrors.name}
      />
      <button type="submit" className="btn" disabled={isSubmitting || name.trim() === user.name}>
        {isSubmitting ? "Saving..." : "Save changes"}
      </button>
    </form>
  );
}

const EMPTY_PASSWORD_FORM = { currentPassword: "", newPassword: "", confirmPassword: "" };

function ChangePasswordForm({ onTokenReplaced }) {
  const [form, setForm] = useState(EMPTY_PASSWORD_FORM);
  const [fieldErrors, setFieldErrors] = useState({});
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  function handleChange(event) {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
    setFieldErrors((current) => ({ ...current, [name]: "" }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setSuccess("");

    const errors = onlyErrors({
      currentPassword: validateLoginPassword(form.currentPassword),
      newPassword: validateNewPassword(form.newPassword),
      confirmPassword: validateConfirmPassword(form.newPassword, form.confirmPassword),
    });
    setFieldErrors(errors);
    if (Object.keys(errors).length > 0) {
      return;
    }

    setIsSubmitting(true);
    try {
      const data = await changePassword({
        currentPassword: form.currentPassword,
        newPassword: form.newPassword,
      });
      // The old token is revoked; keep this session alive with the new one
      onTokenReplaced(data.access_token);
      setForm(EMPTY_PASSWORD_FORM);
      setSuccess("Password changed. Other devices have been logged out.");
    } catch (err) {
      const apiErrors = getFieldErrors(err);
      setFieldErrors({
        currentPassword: apiErrors.current_password,
        newPassword: apiErrors.new_password,
      });
      setError(getErrorMessage(err));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} noValidate>
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
      <FormField
        id="currentPassword"
        label="Current password"
        type="password"
        autoComplete="current-password"
        value={form.currentPassword}
        onChange={handleChange}
        error={fieldErrors.currentPassword}
      />
      <FormField
        id="newPassword"
        label="New password"
        type="password"
        autoComplete="new-password"
        value={form.newPassword}
        onChange={handleChange}
        error={fieldErrors.newPassword}
        hint="At least 8 characters, with a letter and a number."
      />
      <FormField
        id="confirmPassword"
        label="Confirm new password"
        type="password"
        autoComplete="new-password"
        value={form.confirmPassword}
        onChange={handleChange}
        error={fieldErrors.confirmPassword}
      />
      <button type="submit" className="btn" disabled={isSubmitting}>
        {isSubmitting ? "Changing password..." : "Change password"}
      </button>
    </form>
  );
}

export default function ProfilePage() {
  const { user, updateUser, replaceToken } = useAuth();

  if (!user) {
    return (
      <div className="card">
        <p className="loading">Loading your profile...</p>
      </div>
    );
  }

  return (
    <div className="narrow">
      <section className="card">
        <h1>Your profile</h1>
        <p className="field-hint">
          Member since {new Date(user.created_at).toLocaleDateString()}
        </p>
        {/* key: resets the form if a different user's profile loads */}
        <ProfileForm key={user.id} user={user} onUpdated={updateUser} />
      </section>

      <section className="card">
        <h2>Change password</h2>
        <ChangePasswordForm onTokenReplaced={replaceToken} />
      </section>
    </div>
  );
}
