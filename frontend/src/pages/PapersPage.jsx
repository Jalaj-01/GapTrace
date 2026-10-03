import React, { useEffect, useState, useMemo } from 'react';
import {
  BookOpen,
  Search,
  UploadCloud,
  FileText,
  RotateCw,
  ExternalLink,
  ChevronDown,
  CheckCircle2,
  Calendar,
  Layers,
  Sparkles,
  ArrowRight,
  Filter,
  Eye,
} from 'lucide-react';
import { useResearch } from '../contexts/ResearchContext';
import { fetchPapers, uploadPaperFile, processPaperNLP, fetchTopics } from '../services/api';
import { LoadingSpinner, SkeletonTable } from '../components/ui/LoadingSkeleton';
import ErrorBanner from '../components/ui/ErrorBanner';
import EmptyState from '../components/ui/EmptyState';

export default function PapersPage() {
  const { openPaperDetail, setIsUploaderOpen } = useResearch();

  const [papers, setPapers] = useState([]);
  const [topics, setTopics] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filters & Search
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedYear, setSelectedYear] = useState('ALL');
  const [selectedTopic, setSelectedTopic] = useState('ALL');

  // Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 10;

  // Uploading state inside page
  const [isUploading, setIsUploading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState('');

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [papersData, topicsData] = await Promise.allSettled([
        fetchPapers(0, 200),
        fetchTopics(),
      ]);

      const papersList = papersData.status === 'fulfilled' && Array.isArray(papersData.value) ? papersData.value : [];
      const topicsList = topicsData.status === 'fulfilled' && Array.isArray(topicsData.value) ? topicsData.value : [];

      setPapers(papersList);
      setTopics(topicsList);
    } catch (err) {
      setError(err.message || 'Failed to load paper library.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // Compute unique years from paper collection
  const availableYears = useMemo(() => {
    const years = new Set();
    papers.forEach((p) => {
      if (p.year) years.add(p.year);
    });
    return Array.from(years).sort((a, b) => b - a);
  }, [papers]);

  // Filter papers
  const filteredPapers = useMemo(() => {
    return papers.filter((p) => {
      // Search query
      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        const matchesTitle = p.title?.toLowerCase().includes(q);
        const matchesFilename = p.filename?.toLowerCase().includes(q);
        const matchesAuthors = Array.isArray(p.authors)
          ? p.authors.some((a) => String(a).toLowerCase().includes(q))
          : false;
        if (!matchesTitle && !matchesFilename && !matchesAuthors) return false;
      }

      // Year filter
      if (selectedYear !== 'ALL') {
        if (Number(p.year) !== Number(selectedYear)) return false;
      }

      // Topic filter
      if (selectedTopic !== 'ALL') {
        if (p.topic_name && p.topic_name !== selectedTopic) return false;
      }

      return true;
    });
  }, [papers, searchQuery, selectedYear, selectedTopic]);

  // Paginated view
  const totalPages = Math.max(1, Math.ceil(filteredPapers.length / pageSize));
  const paginatedPapers = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return filteredPapers.slice(start, start + pageSize);
  }, [filteredPapers, currentPage, pageSize]);

  const handleInlineFileUpload = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    setUploadMessage(`Uploading ${file.name}...`);
    try {
      const uploaded = await uploadPaperFile(file);
      setUploadMessage(`Parsing NLP for ${file.name}...`);
      try {
        await processPaperNLP(uploaded.id);
      } catch {
        // NLP can finish asynchronously
      }
      setUploadMessage(`Successfully ingested "${file.name}"!`);
      await loadData();
    } catch (err) {
      setError(`Upload failed: ${err.message}`);
    } finally {
      setIsUploading(false);
      setTimeout(() => setUploadMessage(''), 4000);
    }
  };

  return (
    <div className="papers-page-container p-6 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-subtle">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-primary flex items-center gap-2.5">
            <BookOpen size={24} className="text-blue-400 flex-shrink-0" />
            <span>Scientific Paper Library</span>
          </h1>
          <p className="text-sm text-secondary mt-1">
            Browse ingested publications, search evidence passages, and view structured scientific extractions.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <label className="cursor-pointer px-3 py-1.5 text-xs font-semibold bg-primary text-primary-contrast rounded-md hover:opacity-90 transition inline-flex items-center gap-1.5 shadow-sm">
            <UploadCloud size={14} className="flex-shrink-0" />
            <span>Upload PDF</span>
            <input
              type="file"
              accept=".pdf"
              onChange={handleInlineFileUpload}
              style={{ display: 'none' }}
              disabled={isUploading}
            />
          </label>
          <button
            onClick={loadData}
            disabled={loading}
            className="p-1.5 border border-subtle rounded-md hover:bg-muted text-secondary hover:text-primary transition"
            title="Reload papers"
          >
            <RotateCw size={14} className={loading ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>

      <ErrorBanner message={error} onRetry={loadData} />

      {uploadMessage && (
        <div className="p-3 bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs rounded-md flex items-center gap-2">
          <Sparkles size={14} className="animate-spin" />
          <span>{uploadMessage}</span>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="grid grid-cols-1 sm:grid-cols-12 gap-3 bg-card border border-subtle rounded-lg p-3">
        {/* Search */}
        <div className="sm:col-span-6 relative">
          <Search size={15} className="absolute left-3 top-2.5 text-secondary" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setCurrentPage(1);
            }}
            placeholder="Search papers by title, author, or keyword..."
            className="w-full pl-9 pr-3 py-1.5 text-xs bg-muted/30 border border-subtle rounded-md text-primary focus:outline-none focus:border-primary"
          />
        </div>

        {/* Year Filter */}
        <div className="sm:col-span-3 flex items-center gap-2">
          <Calendar size={14} className="text-secondary flex-shrink-0" />
          <select
            value={selectedYear}
            onChange={(e) => {
              setSelectedYear(e.target.value);
              setCurrentPage(1);
            }}
            className="w-full py-1.5 px-2 text-xs bg-muted/30 border border-subtle rounded-md text-primary"
          >
            <option value="ALL">All Years</option>
            {availableYears.map((yr) => (
              <option key={yr} value={yr}>
                {yr}
              </option>
            ))}
          </select>
        </div>

        {/* Topic Filter */}
        <div className="sm:col-span-3 flex items-center gap-2">
          <Layers size={14} className="text-secondary flex-shrink-0" />
          <select
            value={selectedTopic}
            onChange={(e) => {
              setSelectedTopic(e.target.value);
              setCurrentPage(1);
            }}
            className="w-full py-1.5 px-2 text-xs bg-muted/30 border border-subtle rounded-md text-primary"
          >
            <option value="ALL">All Topics</option>
            {topics.map((t) => (
              <option key={t.topic_id} value={t.topic_name}>
                {t.topic_name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Paper List Content */}
      {loading ? (
        <div className="space-y-4">
          <LoadingSpinner text="Fetching scientific publications..." />
          <SkeletonTable rows={6} cols={5} />
        </div>
      ) : filteredPapers.length === 0 ? (
        <EmptyState
          icon={FileText}
          title="No papers found"
          description={
            searchQuery || selectedYear !== 'ALL' || selectedTopic !== 'ALL'
              ? 'No publications match your filter criteria. Try clearing filters.'
              : 'The paper library is empty. Upload scientific PDF publications to begin research intelligence analysis.'
          }
          actionLabel="Clear Filters"
          onAction={() => {
            setSearchQuery('');
            setSelectedYear('ALL');
            setSelectedTopic('ALL');
          }}
        />
      ) : (
        <div className="space-y-4">
          <div className="border border-subtle rounded-lg bg-card overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-muted/50 border-b border-subtle text-secondary uppercase font-mono tracking-wider">
                  <tr>
                    <th className="py-3 px-4" style={{ width: '70px' }}>ID</th>
                    <th className="py-3 px-4" style={{ minWidth: '340px' }}>Title & Publication</th>
                    <th className="py-3 px-4" style={{ width: '220px' }}>Authors</th>
                    <th className="py-3 px-4" style={{ width: '90px' }}>Year</th>
                    <th className="py-3 px-4" style={{ width: '90px' }}>Sections</th>
                    <th className="py-3 px-4 text-right" style={{ width: '110px' }}>Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-subtle">
                  {paginatedPapers.map((paper) => (
                    <tr
                      key={paper.id}
                      className="hover:bg-muted/20 transition group cursor-pointer"
                      onClick={() => openPaperDetail(paper.id)}
                    >
                      <td className="py-3 px-4 font-mono text-secondary" style={{ width: '70px' }}>
                        #{paper.id}
                      </td>
                      <td className="py-3 px-4" style={{ minWidth: '340px' }}>
                        <div className="font-semibold text-primary group-hover:text-blue-400 transition">
                          {paper.title || paper.filename}
                        </div>
                        {paper.abstract && (
                          <div className="text-[11px] text-secondary line-clamp-2 mt-1">
                            {paper.abstract}
                          </div>
                        )}
                      </td>
                      <td className="py-3 px-4 text-secondary truncate" style={{ width: '220px', maxWidth: '220px' }}>
                        {Array.isArray(paper.authors)
                          ? paper.authors.join(', ')
                          : paper.authors || 'Unknown'}
                      </td>
                      <td className="py-3 px-4 font-mono text-secondary" style={{ width: '90px' }}>
                        {paper.year || '—'}
                      </td>
                      <td className="py-3 px-4 font-mono text-secondary" style={{ width: '90px' }}>
                        {paper.section_count || paper.sections?.length || 0}
                      </td>
                      <td className="py-3 px-4 text-right" style={{ width: '110px' }}>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            openPaperDetail(paper.id);
                          }}
                          className="px-2.5 py-1 text-[11px] font-medium border border-subtle rounded hover:bg-muted text-primary transition inline-flex items-center gap-1 shadow-sm"
                        >
                          <Eye size={12} className="flex-shrink-0" />
                          <span>Inspect</span>
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Pagination Controls */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between text-xs text-secondary px-2">
              <div>
                Showing {(currentPage - 1) * pageSize + 1} to{' '}
                {Math.min(currentPage * pageSize, filteredPapers.length)} of{' '}
                {filteredPapers.length} papers
              </div>
              <div className="flex items-center gap-1">
                <button
                  disabled={currentPage === 1}
                  onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                  className="px-2.5 py-1 border border-subtle rounded disabled:opacity-40 hover:bg-muted"
                >
                  Previous
                </button>
                <span className="px-2 font-mono">
                  {currentPage} / {totalPages}
                </span>
                <button
                  disabled={currentPage === totalPages}
                  onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                  className="px-2.5 py-1 border border-subtle rounded disabled:opacity-40 hover:bg-muted"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
