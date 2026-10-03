import React, { useEffect, useState } from 'react';
import { Menu, PanelLeftClose, PanelLeftOpen, ShieldCheck, AlertCircle, FileUp, Sparkles } from 'lucide-react';
import { useResearch } from '../../contexts/ResearchContext';
import { fetchHealth } from '../../services/api';

export default function Header({ isSidebarOpen, onToggleSidebar }) {
  const { activeView, activeSession, setIsUploaderOpen, startNewResearch } = useResearch();
  const [healthStatus, setHealthStatus] = useState({ online: true, dialect: 'sqlite' });

  useEffect(() => {
    let isMounted = true;
    const check = async () => {
      const res = await fetchHealth();
      if (isMounted) {
        if (res.success && res.data?.status === 'healthy') {
          setHealthStatus({ online: true, dialect: res.data.database?.dialect || 'sqlite' });
        } else {
          setHealthStatus({ online: false, dialect: 'offline' });
        }
      }
    };
    check();
    const interval = setInterval(check, 30000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  const getViewTitle = () => {
    switch (activeView) {
      case 'dashboard':
        return 'Dashboard';
      case 'welcome':
        return 'Research Workspace';
      case 'session':
        return activeSession?.title || 'Research Session';
      case 'papers':
        return 'Paper Library';
      case 'paper-detail':
        return 'Paper Detail';
      case 'landscape':
        return 'Research Landscape';
      case 'graph':
        return 'Interactive Research Graph';
      case 'gaps':
        return 'Potential Gaps Catalogue';
      case 'gap-detail':
        return 'Gap Detail';
      case 'genealogy':
        return 'Gap Genealogy';
      case 'lifecycle':
        return 'Gap Lifecycle';
      case 'counter-evidence':
        return 'Counter-Evidence Verification';
      case 'evidence':
        return 'Evidence Explorer';
      case 'report':
        return 'Research Report';
      default:
        return 'Research Workspace';
    }
  };

  return (
    <header className="header-root">
      <div className="header-left">
        <button
          className="sidebar-toggle-btn"
          onClick={onToggleSidebar}
          title={isSidebarOpen ? 'Collapse sidebar' : 'Expand sidebar'}
          aria-label={isSidebarOpen ? 'Collapse sidebar' : 'Expand sidebar'}
        >
          {isSidebarOpen ? <PanelLeftClose size={18} /> : <PanelLeftOpen size={18} />}
        </button>

        <div className="header-breadcrumb">
          <span className="crumb-root" onClick={startNewResearch} role="button">
            GapTrace
          </span>
          <span className="crumb-sep">/</span>
          <span className="crumb-current truncate">{getViewTitle()}</span>
        </div>
      </div>

      <div className="header-right">
        {/* Backend Connectivity Status */}
        <div
          className={`health-badge ${healthStatus.online ? 'healthy' : 'offline'}`}
          title={`Backend API is ${healthStatus.online ? 'Online' : 'Offline'}`}
        >
          <div className="status-dot" />
          <span className="status-label">{healthStatus.online ? 'API Online' : 'Offline'}</span>
        </div>

        {/* Quick Add Papers CTA */}
        <button
          className="quick-upload-btn"
          onClick={() => setIsUploaderOpen(true)}
          title="Upload Research Papers"
        >
          <FileUp size={15} />
          <span>Upload PDF</span>
        </button>
      </div>
    </header>
  );
}
