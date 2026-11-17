"use client";

/**
 * UploadPanel — top-level upload feature panel.
 *
 * Composes UploadZone (drag-and-drop selection) and FileList (selected files
 * with per-file results) into the complete upload experience.
 *
 * State responsibilities:
 * - selectedFiles: files chosen by the user (pre-upload)
 * - results:       per-file outcomes returned by the backend
 * - uploading:     whether a batch submission is in-flight
 * - batchError:    a batch-level error (e.g., too many files sent)
 */

import { useCallback, useState } from "react";
import type { FileUploadResult } from "@/services/uploadService";
import { uploadDocuments } from "@/services/uploadService";
import UploadZone, { type SelectedFile } from "./UploadZone";
import FileList from "./FileList";

interface UploadPanelProps {
  sessionId?: string;
  onUploadSuccess?: () => void;
}

export default function UploadPanel({ sessionId, onUploadSuccess }: UploadPanelProps = {}) {
  const [selectedFiles, setSelectedFiles] = useState<SelectedFile[]>([]);
  const [results, setResults] = useState<Map<string, FileUploadResult>>(
    new Map()
  );
  const [uploading, setUploading] = useState(false);
  const [batchError, setBatchError] = useState<string | null>(null);

  /** Key used to correlate a SelectedFile with its result. */
  const fileKey = (sf: SelectedFile, index: number) =>
    sf.file.name + "_" + index;

  const handleRemove = useCallback((index: number) => {
    setSelectedFiles((prev) => prev.filter((_, i) => i !== index));
    setResults((prev) => {
      const next = new Map(prev);
      next.delete(`${prev.keys().next().value}_${index}`);
      return next;
    });
  }, []);

  const handleRetry = useCallback(
    (index: number) => {
      // Remove the rejected file from the list so the user can re-add it.
      setSelectedFiles((prev) => prev.filter((_, i) => i !== index));
      setResults((prev) => {
        const keys = Array.from(prev.keys());
        const next = new Map(prev);
        next.delete(keys[index]);
        return next;
      });
    },
    []
  );

  const handleUpload = async () => {
    const valid = selectedFiles.filter((sf) => sf.clientError === null);
    if (valid.length === 0) return;

    setBatchError(null);
    setUploading(true);

    try {
      const response = await uploadDocuments(
        valid.map((sf) => sf.file),
        sessionId
      );

      // Map results back to selected files by index into the valid subset
      const nextResults = new Map(results);
      let validIndex = 0;
      selectedFiles.forEach((sf, i) => {
        if (sf.clientError !== null) return;
        const result = response.results[validIndex];
        if (result) nextResults.set(fileKey(sf, i), result);
        validIndex++;
      });
      setResults(nextResults);
      if (onUploadSuccess) {
        onUploadSuccess();
      }
    } catch (err) {
      setBatchError(
        err instanceof Error ? err.message : "Upload failed. Please try again."
      );
    } finally {
      setUploading(false);
    }
  };

  const validFileCount = selectedFiles.filter(
    (sf) => sf.clientError === null
  ).length;

  const allDone =
    selectedFiles.length > 0 &&
    selectedFiles.every((sf, i) => {
      if (sf.clientError !== null) return true; // client-invalid files don't need uploading
      return results.has(fileKey(sf, i));
    });

  return (
    <section aria-labelledby="upload-heading" className="w-full max-w-xl">
      <h2
        id="upload-heading"
        className="mb-4 text-lg font-semibold text-zinc-900 dark:text-zinc-100"
      >
        Upload Research Papers
      </h2>

      <UploadZone
        selectedFiles={selectedFiles}
        onChange={setSelectedFiles}
        disabled={uploading}
      />

      <FileList
        files={selectedFiles}
        results={results}
        onRemove={handleRemove}
        onRetry={handleRetry}
        uploading={uploading}
      />

      {/* Batch-level error */}
      {batchError && (
        <p
          role="alert"
          className="mt-3 text-sm text-red-600 dark:text-red-400"
        >
          {batchError}
        </p>
      )}

      {/* Upload button */}
      {validFileCount > 0 && !allDone && (
        <button
          type="button"
          disabled={uploading}
          onClick={handleUpload}
          className="mt-4 inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60 dark:bg-blue-500 dark:hover:bg-blue-600"
        >
          {uploading ? (
            <>
              <svg
                aria-hidden="true"
                className="h-4 w-4 animate-spin"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8v8H4z"
                />
              </svg>
              Uploading…
            </>
          ) : (
            `Upload ${validFileCount} file${validFileCount !== 1 ? "s" : ""}`
          )}
        </button>
      )}

      {/* All done summary */}
      {allDone && selectedFiles.length > 0 && (
        <p className="mt-4 text-sm text-zinc-600 dark:text-zinc-400">
          Upload complete.{" "}
          <button
            type="button"
            className="font-medium text-blue-600 underline dark:text-blue-400"
            onClick={() => {
              setSelectedFiles([]);
              setResults(new Map());
              setBatchError(null);
            }}
          >
            Upload more files
          </button>
        </p>
      )}
    </section>
  );
}

