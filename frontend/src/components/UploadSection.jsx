import { useState } from "react";
import { uploadDocuments } from "../api/documents";
import { getErrorMessage } from "../api/errors";
import { formatFileSize } from "../utils/format";

// Mirrors MAX_UPLOAD_SIZE_MB / MAX_FILES_PER_UPLOAD on the backend (which checks again)
const MAX_FILE_MB = 20;
const MAX_FILES = 10;

function validateFiles(files) {
  if (files.length === 0) return "Choose at least one PDF file.";
  if (files.length > MAX_FILES) return `You can upload at most ${MAX_FILES} files at once.`;
  for (const file of files) {
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      return `"${file.name}" is not a PDF. Only .pdf files can be uploaded.`;
    }
    if (file.size === 0) return `"${file.name}" is empty.`;
    if (file.size > MAX_FILE_MB * 1024 * 1024) {
      return `"${file.name}" is larger than the ${MAX_FILE_MB} MB limit.`;
    }
  }
  return "";
}

export default function UploadSection({ onUploaded }) {
  const [files, setFiles] = useState([]);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [progress, setProgress] = useState(null); // null = not uploading
  // Changing the key remounts the <input>, which clears the chosen files
  const [inputKey, setInputKey] = useState(0);

  const isUploading = progress !== null;

  function handleChange(event) {
    const chosen = Array.from(event.target.files ?? []);
    setFiles(chosen);
    setSuccess("");
    setError(chosen.length > 0 ? validateFiles(chosen) : "");
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setSuccess("");

    const validationError = validateFiles(files);
    setError(validationError);
    if (validationError) {
      return;
    }

    setProgress(0);
    try {
      const documents = await uploadDocuments(files, setProgress);
      onUploaded(documents);
      setSuccess(
        documents.length === 1
          ? `"${documents[0].original_filename}" uploaded. It is being processed now.`
          : `${documents.length} files uploaded. They are being processed now.`,
      );
      setFiles([]);
      setInputKey((key) => key + 1);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setProgress(null);
    }
  }

  return (
    <section className="card">
      <h2>Upload PDFs</h2>

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
        <div className="form-field">
          <label htmlFor="pdf-files">Choose one or more PDF files</label>
          <input
            key={inputKey}
            id="pdf-files"
            type="file"
            accept="application/pdf,.pdf"
            multiple
            onChange={handleChange}
            disabled={isUploading}
          />
          <p className="field-hint">
            Text-based PDFs only (scanned images can&apos;t be read). Up to {MAX_FILES} files,
            {" "}{MAX_FILE_MB} MB each.
          </p>
        </div>

        {files.length > 0 && (
          <ul className="file-list">
            {files.map((file) => (
              <li key={`${file.name}-${file.size}`}>
                {file.name} <span className="muted">({formatFileSize(file.size)})</span>
              </li>
            ))}
          </ul>
        )}

        {isUploading && (
          <div className="progress" role="progressbar" aria-valuenow={progress} aria-valuemin={0} aria-valuemax={100}>
            <div className="progress-bar" style={{ width: `${progress}%` }} />
            <span className="progress-label">
              {progress < 100 ? `Uploading... ${progress}%` : "Saving..."}
            </span>
          </div>
        )}

        <button type="submit" className="btn" disabled={isUploading || files.length === 0 || Boolean(error)}>
          {isUploading ? "Uploading..." : "Upload"}
        </button>
      </form>
    </section>
  );
}
