import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import App from '../src/App';
import * as api from '../src/services/api';

vi.mock('../src/services/api');

describe('PHASE 10: End-to-End Research Intelligence Workflow', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('executes full pipeline: Upload paper -> process NLP -> search evidence -> view landscape -> view potential gap -> inspect genealogy -> inspect counter-evidence -> generate report', async () => {
    // 1. Initial State Mocks
    api.fetchHealth.mockResolvedValue({ success: true, data: { status: 'healthy' } });
    api.fetchPapers.mockResolvedValue([
      { id: 1, title: 'Invariance in Machine Learning', authors: ['Martin Arjovsky'], year: 2021, section_count: 5 },
    ]);
    api.fetchTopics.mockResolvedValue([{ topic_id: 101, topic_name: 'Invariant Representation' }]);

    // 2. Upload Paper Mock
    api.uploadPaperFile.mockResolvedValue({
      id: 2,
      filename: 'subpopulation_shift.pdf',
      title: 'Subpopulation Shift in Clinical NLP',
      year: 2024,
    });
    api.processPaperNLP.mockResolvedValue({
      paper_id: 2,
      sentences_count: 42,
      extractions_count: 18,
    });

    // 3. Search Evidence Mock
    api.searchSemanticEvidence.mockResolvedValue({
      query: 'subpopulation shift clinical notes',
      total_results: 1,
      retrieval_method: 'semantic_vector_faiss',
      results: [
        {
          source_text: 'Models experience catastrophic degradation under subpopulation shift in clinical notes.',
          similarity_score: 0.9412,
          paper: { paper_id: 2, title: 'Subpopulation Shift in Clinical NLP', year: 2024 },
          section: 'Discussion & Limitations',
          page: 9,
          extraction_type: 'LIMITATION',
        },
      ],
    });

    // 4. Landscape Mock
    api.fetchTopicsOverview.mockResolvedValue({
      total_topics: 1,
      major_topics: [],
      emerging_topics: [],
      declining_topics: [],
      persistent_topics: [
        {
          topic_id: 101,
          topic_name: 'Invariant Representation',
          status: 'PERSISTENT',
          paper_count: 6,
          sentence_count: 45,
          representative_terms: [{ term: 'causal', weight: 0.92 }],
          temporal_distribution: { '2021': 2, '2022': 2, '2024': 2 },
        },
      ],
      all_topics: [
        {
          topic_id: 101,
          topic_name: 'Invariant Representation',
          status: 'PERSISTENT',
          paper_count: 6,
          sentence_count: 45,
          representative_terms: [{ term: 'causal', weight: 0.92 }],
          temporal_distribution: { '2021': 2, '2022': 2, '2024': 2 },
        },
      ],
    });

    // 5. Gap Candidates Mock
    api.fetchGapCandidates.mockResolvedValue({
      total_candidates: 1,
      candidates: [
        {
          gap_id: 'gap-subpop-shift-01',
          title: 'Subpopulation Shift Generalization Failure',
          description: 'Performance degrades severely across hospital sites under demographic shift.',
          gap_type: 'repeated_limitation',
          gap_priority_score: 0.842,
          confidence: 0.91,
          supporting_papers: [{ paper_id: 1, year: 2021 }, { paper_id: 2, year: 2024 }],
          signals: { conflicting_evidence: 0.5 },
        },
      ],
    });
    api.fetchGapSignalsOverview.mockResolvedValue({ total_signals: 7 });

    // 6. Genealogy Mock
    api.fetchGapGenealogy.mockResolvedValue({
      gap_id: 'gap-subpop-shift-01',
      gap_title: 'Subpopulation Shift Generalization Failure',
      root_limitation: 'Spurious correlation reliance in standard ERM loss.',
      evolutionary_chain: [
        'Limitation Identified',
        'Attempted Solution',
        'Remaining Limitation',
        'Current Candidate Gap',
      ],
      total_transitions: 2,
      transitions: [
        {
          step_number: 1,
          stage_name: 'Limitation Identified',
          description: 'ERM models rely heavily on hospital-specific spurious background tokens.',
          relationship: 'limited_by',
          year: 2021,
          source_sentence: 'ERM optimizes for spurious artifacts.',
        },
        {
          step_number: 2,
          stage_name: 'Attempted Solution',
          description: 'Environment-balanced risk minimization fails on out-of-distribution demographic drift.',
          relationship: 'addresses',
          year: 2024,
          source_sentence: 'Mitigation remains incomplete.',
        },
      ],
    });

    // 7. Counter-Evidence Mock
    api.fetchGapCounterEvidence.mockResolvedValue({
      gap_id: 'gap-subpop-shift-01',
      counter_evidence: [
        {
          evidence_id: 'ce-1',
          paper_title: 'Robust Clinical Transfer',
          publication_year: 2024,
          source_text: 'Adversarial domain alignment reduces AUROC drop to under 3%.',
          nli_result: { label: 'CONTRADICTION', confidence: 0.88 },
        },
      ],
      addressed_by_evidence: [],
      contradictory_evidence: [],
    });
    api.fetchGapVerification.mockResolvedValue({
      gap_id: 'gap-subpop-shift-01',
      final_status: 'PARTIALLY_ADDRESSED',
      verification_confidence: 0.84,
      status_reasoning: 'Domain alignment provides partial mitigation, but unmodeled subpopulation shifts still degrade performance.',
    });

    // 8. Research Report Synthesis Mock
    api.synthesizeGapReport.mockResolvedValue({
      gap_id: 'gap-subpop-shift-01',
      gap_title: 'Subpopulation Shift Generalization Failure',
      provider: 'gemini',
      model: 'gemini-1.5-pro',
      gap_explanation: 'Clinical neural models suffer severe performance collapse on subpopulation shifts [E1].',
      why_it_matters: 'Poses direct patient safety hazards when deployed across disparate demographic cohorts.',
      supporting_evidence_summary: 'Evaluations across three healthcare systems exhibit up to 28% drop.',
      counter_evidence_summary: 'Adversarial alignment offers local mitigation but lacks guarantees [E2].',
      current_status: 'PERSISTENT',
      potential_research_questions: ['Can group-invariant representations bound clinical reasoning error?'],
      potential_future_directions: ['Design distributionally robust optimization for electronic health records.'],
      evidence_limitations: 'Evaluations limited to retrospective observational records.',
      citations: {
        E1: {
          citation_id: 'E1',
          paper_title: 'Subpopulation Shift in Clinical NLP',
          page: 9,
          section: 'Limitations',
          sentence_text: 'Models experience catastrophic degradation under subpopulation shift in clinical notes.',
        },
      },
      validation_report: {
        total_claims: 1,
        claims_with_citations: 1,
        supported_claims: 1,
        unsupported_claims: 0,
        contradicted_claims: 0,
        hallucinated_citations: 0,
        evidence_support_rate: 1.0,
        is_valid: true,
      },
      synthesized_at: new Date().toISOString(),
    });

    const { container } = render(<App />);

    // STEP 1: Navigate to Paper Library & Upload Paper
    const papersNavBtn = screen.getByRole('button', { name: /^Papers/i });
    fireEvent.click(papersNavBtn);

    await waitFor(() => {
      expect(screen.getByText(/Scientific Paper Library/i)).toBeDefined();
    });

    const fileInput = container.querySelector('input[type="file"]');
    const pdfFile = new File(['%PDF-1.4 paper content'], 'subpopulation_shift.pdf', { type: 'application/pdf' });
    fireEvent.change(fileInput, { target: { files: [pdfFile] } });

    await waitFor(() => {
      expect(api.uploadPaperFile).toHaveBeenCalledWith(pdfFile);
    });

    // STEP 2: Process NLP
    await waitFor(() => {
      expect(api.processPaperNLP).toHaveBeenCalledWith(2);
    });

    // STEP 3: Navigate to Evidence Explorer & Search Evidence
    const evidenceNavBtn = screen.getByRole('button', { name: /Evidence Explorer/i });
    fireEvent.click(evidenceNavBtn);

    await waitFor(() => {
      expect(screen.getByText(/Semantic Evidence Explorer/i)).toBeDefined();
    });

    const searchEvidenceBtn = screen.getByRole('button', { name: /Search Evidence/i });
    fireEvent.click(searchEvidenceBtn);

    await waitFor(() => {
      expect(api.searchSemanticEvidence).toHaveBeenCalled();
      expect(screen.getByText(/Models experience catastrophic degradation/i)).toBeDefined();
      expect(screen.getByText(/0.9412/i)).toBeDefined();
    });

    // STEP 4: Navigate to Research Landscape
    const landscapeNavBtn = screen.getByRole('button', { name: /Research Landscape/i });
    fireEvent.click(landscapeNavBtn);

    await waitFor(() => {
      expect(screen.getByText(/Research Landscape & Topic Discovery/i)).toBeDefined();
      expect(screen.getAllByText(/Invariant Representation/i).length).toBeGreaterThanOrEqual(1);
    });

    // STEP 5: Navigate to Potential Gaps
    const gapsNavBtn = screen.getByRole('button', { name: /Potential Gaps/i });
    fireEvent.click(gapsNavBtn);

    await waitFor(() => {
      expect(screen.getByText(/Potential Research Gaps Catalogue/i)).toBeDefined();
      expect(screen.getAllByText(/Subpopulation Shift Generalization Failure/i).length).toBeGreaterThanOrEqual(1);
    });

    // STEP 6: Inspect Gap Genealogy
    const genealogyBtn = screen.getByRole('button', { name: /^Gap Genealogy$/i });
    fireEvent.click(genealogyBtn);

    await waitFor(() => {
      expect(screen.getByText(/Gap Genealogy & Developmental Progression/i)).toBeDefined();
      expect(screen.getByText(/Spurious correlation reliance in standard ERM loss/i)).toBeDefined();
      expect(screen.getByText(/ERM models rely heavily on hospital-specific spurious background tokens/i)).toBeDefined();
    });

    // STEP 7: Inspect Counter-Evidence
    const counterNavBtn = screen.getByRole('button', { name: /^Counter-Evidence$/i });
    fireEvent.click(counterNavBtn);

    await waitFor(() => {
      expect(screen.getByText(/Counter-Evidence & Verification/i)).toBeDefined();
      expect(screen.getByText(/Adversarial domain alignment reduces AUROC drop/i)).toBeDefined();
      expect(screen.getByText(/CONTRADICTION/i)).toBeDefined();
    });

    // STEP 8: Generate Report
    const reportNavBtn = screen.getByRole('button', { name: /^Research Report$/i });
    fireEvent.click(reportNavBtn);

    await waitFor(() => {
      expect(screen.getByText(/Evidence-Grounded Research Report/i)).toBeDefined();
    });

    const generateBtn = screen.getByRole('button', { name: /Generate Grounded Report/i });
    fireEvent.click(generateBtn);

    await waitFor(() => {
      expect(api.synthesizeGapReport).toHaveBeenCalled();
      expect(screen.getByText(/Clinical neural models suffer severe performance collapse on subpopulation shifts/i)).toBeDefined();
      expect(screen.getByText(/Grounded Evidence Citations Map/i)).toBeDefined();
      expect(screen.getByText(/AUDIT VERDICT: VALID/i)).toBeDefined();
    });
  }, 30000);
});
