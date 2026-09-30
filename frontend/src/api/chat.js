import { api } from "./client";

export async function listMessages(documentId) {
  const response = await api.get(`/api/documents/${documentId}/messages`);
  return response.data;
}

export async function askQuestion(documentId, question) {
  const response = await api.post(
    `/api/documents/${documentId}/chat`,
    { question },
    // Embedding + search + LLM (+ a possible dictionary lookup) can take a while
    { timeout: 90 * 1000 },
  );
  return response.data;
}
