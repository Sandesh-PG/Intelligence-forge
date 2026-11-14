"use client";

/**
 * UploadZone — drag-and-drop and click-to-select area for PDF files.
 *
 * Enforces client-side constraints before submission:
 * - PDF files only (by extension and MIME type)
 * - Maximum 3 files per batch
 * - Maximum 20 MB per file
 * - Maximum 60 MB combined
 *
 * The backend also enforces all of these limits independently.
 */

import React, { useCallback, useRef, useState } from "react";

const MAX_FILES = 3;
const MAX_FILE_BYTES = 20 * 1024 * 1024; // 20 MB
const MAX_BATCH_BYTES = 60 * 1024 * 1024; // 60 MB

export interface SelectedFile {
  file: File;
  /** Client-side pre-validation error, if any. */
  clientError: string | null;
}

interface UploadZoneProps {
  selectedFiles: SelectedFile[];
  onChange: (files: SelectedFile[]) => void;
  disabled?: boolean;
}

function validateFiles(incoming: File[], existing: SelectedFile[]): SelectedFile[] {
  const updated: SelectedFile[] = [];

  let batchBytes = existing
    .filter((sf) => sf.clientError === null)
    .reduce((sum, sf) => sum + sf.file.size, 0);

  for (const file of incoming) {
    let clientError: string | null = null;

    const ext = file.name.split(".").pop()?.toLowerCase();
    if (ext !== "pdf" || (file.type !== "" && file.type !== "application/pdf")) {
      clientError = "Only PDF files are supported.";
    } else if (file.size === 0) {
      clientError = "File is empty.";
    } else if (file.size > MAX_FILE_BYTES) {
      clientError = `File size ${(file.size / 1024 / 1024).toFixed(1)} MB exceeds the 20 MB limit.`;
    } else if (batchBytes + file.size > MAX_BATCH_BYTES) {
      clientError = "Adding this file would exceed the 60 MB combined batch limit.";
    } else {
      batchBytes += file.size;
    }

    updated.push({ file, clientError });
  }

  return updated;
}

export default function UploadZone({
  selectedFiles,
  onChange,
  disabled = false,
}: UploadZoneProps) {
  const [isDragging, setIsDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const addFiles = useCallback(
    (incoming: File[]) => {
      const remaining = MAX_FILES - selectedFiles.length;
      if (remaining <= 0) return;

      const toAdd = incoming.slice(0, remaining);
      const validated = validateFiles(toAdd, selectedFiles);
      onChange([...selectedFiles, ...validated]);
    },
    [selectedFiles, onChange]
  );

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files ?? []);
    addFiles(files);
    // Reset so the same file can be re-selected after removal
    e.target.value = "";
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (!disabled) setIsDragging(true);
  };

  const handleDragLeave = () => setIsDragging(false);

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    if (disabled) return;
    const files = Array.from(e.dataTransfer.files);
    addFiles(files);
  };

  const handleClick = () => {
    if (!disabled) inputRef.current?.click();
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      handleClick();
    }
  };

  const isFull = selectedFiles.length >= MAX_FILES;
  const isInteractive = !disabled && !isFull;

  return (
    <div
      role="button"
      tabIndex={isInteractive ? 0 : -1}
      aria-label="Upload area: click or drag and drop PDF files here"
      aria-disabled={!isInteractive}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className={[
        "flex flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed px-6 py-10 text-center transition-colors",
        isInteractive
          ? "cursor-pointer hover:border-blue-500 hover:bg-blue-50 dark:hover:border-blue-400 dark:hover:bg-blue-950"
          : "cursor-not-allowed opacity-50",
        isDragging
          ? "border-blue-500 bg-blue-50 dark:border-blue-400 dark:bg-blue-950"
          : "border-zinc-300 dark:border-zinc-600",
      ].join(" ")}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,application/pdf"
        multiple
        className="sr-only"
        aria-hidden="true"
        tabIndex={-1}
        disabled={!isInteractive}
        onChange={handleInputChange}
      />
      <svg
        aria-hidden="true"
        xmlns="http://www.w3.org/2000/svg"
        className="h-10 w-10 text-zinc-400"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        strokeWidth={1.5}
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M9 13h6m-3-3v6m-9 1V7a2 2 0 012-2h6l2 2h6a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2z"
        />
      </svg>

      {isFull ? (
        <p className="text-sm text-zinc-500 dark:text-zinc-400">
          Maximum of {MAX_FILES} files selected.
        </p>
      ) : (
        <>
          <p className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
            Drag and drop PDFs here, or{" "}
            <span className="text-blue-600 underline dark:text-blue-400">
              click to select
            </span>
          </p>
          <p className="text-xs text-zinc-500 dark:text-zinc-400">
            Up to {MAX_FILES} PDFs · 20 MB per file · 60 MB total
          </p>
        </>
      )}
    </div>
  );
}

