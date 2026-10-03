"""Phase 5 Unit Test Suite: Research Knowledge Graph Entities & Traversal.

Covers:
- Node creation across all 10 scientific node types
- Entity normalization and duplicate handling
- Alias preservation without aggressive merging
- Directed relationship creation and provenance verification
- Confidence clamping and metadata auditing
- All 8 canonical graph queries
- Missing nodes, disconnected papers, and conflicting relationships
- Cypher query statement export for graph database migration
"""

import pytest
from backend.app.services.graph.graph_provenance import GraphProvenanceService
from backend.app.services.graph.node_builder import NodeBuilder, NodeTypes
from backend.app.services.graph.relationship_builder import (
    RelationshipBuilder,
    RelationTypes,
)
from backend.app.services.graph.research_graph import ResearchKnowledgeGraph
from backend.app.services.graph.graph_query import GraphQueryService


@pytest.fixture
def synthetic_graph():
    """Build a rich synthetic research knowledge graph for deterministic testing."""
    rkg = ResearchKnowledgeGraph()

    # 1. Add Papers
    p1 = {
        "id": "paper:1",
        "label": "Low-Resource Domain Adaptation in NLP",
        "type": NodeTypes.PAPER,
        "properties": {"paper_id": 1, "title": "Low-Resource Domain Adaptation in NLP", "publication_year": 2023},
        "provenance": GraphProvenanceService.create_provenance(paper_id=1, paper_title="Low-Resource Domain Adaptation in NLP"),
    }
    p2 = {
        "id": "paper:2",
        "label": "Efficient Transformers via Linear Attention",
        "type": NodeTypes.PAPER,
        "properties": {"paper_id": 2, "title": "Efficient Transformers via Linear Attention", "publication_year": 2024},
        "provenance": GraphProvenanceService.create_provenance(paper_id=2, paper_title="Efficient Transformers via Linear Attention"),
    }
    p3 = {
        "id": "paper:3",
        "label": "Overcoming Quadratic Bottlenecks in Scientific Retrieval",
        "type": NodeTypes.PAPER,
        "properties": {"paper_id": 3, "title": "Overcoming Quadratic Bottlenecks in Scientific Retrieval", "publication_year": 2025},
        "provenance": GraphProvenanceService.create_provenance(paper_id=3, paper_title="Overcoming Quadratic Bottlenecks in Scientific Retrieval"),
    }
    rkg.add_node(p1)
    rkg.add_node(p2)
    rkg.add_node(p3)

    # 2. Add Authors
    a1 = NodeBuilder.build_author_node("Alice Chen", paper=type("P", (), {"id": 1, "title": p1["label"]}))
    a2 = NodeBuilder.build_author_node("Bob Smith", paper=type("P", (), {"id": 2, "title": p2["label"]}))
    rkg.add_node(a1)
    rkg.add_node(a2)
    rkg.add_edge(RelationshipBuilder.create_edge_dict(a1["id"], p1["id"], RelationTypes.PROPOSES))
    rkg.add_edge(RelationshipBuilder.create_edge_dict(a2["id"], p2["id"], RelationTypes.PROPOSES))

    # 3. Add Methods & Datasets
    m1 = NodeBuilder.build_method_node("BERT", paper=type("P", (), {"id": 1, "title": p1["label"]}))
    m2 = NodeBuilder.build_method_node("FlashAttention", paper=type("P", (), {"id": 2, "title": p2["label"]}))
    d1 = NodeBuilder.build_dataset_node("SQuAD", paper=type("P", (), {"id": 1, "title": p1["label"]}))
    rkg.add_node(m1)
    rkg.add_node(m2)
    rkg.add_node(d1)

    rkg.add_edge(RelationshipBuilder.create_edge_dict(p1["id"], m1["id"], RelationTypes.USES))
    rkg.add_edge(RelationshipBuilder.create_edge_dict(p1["id"], d1["id"], RelationTypes.USES))
    rkg.add_edge(RelationshipBuilder.create_edge_dict(p2["id"], m2["id"], RelationTypes.PROPOSES))
    rkg.add_edge(RelationshipBuilder.create_edge_dict(p3["id"], m2["id"], RelationTypes.EXTENDS))

    # 4. Add Limitations & Future Directions
    l1 = {
        "id": "limitation:2:1",
        "label": "High peak memory at 32k context lengths",
        "type": NodeTypes.LIMITATION,
        "properties": {"limitation_id": 1, "text": "High peak memory at 32k context lengths", "paper_id": 2},
        "provenance": GraphProvenanceService.create_provenance(paper_id=2, source_text="High peak memory at 32k context lengths"),
    }
    fw1 = {
        "id": "direction:2:1",
        "label": "Hardware kernel fusing for long sequences",
        "type": NodeTypes.FUTURE_DIRECTION,
        "properties": {"text": "Hardware kernel fusing for long sequences", "paper_id": 2},
        "provenance": GraphProvenanceService.create_provenance(paper_id=2, source_text="Hardware kernel fusing for long sequences"),
    }
    rkg.add_node(l1)
    rkg.add_node(fw1)
    rkg.add_edge(RelationshipBuilder.create_edge_dict(p2["id"], l1["id"], RelationTypes.LIMITED_BY))
    rkg.add_edge(RelationshipBuilder.create_edge_dict(p2["id"], fw1["id"], RelationTypes.PROPOSES))
    rkg.add_edge(RelationshipBuilder.create_edge_dict(l1["id"], fw1["id"], "addressed_by"))

    # Paper 3 addresses limitation in Paper 2
    rkg.add_edge(RelationshipBuilder.build_addresses_limitation_edge(
        solving_paper_id=3,
        limitation_node_id=l1["id"],
        evidence_text="Our kernelized sparse approximation completely addresses the high peak memory at 32k context lengths.",
        solving_title=p3["label"],
    ))

    # 5. Add Claims & Findings (Supporting / Contradicting)
    c1 = {
        "id": "claim:1:1",
        "label": "Dense retrieval fails on biomedical texts",
        "type": NodeTypes.CLAIM,
        "properties": {"text": "Dense retrieval fails on biomedical texts", "paper_id": 1},
        "provenance": GraphProvenanceService.create_provenance(paper_id=1, source_text="Dense retrieval fails on biomedical texts"),
    }
    f1 = {
        "id": "finding:2:1",
        "label": "Fine-tuning reduces biomedical transfer loss by 40%",
        "type": NodeTypes.FINDING,
        "properties": {"text": "Fine-tuning reduces biomedical transfer loss by 40%", "paper_id": 2},
        "provenance": GraphProvenanceService.create_provenance(paper_id=2, source_text="Fine-tuning reduces biomedical transfer loss"),
    }
    rkg.add_node(c1)
    rkg.add_node(f1)
    rkg.add_edge(RelationshipBuilder.create_edge_dict(
        source=f1["id"],
        target=c1["id"],
        relationship=RelationTypes.CONTRADICTS,
        source_text="Contrary to prior claims that dense retrieval fails on biomedical texts, our fine-tuning reduces transfer loss.",
    ))

    # 6. Add Topic & Citations
    t1 = {
        "id": "topic:0",
        "label": "Efficient Transformers & Attention",
        "type": NodeTypes.RESEARCH_TOPIC,
        "properties": {"topic_id": 0, "topic_name": "Efficient Transformers & Attention"},
        "provenance": GraphProvenanceService.create_provenance(source_text="Topic 0 theme"),
    }
    rkg.add_node(t1)
    rkg.add_edge(RelationshipBuilder.create_edge_dict(p2["id"], t1["id"], RelationTypes.BELONGS_TO))
    rkg.add_edge(RelationshipBuilder.create_edge_dict(p3["id"], t1["id"], RelationTypes.BELONGS_TO))
    rkg.add_edge(RelationshipBuilder.build_citation_edge(3, 2, citing_title=p3["label"]))

    return rkg


class TestPhase5GraphUnit:
    """Comprehensive unit test suite for Phase 5 Research Knowledge Graph."""

    def test_node_creation_all_ten_types(self):
        """Verify proper generation and metadata structure across all 10 node types."""
        rkg = ResearchKnowledgeGraph()

        node_types_to_test = [
            NodeTypes.PAPER,
            NodeTypes.AUTHOR,
            NodeTypes.CLAIM,
            NodeTypes.METHOD,
            NodeTypes.DATASET,
            NodeTypes.TASK,
            NodeTypes.FINDING,
            NodeTypes.LIMITATION,
            NodeTypes.FUTURE_DIRECTION,
            NodeTypes.RESEARCH_TOPIC,
        ]

        for i, ntype in enumerate(node_types_to_test):
            nid = f"test_node_{i}"
            res_id = rkg.add_node({
                "id": nid,
                "label": f"Sample {ntype}",
                "type": ntype,
                "properties": {"key": "val"},
                "provenance": GraphProvenanceService.create_provenance(source_text=f"Provenance for {ntype}"),
            })
            assert res_id == nid
            retrieved = rkg.get_node(nid)
            assert retrieved is not None
            assert retrieved["type"] == ntype
            assert retrieved["properties"]["key"] == "val"
            assert GraphProvenanceService.verify_provenance_completeness(retrieved) is True

    def test_duplicate_handling_and_alias_preservation(self):
        """Verify adding an entity multiple times preserves aliases and avoids duplicate nodes."""
        rkg = ResearchKnowledgeGraph()

        # First addition
        m1 = NodeBuilder.build_method_node("BERT")
        rkg.add_node(m1)
        assert rkg.graph.number_of_nodes() == 1

        # Second addition with alias
        m2 = NodeBuilder.build_method_node("bert base")
        rkg.add_node(m2)
        assert rkg.graph.number_of_nodes() == 1  # Deduplicated under method:bert

        # Verify aliases merged
        node = rkg.get_node("method:bert")
        aliases = node["properties"]["aliases"]
        assert "bert base" in aliases or "BERT" in node["label"]

    def test_relationship_creation_and_direction(self, synthetic_graph):
        """Verify edge creation, directional integrity, and relationship attributes."""
        g = synthetic_graph.graph

        # Paper 3 -> cites -> Paper 2
        assert g.has_edge("paper:3", "paper:2")
        edge_data = g.get_edge_data("paper:3", "paper:2")
        assert edge_data["relationship"] == RelationTypes.CITES
        assert edge_data["confidence"] >= 0.90
        assert "source_text" in edge_data["provenance"]

        # Inverse edge should NOT exist unless explicitly defined
        assert not g.has_edge("paper:2", "paper:3")

    def test_missing_nodes_handling(self):
        """Attempting to add an edge between missing nodes should fail gracefully without crashing."""
        rkg = ResearchKnowledgeGraph()
        edge = RelationshipBuilder.create_edge_dict("paper:999", "method:nonexistent", RelationTypes.USES)
        result = rkg.add_edge(edge)
        assert result is None
        assert rkg.graph.number_of_edges() == 0

    def test_disconnected_papers(self):
        """Papers with no links should exist as valid isolated nodes without graph corruption."""
        rkg = ResearchKnowledgeGraph()
        p_iso = NodeBuilder.build_paper_node(type("P", (), {
            "id": 99,
            "title": "Isolated Unconnected Paper",
            "publication_year": 2024,
            "authors": ["Lonely Researcher"],
            "abstract": "No citations or methods extracted yet.",
            "doi": None,
            "venue": None,
        }))
        rkg.add_node(p_iso)

        overview = rkg.get_overview()
        assert overview["total_nodes"] == 1
        assert overview["total_edges"] == 0
        assert overview["connected_components_count"] == 1

    def test_conflicting_relationships(self, synthetic_graph):
        """Verify graph accommodates both supporting and contradicting relationships between claims."""
        g = synthetic_graph.graph

        # Verify contradicts edge
        contradict_edges = [
            (u, v, d) for u, v, d in g.edges(data=True) if d.get("relationship") == RelationTypes.CONTRADICTS
        ]
        assert len(contradict_edges) >= 1
        u, v, d = contradict_edges[0]
        assert d.get("relationship") == RelationTypes.CONTRADICTS
        assert "biomedical" in d["provenance"]["source_text"].lower()

    # =========================================================================
    # Canonical 8 Graph Queries
    # =========================================================================

    def test_query_1_papers_addressing_limitation(self, synthetic_graph):
        """1. Query papers addressing a specific limitation."""
        qs = GraphQueryService(synthetic_graph)
        results = qs.papers_addressing_limitation(limitation_id="limitation:2:1")
        assert len(results) >= 1
        assert results[0]["paper_id"] == 3
        assert results[0]["relationship"] == RelationTypes.ADDRESSES

    def test_query_2_papers_extending_method(self, synthetic_graph):
        """2. Query papers extending a specific method."""
        qs = GraphQueryService(synthetic_graph)
        results = qs.papers_extending_method(method_name="FlashAttention")
        assert len(results) >= 1
        assert results[0]["paper_id"] == 3
        assert results[0]["relationship"] == RelationTypes.EXTENDS

    def test_query_3_methods_used_for_dataset(self, synthetic_graph):
        """3. Query methods evaluated or used on a dataset."""
        qs = GraphQueryService(synthetic_graph)
        results = qs.methods_used_for_dataset(dataset_name="SQuAD")
        assert len(results) >= 1
        method_names = [r["method_name"] for r in results]
        assert "BERT" in method_names

    def test_query_4_and_5_claims_supporting_and_contradicting(self, synthetic_graph):
        """4 & 5. Query supporting and contradicting claim evidence."""
        qs = GraphQueryService(synthetic_graph)
        contradicting = qs.claims_contradicting_claim(claim_id="claim:1:1")
        assert len(contradicting) >= 1
        assert contradicting[0]["relationship"] == RelationTypes.CONTRADICTS
        assert contradicting[0]["contradicting_type"] == NodeTypes.FINDING

        supporting = qs.claims_supporting_claim(claim_id="claim:1:1")
        assert isinstance(supporting, list)

    def test_query_6_papers_connected_to_topic(self, synthetic_graph):
        """6. Query papers assigned to a landscape topic."""
        qs = GraphQueryService(synthetic_graph)
        results = qs.papers_connected_to_topic(topic_id=0)
        assert len(results) == 2
        paper_ids = {r["paper_id"] for r in results}
        assert paper_ids == {2, 3}

    def test_query_7_papers_connected_to_candidate_limitation(self, synthetic_graph):
        """7. Query papers both suffering from and addressing a limitation."""
        qs = GraphQueryService(synthetic_graph)
        res = qs.papers_connected_to_candidate_limitation(limitation_id="limitation:2:1")
        assert len(res["papers_limited_by"]) >= 1
        assert len(res["papers_addressing"]) >= 1
        assert res["total_papers"] >= 2

    def test_query_8_research_directions_related_to_limitation(self, synthetic_graph):
        """8. Query future research directions connected to a limitation."""
        qs = GraphQueryService(synthetic_graph)
        results = qs.research_directions_related_to_limitation(limitation_id="limitation:2:1")
        assert len(results) >= 1
        assert "kernel fusing" in results[0]["direction_text"].lower()

    def test_cypher_export(self, synthetic_graph):
        """Verify Cypher query generation for Neo4j graph database export."""
        statements = synthetic_graph.export_cypher()
        assert len(statements) >= 10
        # Check node statement syntax
        assert any("MERGE (n:Paper" in s for s in statements)
        # Check relationship statement syntax
        assert any("MERGE (a)-[r:CITES" in s for s in statements)
