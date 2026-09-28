import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import App from '../src/App';

describe('Scientific Paper Gap Finder - Frontend Application', () => {
  beforeEach(() => {
    // Mock global fetch for health check
    global.fetch = vi.fn().mockImplementation((url) => {
      if (typeof url === 'string' && url.includes('/health')) {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              status: 'healthy',
              version: '0.1.0',
              environment: 'development',
              timestamp: new Date().toISOString(),
              database: { status: 'connected', dialect: 'sqlite', fallback_in_use: true },
              services: { api: 'operational', llm_provider: 'gemini' },
            }),
        });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve([]),
      });
    });
  });

  it('renders application header and title correctly', async () => {
    render(<App />);
    const headings = screen.getAllByText(/Scientific Paper Gap Finder/i);
    expect(headings.length).toBeGreaterThanOrEqual(1);

    const phaseBadges = screen.getAllByText(/Phase 0 Foundation/i);
    expect(phaseBadges.length).toBeGreaterThanOrEqual(1);
  });

  it('renders architecture pipeline topology', async () => {
    render(<App />);
    const archTitle = screen.getByText(/System Architecture & Pipeline Topology/i);
    expect(archTitle).toBeDefined();

    expect(screen.getByText(/NetworkX Graph/i)).toBeDefined();
    const faissElements = screen.getAllByText(/FAISS/i);
    expect(faissElements.length).toBeGreaterThanOrEqual(1);
    const pgElements = screen.getAllByText(/PostgreSQL/i);
    expect(pgElements.length).toBeGreaterThanOrEqual(1);
  });

  it('renders modular components registry', async () => {
    render(<App />);
    const tableHeader = screen.getByText(/Subsystem Component/i);
    expect(tableHeader).toBeDefined();
  });

  it('renders scientific paper ingestion upload component', async () => {
    render(<App />);
    const uploadTitle = screen.getByText(/Scientific Paper Ingestion & PDF Parser/i);
    expect(uploadTitle).toBeDefined();

    const browsePrompt = screen.getByText(/Click to select PDF or drag and drop/i);
    expect(browsePrompt).toBeDefined();
  });
});
