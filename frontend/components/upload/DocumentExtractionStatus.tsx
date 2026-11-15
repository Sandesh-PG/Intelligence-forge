"use client";

import { useEffect, useState } from "react";
import {
    DocumentStatusResponse,
    ExtractionJobStatus,
    getDocumentStatus,
    triggerDocumentExtraction,
} from "@/services/uploadService";

const ACTIVE_STATES: ExtractionJobStatus[] = [
    "uploaded",
    "queued",
    "parsing",
    "extracting",
];

interface DocumentExtractionStatusProps {
    docId: string;
    originalFilename: string;
}

export function DocumentExtractionStatus({
    docId,
    originalFilename,
}: DocumentExtractionStatusProps) {
    const [job, setJob] = useState<DocumentStatusResponse | null>(null);
    const [retrying, setRetrying] = useState(false);
    const [pollTrigger, setPollTrigger] = useState(0);

    useEffect(() => {
        let cancelled = false;
        let timer: ReturnType<typeof setTimeout> | null = null;

        const poll = async () => {
            try {
                const data = await getDocumentStatus(docId);
                if (cancelled) return;
                setJob(data);
                if (ACTIVE_STATES.includes(data.status)) {
                    timer = setTimeout(poll, 2500);
                }
            } catch {
                if (!cancelled) {
                    timer = setTimeout(poll, 4000);
                }
            }
        };

        void poll();

        return () => {
            cancelled = true;
            if (timer) clearTimeout(timer);
        };
    }, [docId, pollTrigger]);

    const handleRetry = async () => {
        setRetrying(true);
        try {
            const updated = await triggerDocumentExtraction(docId);
            setJob(updated);
            setPollTrigger((prev) => prev + 1);
        } finally {
            setRetrying(false);
        }
    };

    const status = job?.status ?? "queued";

    return (
        <div
            className="mt-2 flex flex-wrap items-center justify-between gap-2 text-xs"
            aria-live="polite"
        >
            <div className="flex flex-wrap items-center gap-2">
                {(status === "uploaded" || status === "queued") && (
                    <span className="rounded bg-slate-100 px-2 py-0.5 font-medium text-slate-700">
                        Status: Queued for local extraction
                    </span>
                )}
                {status === "parsing" && (
                    <span className="rounded bg-amber-100 px-2 py-0.5 font-medium text-amber-800">
                        Status: Parsing PDF layout &amp; tables (Docling)...
                    </span>
                )}
                {status === "extracting" && (
                    <span className="rounded bg-blue-100 px-2 py-0.5 font-medium text-blue-800">
                        Status: Extracting entities &amp; relations (Ollama)...
                    </span>
                )}
                {status === "completed" && (
                    <span className="rounded bg-emerald-100 px-2 py-0.5 font-medium text-emerald-800">
                        Status: Completed — {job?.entity_count ?? 0} entities,{" "}
                        {job?.relationship_count ?? 0} relationships ({job?.page_count ?? 0}{" "}
                        pages)
                    </span>
                )}
                {status === "failed" && (
                    <span className="rounded bg-red-100 px-2 py-0.5 font-medium text-red-800">
                        Status: Failed ({job?.error_code ?? "ERROR"}) —{" "}
                        {job?.error_message ?? "Extraction failed."}
                    </span>
                )}
            </div>

            {status === "failed" && (
                <button
                    type="button"
                    onClick={handleRetry}
                    disabled={retrying}
                    aria-label={`Retry extraction for ${originalFilename}`}
                    className="rounded border border-slate-300 px-2.5 py-1 font-medium text-slate-700 hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-slate-500 disabled:opacity-50 dark:border-zinc-600 dark:text-zinc-200 dark:hover:bg-zinc-800"
                >
                    {retrying ? "Retrying..." : "Retry Extraction"}
                </button>
            )}
        </div>
    );
}