import React, { useEffect, useState } from 'react';
import { FileSearch, Search, Filter, Copy, Check, Quote, ExternalLink, Sparkles } from 'lucide-react';
import { useResearch } from '../contexts/ResearchContext';
import { fetchPaperSentences } from '../services/api';

const SAMPLE_EVIDENCE_STREAM = [
  {
    id: 1,
    category: 'LIMITATION',
    confidence: 0.96,
    text: 'A notable limitation of our method is that quadratic attention memory complexity limits input contexts to 2048 tokens.',
    paperTitle: 'Flash-Linear Attention: Boundaries and Trade-offs',
    section: 'Limitations',
    page: 12,
    order: 3,
  },
  {
    id: 2,
    category: 'PROBLEM',
    confidence: 0.94,
    text: 'However, existing transformer models suffer from quadratic memory complexity with respect to sequence length.',
    paperTitle: 'Efficient Transformers: A Systematic Survey',
    section: 'Introduction',
    page: 1,
    order: 4,
  },
  {
    id: 3,
    category: 'RESULT',
    confidence: 0.97,
    text: 'As shown in Table 2, our proposed method surpasses the strong baseline by 3.8 BLEU points (p < 0.01).',
    paperTitle: 'Self-Supervised Sequence Alignment',
    section: 'Results',
    page: 7,
    order: 2,
  },
  {
    id: 4,
    category: 'FUTURE_WORK',
    confidence: 0.93,
    text: 'In future work, we plan to extend our framework to multilingual and cross-modal scientific paper corpora.',
    paperTitle: 'GapTrace: Evidence-Grounded Temporal Gap Discovery',
    section: 'Conclusion',
    page: 14,
    order: 6,
  },
  {
    id: 5,
    category: 'LIMITATION',
    confidence: 0.95,
    text: 'The primary limitation is that our empirical findings may not generalize well to non-English language corpora.',
    paperTitle: 'Cross-Lingual Clinical Question Answering at Scale',
    section: 'Discussion & Limitations',
    page: 9,
    order: 1,
  },
  {
    id: 6,
    category: 'METHOD',
    confidence: 0.92,
    text: 'We optimize the network parameters using the AdamW optimizer with an initial learning rate of 2e-5 and cosine annealing.',
    paperTitle: 'Linear Complexity Transformers with Dual Attention',
    section: 'Methodology',
    page: 4,
    order: 5,
  },
];

export default function EvidenceExplorerPage() {
  const { backendPapers } = useResearch();
  const [selectedCategory, setSelectedCategory] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [copiedId, setCopiedId] = useState(null);
  const [liveSentences, setLiveSentences] = useState(SAMPLE_EVIDENCE_STREAM);

  // Attempt to load live sentences from first ingested paper if available
  useEffect(() => {
    const loadRealSentences = async () => {
      if (backendPapers.length > 0) {
        try {
          const sents = await fetchPaperSentences(backendPapers[0].id);
          if (Array.isArray(sents) && sents.length > 0) {
            const formatted = sents.map((s) => ({
              id: s.id,
              category: s.discourse_class || 'OTHER',
              confidence: s.classification_confidence || 0.9,
              text: s.source_text,
              paperTitle: backendPapers[0].title || backendPapers[0].filename,
              section: s.section_name || 'General',
              page: s.page_number || 1,
              order: s.sentence_order || 1,
            }));
            setLiveSentences([...formatted, ...SAMPLE_EVIDENCE_STREAM]);
          }
        } catch {
          // Keep defaults
        }
      }
    };
    loadRealSentences();
  }, [backendPapers]);

  const categories = [
    'ALL',
    'LIMITATION',
    'PROBLEM',
    'OBJECTIVE',
    'METHOD',
    'DATASET',
    'METRIC',
    'RESULT',
    'FUTURE_WORK',
  ];

  const filtered = liveSentences.filter((item) => {
    const matchesCategory =
      selectedCategory === 'ALL' || item.category === selectedCategory;
    const matchesSearch =
      !searchQuery ||
      item.text.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.section.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  const handleCopy = (id, text) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <div className="evidence-explorer-container">
      <div className="page-header-row">
        <div>
          <h2 className="page-title">Evidence Explorer</h2>
          <p className="page-subtitle">
            Query classified scientific sentences across ingested literature with strict section and page provenance.
          </p>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="evidence-filter-bar">
        <div className="search-input-box">
          <Search size={15} className="search-icon" />
          <input
            type="text"
            placeholder="Search evidence text, keywords, or section headers..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>

        <div className="category-pills-row">
          {categories.map((cat) => (
            <button
              key={cat}
              className={`cat-pill-btn ${selectedCategory === cat ? 'active' : ''}`}
              onClick={() => setSelectedCategory(cat)}
            >
              {cat}
            </button>
          ))}
        </div>
      </div>

      {/* Evidence Stream */}
      <div className="evidence-stream-list">
        {filtered.length === 0 ? (
          <div className="empty-state-box">
            <FileSearch size={36} />
            <p className="empty-title">No matching evidence</p>
            <p className="empty-sub">Try selecting another discourse category or adjusting your search keywords.</p>
          </div>
        ) : (
          filtered.map((item) => (
            <article key={item.id} className="explorer-evidence-card">
              <div className="card-top-bar">
                <span className={`discourse-badge badge-${item.category.toLowerCase()}`}>
                  {item.category}
                </span>
                <span className="confidence-pill font-mono">
                  {Math.round(item.confidence * 100)}% confidence
                </span>
                <button
                  className="copy-btn"
                  onClick={() => handleCopy(item.id, item.text)}
                  title="Copy evidence quote"
                >
                  {copiedId === item.id ? (
                    <Check size={13} className="text-emerald" />
                  ) : (
                    <Copy size={13} />
                  )}
                </button>
              </div>

              <blockquote className="evidence-body">
                "{item.text}"
              </blockquote>

              <div className="card-bottom-provenance font-mono">
                <span className="prov-paper truncate" title={item.paperTitle}>
                  {item.paperTitle}
                </span>
                <span className="prov-dot">•</span>
                <span className="prov-sec">§ {item.section}</span>
                <span className="prov-dot">•</span>
                <span className="prov-page">Page {item.page}</span>
                <span className="prov-dot">•</span>
                <span className="prov-order">Sentence #{item.order}</span>
              </div>
            </article>
          ))
        )}
      </div>
    </div>
  );
}
