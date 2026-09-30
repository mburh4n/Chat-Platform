import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { deleteDocument, listDocuments } from "../api/documents";
import { getErrorMessage } from "../api/errors";
import StatusBadge from "../components/StatusBadge";
import UploadSection from "../components/UploadSection";
import { formatDateTime, formatFileSize } from "../utils/format";

// How often to re-check while a document is still being processed
const POLL_INTERVAL_MS = 3000;

function DocumentRow({ document, isDeleting, onDelete }) {
  const isReady = document.status === "ready";

  return (
    <li className="document-row">
      <div className="document-info">
        <div className="document-title">
          <span className="document-name" title={document.original_filename}>
            {document.original_filename}
          </span>
          <StatusBadge status={document.status} />
        </div>
        <p className="muted">
          {formatFileSize(document.file_size)}
          {document.page_count !== null && ` · ${document.page_count} page(s)`}
          {isReady && ` · ${document.chunk_count} chunk(s)`}
          {` · uploaded ${formatDateTime(document.created_at)}`}
        </p>
        {document.status === "failed" && document.error_message && (
          <p className="field-error">{document.error_message}</p>
        )}
      </div>

      <div className="document-actions">
        {isReady ? (
          <Link className="btn btn-small" to={`/documents/${document.id}/chat`}>
            Chat
          </Link>
        ) : (
          <button type="button" className="btn btn-small" disabled>
            Chat
          </button>
        )}
        <button
          type="button"
          className="btn btn-small btn-danger"
          onClick={() => onDelete(document)}
          disabled={isDeleting}
        >
          {isDeleting ? "Deleting..." : "Delete"}
        </button>
      </div>
    </li>
  );
}

export default function DashboardPage() {
  const [documents, setDocuments] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [deletingId, setDeletingId] = useState(null);

  // Increasing refreshKey re-runs the loading effect (retry button, polling)
  const [refreshKey, setRefreshKey] = useState(0);
  const refresh = useCallback(() => setRefreshKey((key) => key + 1), []);

  useEffect(() => {
    let cancelled = false; // ignore answers that arrive after the page is left
    listDocuments()
      .then((data) => {
        if (cancelled) return;
        setDocuments(data);
        setError("");
      })
      .catch((err) => {
        if (!cancelled) setError(getErrorMessage(err, "Could not load your documents."));
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [refreshKey]);

  // While anything is "processing", refresh the list every few seconds
  const hasProcessing = documents.some((d) => d.status === "processing");
  useEffect(() => {
    if (!hasProcessing) {
      return;
    }
    const timerId = setTimeout(refresh, POLL_INTERVAL_MS);
    return () => clearTimeout(timerId);
  }, [hasProcessing, documents, refresh]);

  function handleUploaded(newDocuments) {
    setDocuments((current) => [...newDocuments, ...current]);
  }

  async function handleDelete(document) {
    const confirmed = window.confirm(
      `Delete "${document.original_filename}"? Its chat history will be deleted too. This cannot be undone.`,
    );
    if (!confirmed) {
      return;
    }

    setDeletingId(document.id);
    setError("");
    try {
      await deleteDocument(document.id);
      setDocuments((current) => current.filter((d) => d.id !== document.id));
    } catch (err) {
      setError(getErrorMessage(err, "Could not delete the document."));
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <>
      <UploadSection onUploaded={handleUploaded} />

      <section className="card">
        <div className="section-header">
          <h2>Your documents</h2>
          {hasProcessing && <span className="muted">Processing... this updates automatically</span>}
        </div>

        {error && (
          <div className="alert alert-error" role="alert">
            {error}{" "}
            <button type="button" className="btn-link" onClick={refresh}>
              Try again
            </button>
          </div>
        )}

        {isLoading ? (
          <p className="loading">Loading your documents...</p>
        ) : documents.length === 0 ? (
          <p className="muted">No documents yet. Upload a PDF above to start chatting with it.</p>
        ) : (
          <ul className="document-list">
            {documents.map((document) => (
              <DocumentRow
                key={document.id}
                document={document}
                isDeleting={deletingId === document.id}
                onDelete={handleDelete}
              />
            ))}
          </ul>
        )}
      </section>
    </>
  );
}
