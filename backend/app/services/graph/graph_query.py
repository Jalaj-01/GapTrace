"""Graph Query Engine for Targeted Research Exploration (Phase 5).

Implements the 8 required scientific research graph query modes:
1. Papers addressing a limitation
2. Papers extending a method
3. Methods used for a dataset
4. Claims supporting another claim
5. Claims contradicting another claim
6. Papers connected to a topic
7. Papers connected to a candidate limitation
8. Research directions related to a limitation
"""

import re
from typing import Any, Dict, List, Optional
import networkx as nx

from backend.app.core.logging import get_logger
from backend.app.services.graph.node_builder import NodeBuilder, NodeTypes
from backend.app.services.graph.relationship_builder import RelationTypes
from backend.app.services.graph.research_graph import ResearchKnowledgeGraph

logger = get_logger("app.graph.query")


class GraphQueryService:
    """Specialized query service executing scientific graph traversals."""

    def __init__(self, rkg: ResearchKnowledgeGraph):
        self.rkg = rkg

    @property
    def graph(self) -> nx.DiGraph:
        return self.rkg.graph

    def papers_addressing_limitation(
        self,
        limitation_id: Optional[str] = None,
        limitation_text: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """1. Find papers addressing a specific limitation."""
        target_nodes = self._find_limitation_nodes(limitation_id, limitation_text)
        results = []

        for l_nid in target_nodes:
            # Look for incoming edges with 'addresses'
            for u, v, data in self.graph.in_edges(l_nid, data=True):
                if data.get("relationship") == RelationTypes.ADDRESSES:
                    u_data = self.graph.nodes[u]
                    results.append({
                        "paper_node_id": u,
                        "paper_id": u_data.get("properties", {}).get("paper_id"),
                        "paper_title": u_data.get("properties", {}).get("title"),
                        "publication_year": u_data.get("properties", {}).get("publication_year"),
                        "target_limitation_id": l_nid,
                        "relationship": RelationTypes.ADDRESSES,
                        "confidence": data.get("confidence", 1.0),
                        "evidence_text": data.get("provenance", {}).get("source_text"),
                        "provenance": data.get("provenance", {}),
                    })
        return results

    def papers_extending_method(
        self,
        method_name: Optional[str] = None,
        method_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """2. Find papers extending a specific scientific method."""
        m_nid = method_id or (f"method:{NodeBuilder.slugify(method_name)}" if method_name else None)
        if not m_nid or not self.graph.has_node(m_nid):
            # Try fuzzy search on method labels
            m_nid = self._find_node_by_label_or_alias(method_name or "", NodeTypes.METHOD)

        if not m_nid:
            return []

        results = []
        for u, v, data in self.graph.in_edges(m_nid, data=True):
            if data.get("relationship") == RelationTypes.EXTENDS:
                u_data = self.graph.nodes[u]
                results.append({
                    "paper_node_id": u,
                    "paper_id": u_data.get("properties", {}).get("paper_id"),
                    "paper_title": u_data.get("properties", {}).get("title"),
                    "publication_year": u_data.get("properties", {}).get("publication_year"),
                    "extended_method": self.graph.nodes[m_nid].get("label"),
                    "relationship": RelationTypes.EXTENDS,
                    "confidence": data.get("confidence", 1.0),
                    "evidence_text": data.get("provenance", {}).get("source_text"),
                    "provenance": data.get("provenance", {}),
                })
        return results

    def methods_used_for_dataset(
        self,
        dataset_name: Optional[str] = None,
        dataset_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """3. Find scientific methods evaluated or trained on a specific dataset."""
        d_nid = dataset_id or (f"dataset:{NodeBuilder.slugify(dataset_name)}" if dataset_name else None)
        if not d_nid or not self.graph.has_node(d_nid):
            d_nid = self._find_node_by_label_or_alias(dataset_name or "", NodeTypes.DATASET)

        if not d_nid:
            return []

        # Find all papers using this dataset
        papers_using_dataset = set()
        for u, v, data in self.graph.in_edges(d_nid, data=True):
            if data.get("relationship") == RelationTypes.USES and self.graph.nodes[u].get("type") == NodeTypes.PAPER:
                papers_using_dataset.add(u)

        methods_found = []
        seen_methods = set()

        for p_nid in papers_using_dataset:
            # Find methods connected to these papers
            for u, v, data in self.graph.out_edges(p_nid, data=True):
                target_node = self.graph.nodes[v]
                if target_node.get("type") == NodeTypes.METHOD:
                    m_label = target_node.get("label")
                    if m_label not in seen_methods:
                        seen_methods.add(m_label)
                        methods_found.append({
                            "method_node_id": v,
                            "method_name": m_label,
                            "paper_id": self.graph.nodes[p_nid].get("properties", {}).get("paper_id"),
                            "paper_title": self.graph.nodes[p_nid].get("properties", {}).get("title"),
                            "dataset_name": self.graph.nodes[d_nid].get("label"),
                            "relationship": data.get("relationship", RelationTypes.USES),
                            "confidence": data.get("confidence", 0.90),
                            "provenance": data.get("provenance", {}),
                        })
        return methods_found

    def claims_supporting_claim(
        self,
        claim_id: Optional[str] = None,
        claim_text: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """4. Find claims or findings supporting a target scientific claim."""
        target_nid = claim_id or self._find_claim_or_finding_node(claim_text)
        if not target_nid:
            return []

        results = []
        for u, v, data in self.graph.in_edges(target_nid, data=True):
            if data.get("relationship") == RelationTypes.SUPPORTS:
                u_node = self.graph.nodes[u]
                results.append({
                    "supporting_node_id": u,
                    "supporting_type": u_node.get("type"),
                    "supporting_text": u_node.get("properties", {}).get("text"),
                    "target_claim_id": target_nid,
                    "relationship": RelationTypes.SUPPORTS,
                    "confidence": data.get("confidence", 0.85),
                    "provenance": data.get("provenance", {}),
                })
        return results

    def claims_contradicting_claim(
        self,
        claim_id: Optional[str] = None,
        claim_text: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """5. Find claims, findings, or limitations contradicting a target scientific claim."""
        target_nid = claim_id or self._find_claim_or_finding_node(claim_text)
        if not target_nid:
            return []

        results = []
        for u, v, data in self.graph.in_edges(target_nid, data=True):
            if data.get("relationship") == RelationTypes.CONTRADICTS:
                u_node = self.graph.nodes[u]
                results.append({
                    "contradicting_node_id": u,
                    "contradicting_type": u_node.get("type"),
                    "contradicting_text": u_node.get("properties", {}).get("text"),
                    "target_claim_id": target_nid,
                    "relationship": RelationTypes.CONTRADICTS,
                    "confidence": data.get("confidence", 0.85),
                    "provenance": data.get("provenance", {}),
                })
        return results

    def papers_connected_to_topic(
        self,
        topic_id: int,
    ) -> List[Dict[str, Any]]:
        """6. Find all papers connected to a specific research landscape topic."""
        t_nid = f"topic:{topic_id}"
        if not self.graph.has_node(t_nid):
            return []

        results = []
        t_node = self.graph.nodes[t_nid]
        for u, v, data in self.graph.in_edges(t_nid, data=True):
            if data.get("relationship") == RelationTypes.BELONGS_TO:
                p_node = self.graph.nodes[u]
                results.append({
                    "paper_node_id": u,
                    "paper_id": p_node.get("properties", {}).get("paper_id"),
                    "paper_title": p_node.get("properties", {}).get("title"),
                    "publication_year": p_node.get("properties", {}).get("publication_year"),
                    "topic_id": topic_id,
                    "topic_name": t_node.get("label"),
                    "confidence": data.get("confidence", 1.0),
                    "provenance": data.get("provenance", {}),
                })
        return results

    def papers_connected_to_candidate_limitation(
        self,
        limitation_text: Optional[str] = None,
        limitation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """7. Find all papers connected to a limitation (both limited by it and addressing it)."""
        target_nodes = self._find_limitation_nodes(limitation_id, limitation_text)
        limited_papers = []
        addressing_papers = []

        for l_nid in target_nodes:
            # Ingoing edges
            for u, v, data in self.graph.in_edges(l_nid, data=True):
                p_data = self.graph.nodes[u]
                if data.get("relationship") == RelationTypes.LIMITED_BY:
                    limited_papers.append({
                        "paper_id": p_data.get("properties", {}).get("paper_id"),
                        "paper_title": p_data.get("properties", {}).get("title"),
                        "evidence_text": data.get("provenance", {}).get("source_text"),
                        "provenance": data.get("provenance", {}),
                    })
                elif data.get("relationship") == RelationTypes.ADDRESSES:
                    addressing_papers.append({
                        "paper_id": p_data.get("properties", {}).get("paper_id"),
                        "paper_title": p_data.get("properties", {}).get("title"),
                        "evidence_text": data.get("provenance", {}).get("source_text"),
                        "provenance": data.get("provenance", {}),
                    })

        return {
            "matched_limitations": target_nodes,
            "papers_limited_by": limited_papers,
            "papers_addressing": addressing_papers,
            "total_papers": len(limited_papers) + len(addressing_papers),
        }

    def research_directions_related_to_limitation(
        self,
        limitation_id: Optional[str] = None,
        limitation_text: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """8. Find research directions and future work proposed to resolve or study a limitation."""
        target_nodes = self._find_limitation_nodes(limitation_id, limitation_text)
        directions = []

        for l_nid in target_nodes:
            # 1. Check direct edges from limitation to future direction
            for u, v, data in self.graph.out_edges(l_nid, data=True):
                target_node = self.graph.nodes[v]
                if target_node.get("type") == NodeTypes.FUTURE_DIRECTION:
                    directions.append({
                        "direction_node_id": v,
                        "direction_text": target_node.get("properties", {}).get("text"),
                        "limitation_id": l_nid,
                        "relationship": data.get("relationship"),
                        "provenance": target_node.get("provenance", {}),
                    })

            # 2. Check future directions proposed by the same paper that documented the limitation
            for u, v, data in self.graph.in_edges(l_nid, data=True):
                if data.get("relationship") == RelationTypes.LIMITED_BY:
                    p_nid = u
                    for _, fw_v, fw_data in self.graph.out_edges(p_nid, data=True):
                        fw_node = self.graph.nodes[fw_v]
                        if fw_node.get("type") == NodeTypes.FUTURE_DIRECTION:
                            directions.append({
                                "direction_node_id": fw_v,
                                "direction_text": fw_node.get("properties", {}).get("text"),
                                "source_paper_title": self.graph.nodes[p_nid].get("properties", {}).get("title"),
                                "limitation_id": l_nid,
                                "relationship": "same_paper_future_work",
                                "provenance": fw_node.get("provenance", {}),
                            })
        return directions

    # Helper lookup routines
    def _find_limitation_nodes(
        self,
        limitation_id: Optional[str] = None,
        limitation_text: Optional[str] = None,
    ) -> List[str]:
        if limitation_id and self.graph.has_node(limitation_id):
            return [limitation_id]

        matched = []
        q = (limitation_text or limitation_id or "").lower()
        for nid, data in self.graph.nodes(data=True):
            if data.get("type") == NodeTypes.LIMITATION:
                t = data.get("properties", {}).get("text", "").lower()
                if q in t or nid == limitation_id:
                    matched.append(nid)
        return matched

    def _find_node_by_label_or_alias(self, query: str, node_type: str) -> Optional[str]:
        q = query.lower().strip()
        for nid, data in self.graph.nodes(data=True):
            if data.get("type") == node_type:
                label = data.get("label", "").lower()
                aliases = [a.lower() for a in data.get("properties", {}).get("aliases", [])]
                if q == label or q in aliases or q in nid.lower():
                    return nid
        return None

    def _find_claim_or_finding_node(self, query_text: Optional[str]) -> Optional[str]:
        if not query_text:
            return None
        q = query_text.lower().strip()
        for nid, data in self.graph.nodes(data=True):
            if data.get("type") in (NodeTypes.CLAIM, NodeTypes.FINDING):
                text = data.get("properties", {}).get("text", "").lower()
                if q in text or nid == query_text:
                    return nid
        return None
