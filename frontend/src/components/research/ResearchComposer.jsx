import React, { useRef, useState } from 'react';
import {
  Paperclip,
  Search,
  ArrowUp,
  FileText,
  X,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Sparkles,
} from 'lucide-react';
import { useResearch } from '../../contexts/ResearchContext';

export default function ResearchComposer() {
  const {
    stagedFiles,
    stageAndUploadFiles,
    removeStagedFile,
    setIsUploaderOpen,
    runAnalysis,
    isAnalyzing,
    analysisStep,
    setActiveView,
  } = useResearch();

  const [promptText, setPromptText] = useState('');
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef(null);
  const textareaRef = useRef(null);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleSubmit = () => {
    if (isAnalyzing) return;
    if (promptText.trim() || stagedFiles.length > 0) {
      runAnalysis(promptText.trim());
    }
  };

  const handleFilesSelect = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      stageAndUploadFiles(e.target.files);
      e.target.value = '';
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const pdfs = Array.from(e.dataTransfer.files).filter(
        (f) => f.type === 'application/pdf' || f.name.endsWith('.pdf')
      );
      if (pdfs.length > 0) {
        stageAndUploadFiles(pdfs);
      }
    }
  };

  return (
    <div className="composer-wrapper">
      <div
        className={`composer-card ${isDragOver ? 'drag-over' : ''} ${isAnalyzing ? 'analyzing' : ''}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        {/* Hidden File Input for Native File Picker */}
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFilesSelect}
          multiple
          accept=".pdf,application/pdf"
          style={{ display: 'none' }}
        />

        {/* Drag Overlay Hint */}
        {isDragOver && (
          <div className="composer-drag-hint">
            <FileText size={28} />
            <span>Drop scientific PDF papers here</span>
          </div>
        )}

        {/* Staged File Cards List */}
        {stagedFiles.length > 0 && (
          <div className="staged-files-tray">
            {stagedFiles.map((file) => {
              const isReady = file.status === 'ready';
              const isFailed = file.status === 'failed';
              const isLoading = !isReady && !isFailed;

              return (
                <div key={file.id} className={`staged-paper-pill ${file.status}`}>
                  <FileText size={13} className="paper-pill-icon" />
                  <div className="paper-pill-meta">
                    <span className="paper-pill-name truncate" title={file.name}>
                      {file.name}
                    </span>
                    <span className="paper-pill-status">
                      {isLoading && <Loader2 size={10} className="spin-icon" />}
                      {isReady && <CheckCircle2 size={10} className="success-icon" />}
                      {isFailed && <AlertCircle size={10} className="error-icon" />}
                      <span>
                        {file.status === 'ready'
                          ? `${file.size} • Ready`
                          : file.status === 'failed'
                          ? 'Failed'
                          : `${file.status.charAt(0).toUpperCase() + file.status.slice(1)}...`}
                      </span>
                    </span>
                  </div>
                  <button
                    className="pill-remove-btn"
                    onClick={() => removeStagedFile(file.id)}
                    title="Remove paper"
                  >
                    <X size={12} />
                  </button>
                </div>
              );
            })}
          </div>
        )}

        {/* Input Textarea Area */}
        <div className="composer-input-row">
          <textarea
            ref={textareaRef}
            className="composer-textarea"
            rows={2}
            placeholder="Add research papers or ask a research question..."
            value={promptText}
            onChange={(e) => setPromptText(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isAnalyzing}
          />
        </div>

        {/* Bottom Toolbar */}
        <div className="composer-toolbar">
          <div className="toolbar-left">
            <button
              className="toolbar-btn add-papers-btn"
              onClick={() => setIsUploaderOpen(true)}
              title="Add research papers (PDF)"
              type="button"
            >
              <Paperclip size={15} />
              <span>Add Papers</span>
              {stagedFiles.length > 0 && (
                <span className="toolbar-count-badge">{stagedFiles.length}</span>
              )}
            </button>

            <button
              className="toolbar-btn search-evidence-btn"
              onClick={() => setActiveView('evidence')}
              title="Search Extracted Evidence Database"
              type="button"
            >
              <Search size={15} />
              <span>Search Evidence</span>
            </button>
          </div>

          <div className="toolbar-right">
            <button
              className={`analyze-submit-btn ${
                promptText.trim() || stagedFiles.length > 0 ? 'ready' : 'idle'
              }`}
              onClick={handleSubmit}
              disabled={isAnalyzing || (!promptText.trim() && stagedFiles.length === 0)}
              title="Start Gap Analysis"
              aria-label="Analyze research prompt and papers"
            >
              {isAnalyzing ? (
                <>
                  <Loader2 size={16} className="spin-icon" />
                  <span className="analyze-label">Analyzing...</span>
                </>
              ) : (
                <>
                  <span className="analyze-label">Analyze</span>
                  <ArrowUp size={16} />
                </>
              )}
            </button>
          </div>
        </div>

        {/* Live Multi-Stage Analysis Progress */}
        {isAnalyzing && (
          <div className="analysis-progress-strip">
            <div className="progress-bar-indeterminate" />
            <span className="progress-step-text">{analysisStep || 'Synthesizing scientific NLP graph...'}</span>
          </div>
        )}
      </div>
    </div>
  );
}
