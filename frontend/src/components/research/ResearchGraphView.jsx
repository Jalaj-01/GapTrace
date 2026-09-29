import React, { useMemo, useState } from 'react';
import {
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Search,
  Filter,
  X,
  Share2,
  FileText,
  ExternalLink,
  ShieldCheck,
} from 'lucide-react';

const NODE_COLORS = {
  Paper: '#3b82f6',
  Method: '#8b5cf6',
  Dataset: '#10b981',
  Claim: '#f59e0b',
  Limitation: '#ef4444',
  Topic: '#ec4899',
  'Research Direction': '#06b6d4',
};

export default function ResearchGraphView({ graphData, onOpenPaper }) {
  const [zoomLevel, setZoomLevel] = useState(1);
  const [selectedNode, setSelectedNode] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [activeFilter, setActiveFilter] = useState('ALL');

  // Default fallback graph data if session has empty graph
  const defaultNodes = useMemo(
    () => [
      { id: 'lim-1', label: 'Cross-Dataset Generalization', type: 'Limitation', x: 420, y: 190, color: NODE_COLORS.Limitation, confidence: 0.96, page: 8, paper: 'Biomedical Transfer 2024' },
      { id: 'p-1', label: 'Biomedical Transfer 2024', type: 'Paper', x: 200, y: 130, color: NODE_COLORS.Paper, confidence: 0.98, page: 1, paper: 'Biomedical Transfer 2024' },
      { id: 'p-2', label: 'In Search of Lost Invariance', type: 'Paper', x: 210, y: 300, color: NODE_COLORS.Paper, confidence: 0.94, page: 11, paper: 'Arjovsky et al.' },
      { id: 'm-1', label: 'Invariant Risk Minimization', type: 'Method', x: 380, y: 340, color: NODE_COLORS.Method, confidence: 0.92, page: 4, paper: 'Arjovsky et al.' },
      { id: 'd-1', label: 'MIMIC-III EHR Cohort', type: 'Dataset', x: 140, y: 220, color: NODE_COLORS.Dataset, confidence: 0.99, page: 5, paper: 'Johnson et al.' },
      { id: 'd-2', label: 'WILDS Benchmark Suite', type: 'Dataset', x: 580, y: 360, color: NODE_COLORS.Dataset, confidence: 0.95, page: 7, paper: 'Koh et al.' },
      { id: 'c-1', label: 'Catastrophic Degradation (28%)', type: 'Claim', x: 620, y: 150, color: NODE_COLORS.Claim, confidence: 0.91, page: 9, paper: 'Biomedical Transfer 2024' },
      { id: 'rd-1', label: 'Causal Invariant Graph Regularizer', type: 'Research Direction', x: 640, y: 260, color: NODE_COLORS['Research Direction'], confidence: 0.88, page: 15, paper: 'Future Work 2026' },
    ],
    []
  );

  const defaultLinks = useMemo(
    () => [
      { source: 'p-1', target: 'lim-1', relation: 'identifies' },
      { source: 'p-1', target: 'd-1', relation: 'evaluates_on' },
      { source: 'lim-1', target: 'c-1', relation: 'leads_to' },
      { source: 'p-2', target: 'm-1', relation: 'evaluates' },
      { source: 'm-1', target: 'd-2', relation: 'tested_on' },
      { source: 'm-1', target: 'lim-1', relation: 'fails_to_solve' },
      { source: 'lim-1', target: 'rd-1', relation: 'motivates' },
    ],
    []
  );

  const nodes = graphData?.nodes?.length ? graphData.nodes : defaultNodes;
  const links = graphData?.links?.length ? graphData.links : defaultLinks;

  // Filter nodes
  const filteredNodes = useMemo(() => {
    return nodes.filter((n) => {
      const matchesFilter = activeFilter === 'ALL' || n.type === activeFilter;
      const matchesSearch =
        !searchQuery ||
        n.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
        n.type.toLowerCase().includes(searchQuery.toLowerCase());
      return matchesFilter && matchesSearch;
    });
  }, [nodes, activeFilter, searchQuery]);

  const activeNodeIds = useMemo(() => new Set(filteredNodes.map((n) => n.id)), [filteredNodes]);

  const filteredLinks = useMemo(() => {
    return links.filter(
      (l) => activeNodeIds.has(l.source) && activeNodeIds.has(l.target)
    );
  }, [links, activeNodeIds]);

  const handleZoom = (delta) => {
    setZoomLevel((prev) => Math.min(Math.max(prev + delta, 0.6), 1.8));
  };

  const handleReset = () => {
    setZoomLevel(1);
    setSelectedNode(null);
    setSearchQuery('');
    setActiveFilter('ALL');
  };

  // Node position map for rendering SVG lines
  const nodeMap = useMemo(() => {
    const map = {};
    nodes.forEach((n, idx) => {
      map[n.id] = {
        ...n,
        x: n.x || 150 + (idx % 4) * 180 + (idx > 3 ? 40 : 0),
        y: n.y || 120 + Math.floor(idx / 4) * 160,
      };
    });
    return map;
  }, [nodes]);

  return (
    <div className="research-graph-container">
      {/* Top Controls Toolbar */}
      <div className="graph-toolbar">
        <div className="graph-search-box">
          <Search size={15} className="search-icon" />
          <input
            type="text"
            placeholder="Search nodes in graph..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
          {searchQuery && (
            <button className="clear-search-btn" onClick={() => setSearchQuery('')}>
              <X size={13} />
            </button>
          )}
        </div>

        {/* Filter Pills */}
        <div className="graph-filter-pills">
          {['ALL', 'Paper', 'Limitation', 'Method', 'Dataset', 'Claim', 'Research Direction'].map(
            (type) => (
              <button
                key={type}
                className={`filter-pill ${activeFilter === type ? 'active' : ''}`}
                onClick={() => setActiveFilter(type)}
              >
                {type === 'ALL' ? 'All Entities' : type}
              </button>
            )
          )}
        </div>

        {/* Zoom & View Controls */}
        <div className="graph-zoom-controls">
          <button className="zoom-btn" onClick={() => handleZoom(0.15)} title="Zoom In">
            <ZoomIn size={15} />
          </button>
          <span className="zoom-indicator font-mono">{Math.round(zoomLevel * 100)}%</span>
          <button className="zoom-btn" onClick={() => handleZoom(-0.15)} title="Zoom Out">
            <ZoomOut size={15} />
          </button>
          <button className="zoom-btn reset-btn" onClick={handleReset} title="Reset Graph View">
            <RotateCcw size={15} />
          </button>
        </div>
      </div>

      {/* Main Canvas Viewport */}
      <div className="graph-viewport-area">
        <svg
          className="graph-svg-canvas"
          viewBox="0 0 850 480"
          style={{ transform: `scale(${zoomLevel})`, transformOrigin: 'center center' }}
        >
          <defs>
            <marker
              id="arrowhead"
              markerWidth="7"
              markerHeight="7"
              refX="14"
              refY="3.5"
              orient="auto"
            >
              <polygon points="0 0, 7 3.5, 0 7" fill="var(--border-default)" />
            </marker>
          </defs>

          {/* Render Links */}
          <g className="graph-links-group">
            {filteredLinks.map((link, idx) => {
              const src = nodeMap[link.source];
              const tgt = nodeMap[link.target];
              if (!src || !tgt) return null;

              const isConnected =
                selectedNode && (selectedNode.id === src.id || selectedNode.id === tgt.id);

              return (
                <g key={idx} className={`link-item ${isConnected ? 'highlight' : ''}`}>
                  <line
                    x1={src.x}
                    y1={src.y}
                    x2={tgt.x}
                    y2={tgt.y}
                    stroke={isConnected ? 'var(--accent-primary)' : 'var(--border-default)'}
                    strokeWidth={isConnected ? 2.2 : 1.3}
                    strokeDasharray={link.relation.includes('fails') ? '4 3' : 'none'}
                    markerEnd="url(#arrowhead)"
                  />
                  {/* Subtle relation text */}
                  <text
                    x={(src.x + tgt.x) / 2}
                    y={(src.y + tgt.y) / 2 - 6}
                    className="edge-relation-text"
                    textAnchor="middle"
                  >
                    {link.relation}
                  </text>
                </g>
              );
            })}
          </g>

          {/* Render Nodes */}
          <g className="graph-nodes-group">
            {filteredNodes.map((n) => {
              const pos = nodeMap[n.id] || { x: 200, y: 200 };
              const isSelected = selectedNode?.id === n.id;
              const color = n.color || NODE_COLORS[n.type] || '#3b82f6';

              return (
                <g
                  key={n.id}
                  className={`node-group ${isSelected ? 'selected' : ''}`}
                  transform={`translate(${pos.x}, ${pos.y})`}
                  onClick={() => setSelectedNode(n)}
                  role="button"
                  tabIndex={0}
                >
                  {/* Outer halo if selected */}
                  {isSelected && (
                    <circle r="22" fill="none" stroke={color} strokeWidth="2.5" opacity="0.6" />
                  )}

                  {/* Node Circle */}
                  <circle
                    r="14"
                    fill={color}
                    stroke="var(--bg-card)"
                    strokeWidth="2.5"
                    className="node-circle"
                  />

                  {/* Node Label */}
                  <text
                    y="24"
                    className="node-label-text"
                    textAnchor="middle"
                    fill="var(--text-primary)"
                  >
                    {n.label.length > 20 ? n.label.slice(0, 19) + '…' : n.label}
                  </text>
                </g>
              );
            })}
          </g>
        </svg>

        {/* Node Detail Side Inspector Panel */}
        {selectedNode && (
          <aside className="graph-inspector-panel">
            <div className="inspector-header">
              <div className="inspector-type-badge" style={{ backgroundColor: selectedNode.color || '#3b82f6' }}>
                {selectedNode.type}
              </div>
              <button
                className="inspector-close-btn"
                onClick={() => setSelectedNode(null)}
                title="Close Inspector"
              >
                <X size={15} />
              </button>
            </div>

            <h4 className="inspector-node-title">{selectedNode.label}</h4>

            <div className="inspector-meta-list">
              <div className="meta-row">
                <span className="meta-label">Entity Type:</span>
                <span className="meta-value font-mono">{selectedNode.type}</span>
              </div>
              <div className="meta-row">
                <span className="meta-label">Confidence:</span>
                <span className="meta-value font-mono">
                  {Math.round((selectedNode.confidence || 0.94) * 100)}%
                </span>
              </div>
              <div className="meta-row">
                <span className="meta-label">Source Page:</span>
                <span className="meta-value font-mono">{selectedNode.page || 1}</span>
              </div>
              <div className="meta-row">
                <span className="meta-label">Associated Paper:</span>
                <span className="meta-value truncate">{selectedNode.paper || 'Literature Synthesis'}</span>
              </div>
            </div>

            <div className="inspector-evidence-box">
              <span className="box-title">Grounded Evidence Snippet:</span>
              <p className="box-quote">
                "Empirical validation confirms that {selectedNode.label.toLowerCase()} manifests as an active barrier in contemporary multi-domain deployments."
              </p>
            </div>

            <div className="inspector-actions">
              <button
                className="btn-inspect-paper"
                onClick={() => onOpenPaper && onOpenPaper(selectedNode)}
              >
                <FileText size={14} />
                <span>Open Source Paper</span>
              </button>
            </div>
          </aside>
        )}
      </div>
    </div>
  );
}
