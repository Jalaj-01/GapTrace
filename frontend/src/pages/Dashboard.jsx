import React from 'react';
import Header from '../components/Header';
import HealthCard from '../components/HealthCard';
import PaperUploadCard from '../components/PaperUploadCard';
import ArchitecturePipeline from '../components/ArchitecturePipeline';
import ModularComponentsView from '../components/ModularComponentsView';
import { useHealth } from '../hooks/useHealth';

export default function Dashboard() {
  const { healthData, error, lastChecked, loading, refetch } = useHealth(15000);

  return (
    <div className="dashboard-layout">
      {/* Top Header */}
      <Header
        healthData={healthData}
        error={error}
        onRefresh={refetch}
        loading={loading}
      />

      <main className="dashboard-content">
        {/* Live Diagnostics Card */}
        <section className="dashboard-section animate-fade-in">
          <HealthCard
            healthData={healthData}
            error={error}
            lastChecked={lastChecked}
          />
        </section>

        {/* Phase 1: PDF Ingestion & Parser */}
        <section className="dashboard-section animate-fade-in" style={{ animationDelay: '0.05s' }}>
          <PaperUploadCard />
        </section>

        {/* Visual Architecture Pipeline */}
        <section className="dashboard-section animate-fade-in" style={{ animationDelay: '0.1s' }}>
          <ArchitecturePipeline />
        </section>

        {/* Modular Component Registry */}
        <section className="dashboard-section animate-fade-in" style={{ animationDelay: '0.2s' }}>
          <ModularComponentsView />
        </section>
      </main>

      {/* Footer */}
      <footer className="dashboard-footer">
        <p>
          Scientific Paper Gap Finder &bull; Phase 0 Foundation Complete &bull; Backend: FastAPI &bull; Frontend: React + Vite
        </p>
      </footer>
    </div>
  );
}
