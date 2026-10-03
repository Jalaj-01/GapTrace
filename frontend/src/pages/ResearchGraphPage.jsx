import React, { useState, useEffect, useMemo } from 'react';
import {
  Share2,
  RefreshCw,
  Search,
  Filter,
  Layers,
  FileText,
  Cpu,
  Database,
  AlertTriangle,
  Compass,
  Quote,
  Eye,
  X,
  ExternalLink,
  Download,
  Sparkles,
  Info,
} from 'lucide-react';
import {
  fetchGraphOverview,
  buildGraph,
  fetchPaperSubgraph,
  fetchLimitationGraph,
  fetchMethodGraph,
  fetchPapers,
  exportCypher,
} from '../services/api';
import { useResearch } from '../contexts/ResearchContext';
import { LoadingSpinner, SkeletonCard } from '../components/ui/LoadingSkeleton';
import ErrorBanner from '../components/ui/ErrorBanner';
import EmptyState from '../components/ui/EmptyState';

const TYPE_CONFIG = {
  Paper: { label: 'Paper', color: '#3b82f6', bg: 'bg-blue-500/10 text-blue-400 border-blue-500/20' },
  Method: { label: 'Method', color: '#8b5cf6', bg: 'bg-purple-500/10 text-purple-400 border-purple-500/20' },
  Dataset: { label: 'Dataset', color: '#10b981', bg: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' },
  Claim: { label: 'Claim', color: '#f59e0b', bg: 'bg-amber-500/10 text-amber-400 border-amber-500/20' },
  Limitation: { label: 'Limitation', color: '#ef4444', bg: 'bg-red-500/10 text-red-400 border-red-500/20' },
  Topic: { label: 'Topic', color: '#ec4899', bg: 'bg-pink-500/10 text-pink-400 border-pink-500/20' },
  FutureDirection: { label: 'Research Direction', color: '#06b6d4', bg: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20' },
};

export default function ResearchGraphPage() {
  const { openPaperDetail } = useResearch();

  const [overview, setOverview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isBuilding, setIsBuilding] = useState(false);
  const [error, setError] = useState(null);

  // Graph elements
  const [nodes, setNodes] = useState([]);
  const [edges, setEdges] = useState([]);
  const [selectedNode, setSelectedNode] = useState(null);
  const [nodeProvenance, setNodeProvenance] = useState(null);
  const [loadingProvenance, setLoadingProvenance] = useState(false);

  // Filters & Search
  const [selectedType, setSelectedType] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [cypherModalOpen, setCypherModalOpen] = useState(false);
  const [cypherStatements, setCypherStatements] = useState([]);

  const loadGraph = async () => {
    setLoading(true);
    setError(null);
    try {
      const ov = await fetchGraphOverview();
      setOverview(ov);

      // Fetch papers to extract subgraphs for interactive visualization
      const papers = await fetchPapers(0, 10);
      const allNodes = new Map();
      const allEdges = [];

      for (const p of papers.slice(0, 5)) {
        try {
          const sub = await fetchPaperSubgraph(p.id, 1);
          if (sub?.nodes) {
            sub.nodes.forEach((n) => {
              if (!allNodes.has(n.id)) {
                allNodes.set(n.id, n);
              }
            });
          }
          if (sub?.edges) {
            sub.edges.forEach((e) => {
              allEdges.push(e);
            });
          }
        } catch {
          // Non-blocking
        }
      }

      setNodes(Array.from(allNodes.values()));
      setEdges(allEdges);
    } catch (err) {
      setError(err.message || 'Failed to load research knowledge graph.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadGraph();
  }, []);

  const handleRebuildGraph = async () => {
    setIsBuilding(true);
    setError(null);
    try {
      const res = await buildGraph();
      setOverview(res);
      await loadGraph();
    } catch (err) {
      setError(`Rebuild failed: ${err.message}`);
    } finally {
      setIsBuilding(false);
    }
  };

  const handleNodeClick = async (node) => {
    setSelectedNode(node);
    setLoadingProvenance(true);
    setNodeProvenance(null);
    try {
      if (node.type === 'Limitation') {
        const data = await fetchLimitationGraph(node.id);
        setNodeProvenance(data);
      } else if (node.type === 'Method') {
        const data = await fetchMethodGraph(node.id);
        setNodeProvenance(data);
      } else if (node.type === 'Paper' && node.properties?.paper_id) {
        setNodeProvenance({
          paper_id: node.properties.paper_id,
          title: node.properties.title,
          abstract: node.properties.abstract,
          year: node.properties.year,
        });
      } else {
        setNodeProvenance({
          label: node.label,
          properties: node.properties,
          provenance: node.provenance,
        });
      }
    } catch {
      setNodeProvenance({
        label: node.label,
        properties: node.properties,
        provenance: node.provenance,
      });
    } finally {
      setLoadingProvenance(false);
    }
  };

  const handleExportCypher = async () => {
    try {
      const data = await exportCypher();
      setCypherStatements(data?.statements || []);
      setCypherModalOpen(true);
    } catch (err) {
      setError(`Cypher export failed: ${err.message}`);
    }
  };

  // Filter nodes
  const filteredNodes = useMemo(() => {
    return nodes.filter((n) => {
      if (selectedType !== 'ALL' && n.type !== selectedType) return false;
      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        return n.label?.toLowerCase().includes(q) || n.type?.toLowerCase().includes(q);
      }
      return true;
    });
  }, [nodes, selectedType, searchQuery]);

  const activeNodeIds = useMemo(
    () => new Set(filteredNodes.map((n) => n.id)),
    [filteredNodes]
  );

  const filteredEdges = useMemo(() => {
    return edges.filter(
      (e) => activeNodeIds.has(e.source) && activeNodeIds.has(e.target)
    );
  }, [edges, activeNodeIds]);

  // Compute clean radial / concentric node layout coordinates
  const layoutedNodes = useMemo(() => {
    const centerX = 400;
    const centerY = 270;

    // Group nodes by category
    const centerNodes = filteredNodes.filter((n) => n.type === 'Paper');
    const innerNodes = filteredNodes.filter((n) => n.type === 'Topic');
    const midNodes = filteredNodes.filter((n) => n.type === 'Method' || n.type === 'Dataset');
    const outerNodes = filteredNodes.filter(
      (n) => n.type === 'Claim' || n.type === 'Limitation' || n.type === 'FutureDirection'
    );
    const otherNodes = filteredNodes.filter(
      (n) => !['Paper', 'Topic', 'Method', 'Dataset', 'Claim', 'Limitation', 'FutureDirection'].includes(n.type)
    );

    const result = [];

    // Center layer: Papers
    centerNodes.forEach((node, idx) => {
      if (centerNodes.length === 1) {
        result.push({ ...node, x: centerX, y: centerY, layer: 'center' });
      } else {
        const angle = (idx / centerNodes.length) * 2 * Math.PI;
        result.push({
          ...node,
          x: centerX + 50 * Math.cos(angle),
          y: centerY + 50 * Math.sin(angle),
          layer: 'center',
        });
      }
    });

    // Inner layer: Topics (r = 115)
    innerNodes.forEach((node, idx) => {
      const angle = (idx / Math.max(1, innerNodes.length)) * 2 * Math.PI - Math.PI / 4;
      result.push({
        ...node,
        x: centerX + 115 * Math.cos(angle),
        y: centerY + 115 * Math.sin(angle),
        layer: 'inner',
      });
    });

    // Mid layer: Methods & Datasets (r = 180)
    midNodes.forEach((node, idx) => {
      const angle = (idx / Math.max(1, midNodes.length)) * 2 * Math.PI + Math.PI / 6;
      result.push({
        ...node,
        x: centerX + 180 * Math.cos(angle),
        y: centerY + 180 * Math.sin(angle),
        layer: 'mid',
      });
    });

    // Outer layer: Claims, Limitations, Directions, Others (r = 235)
    const combinedOuter = [...outerNodes, ...otherNodes];
    combinedOuter.forEach((node, idx) => {
      const angle = (idx / Math.max(1, combinedOuter.length)) * 2 * Math.PI;
      result.push({
        ...node,
        x: centerX + 235 * Math.cos(angle),
        y: centerY + 235 * Math.sin(angle),
        layer: 'outer',
      });
    });

    return result;
  }, [filteredNodes]);

  const nodeMap = useMemo(() => {
    const m = {};
    layoutedNodes.forEach((n) => {
      m[n.id] = n;
    });
    return m;
  }, [layoutedNodes]);

  return (
    <div className="research-graph-page p-6 space-y-6 max-w-7xl mx-auto">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-subtle">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-primary flex items-center gap-2">
            <Share2 size={24} className="text-purple-400" />
            Research Knowledge Graph
          </h1>
          <p className="text-sm text-secondary mt-1">
            Provenance-aware scientific discourse graph connecting papers, methods, datasets, claims, limitations, topics, and directions.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleExportCypher}
            className="px-3 py-1.5 text-xs font-medium border border-subtle rounded-md hover:bg-muted text-secondary hover:text-primary transition flex items-center gap-1.5"
          >
            <Download size={13} />
            <span>Export Cypher</span>
          </button>
          <button
            onClick={handleRebuildGraph}
            disabled={isBuilding}
            className="px-3.5 py-1.5 text-xs font-semibold bg-primary text-primary-contrast rounded-md hover:opacity-90 transition flex items-center gap-1.5"
          >
            <Sparkles size={13} className={isBuilding ? 'animate-spin' : ''} />
            <span>{isBuilding ? 'Rebuilding Graph...' : 'Rebuild Graph'}</span>
          </button>
          <button
            onClick={loadGraph}
            disabled={loading}
            className="p-1.5 border border-subtle rounded-md hover:bg-muted text-secondary hover:text-primary transition"
            title="Reload Graph"
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>

      <ErrorBanner message={error} onRetry={loadGraph} />

      {/* Graph Topology Statistics */}
      {overview && (
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3">
          <div className="bg-card border border-subtle rounded-lg p-3">
            <span className="text-[11px] font-semibold text-secondary uppercase block mb-0.5">
              Total Nodes
            </span>
            <span className="text-xl font-bold font-mono text-primary">
              {overview.total_nodes}
            </span>
          </div>
          <div className="bg-card border border-subtle rounded-lg p-3">
            <span className="text-[11px] font-semibold text-secondary uppercase block mb-0.5">
              Discourse Edges
            </span>
            <span className="text-xl font-bold font-mono text-primary">
              {overview.total_edges}
            </span>
          </div>
          <div className="bg-card border border-subtle rounded-lg p-3">
            <span className="text-[11px] font-semibold text-secondary uppercase block mb-0.5">
              Graph Density
            </span>
            <span className="text-xl font-bold font-mono text-primary">
              {(overview.density || 0).toFixed(4)}
            </span>
          </div>
          <div className="bg-card border border-subtle rounded-lg p-3">
            <span className="text-[11px] font-semibold text-secondary uppercase block mb-0.5">
              Components
            </span>
            <span className="text-xl font-bold font-mono text-primary">
              {overview.connected_components_count || 1}
            </span>
          </div>
          <div className="bg-card border border-subtle rounded-lg p-3">
            <span className="text-[11px] font-semibold text-secondary uppercase block mb-0.5">
              Engine
            </span>
            <span className="text-xs font-mono text-primary font-semibold">
              {overview.graph_database_engine || 'NetworkX'}
            </span>
          </div>
          <div className="bg-card border border-subtle rounded-lg p-3">
            <span className="text-[11px] font-semibold text-secondary uppercase block mb-0.5">
              Synchronized
            </span>
            <span className="text-[11px] font-mono text-secondary truncate block">
              {overview.last_built_at ? new Date(overview.last_built_at).toLocaleTimeString() : 'Active'}
            </span>
          </div>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-3 bg-card border border-subtle rounded-lg p-3">
        <div className="flex flex-wrap items-center gap-1.5 w-full lg:w-auto">
          <span className="text-xs font-semibold text-secondary flex items-center gap-1 mr-1">
            <Filter size={13} />
            <span>Type:</span>
          </span>
          {['ALL', 'Paper', 'Method', 'Dataset', 'Claim', 'Limitation', 'Topic', 'FutureDirection'].map((t) => (
            <button
              key={t}
              onClick={() => setSelectedType(t)}
              className={`px-2.5 py-1 text-xs rounded-md transition font-medium whitespace-nowrap ${
                selectedType === t
                  ? 'bg-primary text-primary-contrast'
                  : 'bg-muted/40 text-secondary hover:text-primary hover:bg-muted'
              }`}
            >
              {TYPE_CONFIG[t]?.label || t}
            </button>
          ))}
        </div>

        <div className="relative w-full lg:w-64">
          <Search size={14} className="absolute left-3 top-2.5 text-secondary" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search nodes..."
            className="w-full pl-8 pr-3 py-1.5 text-xs bg-muted/30 border border-subtle rounded-md text-primary"
          />
        </div>
      </div>

      {/* Clean Helper Hint Banner (outside canvas) */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 px-3.5 py-2 bg-muted/20 border border-subtle rounded-lg text-xs text-secondary">
        <div className="flex items-center gap-2">
          <Info size={14} className="text-primary flex-shrink-0" />
          <span>Click any node to reveal exact source provenance, discourse edges, and extracted passages.</span>
        </div>
        <div className="text-[11px] font-mono text-muted">
          Active: {filteredNodes.length} nodes &bull; {filteredEdges.length} edges
        </div>
      </div>

      {loading ? (
        <div className="space-y-4">
          <LoadingSpinner text="Rendering knowledge graph nodes and discourse edges..." />
          <SkeletonCard count={2} height={200} />
        </div>
      ) : nodes.length === 0 ? (
        <EmptyState
          icon={Share2}
          title="Empty Research Knowledge Graph"
          description="Click 'Rebuild Graph' to ingest all papers, limitations, methods, and topics into the directed graph."
          actionLabel="Build Graph"
          onAction={handleRebuildGraph}
        />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Main SVG Graph Canvas (8 cols) */}
          <div className="lg:col-span-8 bg-card border border-subtle rounded-lg p-4 relative overflow-hidden flex flex-col justify-center items-center min-h-[520px]">
            <svg
              viewBox="0 0 800 560"
              className="w-full h-full cursor-default select-none"
              style={{ maxHeight: '560px' }}
            >
              {/* Edges */}
              <g className="edges">
                {filteredEdges.map((edge, idx) => {
                  const s = nodeMap[edge.source];
                  const t = nodeMap[edge.target];
                  if (!s || !t) return null;
                  const isEdgeActive =
                    selectedNode && (selectedNode.id === s.id || selectedNode.id === t.id);

                  return (
                    <g key={edge.id || idx}>
                      <line
                        x1={s.x}
                        y1={s.y}
                        x2={t.x}
                        y2={t.y}
                        stroke={isEdgeActive ? '#8b5cf6' : 'currentColor'}
                        strokeOpacity={isEdgeActive ? 0.9 : 0.25}
                        strokeWidth={isEdgeActive ? 2 : 1}
                        className="text-subtle transition-all"
                      />
                      {/* Edge Label for active */}
                      {isEdgeActive && (
                        <text
                          x={(s.x + t.x) / 2}
                          y={(s.y + t.y) / 2 - 4}
                          textAnchor="middle"
                          fill="#a78bfa"
                          fontSize="9"
                          fontFamily="monospace"
                        >
                          {edge.relationship}
                        </text>
                      )}
                    </g>
                  );
                })}
              </g>

              {/* Nodes */}
              <g className="nodes">
                {layoutedNodes.map((node) => {
                  const isSelected = selectedNode?.id === node.id;
                  const cfg = TYPE_CONFIG[node.type] || { color: '#94a3b8' };
                  return (
                    <g
                      key={node.id}
                      onClick={() => handleNodeClick(node)}
                      className="cursor-pointer group"
                    >
                      <title>{node.label} ({node.type})</title>
                      <circle
                        cx={node.x}
                        cy={node.y}
                        r={isSelected ? 18 : node.layer === 'center' ? 16 : 12}
                        fill={cfg.color}
                        fillOpacity={isSelected ? 0.95 : 0.8}
                        stroke={isSelected ? '#ffffff' : 'rgba(255,255,255,0.25)'}
                        strokeWidth={isSelected ? 2.5 : 1}
                        className="transition-all hover:scale-110"
                      />
                      {/* Dynamic label positioning without collision */}
                      <text
                        x={node.x}
                        y={node.y + (isSelected ? 24 : 20)}
                        textAnchor="middle"
                        fill="currentColor"
                        fontSize={isSelected ? '11' : node.layer === 'center' ? '11' : '9.5'}
                        fontWeight={isSelected ? '600' : '400'}
                        className="text-primary pointer-events-none select-none"
                      >
                        {node.label.length > 18 ? node.label.slice(0, 16) + '…' : node.label}
                      </text>
                    </g>
                  );
                })}
              </g>
            </svg>
          </div>

          {/* Node Provenance Drawer (4 cols) */}
          <div className="lg:col-span-4">
            {selectedNode ? (
              <div className="border border-subtle rounded-lg bg-card p-5 space-y-4 sticky top-4">
                <div className="flex items-center justify-between pb-3 border-b border-subtle">
                  <div className="flex items-center gap-2">
                    <span
                      className={`text-[10px] font-mono px-2 py-0.5 rounded font-semibold ${
                        TYPE_CONFIG[selectedNode.type]?.bg || 'bg-muted text-secondary'
                      }`}
                    >
                      {selectedNode.type}
                    </span>
                    <span className="text-xs font-mono text-secondary truncate max-w-[140px]">
                      {selectedNode.id}
                    </span>
                  </div>
                  <button
                    onClick={() => setSelectedNode(null)}
                    className="text-secondary hover:text-primary"
                  >
                    <X size={15} />
                  </button>
                </div>

                <div>
                  <h3 className="text-base font-bold text-primary mb-1">
                    {selectedNode.label}
                  </h3>
                </div>

                {loadingProvenance ? (
                  <LoadingSpinner text="Retrieving provenance..." />
                ) : (
                  nodeProvenance && (
                    <div className="space-y-3 text-xs">
                      {/* Paper Provenance */}
                      {nodeProvenance.paper_id && (
                        <div className="p-3 bg-muted/20 border border-subtle rounded space-y-1">
                          <span className="font-semibold text-secondary uppercase text-[10px] block">
                            Source Paper
                          </span>
                          <div className="font-medium text-primary">
                            {nodeProvenance.title || `Paper #${nodeProvenance.paper_id}`}
                          </div>
                          <button
                            onClick={() => openPaperDetail(nodeProvenance.paper_id)}
                            className="text-blue-400 hover:underline flex items-center gap-1 mt-1 text-[11px]"
                          >
                            <span>Inspect Paper</span> &rarr;
                          </button>
                        </div>
                      )}

                      {/* Source Sentence Provenance */}
                      {selectedNode.provenance?.source_sentence && (
                        <div className="p-3 bg-muted/20 border border-subtle rounded space-y-1">
                          <span className="font-semibold text-secondary uppercase text-[10px] block">
                            Exact Source Sentence
                          </span>
                          <p className="text-secondary leading-relaxed">
                            &ldquo;{selectedNode.provenance.source_sentence}&rdquo;
                          </p>
                          <div className="flex items-center gap-3 text-[10px] text-secondary font-mono mt-1">
                            <span>Section: {selectedNode.provenance.section || 'Unknown'}</span>
                            <span>Page: {selectedNode.provenance.page || 1}</span>
                          </div>
                        </div>
                      )}

                      {/* Papers Addressing / Limiting */}
                      {nodeProvenance.papers_limited_by &&
                        nodeProvenance.papers_limited_by.length > 0 && (
                          <div>
                            <span className="font-semibold text-secondary uppercase text-[10px] block mb-1">
                              Papers Limited By This ({nodeProvenance.papers_limited_by.length})
                            </span>
                            <div className="space-y-1">
                              {nodeProvenance.papers_limited_by.map((item, idx) => (
                                <div
                                  key={idx}
                                  className="p-2 border border-subtle rounded bg-muted/10 text-[11px] text-primary"
                                >
                                  {item.paper_title || `Paper #${item.paper_id}`}
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                      {nodeProvenance.papers_addressing &&
                        nodeProvenance.papers_addressing.length > 0 && (
                          <div>
                            <span className="font-semibold text-secondary uppercase text-[10px] block mb-1">
                              Papers Addressing This ({nodeProvenance.papers_addressing.length})
                            </span>
                            <div className="space-y-1">
                              {nodeProvenance.papers_addressing.map((item, idx) => (
                                <div
                                  key={idx}
                                  className="p-2 border border-subtle rounded bg-emerald-500/5 border-emerald-500/20 text-[11px] text-emerald-400"
                                >
                                  {item.paper_title || `Paper #${item.paper_id}`}
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                      {/* Proposing & Using papers for methods */}
                      {nodeProvenance.proposing_papers &&
                        nodeProvenance.proposing_papers.length > 0 && (
                          <div>
                            <span className="font-semibold text-secondary uppercase text-[10px] block mb-1">
                              Proposed By
                            </span>
                            <div className="space-y-1">
                              {nodeProvenance.proposing_papers.map((item, idx) => (
                                <div
                                  key={idx}
                                  className="p-2 border border-subtle rounded bg-muted/10 text-[11px]"
                                >
                                  {item.paper_title}
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                    </div>
                  )
                )}
              </div>
            ) : (
              <div className="border border-subtle rounded-lg bg-card p-6 text-center text-secondary text-xs">
                Select any node on the graph canvas to inspect its source provenance and empirical connections.
              </div>
            )}
          </div>
        </div>
      )}

      {/* Cypher Export Modal */}
      {cypherModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4">
          <div className="bg-card border border-subtle rounded-lg max-w-2xl w-full p-5 space-y-4 shadow-xl">
            <div className="flex items-center justify-between pb-3 border-b border-subtle">
              <h3 className="text-base font-bold text-primary">
                Exported Neo4j / Memgraph Cypher Statements
              </h3>
              <button
                onClick={() => setCypherModalOpen(false)}
                className="text-secondary hover:text-primary"
              >
                <X size={16} />
              </button>
            </div>
            <p className="text-xs text-secondary">
              Use these Cypher statements to migrate the in-memory directed research graph into a graph database:
            </p>
            <div className="bg-muted p-3 rounded font-mono text-[11px] max-h-72 overflow-y-auto space-y-1 text-primary">
              {cypherStatements.map((stmt, idx) => (
                <div key={idx}>{stmt}</div>
              ))}
            </div>
            <div className="flex justify-end">
              <button
                onClick={() => setCypherModalOpen(false)}
                className="px-4 py-1.5 text-xs font-semibold bg-primary text-primary-contrast rounded-md"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
