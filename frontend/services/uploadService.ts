/**
 * Upload service — communicates with the FastAPI backend's POST /api/upload endpoint
 * and document extraction status endpoints.
 * All API request logic is kept here, away from UI components.
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type UploadStatus = "accepted" | "rejected";

export interface FileUploadResult {
  original_filename: string;
  document_id: string | null;
  doc_id?: string | null;
  status: UploadStatus;
  rejection_reason: string | null;
  session_id?: string | null;
}

export interface BatchUploadResponse {
  results: FileUploadResult[];
  session_id?: string | null;
}

/**
 * Submit a batch of File objects to the backend upload endpoint.
 *
 * @param files - Array of File objects selected or dropped by the user.
 * @param sessionId - Optional chat session ID to bind uploads to.
 * @returns Parsed BatchUploadResponse from the backend.
 * @throws Error with a human-readable message on network or server failure.
 */
export async function uploadDocuments(
  files: File[],
  sessionId?: string
): Promise<BatchUploadResponse> {
  const formData = new FormData();
  for (const file of files) {
    formData.append("files", file);
  }
  if (sessionId) {
    formData.append("session_id", sessionId);
  }

  const response = await fetch(`${API_BASE_URL}/api/upload`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    let detail = `Server returned ${response.status}`;
    try {
      const body = await response.json();
      if (body?.detail) detail = String(body.detail);
    } catch {
      // ignore JSON parse failure — use the status-based message
    }
    throw new Error(detail);
  }

  return response.json() as Promise<BatchUploadResponse>;
}

export type ExtractionJobStatus =
  | "uploaded"
  | "queued"
  | "parsing"
  | "extracting"
  | "completed"
  | "failed";

export interface DocumentStatusResponse {
  doc_id: string;
  original_filename: string;
  status: ExtractionJobStatus;
  page_count: number | null;
  entity_count: number | null;
  relationship_count: number | null;
  error_code: string | null;
  error_message: string | null;
  updated_at: string;
}

export async function getDocumentStatus(docId: string): Promise<DocumentStatusResponse> {
  const response = await fetch(
    `${API_BASE_URL}/api/documents/${encodeURIComponent(docId)}/status`,
    { cache: "no-store" }
  );

  if (!response.ok) {
    throw new Error(`Failed to fetch document status (${response.status})`);
  }

  return response.json() as Promise<DocumentStatusResponse>;
}

export async function triggerDocumentExtraction(docId: string): Promise<DocumentStatusResponse> {
  const response = await fetch(
    `${API_BASE_URL}/api/documents/${encodeURIComponent(docId)}/extract`,
    { method: "POST" }
  );

  if (!response.ok) {
    throw new Error(`Failed to re-trigger extraction (${response.status})`);
  }

  return response.json() as Promise<DocumentStatusResponse>;
}
