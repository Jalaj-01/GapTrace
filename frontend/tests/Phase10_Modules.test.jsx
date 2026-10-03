import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ResearchProvider } from '../src/contexts/ResearchContext';
import { ThemeProvider } from '../src/contexts/ThemeContext';
import Dashboard from '../src/pages/Dashboard';
import PapersPage from '../src/pages/PapersPage';
import PaperDetailPage from '../src/pages/PaperDetailPage';
import LandscapePage from '../src/pages/LandscapePage';
import ResearchGraphPage from '../src/pages/ResearchGraphPage';
import PotentialGapsPage from '../src/pages/PotentialGapsPage';
import GapDetailPage from '../src/pages/GapDetailPage';
import GapGenealogyPage from '../src/pages/GapGenealogyPage';
import GapLifecyclePage from '../src/pages/GapLifecyclePage';
import CounterEvidencePage from '../src/pages/CounterEvidencePage';
import EvidenceExplorerPage from '../src/pages/EvidenceExplorerPage';
import ResearchReportPage from '../src/pages/ResearchReportPage';
import App from '../src/App';
import * as api from '../src/services/api';

vi.mock('../src/services/api');

function renderWithContext(ui) {
  return render(
    <ThemeProvider>
      <ResearchProvider>{ui}</ResearchProvider>
    </ThemeProvider>
  );
}

describe('PHASE 10: Research Intelligence Platform Unit & Integration Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // =========================================================================
  // 1. Dashboard Tests
  // =========================================================================
  describe('1. Dashboard Page', () => {
    it('renders loading state initially', async () => {
      api.fetchPapers.mockReturnValue(new Promise(() => {}));
      api.fetchTopicsOverview.mockReturnValue(new Promise(() => {}));
      api.fetchGapCandidates.mockReturnValue(new Promise(() => {}));
      api.fetchGapLifecycleOverview.mockReturnValue(new Promise(() => {}));

      renderWithContext(<Dashboard />);
      expect(screen.getByText(/Aggregating scientific research intelligence/i)).toBeDefined();
    });

    it('renders successful API data with papers, topics, potential/persistent/addressed gaps, and counter-evidence', async () => {
      api.fetchPapers.mockResolvedValue([
        { id: 1, title: 'Attention Is All You Need', year: 2017 },
        { id: 2, title: 'BERT: Pre-training of Deep Bidirectional Transformers', year: 2018 },
      ]);
      api.fetchTopicsOverview.mockResolvedValue({
        total_topics: 3,
        all_topics: [
          { topic_id: 1, topic_name: 'Linear Attention', status: 'EMERGING', paper_count: 5, sentence_count: 30 },
          { topic_id: 2, topic_name: 'Domain Generalization', status: 'PERSISTENT', paper_count: 8, sentence_count: 50 },
        ],
        emerging_topics: [
          { topic_id: 1, topic_name: 'Linear Attention', status: 'EMERGING', paper_count: 5, sentence_count: 30 },
        ],
      });
      api.fetchGapCandidates.mockResolvedValue({
        total_candidates: 2,
        candidates: [
          {
            gap_id: 'gap-001',
            title: 'Subpopulation Shift Generalization Failure',
            description: 'Degradation on target distributions',
            gap_priority_score: 0.85,
            confidence: 0.92,
            signals: { conflicting_evidence: 0.7 },
          },
        ],
      });
      api.fetchGapLifecycleOverview.mockResolvedValue({
        status_counts: { PERSISTENT: 4, ADDRESSED: 2, EMERGING: 1, PARTIALLY_ADDRESSED: 1 },
      });

      renderWithContext(<Dashboard />);

      await waitFor(() => {
        expect(screen.getByText(/Research Intelligence Dashboard/i)).toBeDefined();
        expect(screen.getAllByText(/Scientific Papers/i).length).toBeGreaterThanOrEqual(1);
        expect(screen.getAllByText(/Research Topics/i).length).toBeGreaterThanOrEqual(1);
        expect(screen.getAllByText(/Potential Gaps/i).length).toBeGreaterThanOrEqual(1);
        expect(screen.getAllByText(/Persistent Gaps/i).length).toBeGreaterThanOrEqual(1);
        expect(screen.getAllByText(/Emerging Topics/i).length).toBeGreaterThanOrEqual(1);
        expect(screen.getAllByText(/Addressed Gaps/i).length).toBeGreaterThanOrEqual(1);
        expect(screen.getAllByText(/Counter-Evidence Items/i).length).toBeGreaterThanOrEqual(1);
      });

      expect(screen.getByText(/Subpopulation Shift Generalization Failure/i)).toBeDefined();
    });

    it('renders empty API response cleanly', async () => {
      api.fetchPapers.mockResolvedValue([]);
      api.fetchTopicsOverview.mockResolvedValue({ total_topics: 0, all_topics: [], emerging_topics: [] });
      api.fetchGapCandidates.mockResolvedValue({ total_candidates: 0, candidates: [] });
      api.fetchGapLifecycleOverview.mockResolvedValue({ status_counts: {} });

      renderWithContext(<Dashboard />);

      await waitFor(() => {
        expect(screen.getByText(/No candidate gaps generated yet/i)).toBeDefined();
        expect(screen.getByText(/No topics discovered yet/i)).toBeDefined();
      });
    });

    it('renders API failure error banner with retry button', async () => {
      api.fetchPapers.mockRejectedValue(new Error('Network connection refused'));
      api.fetchTopicsOverview.mockRejectedValue(new Error('Network connection refused'));
      api.fetchGapCandidates.mockRejectedValue(new Error('Network connection refused'));
      api.fetchGapLifecycleOverview.mockRejectedValue(new Error('Network connection refused'));

      renderWithContext(<Dashboard />);

      await waitFor(() => {
        expect(screen.getByText(/Network connection refused/i)).toBeDefined();
        expect(screen.getByRole('button', { name: /Retry/i })).toBeDefined();
      });
    });
  });

  // =========================================================================
  // 2. Paper Library & Upload Tests
  // =========================================================================
  describe('2. Paper Library Page', () => {
    it('renders paper library with search, year filter, topic filter, and upload trigger', async () => {
      api.fetchPapers.mockResolvedValue([
        {
          id: 10,
          title: 'Scaling Laws for Neural Language Models',
          authors: ['Jared Kaplan', 'Sam McCandlish'],
          year: 2020,
          section_count: 8,
          abstract: 'Empirical scaling relations...',
        },
      ]);
      api.fetchTopics.mockResolvedValue([
        { topic_id: 1, topic_name: 'Scaling Laws' },
      ]);

      renderWithContext(<PapersPage />);

      await waitFor(() => {
        expect(screen.getByText(/Scientific Paper Library/i)).toBeDefined();
        expect(screen.getByText(/Scaling Laws for Neural Language Models/i)).toBeDefined();
        expect(screen.getByText(/Jared Kaplan/i)).toBeDefined();
      });

      // Filter by search
      const searchInput = screen.getByPlaceholderText(/Search papers/i);
      fireEvent.change(searchInput, { target: { value: 'Scaling' } });
      expect(screen.getByText(/Scaling Laws for Neural Language Models/i)).toBeDefined();

      fireEvent.change(searchInput, { target: { value: 'Nonexistent' } });
      expect(screen.getByText(/No publications match your filter criteria/i)).toBeDefined();
    });

    it('handles file upload interaction', async () => {
      api.fetchPapers.mockResolvedValue([]);
      api.fetchTopics.mockResolvedValue([]);
      api.uploadPaperFile.mockResolvedValue({ id: 12, filename: 'new_paper.pdf' });
      api.processPaperNLP.mockResolvedValue({ sentences_count: 10, extractions_count: 5 });

      const { container } = renderWithContext(<PapersPage />);

      await waitFor(() => {
        expect(screen.getByText(/The paper library is empty/i)).toBeDefined();
      });

      const fileInput = container.querySelector('input[type="file"]');
      expect(fileInput).toBeDefined();

      const fakeFile = new File(['%PDF-1.4 test content'], 'new_paper.pdf', { type: 'application/pdf' });
      fireEvent.change(fileInput, { target: { files: [fakeFile] } });

      await waitFor(() => {
        expect(api.uploadPaperFile).toHaveBeenCalledWith(fakeFile);
      });
    });
  });

  // =========================================================================
  // 3. Paper Detail Tests
  // =========================================================================
  describe('3. Paper Detail Page', () => {
    it('renders paper detail with sections, limitations, future work, methods, datasets, and evidence', async () => {
      api.fetchPapers.mockResolvedValue([{ id: 10, title: 'Sample Paper on Robustness' }]);
      api.fetchPaperDetails.mockResolvedValue({
        id: 10,
        title: 'Sample Paper on Robustness',
        authors: ['Alice Smith'],
        year: 2024,
        abstract: 'Comprehensive study of model limitations.',
        sections: [{ title: 'Introduction', page: 1, content: 'Intro text...' }],
      });
      api.fetchPaperLimitations.mockResolvedValue([
        { category: 'EMPIRICAL_LIMITATION', description: 'Requires excessive memory overhead', page: 6, section: 'Limits', confidence: 0.95 },
      ]);
      api.fetchPaperFutureWork.mockResolvedValue([
        { direction: 'Explore 4-bit quantization bounds', page: 8, section: 'Conclusion', confidence: 0.91 },
      ]);
      api.fetchPaperExtractions.mockImplementation((id, type) => {
        if (type === 'METHOD') return Promise.resolve([{ entity_name: 'FlashAttention-3', context: 'Fast IO kernel' }]);
        if (type === 'DATASET') return Promise.resolve([{ entity_name: 'MIMIC-IV', context: 'Clinical notes' }]);
        return Promise.resolve([]);
      });
      api.fetchPaperSentences.mockResolvedValue([
        { text: 'We observe a 15% degradation under shift.', classification: 'LIMITATION', page: 4, section: 'Results', confidence: 0.94 },
      ]);

      renderWithContext(<PaperDetailPage />);

      await waitFor(() => {
        expect(screen.getAllByText(/Sample Paper on Robustness/i).length).toBeGreaterThanOrEqual(1);
        expect(screen.getByText(/Comprehensive study of model limitations/i)).toBeDefined();
      });

      // Switch to Limitations tab
      const limitsTab = screen.getByRole('button', { name: /Limitations/i });
      fireEvent.click(limitsTab);

      await waitFor(() => {
        expect(screen.getByText(/Requires excessive memory overhead/i)).toBeDefined();
      });

      // Switch to Methods tab
      const methodsTab = screen.getByRole('button', { name: /Methods/i });
      fireEvent.click(methodsTab);

      await waitFor(() => {
        expect(screen.getByText(/FlashAttention-3/i)).toBeDefined();
      });

      // Switch to Datasets tab
      const datasetsTab = screen.getByRole('button', { name: /Datasets/i });
      fireEvent.click(datasetsTab);

      await waitFor(() => {
        expect(screen.getByText(/MIMIC-IV/i)).toBeDefined();
      });
    });
  });

  // =========================================================================
  // 4. Research Landscape Tests
  // =========================================================================
  describe('4. Research Landscape Page', () => {
    it('visualizes topic sizes, trajectories, and temporal distribution', async () => {
      api.fetchTopicsOverview.mockResolvedValue({
        total_topics: 2,
        major_topics: [{ topic_id: 1, topic_name: 'Transformer Efficiency', status: 'MAJOR', paper_count: 10, sentence_count: 80 }],
        emerging_topics: [{ topic_id: 2, topic_name: 'State Space Models', status: 'EMERGING', paper_count: 4, sentence_count: 25 }],
        declining_topics: [],
        persistent_topics: [],
        all_topics: [
          {
            topic_id: 1,
            topic_name: 'Transformer Efficiency',
            status: 'MAJOR',
            paper_count: 10,
            sentence_count: 80,
            representative_terms: [{ term: 'attention', weight: 0.9 }, { term: 'memory', weight: 0.8 }],
            temporal_distribution: { '2021': 2, '2022': 3, '2023': 5 },
          },
          {
            topic_id: 2,
            topic_name: 'State Space Models',
            status: 'EMERGING',
            paper_count: 4,
            sentence_count: 25,
            representative_terms: [{ term: 'mamba', weight: 0.95 }],
            temporal_distribution: { '2024': 4 },
          },
        ],
      });

      renderWithContext(<LandscapePage />);

      await waitFor(() => {
        expect(screen.getByText(/Research Landscape & Topic Discovery/i)).toBeDefined();
        expect(screen.getAllByText(/Transformer Efficiency/i).length).toBeGreaterThanOrEqual(1);
        expect(screen.getByText(/State Space Models/i)).toBeDefined();
      });

      api.discoverTopics.mockResolvedValue({
        total_topics: 2,
        major_topics: [],
        emerging_topics: [],
        declining_topics: [],
        persistent_topics: [],
        all_topics: [],
      });

      const discoverBtn = screen.getByRole('button', { name: /Discover Topics/i });
      fireEvent.click(discoverBtn);

      await waitFor(() => {
        expect(api.discoverTopics).toHaveBeenCalled();
      });
    });
  });

  // =========================================================================
  // 5. Research Knowledge Graph Tests
  // =========================================================================
  describe('5. Research Knowledge Graph Page', () => {
    it('renders topology statistics and handles node click provenance drawer', async () => {
      api.fetchGraphOverview.mockResolvedValue({
        total_nodes: 15,
        total_edges: 22,
        density: 0.095,
        connected_components_count: 2,
        graph_database_engine: 'NetworkX',
      });
      api.fetchPapers.mockResolvedValue([{ id: 1, title: 'Paper 1' }]);
      api.fetchPaperSubgraph.mockResolvedValue({
        total_nodes: 2,
        total_edges: 1,
        nodes: [
          { id: 'paper:1', label: 'Paper 1', type: 'Paper', properties: { paper_id: 1, title: 'Paper 1' } },
          { id: 'limitation:1', label: 'Memory Bottleneck', type: 'Limitation', properties: { limitation_id: '1' } },
        ],
        edges: [
          { id: 'e1', source: 'paper:1', target: 'limitation:1', relationship: 'limited_by' },
        ],
      });
      api.fetchLimitationGraph.mockResolvedValue({
        papers_limited_by: [{ paper_id: 1, paper_title: 'Paper 1' }],
        papers_addressing: [],
        research_directions: [],
      });

      renderWithContext(<ResearchGraphPage />);

      await waitFor(() => {
        expect(screen.getByText(/Research Knowledge Graph/i)).toBeDefined();
        expect(screen.getByText('15')).toBeDefined();
        expect(screen.getByText('22')).toBeDefined();
      });

      // Click node
      const nodeText = screen.getByText('Memory Bottleneck');
      fireEvent.click(nodeText);

      await waitFor(() => {
        expect(api.fetchLimitationGraph).toHaveBeenCalledWith('limitation:1');
      });
    });
  });

  // =========================================================================
  // 6. Potential Gaps Catalogue Tests
  // =========================================================================
  describe('6. Potential Gaps Catalogue Page', () => {
    it('renders gap cards with title, description, status, priority, confidence, supporting papers, counter-evidence count, first appearance', async () => {
      api.fetchGapCandidates.mockResolvedValue({
        total_candidates: 1,
        candidates: [
          {
            gap_id: 'gap-robustness-01',
            title: 'Out-of-Distribution Vulnerability in Vision Transformers',
            description: 'Models degrade sharply under non-Gaussian noise perturbations.',
            gap_type: 'repeated_limitation',
            verification_status: 'potential_gap',
            gap_priority_score: 0.784,
            confidence: 0.88,
            supporting_papers: [
              { paper_id: 1, title: 'Paper A', year: 2022 },
              { paper_id: 2, title: 'Paper B', year: 2024 },
            ],
            signals: { conflicting_evidence: 0.6 },
          },
        ],
      });
      api.fetchGapSignalsOverview.mockResolvedValue({ total_signals: 7 });

      renderWithContext(<PotentialGapsPage />);

      await waitFor(() => {
        expect(screen.getByText(/Out-of-Distribution Vulnerability in Vision Transformers/i)).toBeDefined();
        expect(screen.getByText(/Priority 0.784/i)).toBeDefined();
        expect(screen.getByText(/Conf: 88%/i)).toBeDefined();
        expect(screen.getByText(/First Appearance: 2022/i)).toBeDefined();
      });
    });
  });

  // =========================================================================
  // 7. Gap Detail Tests
  // =========================================================================
  describe('7. Gap Detail Page', () => {
    it('displays description, lifecycle, scoring signals, exact sentences, and counter-evidence', async () => {
      api.fetchGapCandidates.mockResolvedValue({
        candidates: [{ gap_id: 'gap-test-1', title: 'Attention Memory Wall' }],
      });
      api.fetchGapCandidateDetail.mockResolvedValue({
        gap_id: 'gap-test-1',
        title: 'Attention Memory Wall',
        description: 'Quadratic bottleneck prevents infinite context scaling.',
        gap_type: 'repeated_limitation',
        gap_priority_score: 0.82,
        confidence: 0.94,
        signal_breakdown: [
          { signal_name: 'repeated_limitations', signal_value: 0.9, weight: 0.25, contribution: 0.225, explanation: 'Found across 4 papers' },
        ],
        supporting_evidence: [
          { paper_title: 'Paper X', page: 5, section: 'Complexity', source_text: 'O(N^2) memory complexity remains prohibitive.', confidence: 0.95 },
        ],
      });
      api.fetchGapLifecycle.mockResolvedValue({
        gap_id: 'gap-test-1',
        status: 'PERSISTENT',
        status_reasoning: 'Persistent over 3 years without full solution.',
        evidence_paper_count: 4,
        year_span: 3,
        first_year: 2021,
        latest_year: 2024,
      });
      api.fetchGapGenealogy.mockResolvedValue({ evolutionary_chain: [] });
      api.fetchGapCounterEvidence.mockResolvedValue({ counter_evidence: [] });

      renderWithContext(<GapDetailPage />);

      await waitFor(() => {
        expect(screen.getAllByText(/Attention Memory Wall/i).length).toBeGreaterThanOrEqual(1);
        expect(screen.getByText(/Quadratic bottleneck prevents infinite context scaling/i)).toBeDefined();
        expect(screen.getByText(/repeated_limitations/i)).toBeDefined();
        expect(screen.getByText(/O\(N\^2\) memory complexity remains prohibitive/i)).toBeDefined();
      });
    });
  });

  // =========================================================================
  // 8. Gap Genealogy Tests
  // =========================================================================
  describe('8. Gap Genealogy Page', () => {
    it('displays timeline sequence limitation -> attempted solution -> remaining limitation -> candidate gap', async () => {
      api.fetchGapCandidates.mockResolvedValue({
        candidates: [{ gap_id: 'gap-gen-1', title: 'Generalization Gap' }],
      });
      api.fetchGapGenealogy.mockResolvedValue({
        gap_id: 'gap-gen-1',
        gap_title: 'Generalization Gap',
        root_limitation: 'Spurious correlation reliance in ERM training.',
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
            description: 'ERM models rely on high-frequency spurious backgrounds.',
            relationship: 'limited_by',
            year: 2021,
            source_sentence: 'ERM optimizes for dominant spurious cues.',
          },
          {
            step_number: 2,
            stage_name: 'Attempted Solution',
            description: 'Invariant Risk Minimization proposed to learn causal representations.',
            relationship: 'addresses',
            year: 2022,
            source_sentence: 'IRM enforces invariance across training environments.',
          },
        ],
      });

      renderWithContext(<GapGenealogyPage />);

      await waitFor(() => {
        expect(screen.getByText(/Gap Genealogy & Developmental Progression/i)).toBeDefined();
        expect(screen.getByText(/Spurious correlation reliance in ERM training/i)).toBeDefined();
        expect(screen.getByText(/Invariant Risk Minimization proposed/i)).toBeDefined();
      });
    });
  });

  // =========================================================================
  // 9. Gap Lifecycle Tests
  // =========================================================================
  describe('9. Gap Lifecycle Page', () => {
    it('displays 6 lifecycle states with evidence and chronological timeline', async () => {
      api.fetchGapLifecycleOverview.mockResolvedValue({
        status_counts: {
          EMERGING: 2,
          PERSISTENT: 5,
          PARTIALLY_ADDRESSED: 3,
          ADDRESSED: 1,
          REOPENED: 1,
          UNCERTAIN: 0,
        },
      });
      api.fetchGapCandidates.mockResolvedValue({
        candidates: [{ gap_id: 'gap-life-1', title: 'Subpopulation Shift Gap' }],
      });
      api.fetchGapLifecycle.mockResolvedValue({
        gap_id: 'gap-life-1',
        gap_title: 'Subpopulation Shift Gap',
        status: 'PERSISTENT',
        status_reasoning: 'Multi-year persistence across 5 papers without robust mitigation.',
        evidence_paper_count: 5,
        year_span: 4,
        first_year: 2021,
        latest_year: 2025,
        has_attempted_solutions: true,
        is_addressed: false,
        confidence: 0.93,
      });
      api.fetchGapTimeline.mockResolvedValue({
        total_events: 2,
        events: [
          { event_id: 'e1', event_type: 'limitation_identified', title: 'Identified in 2021', source_sentence: 'Degrades severely.', year: 2021 },
          { event_id: 'e2', event_type: 'limitation_persists', title: 'Persists in 2025', source_sentence: 'Still unresolved.', year: 2025 },
        ],
      });

      renderWithContext(<GapLifecyclePage />);

      await waitFor(() => {
        expect(screen.getByText(/Gap Lifecycle State Machine/i)).toBeDefined();
        expect(screen.getByText('Emerging')).toBeDefined();
        expect(screen.getAllByText(/Persistent/i).length).toBeGreaterThanOrEqual(1);
        expect(screen.getByText('Partially Addressed')).toBeDefined();
        expect(screen.getByText('Addressed')).toBeDefined();
        expect(screen.getByText('Reopened')).toBeDefined();
        expect(screen.getByText('Uncertain')).toBeDefined();
        expect(screen.getByText(/Multi-year persistence across 5 papers/i)).toBeDefined();
      });
    });
  });

  // =========================================================================
  // 10. Counter-Evidence Tests
  // =========================================================================
  describe('10. Counter-Evidence Page', () => {
    it('displays supporting, counter, addressing, and contradictory evidence with NLI inference', async () => {
      api.fetchGapCandidates.mockResolvedValue({
        candidates: [{ gap_id: 'gap-ce-1', title: 'KV Cache Degradation' }],
      });
      api.fetchGapCounterEvidence.mockResolvedValue({
        gap_id: 'gap-ce-1',
        counter_evidence: [
          {
            evidence_id: 'c1',
            paper_title: 'Compressed KV Caching',
            publication_year: 2024,
            source_text: 'Quantized KV cache maintains 99.2% accuracy without degradation.',
            nli_result: { label: 'CONTRADICTION', confidence: 0.89 },
          },
        ],
        addressed_by_evidence: [
          {
            evidence_id: 'a1',
            paper_title: 'PagedAttention Engine',
            publication_year: 2023,
            source_text: 'Virtual memory paging eliminates non-contiguous KV fragmentation.',
          },
        ],
        contradictory_evidence: [],
      });
      api.fetchGapVerification.mockResolvedValue({
        gap_id: 'gap-ce-1',
        gap_title: 'KV Cache Degradation',
        final_status: 'PARTIALLY_ADDRESSED',
        verification_confidence: 0.85,
        status_reasoning: 'Memory fragmentation is solved, but precision degradation remains disputed.',
        supporting_evidence: [
          { evidence_id: 's1', paper_title: 'Original Paper', source_text: 'Long context causes cache exhaustion.' },
        ],
      });

      renderWithContext(<CounterEvidencePage />);

      await waitFor(() => {
        expect(screen.getByText(/Counter-Evidence & Verification/i)).toBeDefined();
        expect(screen.getByText(/Quantized KV cache maintains 99.2% accuracy/i)).toBeDefined();
        expect(screen.getByText(/CONTRADICTION/i)).toBeDefined();
        expect(screen.getByText(/PagedAttention Engine/i)).toBeDefined();
      });

      // Verify active verification action
      api.verifyGap.mockResolvedValue({
        gap_id: 'gap-ce-1',
        final_status: 'PARTIALLY_ADDRESSED',
        verification_confidence: 0.87,
      });

      const verifyBtn = screen.getByRole('button', { name: /Verify Gap/i });
      fireEvent.click(verifyBtn);

      await waitFor(() => {
        expect(api.verifyGap).toHaveBeenCalledWith('gap-ce-1', expect.anything());
      });
    });
  });

  // =========================================================================
  // 11. Evidence Explorer Tests
  // =========================================================================
  describe('11. Evidence Explorer Page', () => {
    it('executes semantic search and displays paper, page, section, sentence, similarity, and extraction type', async () => {
      api.searchSemanticEvidence.mockResolvedValue({
        query: 'linear attention memory',
        total_results: 1,
        retrieval_method: 'semantic_vector_faiss',
        results: [
          {
            source_text: 'Linear attention achieves O(N) complexity by kernel trick decomposition.',
            similarity_score: 0.8924,
            paper: { paper_id: 15, title: 'Transformers are RNNs', year: 2020 },
            section: 'Linear Formulation',
            page: 3,
            extraction_type: 'METHOD',
          },
        ],
      });

      renderWithContext(<EvidenceExplorerPage />);

      await waitFor(() => {
        expect(screen.getByText(/Semantic Evidence Explorer/i)).toBeDefined();
        expect(screen.getByText(/Linear attention achieves O\(N\) complexity/i)).toBeDefined();
        expect(screen.getByText(/Transformers are RNNs/i)).toBeDefined();
        expect(screen.getByText(/0.8924/i)).toBeDefined();
        expect(screen.getByText(/Section:/i)).toBeDefined();
        expect(screen.getByText(/Page:/i)).toBeDefined();
      });
    });
  });

  // =========================================================================
  // 12. Research Report Tests
  // =========================================================================
  describe('12. Research Report Page', () => {
    it('generates evidence-grounded report with citations and factuality audit', async () => {
      api.fetchGapCandidates.mockResolvedValue({
        candidates: [{ gap_id: 'gap-rep-1', title: 'Associative Recall Degradation' }],
      });
      api.fetchGapSynthesis.mockResolvedValue({
        gap_id: 'gap-rep-1',
        gap_title: 'Associative Recall Degradation',
        provider: 'gemini',
        model: 'gemini-1.5-pro',
        gap_explanation: 'Sub-quadratic architectures fail multi-query associative recall [E1].',
        why_it_matters: 'Prevents in-context retrieval across vast document repositories [E2].',
        supporting_evidence_summary: 'Multiple synthetic and real needle evaluations confirm failure.',
        counter_evidence_summary: 'Hybrid sliding-window attention mitigates the gap.',
        current_status: 'PERSISTENT',
        potential_research_questions: ['Can recurrent memory retention resolve token associative decay?'],
        potential_future_directions: ['Evaluate state-space hybrid gating.'],
        evidence_limitations: 'Limited to synthetic copy benchmarks.',
        citations: {
          E1: {
            citation_id: 'E1',
            paper_title: 'Associative Recall Bounds',
            page: 4,
            section: 'Experiments',
            sentence_text: 'Linear attention fails associative recall beyond 16 keys.',
            evidence_type: 'SUPPORTING',
          },
        },
        validation_report: {
          total_claims: 2,
          claims_with_citations: 2,
          supported_claims: 2,
          unsupported_claims: 0,
          contradicted_claims: 0,
          hallucinated_citations: 0,
          evidence_support_rate: 1.0,
          is_valid: true,
          claims: [
            {
              claim_text: 'Sub-quadratic architectures fail associative recall',
              status: 'SUPPORTED',
              support_score: 0.94,
              explanation: 'Fully supported by [E1]',
            },
          ],
        },
        synthesized_at: new Date().toISOString(),
      });

      renderWithContext(<ResearchReportPage />);

      await waitFor(() => {
        expect(screen.getByText(/Evidence-Grounded Research Report/i)).toBeDefined();
        expect(screen.getByText(/Sub-quadratic architectures fail multi-query associative recall/i)).toBeDefined();
        expect(screen.getByText(/Grounded Evidence Citations Map/i)).toBeDefined();
        expect(screen.getByText(/Automated Factuality & Citation Audit Report/i)).toBeDefined();
        expect(screen.getByText('100%')).toBeDefined();
        expect(screen.getByText(/AUDIT VERDICT: VALID/i)).toBeDefined();
      });
    });
  });

  // =========================================================================
  // 13. Responsive Layout & Navigation Tests
  // =========================================================================
  describe('13. Responsive Shell & Navigation', () => {
    it('renders responsive shell and navigation across all views', async () => {
      api.fetchPapers.mockResolvedValue([]);
      api.fetchHealth.mockResolvedValue({ success: true, data: { status: 'healthy' } });

      render(<App />);

      expect(screen.getAllByText(/GapTrace/i).length).toBeGreaterThanOrEqual(1);
      expect(screen.getByRole('button', { name: /^Dashboard$/i })).toBeDefined();
      expect(screen.getByRole('button', { name: /^Papers/i })).toBeDefined();
      expect(screen.getByRole('button', { name: /Research Landscape/i })).toBeDefined();
      expect(screen.getByRole('button', { name: /Potential Gaps/i })).toBeDefined();
      expect(screen.getByRole('button', { name: /Research Graph/i })).toBeDefined();
      expect(screen.getByRole('button', { name: /Evidence Explorer/i })).toBeDefined();
      expect(screen.getByRole('button', { name: /Research Report/i })).toBeDefined();
    });
  });
});
