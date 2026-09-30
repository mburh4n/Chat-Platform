import { api } from "./client";

export async function listDocuments() {
  const response = await api.get("/api/documents");
  return response.data;
}

export async function getDocument(documentId) {
  const response = await api.get(`/api/documents/${documentId}`);
  return response.data;
}

// onProgress receives a number from 0 to 100 while the files are sent
export async function uploadDocuments(files, onProgress) {
  const formData = new FormData();
  for (const file of files) {
    formData.append("files", file);
  }

  const response = await api.post("/api/documents", formData, {
    // Overrides the JSON default; the browser adds the multipart boundary
    headers: { "Content-Type": "multipart/form-data" },
    timeout: 5 * 60 * 1000, // large files on slow connections
    onUploadProgress: (event) => {
      if (onProgress && event.total) {
        onProgress(Math.round((event.loaded / event.total) * 100));
      }
    },
  });
  return response.data;
}

export async function deleteDocument(documentId) {
  const response = await api.delete(`/api/documents/${documentId}`);
  return response.data;
}
