import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { askQuestion, listMessages } from "../api/chat";
import { getDocument } from "../api/documents";
import { getErrorMessage } from "../api/errors";
import StatusBadge from "../components/StatusBadge";
import { formatDateTime } from "../utils/format";

const MAX_QUESTION_LENGTH = 2000;

function ChatMessage({ message, isPending = false }) {
  return (
    <li className="chat-exchange">
      <div className="chat-bubble chat-question">
        <p>{message.question}</p>
      </div>
      <div className="chat-bubble chat-answer">
        {isPending ? (
          <p className="typing" aria-live="polite">
            Thinking<span>.</span>
            <span>.</span>
            <span>.</span>
          </p>
        ) : (
          <>
            <p>{message.answer}</p>
            <div className="chat-meta">
              {message.used_tool && (
                <span className="badge badge-tool" title="The answer used the MCP get_word_definition tool">
                  Used dictionary tool
                </span>
              )}
              <span className="muted">{formatDateTime(message.created_at)}</span>
            </div>
          </>
        )}
      </div>
    </li>
  );
}

export default function ChatPage() {
  const { documentId } = useParams();

  const [document, setDocument] = useState(null);
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [notFound, setNotFound] = useState(false);

  const [question, setQuestion] = useState("");
  const [pendingQuestion, setPendingQuestion] = useState(null);
  const [sendError, setSendError] = useState("");
  const [inputError, setInputError] = useState("");

  const listEndRef = useRef(null);

  // Load the document and its chat history when the page opens
  useEffect(() => {
    let cancelled = false;
    Promise.all([getDocument(documentId), listMessages(documentId)])
      .then(([doc, history]) => {
        if (cancelled) return;
        setDocument(doc);
        setMessages(history);
      })
      .catch((err) => {
        if (cancelled) return;
        if (err.response?.status === 404 || err.response?.status === 422) {
          setNotFound(true);
        } else {
          setLoadError(getErrorMessage(err, "Could not load this chat."));
        }
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [documentId]);

  // Keep the newest message in view
  useEffect(() => {
    listEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, pendingQuestion]);

  async function sendQuestion() {
    const trimmed = question.trim();
    setSendError("");
    if (!trimmed) {
      setInputError("Type a question first.");
      return;
    }
    if (trimmed.length > MAX_QUESTION_LENGTH) {
      setInputError(`Questions can be at most ${MAX_QUESTION_LENGTH} characters.`);
      return;
    }

    setInputError("");
    setPendingQuestion(trimmed);
    setQuestion("");
    try {
      const message = await askQuestion(documentId, trimmed);
      setMessages((current) => [...current, message]);
    } catch (err) {
      setSendError(getErrorMessage(err, "Could not get an answer. Please try again."));
      setQuestion(trimmed); // give the question back so it can be re-sent
    } finally {
      setPendingQuestion(null);
    }
  }

  function handleSubmit(event) {
    event.preventDefault();
    sendQuestion();
  }

  // Enter sends, Shift+Enter adds a new line
  function handleKeyDown(event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      if (!pendingQuestion) sendQuestion();
    }
  }

  if (isLoading) {
    return (
      <div className="card">
        <p className="loading">Loading chat...</p>
      </div>
    );
  }

  if (notFound) {
    return (
      <div className="card">
        <h1>Document not found</h1>
        <p>This document doesn&apos;t exist or doesn&apos;t belong to you.</p>
        <Link to="/dashboard">Back to your documents</Link>
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="card">
        <div className="alert alert-error" role="alert">
          {loadError}
        </div>
        <Link to="/dashboard">Back to your documents</Link>
      </div>
    );
  }

  const isReady = document.status === "ready";
  const isSending = pendingQuestion !== null;

  return (
    <div className="card chat-card">
      <div className="chat-header">
        <Link to="/dashboard" className="muted">
          &larr; All documents
        </Link>
        <div className="document-title">
          <h1 className="chat-title" title={document.original_filename}>
            {document.original_filename}
          </h1>
          <StatusBadge status={document.status} />
        </div>
        <p className="muted">
          Answers come only from this PDF. Ask what a word means (e.g. &quot;What does
          authentication mean?&quot;) to use the dictionary tool.
        </p>
      </div>

      <section className="chat-history" aria-label="Chat history">
        <h2 className="visually-hidden">Chat history</h2>
        {messages.length === 0 && !isSending ? (
          <p className="muted chat-empty">No questions yet. Ask your first question below.</p>
        ) : (
          <ul className="chat-list">
            {messages.map((message) => (
              <ChatMessage key={message.id} message={message} />
            ))}
            {isSending && <ChatMessage message={{ question: pendingQuestion }} isPending />}
          </ul>
        )}
        <div ref={listEndRef} />
      </section>

      {sendError && (
        <div className="alert alert-error" role="alert">
          {sendError}
        </div>
      )}
      {!isReady && (
        <div className="alert alert-info" role="status">
          This document is {document.status}. You can ask questions once it is ready.
        </div>
      )}

      <form className="chat-form" onSubmit={handleSubmit} noValidate>
        <label htmlFor="question" className="visually-hidden">
          Your question
        </label>
        <textarea
          id="question"
          rows={2}
          placeholder="Ask a question about this PDF..."
          value={question}
          maxLength={MAX_QUESTION_LENGTH}
          onChange={(e) => {
            setQuestion(e.target.value);
            setInputError("");
          }}
          onKeyDown={handleKeyDown}
          disabled={!isReady || isSending}
          aria-invalid={inputError ? "true" : "false"}
        />
        <button type="submit" className="btn btn-small" disabled={!isReady || isSending}>
          {isSending ? "Sending..." : "Send"}
        </button>
      </form>
      {inputError && <p className="field-error">{inputError}</p>}
    </div>
  );
}
