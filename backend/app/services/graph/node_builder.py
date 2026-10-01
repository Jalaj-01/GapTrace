"""Node Builder & Entity Normalization Service (Phase 5).

Handles:
- Creation of the 10 core research knowledge graph node types:
  Paper, Author, Claim, Method, Dataset, Task, Finding, Limitation, FutureDirection, ResearchTopic
- Entity normalization and canonical resolution to prevent duplicates
- Alias preservation without aggressive or uncertain entity merging
- Grounded provenance and confidence tracking on all nodes.
"""

import re
from typing import Any, Dict, List, Optional, Set, Tuple
from backend.app.core.logging import get_logger
from backend.app.services.graph.graph_provenance import GraphProvenanceService

logger = get_logger("app.graph.node_builder")


class NodeTypes:
    """Enumeration of knowledge graph node categories."""
    PAPER = "Paper"
    AUTHOR = "Author"
    CLAIM = "Claim"
    METHOD = "Method"
    DATASET = "Dataset"
    TASK = "Task"
    FINDING = "Finding"
    LIMITATION = "Limitation"
    FUTURE_DIRECTION = "FutureDirection"
    RESEARCH_TOPIC = "ResearchTopic"


# Canonical entity normalization dictionary
CANONICAL_ENTITIES: Dict[str, Tuple[str, str]] = {
    # Methods (normalized_key -> (Canonical Name, Category))
    "bert": ("BERT", NodeTypes.METHOD),
    "bert base": ("BERT", NodeTypes.METHOD),
    "bert large": ("BERT", NodeTypes.METHOD),
    "roberta": ("RoBERTa", NodeTypes.METHOD),
    "transformer": ("Transformer", NodeTypes.METHOD),
    "transformers": ("Transformer", NodeTypes.METHOD),
    "vanilla transformer": ("Transformer", NodeTypes.METHOD),
    "flashattention": ("FlashAttention", NodeTypes.METHOD),
    "flash attention": ("FlashAttention", NodeTypes.METHOD),
    "flash-attention": ("FlashAttention", NodeTypes.METHOD),
    "cnn": ("CNN", NodeTypes.METHOD),
    "convolutional neural network": ("CNN", NodeTypes.METHOD),
    "convolutional neural networks": ("CNN", NodeTypes.METHOD),
    "gnn": ("GNN", NodeTypes.METHOD),
    "graph neural network": ("GNN", NodeTypes.METHOD),
    "lstm": ("LSTM", NodeTypes.METHOD),
    "hdbscan": ("HDBSCAN", NodeTypes.METHOD),
    "bertopic": ("BERTopic", NodeTypes.METHOD),
    "kmeans": ("K-Means", NodeTypes.METHOD),
    "k-means": ("K-Means", NodeTypes.METHOD),
    "umap": ("UMAP", NodeTypes.METHOD),
    "state space model": ("State Space Model", NodeTypes.METHOD),
    "state space models": ("State Space Model", NodeTypes.METHOD),
    "mamba": ("Mamba", NodeTypes.METHOD),

    # Datasets
    "squad": ("SQuAD", NodeTypes.DATASET),
    "squad v1.1": ("SQuAD", NodeTypes.DATASET),
    "squad v2.0": ("SQuAD", NodeTypes.DATASET),
    "glue": ("GLUE", NodeTypes.DATASET),
    "superglue": ("SuperGLUE", NodeTypes.DATASET),
    "imagenet": ("ImageNet", NodeTypes.DATASET),
    "multinli": ("MultiNLI", NodeTypes.DATASET),
    "pubmed": ("PubMed", NodeTypes.DATASET),
    "mimic": ("MIMIC", NodeTypes.DATASET),
    "mimic-iii": ("MIMIC-III", NodeTypes.DATASET),
    "arxiv": ("arXiv", NodeTypes.DATASET),

    # Tasks
    "cross-domain adaptation": ("Cross-Domain Adaptation", NodeTypes.TASK),
    "domain adaptation": ("Domain Adaptation", NodeTypes.TASK),
    "out-of-distribution generalization": ("Out-of-Distribution Generalization", NodeTypes.TASK),
    "scientific text summarization": ("Scientific Text Summarization", NodeTypes.TASK),
    "text summarization": ("Text Summarization", NodeTypes.TASK),
    "summarization": ("Text Summarization", NodeTypes.TASK),
    "evidence extraction": ("Evidence Extraction", NodeTypes.TASK),
    "citation graph representation": ("Citation Graph Representation", NodeTypes.TASK),
    "contrastive representation learning": ("Contrastive Representation Learning", NodeTypes.TASK),
    "question answering": ("Question Answering", NodeTypes.TASK),
}


class NodeBuilder:
    """Builder responsible for synthesizing, deduplicating, and normalizing graph nodes."""

    @staticmethod
    def slugify(text: str) -> str:
        """Create a deterministic slug for graph node IDs."""
        cleaned = re.sub(r"[^\w\s-]", "", text.strip().lower())
        return re.sub(r"[-\s]+", "_", cleaned)[:64]

    @classmethod
    def normalize_entity_name(cls, raw_name: str) -> Tuple[str, str, float]:
        """Normalize an entity name using canonical mappings or clean heuristics.

        Returns:
            Tuple of (canonical_name, slug_id, confidence)
        """
        raw_clean = re.sub(r"\s+", " ", raw_name).strip()
        lookup_key = re.sub(r"[^\w\s]", "", raw_clean.lower())

        if lookup_key in CANONICAL_ENTITIES:
            canonical, _ = CANONICAL_ENTITIES[lookup_key]
            slug = cls.slugify(canonical)
            return canonical, slug, 0.95

        # Heuristic title-casing for novel entities
        tokens = raw_clean.split()
        if len(tokens) == 1 and len(tokens[0]) <= 5 and tokens[0].isalpha():
            # Potential acronym (e.g. BERT, GCN)
            canonical = tokens[0].upper()
        else:
            canonical = raw_clean.title()

        slug = cls.slugify(canonical)
        return canonical, slug, 0.80

    @classmethod
    def build_paper_node(cls, paper: Any) -> Dict[str, Any]:
        """Construct a standardized Paper node."""
        paper_id = getattr(paper, "id", None)
        title = getattr(paper, "title", "Untitled Paper")
        year = getattr(paper, "publication_year", None)
        authors = getattr(paper, "authors", []) or []
        abstract = getattr(paper, "abstract", "") or ""
        doi = getattr(paper, "doi", None)
        venue = getattr(paper, "venue", None)

        node_id = f"paper:{paper_id}" if paper_id else f"paper:{cls.slugify(title)}"

        return {
            "id": node_id,
            "label": title,
            "type": NodeTypes.PAPER,
            "properties": {
                "paper_id": paper_id,
                "title": title,
                "publication_year": year,
                "authors": authors,
                "abstract": abstract[:500] if abstract else "",
                "doi": doi,
                "venue": venue,
            },
            "provenance": GraphProvenanceService.create_provenance(
                paper_id=paper_id,
                paper_title=title,
                section_name="Metadata",
                page_number=1,
                source_text=f"Title: {title}. Year: {year}. Authors: {', '.join(authors) if isinstance(authors, list) else authors}",
                confidence=1.0,
                extraction_method="metadata_ingestion",
            ),
        }

    @classmethod
    def build_author_node(cls, author_name: str, paper: Optional[Any] = None) -> Dict[str, Any]:
        """Construct a normalized Author node."""
        clean_name = " ".join(author_name.strip().split())
        slug = cls.slugify(clean_name)
        node_id = f"author:{slug}"

        paper_id = getattr(paper, "id", None) if paper else None
        paper_title = getattr(paper, "title", None) if paper else None

        return {
            "id": node_id,
            "label": clean_name,
            "type": NodeTypes.AUTHOR,
            "properties": {
                "name": clean_name,
                "slug": slug,
                "aliases": [clean_name],
            },
            "provenance": GraphProvenanceService.create_provenance(
                paper_id=paper_id,
                paper_title=paper_title,
                section_name="Metadata",
                page_number=1,
                source_text=f"Author: {clean_name}",
                confidence=0.98,
                extraction_method="author_metadata",
            ),
        }

    @classmethod
    def build_method_node(
        cls,
        raw_name: str,
        paper: Optional[Any] = None,
        sentence: Optional[Any] = None,
        extraction: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Construct a normalized Method node with alias preservation."""
        canonical_name, slug, conf = cls.normalize_entity_name(raw_name)
        node_id = f"method:{slug}"

        paper_id = getattr(paper, "id", None) or (getattr(sentence, "paper_id", None) if sentence else None)
        paper_title = getattr(paper, "title", None) if paper else None
        sentence_id = getattr(sentence, "id", None) if sentence else None
        source_text = getattr(sentence, "source_text", raw_name) if sentence else raw_name
        section = getattr(sentence, "section_name", "Methodology") if sentence else "Methodology"
        page = getattr(sentence, "page_number", 1) if sentence else 1

        return {
            "id": node_id,
            "label": canonical_name,
            "type": NodeTypes.METHOD,
            "properties": {
                "name": canonical_name,
                "canonical_name": canonical_name,
                "slug": slug,
                "aliases": [raw_name] if raw_name != canonical_name else [],
                "confidence": conf,
            },
            "provenance": GraphProvenanceService.create_provenance(
                paper_id=paper_id,
                paper_title=paper_title,
                sentence_id=sentence_id,
                section_name=section,
                page_number=page,
                source_text=source_text,
                confidence=conf,
                extraction_method="scientific_entity_extractor",
            ),
        }

    @classmethod
    def build_dataset_node(
        cls,
        raw_name: str,
        paper: Optional[Any] = None,
        sentence: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Construct a normalized Dataset node."""
        canonical_name, slug, conf = cls.normalize_entity_name(raw_name)
        node_id = f"dataset:{slug}"

        paper_id = getattr(paper, "id", None) or (getattr(sentence, "paper_id", None) if sentence else None)
        paper_title = getattr(paper, "title", None) if paper else None
        sentence_id = getattr(sentence, "id", None) if sentence else None
        source_text = getattr(sentence, "source_text", raw_name) if sentence else raw_name
        section = getattr(sentence, "section_name", "Experiments") if sentence else "Experiments"
        page = getattr(sentence, "page_number", 1) if sentence else 1

        return {
            "id": node_id,
            "label": canonical_name,
            "type": NodeTypes.DATASET,
            "properties": {
                "name": canonical_name,
                "slug": slug,
                "aliases": [raw_name] if raw_name != canonical_name else [],
                "confidence": conf,
            },
            "provenance": GraphProvenanceService.create_provenance(
                paper_id=paper_id,
                paper_title=paper_title,
                sentence_id=sentence_id,
                section_name=section,
                page_number=page,
                source_text=source_text,
                confidence=conf,
                extraction_method="scientific_entity_extractor",
            ),
        }

    @classmethod
    def build_task_node(
        cls,
        raw_name: str,
        paper: Optional[Any] = None,
        sentence: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Construct a normalized Task node."""
        canonical_name, slug, conf = cls.normalize_entity_name(raw_name)
        node_id = f"task:{slug}"

        paper_id = getattr(paper, "id", None) or (getattr(sentence, "paper_id", None) if sentence else None)
        paper_title = getattr(paper, "title", None) if paper else None
        sentence_id = getattr(sentence, "id", None) if sentence else None
        source_text = getattr(sentence, "source_text", raw_name) if sentence else raw_name
        section = getattr(sentence, "section_name", "Introduction") if sentence else "Introduction"
        page = getattr(sentence, "page_number", 1) if sentence else 1

        return {
            "id": node_id,
            "label": canonical_name,
            "type": NodeTypes.TASK,
            "properties": {
                "name": canonical_name,
                "slug": slug,
                "aliases": [raw_name] if raw_name != canonical_name else [],
                "confidence": conf,
            },
            "provenance": GraphProvenanceService.create_provenance(
                paper_id=paper_id,
                paper_title=paper_title,
                sentence_id=sentence_id,
                section_name=section,
                page_number=page,
                source_text=source_text,
                confidence=conf,
                extraction_method="task_extraction",
            ),
        }

    @classmethod
    def build_claim_node(
        cls,
        sentence: Any,
        extraction: Optional[Any] = None,
        paper: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Construct a Claim node from scientific sentence discourse."""
        sent_id = getattr(sentence, "id", 0)
        paper_id = getattr(sentence, "paper_id", None) or (getattr(paper, "id", None) if paper else None)
        paper_title = getattr(paper, "title", None) if paper else None
        text = getattr(extraction, "extracted_text", None) or getattr(sentence, "source_text", "")
        section = getattr(sentence, "section_name", "General")
        page = getattr(sentence, "page_number", 1)
        conf = getattr(extraction, "confidence", 0.85)

        node_id = f"claim:{paper_id}:{sent_id}"

        return {
            "id": node_id,
            "label": text[:80] + ("..." if len(text) > 80 else ""),
            "type": NodeTypes.CLAIM,
            "properties": {
                "text": text,
                "discourse_type": getattr(extraction, "extraction_type", "CLAIM"),
                "paper_id": paper_id,
                "sentence_id": sent_id,
            },
            "provenance": GraphProvenanceService.create_provenance(
                paper_id=paper_id,
                paper_title=paper_title,
                sentence_id=sent_id,
                section_name=section,
                page_number=page,
                source_text=text,
                confidence=conf,
                extraction_method=getattr(extraction, "extraction_method", "discourse_classifier"),
            ),
        }

    @classmethod
    def build_finding_node(
        cls,
        sentence: Any,
        extraction: Optional[Any] = None,
        paper: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Construct a Finding node representing an empirical result."""
        sent_id = getattr(sentence, "id", 0)
        paper_id = getattr(sentence, "paper_id", None) or (getattr(paper, "id", None) if paper else None)
        paper_title = getattr(paper, "title", None) if paper else None
        text = getattr(extraction, "extracted_text", None) or getattr(sentence, "source_text", "")
        section = getattr(sentence, "section_name", "Results")
        page = getattr(sentence, "page_number", 1)
        conf = getattr(extraction, "confidence", 0.90)

        node_id = f"finding:{paper_id}:{sent_id}"

        return {
            "id": node_id,
            "label": text[:80] + ("..." if len(text) > 80 else ""),
            "type": NodeTypes.FINDING,
            "properties": {
                "text": text,
                "paper_id": paper_id,
                "sentence_id": sent_id,
            },
            "provenance": GraphProvenanceService.create_provenance(
                paper_id=paper_id,
                paper_title=paper_title,
                sentence_id=sent_id,
                section_name=section,
                page_number=page,
                source_text=text,
                confidence=conf,
                extraction_method=getattr(extraction, "extraction_method", "result_detector"),
            ),
        }

    @classmethod
    def build_limitation_node(
        cls,
        sentence: Any,
        extraction: Optional[Any] = None,
        paper: Optional[Any] = None,
        limitation_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Construct a Limitation node preserving precise provenance."""
        sent_id = getattr(sentence, "id", 0)
        paper_id = getattr(sentence, "paper_id", None) or (getattr(paper, "id", None) if paper else None)
        paper_title = getattr(paper, "title", None) if paper else None
        text = getattr(extraction, "extracted_text", None) or getattr(sentence, "source_text", "")
        section = getattr(sentence, "section_name", "Limitations")
        page = getattr(sentence, "page_number", 1)
        conf = getattr(extraction, "confidence", 0.90)

        lid = limitation_id or sent_id or cls.slugify(text[:30])
        node_id = f"limitation:{paper_id}:{lid}"

        return {
            "id": node_id,
            "label": text[:80] + ("..." if len(text) > 80 else ""),
            "type": NodeTypes.LIMITATION,
            "properties": {
                "limitation_id": lid,
                "text": text,
                "paper_id": paper_id,
                "sentence_id": sent_id,
            },
            "provenance": GraphProvenanceService.create_provenance(
                paper_id=paper_id,
                paper_title=paper_title,
                sentence_id=sent_id,
                section_name=section,
                page_number=page,
                source_text=text,
                confidence=conf,
                extraction_method=getattr(extraction, "extraction_method", "limitation_detector"),
            ),
        }

    @classmethod
    def build_future_direction_node(
        cls,
        sentence: Any,
        extraction: Optional[Any] = None,
        paper: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Construct a FutureDirection node."""
        sent_id = getattr(sentence, "id", 0)
        paper_id = getattr(sentence, "paper_id", None) or (getattr(paper, "id", None) if paper else None)
        paper_title = getattr(paper, "title", None) if paper else None
        text = getattr(extraction, "extracted_text", None) or getattr(sentence, "source_text", "")
        section = getattr(sentence, "section_name", "Future Work")
        page = getattr(sentence, "page_number", 1)
        conf = getattr(extraction, "confidence", 0.90)

        node_id = f"direction:{paper_id}:{sent_id}"

        return {
            "id": node_id,
            "label": text[:80] + ("..." if len(text) > 80 else ""),
            "type": NodeTypes.FUTURE_DIRECTION,
            "properties": {
                "text": text,
                "paper_id": paper_id,
                "sentence_id": sent_id,
            },
            "provenance": GraphProvenanceService.create_provenance(
                paper_id=paper_id,
                paper_title=paper_title,
                sentence_id=sent_id,
                section_name=section,
                page_number=page,
                source_text=text,
                confidence=conf,
                extraction_method=getattr(extraction, "extraction_method", "future_work_detector"),
            ),
        }

    @classmethod
    def build_topic_node(cls, topic: Any) -> Dict[str, Any]:
        """Construct a ResearchTopic node from Phase 4 topic discovery."""
        t_id = getattr(topic, "topic_id", 0)
        name = getattr(topic, "topic_name", f"Topic {t_id}")
        terms = getattr(topic, "representative_terms", []) or []
        status = getattr(topic, "trajectory_status", "PERSISTENT")

        node_id = f"topic:{t_id}"

        return {
            "id": node_id,
            "label": name,
            "type": NodeTypes.RESEARCH_TOPIC,
            "properties": {
                "topic_id": t_id,
                "topic_name": name,
                "representative_terms": terms,
                "trajectory_status": status,
            },
            "provenance": GraphProvenanceService.create_provenance(
                section_name="Research Landscape",
                source_text=f"Discovered theme: {name}. Status: {status}. Top terms: {', '.join([str(t.get('term', t)) if isinstance(t, dict) else str(t) for t in terms[:5]])}",
                confidence=0.92,
                extraction_method="bertopic_landscape_discovery",
            ),
        }
