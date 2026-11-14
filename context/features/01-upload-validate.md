# 01 — Upload and Validate Research Papers

Allow users to upload research papers in PDF format through the application. Validate each file and store accepted PDFs locally, reporting the result for every file in the batch.

---

### PDF Upload Interface

- support PDF files only
- allow users to select or drag and drop multiple PDFs
- allow a maximum of 3 PDFs in one batch
- maximum file size is 20 MB per PDF
- maximum combined batch size is 60 MB
- display the selected files before upload
- allow users to remove a selected file before submitting

---

### Backend Upload and Validation

- implement the upload endpoint using the existing FastAPI backend
- validate every file independently
- accept a file only when:
  - its filename has a `.pdf` extension
  - its detected MIME type is `application/pdf`
  - its file signature contains the PDF header (`%PDF-`)
  - the file is readable and is not corrupted
  - the file is not empty
  - the file is not password-protected
- do not trust the filename or client-provided MIME type on its own
- enforce the 20 MB per-file limit and 3-file batch limit on the backend, not only in the UI
- reject unsupported, invalid, oversized, corrupted, unreadable, or password-protected files with a clear reason
- process validation per file so one invalid PDF does not reject valid PDFs in the same batch

---

### Local File Storage

- store accepted PDFs on the backend filesystem
- use a private storage directory at `backend/storage/uploads/`
- do not store uploaded files in a publicly accessible frontend directory
- generate a unique server-side ID and use it as the stored filename
- preserve the original filename as metadata
- allow different files to have the same original filename without overwriting one another
- keep the storage implementation isolated so a different storage provider can be introduced later

---

### Upload Results and Status

- return an individual result for every file in the batch
- for each file, report:
  - original filename
  - generated document ID when accepted
  - upload status
  - rejection reason when rejected
- show each file's result in the UI
- clearly distinguish successful uploads from rejected files
- provide a way to retry failed files
- mark successfully stored files as uploaded and ready for the next ingestion feature
- do not start PDF text extraction, multimodal processing, summarization, entity/relationship extraction, or database indexing in this feature

---

### Metadata Handling

- keep upload metadata in memory for this initial version
- metadata should include the document ID, original filename, stored filename, file size, upload timestamp, and upload status
- metadata is temporary and will be lost when the backend process restarts
- uploaded PDF files remain on disk after a backend restart; persistent metadata storage is not part of this feature

---

### Check when done

- users can upload one or more PDFs, up to 3 per batch
- the UI and backend enforce the 20 MB per-file limit and 60 MB total batch limit
- invalid files are rejected with a useful reason
- valid files in a mixed batch are accepted even when another file is rejected
- accepted PDFs are stored using unique generated filenames in the private backend storage directory
- original filenames are preserved as metadata
- each file's upload result is visible in the UI, with retry available for failed files
- upload metadata is held in memory and is not represented as persistent across backend restarts
- no extraction, LLM, Neo4j, or Qdrant processing is triggered by this feature
- the implementation passes relevant frontend, backend, and upload-validation checks
