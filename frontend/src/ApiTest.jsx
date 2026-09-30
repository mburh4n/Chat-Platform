import { useState } from "react";

import { api } from "./api/client";
import { getErrorMessage, getFieldErrors } from "./api/errors";

// TEMPORARY: used to test the backend connection. Deleted in the next step.
export default function ApiTest() {
  const [result, setResult] = useState("Click a button to send a request.");
  const [loading, setLoading] = useState(false);

  async function run(label, request) {
    setLoading(true);
    setResult(`${label}: sending...`);
    try {
      const response = await request();
      setResult(
        `${label}: SUCCESS (${response.status})\n` +
          JSON.stringify(response.data, null, 2)
      );
    } catch (error) {
      setResult(
        `${label}: ERROR (${error.response?.status ?? "no response"})\n` +
          `Message: ${getErrorMessage(error)}\n` +
          `Field errors: ${JSON.stringify(getFieldErrors(error), null, 2)}`
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ maxWidth: 640, margin: "40px auto", fontFamily: "sans-serif" }}>
      <h1>API connection test</h1>
      <p>Backend: {import.meta.env.VITE_API_URL}</p>

      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <button disabled={loading} onClick={() => run("Health check", () => api.get("/api/health"))}>
          Health check
        </button>
        <button
          disabled={loading}
          onClick={() =>
            run("Wrong login", () =>
              api.post("/api/auth/login", {
                email: "nobody-here@example.com",
                password: "WrongPassword1",
              })
            )
          }
        >
          Wrong login (401)
        </button>
        <button
          disabled={loading}
          onClick={() =>
            run("Invalid sign-up", () =>
              api.post("/api/auth/signup", {
                name: "A",
                email: "not-an-email",
                password: "short",
              })
            )
          }
        >
          Invalid sign-up (422)
        </button>
      </div>

      <pre style={{ marginTop: 16, padding: 12, background: "#f4f5f7", whiteSpace: "pre-wrap" }}>
        {result}
      </pre>
    </div>
  );
}
