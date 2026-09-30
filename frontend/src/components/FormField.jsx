// A labelled input with its error message (or hint) underneath.
// Extra props (type, autoComplete, inputMode, ...) are passed to the <input>.
export default function FormField({ id, label, error, hint, ...inputProps }) {
  const messageId = `${id}-message`;
  const hasMessage = Boolean(error || hint);

  return (
    <div className="form-field">
      <label htmlFor={id}>{label}</label>
      <input
        id={id}
        name={id}
        aria-invalid={error ? "true" : "false"}
        aria-describedby={hasMessage ? messageId : undefined}
        {...inputProps}
      />
      {error ? (
        <p id={messageId} className="field-error">
          {error}
        </p>
      ) : (
        hint && (
          <p id={messageId} className="field-hint">
            {hint}
          </p>
        )
      )}
    </div>
  );
}
