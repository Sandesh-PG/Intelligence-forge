/**
 * Upload service — communicates with the FastAPI backend's POST /api/upload endpoint.
 * All API request logic is kept here, away from UI components.
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type UploadStatus = "accepted" | "rejected";

export interface FileUploadResult {
  original_filename: string;
  document_id: string | null;
  status: UploadStatus;
  rejection_reason: string | null;
}

export interface BatchUploadResponse {
  results: FileUploadResult[];
}

/**
 * Submit a batch of File objects to the backend upload endpoint.
 *
 * @param files - Array of File objects selected or dropped by the user.
 * @returns Parsed BatchUploadResponse from the backend.
 * @throws Error with a human-readable message on network or server failure.
 */
export async function uploadDocuments(
  files: File[]
): Promise<BatchUploadResponse> {
  const formData = new FormData();
  for (const file of files) {
    formData.append("files", file);
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

