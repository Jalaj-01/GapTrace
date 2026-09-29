import React, { useState, useEffect } from 'react';
import { ThemeProvider } from './contexts/ThemeContext';
import { ResearchProvider } from './contexts/ResearchContext';
import Sidebar from './components/layout/Sidebar';
import Header from './components/layout/Header';
import MainWorkspace from './components/layout/MainWorkspace';
import './App.css';

function GapTraceApp() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const handleResize = () => {
      const width = window.innerWidth;
      const mobile = width > 0 && width < 768;
      setIsMobile(mobile);
      if (mobile) {
        setIsSidebarOpen(false);
      } else {
        setIsSidebarOpen(true);
      }
    };

    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const toggleSidebar = () => {
    setIsSidebarOpen((prev) => !prev);
  };

  return (
    <div className={`gaptrace-shell ${isSidebarOpen ? 'sidebar-open' : 'sidebar-closed'}`}>
      {/* Mobile Backdrop */}
      {isMobile && isSidebarOpen && (
        <div
          className="sidebar-mobile-backdrop"
          onClick={() => setIsSidebarOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Left Sidebar */}
      <Sidebar
        isOpen={isSidebarOpen}
        onToggleCollapse={toggleSidebar}
        isMobile={isMobile}
      />

      {/* Main Content Area */}
      <div className="shell-workspace-area">
        <Header isSidebarOpen={isSidebarOpen} onToggleSidebar={toggleSidebar} />
        <MainWorkspace />
      </div>
    </div>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <ResearchProvider>
        <GapTraceApp />
      </ResearchProvider>
    </ThemeProvider>
  );
}
