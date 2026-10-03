# Phase 5 Evaluation: Provenance-Aware Research Knowledge Graph

## Overview

Phase 5 introduces a provenance-preserving **Research Knowledge Graph (RKG)** to **ResearchGapX**. The knowledge graph explicitly connects scientific papers, authors, claims, empirical findings, methods, datasets, tasks, limitations, and future research directions into a structured topological network.

Every entity and relationship retains fine-grained provenance metadata linking back to source publications, structural sections, page numbers, and verbatim textual evidence.

---

## 1. Graph Technology & Architecture

The graph layer is engineered around a modular, graph-database-ready architecture:
- **Core Engine**: Implemented initially with `NetworkX` (`nx.DiGraph`) for in-memory operations and rapid query traversal.
- **Migration Readiness**: Exposes `.export_cypher()` and standardized node/edge dictionaries to enable plug-and-play migration to production graph databases (e.g., Neo4j, Memgraph, or Amazon Neptune) without code restructuring.
- **Strict Evidence Invariance**: Neither nodes nor edges can be fabricated without an explicit provenance record.

### Modular Graph Subsystems

```
backend/app/services/graph/
├── __init__.py               # Service exports and registry
├── research_graph.py         # NetworkX DiGraph wrapper, DB builder, and Cypher exporter
├── node_builder.py           # Entity normalization, alias resolution, 10 node types
├── relationship_builder.py   # High-confidence extraction of 11 directed relationship types
├── graph_query.py            # Targeted scientific graph traversal queries (8 queries)
└── graph_provenance.py       # Evidence grounding, validation, and citation formatting
```

---

## 2. Node Types & Representation

The graph categorizes scientific information into **10 core node types**:

| Node Type | ID Format | Description | Example Entity |
| :--- | :--- | :--- | :--- |
| **`Paper`** | `paper:{id}` | Ingested scientific research document | *Domain Adaptation in Low-Resource Scientific NLP* |
| **`Author`** | `author:{slug}` | Credited scientific researcher | *Alice Chen*, *Bob Smith* |
| **`Claim`** | `claim:{paper_id}:{sentence_id}` | Proposed scientific assertion or objective | *"Dense retrieval degrades under distribution shift"* |
| **`Method`** | `method:{slug}` | Algorithmic technique or architecture | *BERT*, *FlashAttention*, *HDBSCAN* |
| **`Dataset`** | `dataset:{slug}` | Empirical benchmark or corpus | *SQuAD*, *GLUE*, *MIMIC-III* |
| **`Task`** | `task:{slug}` | Scientific problem formulation | *Cross-Domain Adaptation*, *Summarization* |
| **`Finding`** | `finding:{paper_id}:{sentence_id}` | Empirical experimental result | *"Fine-tuning reduces transfer loss by 40%"* |
| **`Limitation`** | `limitation:{paper_id}:{sentence_id}` | Documented technical bottleneck | *"High peak memory at 32k context lengths"* |
| **`FutureDirection`**| `direction:{paper_id}:{sentence_id}` | Explicit author commitment or open direction | *"Hardware kernel fusing for long sequences"* |
| **`ResearchTopic`** | `topic:{id}` | Landscape research theme (Phase 4) | *Topic 0: Context Lengths & Memory* |

### Entity Normalization & Alias Preservation

To prevent node duplication while preserving nuances across papers:
1. **Canonical Dictionary**: Resolves common aliases to canonical labels (e.g. `bert-base`, `bert large`, and `bert` resolve to `BERT`).
2. **Conservative Merging**: Nodes are only merged when canonical identity is unambiguous; novel entities maintain their specific labels while preserving aliases in `properties.aliases`.
3. **Deterministic Slugification**: Node IDs use deterministic slugification (`method:flashattention`, `dataset:squad`).

---

## 3. Relationship Types & Extraction Rules

The graph models **11 directed relationship types**:

| Relationship | Direction | Trigger Criteria | Default Conf. |
| :--- | :--- | :--- | :---: |
| **`cites`** | `Paper → Paper` | Bibliographic reference title matching | 0.98 |
| **`uses`** | `Paper → Method/Dataset` | Empirical evaluation or model usage cues | 0.88 - 0.90 |
| **`proposes`** | `Paper/Author → Method/Finding/Claim` | Author attribution or proposal cues (*"we propose", "our model"*) | 0.95 |
| **`extends`** | `Paper/Method → Method` | Incremental extension cues (*"we extend", "builds upon"*) | 0.90 |
| **`compares`** | `Paper/Method → Method` | Experimental baseline comparison (*"compared against", "versus"*) | 0.85 |
| **`supports`** | `Finding/Claim → Claim` | Positive empirical confirmation or high cosine semantic similarity | 0.85 - 0.95 |
| **`contradicts`** | `Finding/Limitation → Claim` | Refutation cues (*"contrary to prior claims", "fails to generalize"*) | 0.85 - 0.95 |
| **`limited_by`** | `Paper/Method → Limitation` | Limitation discourse extraction (Phase 2) | 0.92 |
| **`addresses`** | `Paper/Method → Limitation` | Cross-paper resolution of documented bottleneck | 0.88 |
| **`studies`** | `Paper → Task/Topic` | Problem formulation or subject investigation | 0.85 |
| **`belongs_to`**| `Paper → ResearchTopic` | Unsupervised landscape topic assignment (Phase 4) | 0.60 - 1.00 |

---

## 4. Provenance Grounding Examples

Every node and edge retains complete evidence traceability.

### Node Provenance Example
```json
{
  "id": "limitation:2:1",
  "label": "High peak memory at 32k context lengths",
  "type": "Limitation",
  "properties": {
    "limitation_id": 1,
    "paper_id": 2,
    "text": "High peak memory at 32k context lengths"
  },
  "provenance": {
    "paper_id": 2,
    "paper_title": "Efficient Transformers via Linear Attention",
    "section_name": "Limitations",
    "page_number": 7,
    "sentence_id": 34,
    "sentence_order": 34,
    "source_text": "A primary limitation of our approach is high peak memory overhead at 32k context lengths.",
    "confidence": 0.92,
    "extraction_method": "limitation_detector"
  }
}
```

### Edge Provenance Example (`addresses`)
```json
{
  "id": "paper:3->addresses->limitation:2:1",
  "source": "paper:3",
  "target": "limitation:2:1",
  "relationship": "addresses",
  "confidence": 0.88,
  "extraction_method": "semantic_limitation_alignment",
  "provenance": {
    "paper_id": 3,
    "paper_title": "Overcoming Quadratic Bottlenecks in Scientific Retrieval",
    "section_name": "Introduction",
    "page_number": 1,
    "sentence_id": 4,
    "source_text": "Our kernelized sparse approximation completely addresses the high peak memory at 32k context lengths.",
    "confidence": 0.88,
    "extraction_method": "semantic_limitation_alignment"
  }
}
```

---

## 5. Canonical Graph Queries & Traversal Use Cases

The graph query service (`GraphQueryService`) provides 8 specialized research traversal methods:

1. **Papers Addressing a Limitation**:
   - Query: `GET /api/v1/graph/query?query_type=addressing_limitation&target_id=limitation:2:1`
   - Returns: Papers that specifically claim to resolve or mitigate the bottleneck with supporting evidence.

2. **Papers Extending a Method**:
   - Query: `GET /api/v1/graph/query?query_type=extending_method&text=FlashAttention`
   - Returns: Publications that adapt or build directly upon the foundational method.

3. **Methods Used for a Dataset**:
   - Query: `GET /api/v1/graph/query?query_type=methods_for_dataset&text=SQuAD`
   - Returns: All architectures and methods evaluated against the benchmark.

4. **Claims Supporting Another Claim**:
   - Query: `GET /api/v1/graph/query?query_type=supporting_claims&target_id=claim:1:1`
   - Returns: Empirical findings and literature claims corroborating the assertion.

5. **Claims Contradicting Another Claim**:
   - Query: `GET /api/v1/graph/query?query_type=contradicting_claims&target_id=claim:1:1`
   - Returns: Conflicting results, counter-evidence, and disputed findings.

6. **Papers Connected to a Topic**:
   - Query: `GET /api/v1/graph/query?query_type=papers_for_topic&topic_id=0`
   - Returns: All corpus papers categorized under the research theme.

7. **Papers Connected to a Candidate Limitation**:
   - Query: `GET /api/v1/graph/query?query_type=papers_for_limitation&text=computational+overhead`
   - Returns: Both papers that suffer from the bottleneck (`limited_by`) and papers that propose solutions (`addresses`).

8. **Research Directions Related to a Limitation**:
   - Query: `GET /api/v1/graph/query?query_type=directions_for_limitation&target_id=limitation:2:1`
   - Returns: Explicit author commitments (`FutureDirection` nodes) proposing next steps.

---

## 6. Graph Statistics & API Surface

| Endpoint | Method | Output Contract | Description |
| :--- | :---: | :--- | :--- |
| `/api/v1/graph/overview` | `GET` | `GraphOverviewResponse` | Topology summary (nodes, edges, density, components) |
| `/api/v1/graph/build` | `POST` | `GraphOverviewResponse` | Synchronizes in-memory directed graph with all database entities |
| `/api/v1/graph/paper/{id}` | `GET` | `GraphSubgraphResponse` | Ego-subgraph surrounding a paper (1-3 hops) with full evidence |
| `/api/v1/graph/limitation/{id}` | `GET` | `Dict[str, Any]` | Limitation node with papers limited by it, directions, and solvers |
| `/api/v1/graph/method/{id}` | `GET` | `Dict[str, Any]` | Method node with proposing, using, and extending papers |
| `/api/v1/graph/query` | `GET` | `GraphQueryResponse` | Targeted execution of any of the 8 canonical graph queries |
| `/api/v1/graph/export/cypher` | `GET` | `Dict[str, Any]` | Generated Cypher queries for Neo4j / Memgraph ingestion |

---

## 7. Known Limitations & Graph Future Work

1. **Entity Coreference Across Venues**: Variational naming conventions (e.g. *"FlashAttention-2"* vs *"FlashAttention v2"*) are normalized via lookup tables and string distance; an unsupervised entity resolution model using sentence-transformer embeddings could further automate new entity alias discovery.
2. **In-Memory Scale**: While NetworkX is optimal for datasets of $10^2$ to $10^5$ nodes, enterprise scale ($> 10^6$ nodes) will benefit from exporting directly to Neo4j via the provided `/api/v1/graph/export/cypher` endpoint.
3. **Indirect Contradiction Reasoning**: Contradictions are currently detected via direct polarity cues and semantic entailment markers. Deep multi-hop contradiction chains across citation paths will be strengthened in downstream analysis.
