import React, { useRef, useState } from 'react';
import {
  UploadCloud,
  FileText,
  X,
  CheckCircle2,
  AlertCircle,
  Loader2,
  FolderOpen,
  ArrowRight,
} from 'lucide-react';
import { useResearch } from '../../contexts/ResearchContext';

export default function PaperUploaderModal() {
  const {
    isUploaderOpen,
    setIsUploaderOpen,
    stagedFiles,
    stageAndUploadFiles,
    removeStagedFile,
    runAnalysis,
  } = useResearch();

  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef(null);

  if (!isUploaderOpen) return null;

  const handleFiles = (files) => {
    const pdfs = Array.from(files).filter(
      (f) => f.type === 'application/pdf' || f.name.endsWith('.pdf')
    );
    if (pdfs.length > 0) {
      stageAndUploadFiles(pdfs);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files) {
      handleFiles(e.dataTransfer.files);
    }
  };

  const allReady = stagedFiles.length > 0 && stagedFiles.every((f) => f.status === 'ready');

  return (
    <div className="modal-backdrop" onClick={() => setIsUploaderOpen(false)}>
      <div
        className="modal-container upload-modal"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="upload-modal-title"
      >
        {/* Header */}
        <div className="modal-header">
          <div>
            <h3 id="upload-modal-title" className="modal-title">
              Upload Scientific Papers
            </h3>
            <p className="modal-subtitle">
              Add PDF manuscripts to extract sentences, limitations, and provenance
            </p>
          </div>
          <button
            className="modal-close-btn"
            onClick={() => setIsUploaderOpen(false)}
            title="Close"
          >
            <X size={18} />
          </button>
        </div>

        {/* Drag & Drop Zone */}
        <div
          className={`upload-dropzone ${isDragOver ? 'drag-over' : ''}`}
          onDragOver={(e) => {
            e.preventDefault();
            setIsDragOver(true);
          }}
          onDragLeave={() => setIsDragOver(false)}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
        >
          <input
            type="file"
            ref={fileInputRef}
            onChange={(e) => {
              if (e.target.files) handleFiles(e.target.files);
            }}
            multiple
            accept=".pdf,application/pdf"
            style={{ display: 'none' }}
          />

          <div className="dropzone-icon">
            <UploadCloud size={36} />
          </div>
          <div className="dropzone-text">
            <span className="dropzone-primary">
              Drag & drop research PDF papers here
            </span>
            <span className="dropzone-secondary">
              or <span className="browse-link">browse files</span> from your computer
            </span>
          </div>
          <div className="dropzone-formats">
            <span>Standard Scientific PDF • Maximum 50 MB per file • Multi-file batch support</span>
          </div>
        </div>

        {/* Uploaded Paper Cards List */}
        {stagedFiles.length > 0 && (
          <div className="uploaded-papers-list">
            <div className="list-title-row">
              <span className="list-title">Staged Papers ({stagedFiles.length})</span>
            </div>

            <div className="paper-cards-grid">
              {stagedFiles.map((file) => {
                const isReady = file.status === 'ready';
                const isFailed = file.status === 'failed';
                const isBusy = !isReady && !isFailed;

                return (
                  <div key={file.id} className={`paper-upload-card ${file.status}`}>
                    <div className="card-file-icon">
                      <FileText size={18} />
                    </div>

                    <div className="card-info truncate">
                      <div className="card-filename truncate" title={file.name}>
                        {file.name}
                      </div>
                      <div className="card-sub-info">
                        <span className="card-size">{file.size}</span>
                        <span className="card-dot">•</span>
                        <span className={`card-status-badge ${file.status}`}>
                          {isBusy && <Loader2 size={11} className="spin-icon" />}
                          {isReady && <CheckCircle2 size={11} className="success-icon" />}
                          {isFailed && <AlertCircle size={11} className="error-icon" />}
                          <span className="capitalize">{file.status}</span>
                        </span>
                      </div>
                    </div>

                    <button
                      className="card-remove-btn"
                      onClick={() => removeStagedFile(file.id)}
                      title="Remove"
                    >
                      <X size={14} />
                    </button>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Modal Footer */}
        <div className="modal-footer">
          <button
            className="btn-secondary"
            onClick={() => setIsUploaderOpen(false)}
          >
            Close
          </button>
          <button
            className="btn-primary"
            onClick={() => {
              setIsUploaderOpen(false);
              runAnalysis();
            }}
            disabled={stagedFiles.length === 0}
          >
            <span>Start Gap Analysis</span>
            <ArrowRight size={15} />
          </button>
        </div>
      </div>
    </div>
  );
}
