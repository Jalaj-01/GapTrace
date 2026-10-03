import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import App from '../src/App';

describe('GapTrace: Lead Research-AI Interface', () => {
  beforeEach(() => {
    // Mock global fetch for health check and papers API
    global.fetch = vi.fn().mockImplementation((url) => {
      if (typeof url === 'string' && url.includes('/health')) {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              status: 'healthy',
              version: '0.2.0',
              environment: 'development',
              timestamp: new Date().toISOString(),
              database: { status: 'connected', dialect: 'sqlite', fallback_in_use: true },
              services: { api: 'operational', llm_provider: 'gemini' },
            }),
        });
      }
      if (typeof url === 'string' && url.includes('/papers')) {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve([
              {
                id: 1,
                filename: 'sample_paper.pdf',
                title: 'Attention Is All You Need',
                authors: ['Ashish Vaswani', 'Noam Shazeer'],
                year: 2017,
                file_size_bytes: 1200000,
                section_count: 7,
              },
            ]),
        });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve([]),
      });
    });
  });

  it('renders GapTrace branding and navigation elements', async () => {
    render(<App />);

    // Brand name
    const brandTitles = screen.getAllByText(/GapTrace/i);
    expect(brandTitles.length).toBeGreaterThanOrEqual(1);

    expect(screen.getByText(/Research Intelligence/i)).toBeDefined();

    // Primary action buttons
    const newResearchElements = screen.getAllByText(/New Research/i);
    expect(newResearchElements.length).toBeGreaterThanOrEqual(1);

    // Navigation links
    expect(screen.getByRole('button', { name: /^Papers/i })).toBeDefined();
    expect(screen.getByRole('button', { name: /Research Landscape/i })).toBeDefined();
    expect(screen.getByRole('button', { name: /Potential Gaps/i })).toBeDefined();
    expect(screen.getByRole('button', { name: /Research Graph/i })).toBeDefined();
    expect(screen.getByRole('button', { name: /Evidence Explorer/i })).toBeDefined();
  });

  it('renders welcome view with headline and research composer', async () => {
    render(<App />);

    // Main heading
    const heading = screen.getByText(/What would you like to research\?/i);
    expect(heading).toBeDefined();

    const subheading = screen.getByText(
      /Upload scientific papers and trace how research gaps emerge, evolve, and are addressed/i
    );
    expect(subheading).toBeDefined();

    // Research composer
    const textarea = screen.getByPlaceholderText(
      /Add research papers or ask a research question\.\.\./i
    );
    expect(textarea).toBeDefined();

    // Composer toolbar buttons
    expect(screen.getByText(/Add Papers/i)).toBeDefined();
    expect(screen.getByText(/Search Evidence/i)).toBeDefined();
    expect(screen.getByText(/Analyze/i)).toBeDefined();
  });

  it('renders research starters and allows initiating a research session', async () => {
    render(<App />);

    // Click starter chip to start an evidence-grounded research session
    const starterChip = screen.getByText(/Cross-dataset generalization/i);
    expect(starterChip).toBeDefined();
    fireEvent.click(starterChip);

    // Verify session top banner
    await waitFor(() => {
      expect(screen.getByText(/Research Session/i)).toBeDefined();
    });

    // Verify status badge
    expect(screen.getAllByText(/EMERGING/i).length).toBeGreaterThanOrEqual(1);

    // Verify evidence metric cards
    expect(screen.getByText(/Supporting evidence/i)).toBeDefined();
    expect(screen.getByText(/Addressing evidence/i)).toBeDefined();
    expect(screen.getAllByText(/Counter-evidence/i).length).toBeGreaterThanOrEqual(1);

    // Verify session tabs
    expect(screen.getByRole('button', { name: /^Overview/i })).toBeDefined();
    expect(screen.getAllByRole('button', { name: /^Evidence/i }).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByRole('button', { name: /^Timeline$/i })).toBeDefined();
    expect(screen.getByRole('button', { name: /^Genealogy$/i })).toBeDefined();
    expect(screen.getByRole('button', { name: /^Research Questions/i })).toBeDefined();
  });

  it('switches tabs in research session view to inspect timeline', async () => {
    render(<App />);

    // Open session
    const starterChip = screen.getByText(/Cross-dataset generalization/i);
    fireEvent.click(starterChip);

    // Wait for session to load
    await waitFor(() => {
      expect(screen.getByText(/Research Session/i)).toBeDefined();
    });

    // Click Timeline tab
    const timelineTab = screen.getByRole('button', { name: /^Timeline$/i });
    fireEvent.click(timelineTab);

    // Verify timeline view renders cleanly
    await waitFor(() => {
      expect(screen.getByText(/No timeline data available/i)).toBeDefined();
    });
  });

  it('supports light and dark theme switching with data-theme attribute', async () => {
    render(<App />);

    const darkBtn = screen.getByLabelText(/Switch to Dark Theme/i);
    const lightBtn = screen.getByLabelText(/Switch to Light Theme/i);

    fireEvent.click(lightBtn);
    expect(document.documentElement.getAttribute('data-theme')).toBe('light');

    fireEvent.click(darkBtn);
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark');
  });

  it('opens settings modal when settings action is triggered', async () => {
    render(<App />);

    // Click Settings button in sidebar
    const settingsBtn = screen.getByRole('button', { name: /Settings/i });
    fireEvent.click(settingsBtn);

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeDefined();
      expect(screen.getByText(/Settings & Configuration/i)).toBeDefined();
    });
  });
});
