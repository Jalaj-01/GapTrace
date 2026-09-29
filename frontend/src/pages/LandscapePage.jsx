import React from 'react';
import { Layers, TrendingUp, Cpu, Globe, Compass, ArrowUpRight, BarChart2 } from 'lucide-react';
import { useResearch } from '../contexts/ResearchContext';

export default function LandscapePage() {
  const { selectSession } = useResearch();

  const clusters = [
    {
      domain: 'Foundation Model Architecture & Efficiency',
      gapsCount: 4,
      trend: '+38% literature volume',
      activeTopics: ['Sub-quadratic linear attention', 'Selective state spaces', 'Quantization calibration', 'KV cache compression'],
      sessionId: 'transformer-eff',
    },
    {
      domain: 'Out-of-Distribution & Robustness',
      gapsCount: 6,
      trend: 'Persistent (5+ years)',
      activeTopics: ['Causal representation learning', 'Subpopulation shift', 'Test-time adaptation', 'Spurious correlation mitigation'],
      sessionId: 'cross-domain-gen',
    },
    {
      domain: 'Cross-Lingual & Low-Resource NLP',
      gapsCount: 5,
      trend: 'Persistent (6+ years)',
      activeTopics: ['Morphological tokenization collapse', 'Synthetic pseudo-parallel degradation', 'Polysynthetic syntax transfer'],
      sessionId: 'low-resource-nlp',
    },
    {
      domain: 'Biomedical & Clinical AI',
      gapsCount: 7,
      trend: '+54% clinical audits',
      activeTopics: ['Clinical hallucination in discharge summaries', 'Telemetry reasoning calibration', 'Multi-modal EHR integration'],
      sessionId: 'medical-llm',
    },
  ];

  return (
    <div className="landscape-page-container">
      <div className="page-header-row">
        <div>
          <h2 className="page-title">Research Landscape</h2>
          <p className="page-subtitle">
            Temporal clusters of active scientific topics, emerging architectural paradigms, and persistent bottlenecks.
          </p>
        </div>
      </div>

      <div className="clusters-grid">
        {clusters.map((cluster, idx) => (
          <div key={idx} className="cluster-card">
            <div className="cluster-header">
              <span className="cluster-trend font-mono">{cluster.trend}</span>
              <span className="cluster-gaps-badge font-mono">{cluster.gapsCount} Active Gaps</span>
            </div>

            <h3 className="cluster-domain-title">{cluster.domain}</h3>

            <div className="cluster-topics-list">
              <span className="topics-label">Key Scientific Themes:</span>
              <div className="topics-pills">
                {cluster.activeTopics.map((topic, tidx) => (
                  <span key={tidx} className="topic-pill">
                    {topic}
                  </span>
                ))}
              </div>
            </div>

            <div className="cluster-footer">
              <button
                className="cluster-explore-btn"
                onClick={() => selectSession(cluster.sessionId)}
              >
                <span>Explore Domain Gaps</span>
                <ArrowUpRight size={14} />
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
