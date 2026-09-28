import React, { useState } from 'react';
import { UploadCloud, FileText, CheckCircle, AlertCircle, ChevronDown, ChevronRight, Hash, Calendar, Users, Code, BookOpen } from 'lucide-react';
import { uploadPaperFile } from '../services/api';

export default function PaperUploadCard({ onUploadSuccess }) {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const [activeSectionIdx, setActiveSectionIdx] = useState(0);
  const [showRawJson, setShowRawJson] = useState(false);

  const handleFileChange = (e) => {
    const selected = e.target.files?.[0];
    if (selected) {
      if (!selected.name.toLowerCase().endsWith('.pdf')) {
        setError('Please select a valid scientific paper in PDF format (.pdf).');
        setFile(null);
        return;
      }
      setFile(selected);
      setError(null);
      setResult(null);
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    setError(null);

    try {
      const data = await uploadPaperFile(file);
      setResult(data);
      if (onUploadSuccess) onUploadSuccess(data);
    } catch (err) {
      setError(err.message || 'An error occurred during paper ingestion.');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="upload-card glass-card">
      <div className="card-header">
        <div className="card-title-group">
          <UploadCloud className="section-icon text-indigo" size={20} />
          <h2 className="card-title">Scientific Paper Ingestion & PDF Parser</h2>
        </div>
        <span className="badge badge-indigo">Phase 1 Active</span>
      </div>

      <p className="card-description">
        Upload a research paper in PDF format. The document will be validated, stored securely, and parsed
        into structured sections, author metadata, abstract, and bibliography citations.
      </p>

      {/* Upload Drop Zone */}
      <div className="upload-dropzone">
        <input
          type="file"
          id="pdf-upload-input"
          accept=".pdf,application/pdf"
          onChange={handleFileChange}
          style={{ display: 'none' }}
        />
        <label htmlFor="pdf-upload-input" className="dropzone-label">
          <FileText size={36} className="dropzone-icon text-cyan" />
          <div className="dropzone-text">
            {file ? (
              <span className="selected-filename">{file.name} ({(file.size / 1024).toFixed(1)} KB)</span>
            ) : (
              <>
                <span className="browse-prompt">Click to select PDF or drag and drop</span>
                <span className="format-hint">Standard two-column or single-column scientific papers up to 25MB</span>
              </>
            )}
          </div>
        </label>

        {file && (
          <div className="upload-btn-row">
            <button
              className="action-btn upload-submit-btn"
              onClick={handleUpload}
              disabled={uploading}
            >
              {uploading ? (
                <>
                  <span className="spinner-icon"></span>
                  <span>Extracting Structure & Parsing Sections...</span>
                </>
              ) : (
                <>
                  <UploadCloud size={16} />
                  <span>Ingest & Extract Paper</span>
                </>
              )}
            </button>
            <button
              className="action-btn-secondary"
              onClick={() => { setFile(null); setResult(null); setError(null); }}
              disabled={uploading}
            >
              Clear
            </button>
          </div>
        )}
      </div>

      {/* Error Message */}
      {error && (
        <div className="error-banner animate-fade-in">
          <AlertCircle size={18} className="text-rose flex-shrink-0" />
          <div className="error-text">
            <strong>Ingestion Error:</strong> {error}
          </div>
        </div>
      )}

      {/* Extracted Structured Paper View */}
      {result && (
        <div className="extracted-result-view animate-fade-in">
          <div className="result-header">
            <div className="result-status-badge">
              <CheckCircle size={16} className="text-green" />
              <span>Paper Successfully Ingested (ID #{result.paper_id})</span>
            </div>
            <button
              className="json-toggle-btn"
              onClick={() => setShowRawJson(!showRawJson)}
            >
              <Code size={14} />
              <span>{showRawJson ? 'Hide Structured JSON' : 'View Structured JSON'}</span>
            </button>
          </div>

          {/* Paper Metadata Card */}
          <div className="paper-meta-summary">
            <h3 className="paper-title-display">{result.title}</h3>

            <div className="meta-chips-row">
              {result.authors && result.authors.length > 0 && (
                <div className="meta-chip">
                  <Users size={13} className="text-cyan" />
                  <span>{result.authors.join(', ')}</span>
                </div>
              )}
              {result.year && (
                <div className="meta-chip">
                  <Calendar size={13} className="text-indigo" />
                  <span>Year: {result.year}</span>
                </div>
              )}
              {result.page_count && (
                <div className="meta-chip">
                  <BookOpen size={13} className="text-green" />
                  <span>{result.page_count} Pages</span>
                </div>
              )}
              {result.doi && (
                <div className="meta-chip">
                  <Hash size={13} className="text-amber" />
                  <span>DOI: {result.doi}</span>
                </div>
              )}
            </div>

            {result.abstract && (
              <div className="abstract-box">
                <span className="abstract-tag">Abstract</span>
                <p className="abstract-text">{result.abstract}</p>
              </div>
            )}
          </div>

          {/* Raw JSON Mode */}
          {showRawJson ? (
            <div className="json-container">
              <pre className="json-code-block">{JSON.stringify(result, null, 2)}</pre>
            </div>
          ) : (
            /* Sections and References Tabs */
            <div className="sections-container">
              <h4 className="sections-heading">
                Extracted Sections ({result.sections?.length || 0})
              </h4>

              <div className="sections-layout">
                {/* Section List sidebar */}
                <div className="sections-nav-list">
                  {result.sections?.map((sec, idx) => (
                    <button
                      key={idx}
                      className={`section-nav-item ${activeSectionIdx === idx ? 'active' : ''}`}
                      onClick={() => setActiveSectionIdx(idx)}
                    >
                      <span className="nav-sec-name">{sec.name}</span>
                      <span className="nav-sec-pages">p. {sec.page_start}{sec.page_end !== sec.page_start ? `-${sec.page_end}` : ''}</span>
                    </button>
                  ))}
                </div>

                {/* Section Content Display */}
                {result.sections && result.sections[activeSectionIdx] && (
                  <div className="active-section-panel">
                    <div className="panel-header">
                      <h5 className="panel-title">{result.sections[activeSectionIdx].name}</h5>
                      <span className="page-range-pill">
                        Pages {result.sections[activeSectionIdx].page_start} - {result.sections[activeSectionIdx].page_end}
                      </span>
                    </div>

                    <div className="panel-body">
                      {result.sections[activeSectionIdx].paragraphs?.length > 0 ? (
                        result.sections[activeSectionIdx].paragraphs.map((p, pIdx) => (
                          <p key={pIdx} className="section-paragraph">{p}</p>
                        ))
                      ) : (
                        <p className="section-paragraph">{result.sections[activeSectionIdx].text}</p>
                      )}
                    </div>
                  </div>
                )}
              </div>

              {/* Bibliographic References */}
              {result.references && result.references.length > 0 && (
                <div className="references-section">
                  <h4 className="sections-heading">
                    Parsed Bibliographic References ({result.references.length})
                  </h4>
                  <div className="references-list">
                    {result.references.map((ref, idx) => (
                      <div key={idx} className="reference-item">
                        <span className="ref-number">[{ref.ref_index}]</span>
                        <div className="ref-details">
                          <p className="ref-text">{ref.raw_text}</p>
                          {ref.year && <span className="ref-year-badge">Year: {ref.year}</span>}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
