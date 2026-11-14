"use client";

/**
 * FileList — displays selected files with their pre-validation state,
 * a remove button for each, and post-upload result badges.
 */

import type { FileUploadResult } from "@/services/uploadService";
import type { SelectedFile } from "./UploadZone";

interface FileListProps {
  files: SelectedFile[];
  results: Map<string, FileUploadResult>;
  onRemove: (index: number) => void;
  onRetry: (index: number) => void;
  uploading: boolean;
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export default function FileList({
  files,
  results,
  onRemove,
  onRetry,
  uploading,
}: FileListProps) {
  if (files.length === 0) return null;

  return (
    <ul className="mt-4 space-y-2" aria-label="Selected files">
      {files.map((sf, index) => {
        const result = results.get(sf.file.name + "_" + index);
        const hasClientError = sf.clientError !== null;

        // Determine visual status
        let statusLabel: string;
        let statusClass: string;
        let statusDetail: string | null = null;

        if (result) {
          if (result.status === "accepted") {
            statusLabel = "Uploaded";
            statusClass =
              "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200";
          } else {
            statusLabel = "Rejected";
            statusClass =
              "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200";
            statusDetail = result.rejection_reason;
          }
        } else if (hasClientError) {
          statusLabel = "Invalid";
          statusClass =
            "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200";
          statusDetail = sf.clientError;
        } else if (uploading) {
          statusLabel = "Uploading…";
          statusClass =
            "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200";
        } else {
          statusLabel = "Ready";
          statusClass =
            "bg-zinc-100 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300";
        }

        const isRejected =
          (result && result.status === "rejected") || hasClientError;
        const canRetry = isRejected && !uploading;

        return (
          <li
            key={`${sf.file.name}-${index}`}
            className="flex flex-col gap-1 rounded-md border border-zinc-200 bg-white px-3 py-2 dark:border-zinc-700 dark:bg-zinc-900"
          >
            <div className="flex items-center gap-2">
              {/* File icon */}
              <svg
                aria-hidden="true"
                xmlns="http://www.w3.org/2000/svg"
                className="h-5 w-5 shrink-0 text-zinc-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={1.5}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"
                />
              </svg>

              {/* Filename + size */}
              <span className="min-w-0 flex-1 truncate text-sm text-zinc-800 dark:text-zinc-200">
                {sf.file.name}
              </span>
              <span className="shrink-0 text-xs text-zinc-400">
                {formatBytes(sf.file.size)}
              </span>

              {/* Status badge */}
              <span
                className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${statusClass}`}
                aria-label={`Status: ${statusLabel}`}
              >
                {statusLabel}
              </span>

              {/* Remove button (shown when not currently uploading and no accepted result yet) */}
              {!uploading && !(result && result.status === "accepted") && (
                <button
                  type="button"
                  aria-label={`Remove ${sf.file.name}`}
                  onClick={() => onRemove(index)}
                  className="shrink-0 rounded p-0.5 text-zinc-400 hover:bg-zinc-100 hover:text-zinc-600 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:hover:bg-zinc-700 dark:hover:text-zinc-300"
                >
                  <svg
                    aria-hidden="true"
                    xmlns="http://www.w3.org/2000/svg"
                    className="h-4 w-4"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2}
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M6 18L18 6M6 6l12 12"
                    />
                  </svg>
                </button>
              )}
            </div>

            {/* Rejection / error detail */}
            {statusDetail && (
              <p
                className="ml-7 text-xs text-red-600 dark:text-red-400"
                role="alert"
              >
                {statusDetail}
              </p>
            )}

            {/* Retry button for failed files */}
            {canRetry && (
              <button
                type="button"
                onClick={() => onRetry(index)}
                className="ml-7 mt-1 w-fit rounded-md border border-zinc-300 bg-white px-2 py-0.5 text-xs font-medium text-zinc-700 hover:bg-zinc-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:border-zinc-600 dark:bg-zinc-800 dark:text-zinc-300 dark:hover:bg-zinc-700"
              >
                Retry
              </button>
            )}
          </li>
        );
      })}
    </ul>
  );
}

