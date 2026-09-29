import React from 'react';
import { X, Settings, Moon, Sun, Laptop, ShieldCheck } from 'lucide-react';
import { useResearch } from '../../contexts/ResearchContext';
import { useTheme } from '../../contexts/ThemeContext';

export default function SettingsModal() {
  const { isSettingsOpen, setIsSettingsOpen } = useResearch();
  const { theme, setTheme } = useTheme();

  if (!isSettingsOpen) return null;

  return (
    <div className="modal-backdrop" onClick={() => setIsSettingsOpen(false)}>
      <div
        className="modal-container settings-modal"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="settings-modal-title"
      >
        <div className="modal-header">
          <div className="title-lockup">
            <Settings size={18} />
            <h3 id="settings-modal-title" className="modal-title">Settings & Configuration</h3>
          </div>
          <button className="modal-close-btn" onClick={() => setIsSettingsOpen(false)}>
            <X size={18} />
          </button>
        </div>

        <div className="settings-body">
          {/* Appearance Section */}
          <div className="setting-group">
            <h4 className="setting-group-title">Theme & Appearance</h4>
            <div className="theme-options-grid">
              <button
                className={`theme-card-option ${theme === 'dark' ? 'active' : ''}`}
                onClick={() => setTheme('dark')}
              >
                <Moon size={20} />
                <span className="theme-name">Dark</span>
                <span className="theme-desc">Near-black #0B0B0C for focused research</span>
              </button>

              <button
                className={`theme-card-option ${theme === 'light' ? 'active' : ''}`}
                onClick={() => setTheme('light')}
              >
                <Sun size={20} />
                <span className="theme-name">Light</span>
                <span className="theme-desc">Clean academic off-white theme</span>
              </button>

              <button
                className={`theme-card-option ${theme === 'system' ? 'active' : ''}`}
                onClick={() => setTheme('system')}
              >
                <Laptop size={20} />
                <span className="theme-name">System</span>
                <span className="theme-desc">Sync automatically with OS preference</span>
              </button>
            </div>
          </div>

          {/* Research NLP Pipeline Parameters */}
          <div className="setting-group">
            <h4 className="setting-group-title">Scientific NLP Configuration</h4>
            <div className="setting-row">
              <div>
                <label className="setting-label">Discourse Confidence Threshold</label>
                <p className="setting-help">Minimum classifier probability for limitation acceptance</p>
              </div>
              <span className="font-mono text-sm">0.70</span>
            </div>

            <div className="setting-row">
              <div>
                <label className="setting-label">Strict Provenance Assertion</label>
                <p className="setting-help">Require page number & section header for every extraction</p>
              </div>
              <input type="checkbox" defaultChecked className="setting-toggle" />
            </div>
          </div>
        </div>

        <div className="modal-footer">
          <button className="btn-primary" onClick={() => setIsSettingsOpen(false)}>
            Save & Close
          </button>
        </div>
      </div>
    </div>
  );
}
