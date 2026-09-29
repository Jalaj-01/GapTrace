import React from 'react';
import {
  Compass,
  BookOpen,
  Layers,
  Target,
  Share2,
  FileSearch,
  Plus,
  Settings,
  HelpCircle,
  Sun,
  Moon,
  Laptop,
  ChevronRight,
  Sparkles,
  CheckCircle2,
} from 'lucide-react';
import { useResearch } from '../../contexts/ResearchContext';
import { useTheme } from '../../contexts/ThemeContext';

export default function Sidebar({ isOpen, onToggleCollapse, isMobile }) {
  const {
    activeView,
    setActiveView,
    activeSession,
    recentSessions,
    selectSession,
    startNewResearch,
    backendPapers,
    setIsSettingsOpen,
    setIsAboutOpen,
  } = useResearch();

  const { theme, effectiveTheme, setTheme } = useTheme();

  const navItems = [
    { id: 'welcome', label: 'New Research', icon: Sparkles },
    { id: 'papers', label: 'Papers', icon: BookOpen, count: backendPapers.length },
    { id: 'landscape', label: 'Research Landscape', icon: Layers },
    { id: 'gaps', label: 'Potential Gaps', icon: Target },
    { id: 'graph', label: 'Research Graph', icon: Share2 },
    { id: 'evidence', label: 'Evidence Explorer', icon: FileSearch },
  ];

  return (
    <aside
      className={`sidebar-root ${isOpen ? 'expanded' : 'collapsed'} ${isMobile ? 'mobile-drawer' : ''}`}
      aria-label="Application Sidebar"
    >
      {/* Top Header: GapTrace Branding */}
      <div className="sidebar-header">
        <div className="brand-lockup" onClick={startNewResearch} role="button" tabIndex={0}>
          <div className="logo-glyph" aria-hidden="true">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
              <path
                d="M12 2L2 7L12 12L22 7L12 2Z"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <path
                d="M2 17L12 22L22 17"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <path
                d="M2 12L12 17L22 12"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>
          {isOpen && (
            <div className="brand-text">
              <span className="brand-title">GapTrace</span>
              <span className="brand-tagline">Research Intelligence</span>
            </div>
          )}
        </div>
      </div>

      {/* New Research Action Button */}
      <div className="sidebar-action">
        <button
          className="new-research-btn"
          onClick={startNewResearch}
          title="Start New Research"
          aria-label="Start New Research"
        >
          <Plus size={16} />
          {isOpen && <span>New Research</span>}
        </button>
      </div>

      {/* Primary Navigation List */}
      <nav className="sidebar-nav">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeView === item.id;
          return (
            <button
              key={item.id}
              className={`nav-item-btn ${isActive ? 'active' : ''}`}
              onClick={() => setActiveView(item.id)}
              title={item.label}
              aria-current={isActive ? 'page' : undefined}
            >
              <Icon size={17} className="nav-icon" />
              {isOpen && <span className="nav-label">{item.label}</span>}
              {isOpen && typeof item.count === 'number' && (
                <span className="nav-badge">{item.count}</span>
              )}
            </button>
          );
        })}
      </nav>

      {/* Divider */}
      <div className="sidebar-divider" />

      {/* Recent Research Sessions */}
      <div className="sidebar-recent-section">
        {isOpen && <div className="recent-heading">Recent</div>}
        <div className="recent-list">
          {recentSessions.map((session) => {
            const isSessionActive = activeView === 'session' && activeSession?.id === session.id;
            return (
              <button
                key={session.id}
                className={`recent-item-btn ${isSessionActive ? 'active' : ''}`}
                onClick={() => selectSession(session.id)}
                title={session.title}
              >
                <div className="recent-bullet" />
                {isOpen && <span className="recent-title truncate">{session.title}</span>}
                {isOpen && isSessionActive && <ChevronRight size={13} className="recent-arrow" />}
              </button>
            );
          })}
        </div>
      </div>

      {/* Bottom Footer: Themes & Settings & User Profile */}
      <div className="sidebar-footer">
        {/* Minimal Theme Switcher */}
        <div className="theme-toggle-bar">
          <button
            className={`theme-btn ${theme === 'dark' ? 'active' : ''}`}
            onClick={() => setTheme('dark')}
            title="Dark theme"
            aria-label="Switch to Dark Theme"
          >
            <Moon size={14} />
          </button>
          <button
            className={`theme-btn ${theme === 'light' ? 'active' : ''}`}
            onClick={() => setTheme('light')}
            title="Light theme"
            aria-label="Switch to Light Theme"
          >
            <Sun size={14} />
          </button>
          <button
            className={`theme-btn ${theme === 'system' ? 'active' : ''}`}
            onClick={() => setTheme('system')}
            title="System theme"
            aria-label="Match System Theme"
          >
            <Laptop size={14} />
          </button>
          {isOpen && <span className="theme-current-label capitalize">{theme}</span>}
        </div>

        {/* Secondary Actions */}
        <div className="footer-links">
          <button
            className="footer-btn"
            onClick={() => setIsSettingsOpen(true)}
            title="Settings"
          >
            <Settings size={15} />
            {isOpen && <span>Settings</span>}
          </button>
          <button
            className="footer-btn"
            onClick={() => setIsAboutOpen(true)}
            title="Help / About"
          >
            <HelpCircle size={15} />
            {isOpen && <span>Help / About</span>}
          </button>
        </div>

        {/* User Profile Card */}
        <div className="user-profile-card">
          <div className="user-avatar" title="Jalaj Gupta (Lead Researcher)">
            <span>JG</span>
          </div>
          {isOpen && (
            <div className="user-details truncate">
              <span className="user-name">Jalaj Gupta</span>
              <span className="user-role">NLP Research Scholar</span>
            </div>
          )}
        </div>
      </div>
    </aside>
  );
}
