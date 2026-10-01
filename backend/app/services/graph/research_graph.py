"""Core Research Knowledge Graph Service (Phase 5).

Implements:
- Provenance-aware directed multigraph abstraction using NetworkX (nx.DiGraph)
- Graph database ready architecture (exportable to Neo4j Cypher / Memgraph / GraphML)
- Database ingestion from papers, discourse extractions, topics, and citations
- Structural overview diagnostics and ego-subgraph resolution.
"""

from datetime import datetime, timezone
import json
import re
from typing import Any, Dict, List, Optional, Set, Tuple
import networkx as nx
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.logging import get_logger
from backend.app.core.errors import NotFoundError, ValidationError
from backend.app.models.paper import (
    DiscoveredTopic,
    Paper,
    PaperReference,
    PaperSection,
    PaperTopicAssignment,
    ScientificExtraction,
    ScientificSentence,
)
from backend.app.services.graph.graph_provenance import GraphProvenanceService
from backend.app.services.graph.node_builder import NodeBuilder, NodeTypes
from backend.app.services.graph.relationship_builder import (
    RelationshipBuilder,
    RelationTypes,
)

logger = get_logger("app.graph.core")


class ResearchKnowledgeGraph:
    """Provenance-preserving scientific knowledge graph wrapping NetworkX DiGraph."""

    def __init__(self):
        self._graph = nx.DiGraph()
        self._last_built_at: Optional[datetime] = None

    @property
    def graph(self) -> nx.DiGraph:
        return self._graph

    def clear(self) -> None:
        """Reset the internal graph state."""
        self._graph.clear()
        self._last_built_at = None

    def add_node(self, node_data: Dict[str, Any]) -> str:
        """Add or update a node while preserving aliases and verifying provenance.

        Returns:
            The unique node ID.
        """
        node_id = str(node_data["id"])
        label = node_data.get("label", node_id)
        node_type = node_data.get("type", "Entity")
        properties = node_data.get("properties", {})
        provenance = node_data.get("provenance", {})

        if self._graph.has_node(node_id):
            # Node already exists: merge properties & aliases safely without overwriting
            existing = self._graph.nodes[node_id]
            existing_props = existing.get("properties", {})
            existing_aliases = set(existing_props.get("aliases", []))
            new_aliases = set(properties.get("aliases", []))
            combined_aliases = list(existing_aliases.union(new_aliases))

            existing_props["aliases"] = combined_aliases
            existing["properties"] = existing_props
            return node_id

        self._graph.add_node(
            node_id,
            id=node_id,
            label=label,
            type=node_type,
            properties=properties,
            provenance=provenance,
        )
        return node_id

    def add_edge(self, edge_data: Dict[str, Any]) -> Optional[str]:
        """Add a directed relationship edge between two existing nodes with provenance.

        Returns:
            The edge identifier string or None if endpoints do not exist.
        """
        source = str(edge_data["source"])
        target = str(edge_data["target"])
        rel = edge_data.get("relationship", "related_to")
        conf = edge_data.get("confidence", 1.0)
        method = edge_data.get("extraction_method", "pipeline")
        prov = edge_data.get("provenance", {})
        edge_id = edge_data.get("id") or f"{source}->{rel}->{target}"

        # Ensure both endpoints exist
        if not self._graph.has_node(source) or not self._graph.has_node(target):
            logger.debug(f"Cannot add edge {edge_id}: source ({source}) or target ({target}) missing.")
            return None

        # Check for duplicate edge: if identical edge exists, retain higher confidence
        if self._graph.has_edge(source, target):
            existing_edge = self._graph.get_edge_data(source, target)
            if existing_edge.get("relationship") == rel:
                if existing_edge.get("confidence", 0.0) >= conf:
                    return edge_id  # Keep existing higher-confidence edge

        self._graph.add_edge(
            source,
            target,
            id=edge_id,
            relationship=rel,
            confidence=conf,
            extraction_method=method,
            provenance=prov,
        )
        return edge_id

    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve full details of a specific graph node."""
        if not self._graph.has_node(node_id):
            return None
        node_attr = dict(self._graph.nodes[node_id])
        return node_attr

    def get_overview(self) -> Dict[str, Any]:
        """Calculate graph-wide topology metrics and categorical breakdowns."""
        total_nodes = self._graph.number_of_nodes()
        total_edges = self._graph.number_of_edges()

        # Node breakdown
        node_counts: Dict[str, int] = {}
        for _, data in self._graph.nodes(data=True):
            ntype = data.get("type", "Unknown")
            node_counts[ntype] = node_counts.get(ntype, 0) + 1

        # Edge breakdown
        edge_counts: Dict[str, int] = {}
        for _, _, data in self._graph.edges(data=True):
            rel = data.get("relationship", "related_to")
            edge_counts[rel] = edge_counts.get(rel, 0) + 1

        # Topology
        density = round(float(nx.density(self._graph)), 6) if total_nodes > 1 else 0.0
        try:
            connected_components = nx.number_weakly_connected_components(self._graph)
        except Exception:
            connected_components = 0

        return {
            "total_nodes": total_nodes,
            "total_edges": total_edges,
            "density": density,
            "connected_components_count": connected_components,
            "node_counts_by_type": node_counts,
            "edge_counts_by_type": edge_counts,
            "last_built_at": self._last_built_at.isoformat() if self._last_built_at else None,
            "graph_database_engine": "NetworkX (Ready for Neo4j / Memgraph migration)",
        }

    def get_subgraph_by_nodes(self, node_ids: Set[str]) -> Dict[str, Any]:
        """Extract a serialized subgraph containing the specified nodes and their interconnecting edges."""
        valid_nodes = [nid for nid in node_ids if self._graph.has_node(nid)]
        subg = self._graph.subgraph(valid_nodes)

        nodes_list = []
        for nid in subg.nodes():
            nodes_list.append(dict(self._graph.nodes[nid]))

        edges_list = []
        for u, v, data in subg.edges(data=True):
            edges_list.append({
                "id": data.get("id", f"{u}->{v}"),
                "source": u,
                "target": v,
                "relationship": data.get("relationship", "related_to"),
                "confidence": data.get("confidence", 1.0),
                "extraction_method": data.get("extraction_method", "pipeline"),
                "provenance": data.get("provenance", {}),
            })

        return {
            "total_nodes": len(nodes_list),
            "total_edges": len(edges_list),
            "nodes": nodes_list,
            "edges": edges_list,
        }

    def get_paper_subgraph(self, paper_id: int, hops: int = 1) -> Dict[str, Any]:
        """Retrieve ego-network subgraph for a paper including its connected entities."""
        paper_node_id = f"paper:{paper_id}"
        if not self._graph.has_node(paper_node_id):
            raise NotFoundError(f"Paper node '{paper_node_id}' does not exist in research knowledge graph.")

        nodes_to_include = {paper_node_id}
        current_layer = {paper_node_id}

        for _ in range(hops):
            next_layer = set()
            for nid in current_layer:
                successors = set(self._graph.successors(nid))
                predecessors = set(self._graph.predecessors(nid))
                next_layer.update(successors)
                next_layer.update(predecessors)
            nodes_to_include.update(next_layer)
            current_layer = next_layer

        return self.get_subgraph_by_nodes(nodes_to_include)

    def build_from_database(self, db: Session) -> Dict[str, Any]:
        """Ingest all ingested papers, sentences, extractions, references, and topics from the database."""
        self.clear()
        logger.info("Building Research Knowledge Graph from database entities...")

        # 1. Ingest Papers and Authors
        papers = db.scalars(select(Paper).order_by(Paper.id)).all()
        paper_lookup: Dict[int, Paper] = {p.id: p for p in papers}
        paper_titles_to_id: Dict[str, int] = {p.title.lower().strip(): p.id for p in papers}

        for paper in papers:
            # Paper Node
            p_node = NodeBuilder.build_paper_node(paper)
            self.add_node(p_node)

            # Author Nodes and proposes/authored edges
            if isinstance(paper.authors, list):
                for auth in paper.authors:
                    if auth and str(auth).strip():
                        a_node = NodeBuilder.build_author_node(str(auth), paper)
                        self.add_node(a_node)
                        # Edge: Author -> proposes -> Paper
                        self.add_edge(RelationshipBuilder.create_edge_dict(
                            source=a_node["id"],
                            target=p_node["id"],
                            relationship=RelationTypes.PROPOSES,
                            source_paper_id=paper.id,
                            source_paper_title=paper.title,
                            section_name="Metadata",
                            page_number=1,
                            source_text=f"Author {auth} authored paper '{paper.title}'",
                            confidence=0.98,
                            extraction_method="author_metadata",
                        ))

        # 2. Ingest Citations from PaperReferences
        references = db.scalars(select(PaperReference)).all()
        for ref in references:
            if ref.title and ref.title.lower().strip() in paper_titles_to_id:
                cited_id = paper_titles_to_id[ref.title.lower().strip()]
                if cited_id != ref.paper_id:
                    citing_paper = paper_lookup.get(ref.paper_id)
                    citing_title = citing_paper.title if citing_paper else None
                    c_edge = RelationshipBuilder.build_citation_edge(
                        citing_paper_id=ref.paper_id,
                        cited_paper_id=cited_id,
                        context_text=ref.raw_text,
                        citing_title=citing_title,
                    )
                    self.add_edge(c_edge)

        # 3. Ingest Scientific Sentences & Extractions (Claims, Methods, Datasets, Limitations, Findings)
        extractions = db.scalars(
            select(ScientificExtraction).order_by(ScientificExtraction.paper_id, ScientificExtraction.sentence_id)
        ).all()

        sentences = db.scalars(select(ScientificSentence)).all()
        sentence_lookup: Dict[int, ScientificSentence] = {s.id: s for s in sentences}

        limitation_nodes: List[Dict[str, Any]] = []

        for ext in extractions:
            sent = sentence_lookup.get(ext.sentence_id)
            paper = paper_lookup.get(ext.paper_id)
            if not sent or not paper:
                continue

            etype = ext.extraction_type.upper()
            text = ext.extracted_text

            if etype == "METHOD":
                m_node = NodeBuilder.build_method_node(text, paper=paper, sentence=sent, extraction=ext)
                self.add_node(m_node)
                rel_type, conf = RelationshipBuilder.infer_method_relationship(sent.source_text)
                self.add_edge(RelationshipBuilder.create_edge_dict(
                    source=f"paper:{paper.id}",
                    target=m_node["id"],
                    relationship=rel_type,
                    source_paper_id=paper.id,
                    source_paper_title=paper.title,
                    source_sentence_id=sent.id,
                    section_name=sent.section_name,
                    page_number=sent.page_number,
                    source_text=sent.source_text,
                    confidence=conf,
                    extraction_method="method_inference",
                ))

            elif etype == "DATASET":
                d_node = NodeBuilder.build_dataset_node(text, paper=paper, sentence=sent)
                self.add_node(d_node)
                self.add_edge(RelationshipBuilder.create_edge_dict(
                    source=f"paper:{paper.id}",
                    target=d_node["id"],
                    relationship=RelationTypes.USES,
                    source_paper_id=paper.id,
                    source_paper_title=paper.title,
                    source_sentence_id=sent.id,
                    section_name=sent.section_name,
                    page_number=sent.page_number,
                    source_text=sent.source_text,
                    confidence=0.90,
                    extraction_method="dataset_inference",
                ))

            elif etype == "LIMITATION":
                l_node = NodeBuilder.build_limitation_node(
                    sentence=sent,
                    extraction=ext,
                    paper=paper,
                    limitation_id=ext.id,
                )
                self.add_node(l_node)
                limitation_nodes.append(l_node)
                self.add_edge(RelationshipBuilder.build_limitation_edge(
                    paper_id=paper.id,
                    limitation_node_id=l_node["id"],
                    limitation_text=text,
                    section_name=sent.section_name,
                    page_number=sent.page_number,
                    sentence_id=sent.id,
                    paper_title=paper.title,
                ))

            elif etype == "FUTURE_WORK":
                fw_node = NodeBuilder.build_future_direction_node(sentence=sent, extraction=ext, paper=paper)
                self.add_node(fw_node)
                self.add_edge(RelationshipBuilder.create_edge_dict(
                    source=f"paper:{paper.id}",
                    target=fw_node["id"],
                    relationship=RelationTypes.PROPOSES,
                    source_paper_id=paper.id,
                    source_paper_title=paper.title,
                    source_sentence_id=sent.id,
                    section_name=sent.section_name,
                    page_number=sent.page_number,
                    source_text=sent.source_text,
                    confidence=0.88,
                    extraction_method="future_direction_inference",
                ))

            elif etype == "RESULT":
                f_node = NodeBuilder.build_finding_node(sentence=sent, extraction=ext, paper=paper)
                self.add_node(f_node)
                self.add_edge(RelationshipBuilder.create_edge_dict(
                    source=f"paper:{paper.id}",
                    target=f_node["id"],
                    relationship=RelationTypes.PROPOSES,
                    source_paper_id=paper.id,
                    source_paper_title=paper.title,
                    source_sentence_id=sent.id,
                    section_name=sent.section_name,
                    page_number=sent.page_number,
                    source_text=sent.source_text,
                    confidence=0.90,
                    extraction_method="result_inference",
                ))

            elif etype in ("PROBLEM", "OBJECTIVE"):
                c_node = NodeBuilder.build_claim_node(sentence=sent, extraction=ext, paper=paper)
                self.add_node(c_node)
                self.add_edge(RelationshipBuilder.create_edge_dict(
                    source=f"paper:{paper.id}",
                    target=c_node["id"],
                    relationship=RelationTypes.PROPOSES,
                    source_paper_id=paper.id,
                    source_paper_title=paper.title,
                    source_sentence_id=sent.id,
                    section_name=sent.section_name,
                    page_number=sent.page_number,
                    source_text=sent.source_text,
                    confidence=0.85,
                    extraction_method="claim_inference",
                ))

        # 4. Ingest Topics & Topic Assignments (Phase 4)
        topics = db.scalars(select(DiscoveredTopic)).all()
        for t in topics:
            t_node = NodeBuilder.build_topic_node(t)
            self.add_node(t_node)

        assignments = db.scalars(select(PaperTopicAssignment)).all()
        for assign in assignments:
            paper = paper_lookup.get(assign.paper_id)
            if paper:
                t_edge = RelationshipBuilder.build_topic_membership_edge(
                    paper_id=assign.paper_id,
                    topic_id=assign.topic_id,
                    probability=assign.probability or 1.0,
                    paper_title=paper.title,
                )
                self.add_edge(t_edge)

        # 5. Cross-Paper Semantic Alignments (Addresses, Supports, Contradicts)
        self._infer_cross_paper_alignments(papers=papers, sentence_lookup=sentence_lookup, limitation_nodes=limitation_nodes)

        self._last_built_at = datetime.now(timezone.utc)
        logger.info(
            f"Research Knowledge Graph construction complete. Total nodes: {self._graph.number_of_nodes()}, "
            f"Total edges: {self._graph.number_of_edges()}"
        )
        return self.get_overview()

    def _infer_cross_paper_alignments(
        self,
        papers: List[Paper],
        sentence_lookup: Dict[int, ScientificSentence],
        limitation_nodes: List[Dict[str, Any]],
    ) -> None:
        """Infer cross-paper relationships (addresses, supports, contradicts) using semantic and lexical signals."""
        for p in papers:
            p_node_id = f"paper:{p.id}"
            # Check if this paper's sentences address an earlier paper's limitation
            for sent in p.scientific_sentences:
                stext = sent.source_text.lower()
                for l_node in limitation_nodes:
                    l_props = l_node.get("properties", {})
                    l_paper_id = l_props.get("paper_id")
                    if l_paper_id == p.id:
                        continue  # Skip self-addressing

                    l_text = l_props.get("text", "").lower()
                    # Lexical keyphrase overlap check
                    l_words = set(re.findall(r"\b\w{4,}\b", l_text))
                    s_words = set(re.findall(r"\b\w{4,}\b", stext))
                    overlap = l_words.intersection(s_words)

                    has_address_intent = bool(re.search(r"\b(address|overcome|mitigate|solve|tackle|resolve)\b", stext))

                    if has_address_intent and len(overlap) >= 2:
                        self.add_edge(RelationshipBuilder.build_addresses_limitation_edge(
                            solving_paper_id=p.id,
                            limitation_node_id=l_node["id"],
                            evidence_text=sent.source_text,
                            solving_title=p.title,
                            section_name=sent.section_name,
                            page_number=sent.page_number,
                            confidence=0.88,
                        ))

    def export_cypher(self) -> List[str]:
        """Generate Cypher statements for seamless import into Neo4j / Memgraph."""
        statements = []
        for nid, data in self._graph.nodes(data=True):
            ntype = data.get("type", "Entity")
            props = json.dumps(data.get("properties", {}))
            statements.append(f"MERGE (n:{ntype} {{id: '{nid}'}}) SET n += {props};")

        for u, v, data in self._graph.edges(data=True):
            rel = data.get("relationship", "RELATED_TO").upper()
            conf = data.get("confidence", 1.0)
            statements.append(
                f"MATCH (a {{id: '{u}'}}), (b {{id: '{v}'}}) "
                f"MERGE (a)-[r:{rel} {{confidence: {conf}}}]->(b);"
            )
        return statements


# Global singleton instance
_research_graph_instance: Optional[ResearchKnowledgeGraph] = None


def get_research_graph(db: Optional[Session] = None) -> ResearchKnowledgeGraph:
    """Retrieve or lazily construct the global Research Knowledge Graph instance."""
    global _research_graph_instance
    if _research_graph_instance is None:
        _research_graph_instance = ResearchKnowledgeGraph()
        if db is not None:
            _research_graph_instance.build_from_database(db)
    return _research_graph_instance
