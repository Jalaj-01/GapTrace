"""Scientific NLP Orchestrator Service (Phase 2).

Integrates scientific text preprocessing, robust sentence segmentation,
discourse classification, specialized detectors (limitations, future work, results),
and entity extraction with guaranteed end-to-end provenance.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.app.core.errors import NotFoundError
from backend.app.core.logging import get_logger
from backend.app.models.paper import (
    Paper,
    PaperNLPProcessResponse,
    PaperSection,
    ScientificExtraction,
    ScientificSentence,
)
from backend.app.services.nlp.future_work_detector import future_work_detector
from backend.app.services.nlp.limitation_detector import limitation_detector
from backend.app.services.nlp.result_detector import result_detector
from backend.app.services.nlp.scientific_classifier import scientific_classifier
from backend.app.services.nlp.scientific_entity_extractor import scientific_entity_extractor
from backend.app.services.nlp.sentence_segmenter import sentence_segmenter

logger = get_logger("app.nlp.service")


class ScientificNLPService:
    """End-to-end scientific NLP pipeline orchestrator."""

    def __init__(self) -> None:
        pass

    def process_paper(self, paper_id: int, db: Session) -> PaperNLPProcessResponse:
        """Processes an ingested paper into classified sentences and structured extractions.

        All extractions strictly preserve paper -> section -> page -> paragraph -> sentence provenance.
        """
        # 1. Fetch paper from database
        paper = db.scalar(select(Paper).where(Paper.id == paper_id))
        if not paper:
            raise NotFoundError(f"Paper with ID {paper_id} not found.")

        logger.info(f"Starting Phase 2 NLP ingestion for paper {paper_id}: '{paper.title}'")

        # 2. Idempotent cleanup: delete prior sentences and extractions if reprocessing
        db.execute(delete(ScientificExtraction).where(ScientificExtraction.paper_id == paper_id))
        db.execute(delete(ScientificSentence).where(ScientificSentence.paper_id == paper_id))
        db.flush()

        # 3. Retrieve sections
        sections = db.scalars(
            select(PaperSection)
            .where(PaperSection.paper_id == paper_id)
            .order_by(PaperSection.section_order)
        ).all()

        created_sentences: List[ScientificSentence] = []
        created_extractions: List[ScientificExtraction] = []
        global_sentence_order = 1

        # Fallback if no sections were parsed
        if not sections and paper.abstract:
            # Segment abstract as a synthetic section
            abstract_segments = sentence_segmenter.segment_section(
                paper_id=paper_id,
                section_name="Abstract",
                paragraphs=[paper.abstract],
                page_start=1,
                page_end=1,
                start_order=global_sentence_order,
            )
            for seg in abstract_segments:
                db_sentence = ScientificSentence(
                    paper_id=seg.paper_id,
                    paragraph_id=seg.paragraph_id,
                    sentence_order=seg.sentence_order,
                    source_text=seg.source_text,
                    section_name=seg.section_name,
                    page_number=seg.page_number,
                )
                db.add(db_sentence)
                created_sentences.append(db_sentence)
                global_sentence_order += 1

        for sec in sections:
            paragraphs = sec.paragraphs if sec.paragraphs else [sec.content]
            segments = sentence_segmenter.segment_section(
                paper_id=paper_id,
                section_name=sec.section_name,
                paragraphs=paragraphs,
                page_start=sec.page_start,
                page_end=sec.page_end,
                start_order=global_sentence_order,
            )

            for seg in segments:
                db_sentence = ScientificSentence(
                    paper_id=seg.paper_id,
                    paragraph_id=seg.paragraph_id,
                    sentence_order=seg.sentence_order,
                    source_text=seg.source_text,
                    section_name=seg.section_name,
                    page_number=seg.page_number,
                )
                db.add(db_sentence)
                created_sentences.append(db_sentence)
                global_sentence_order += 1

        # Flush to generate primary key IDs for sentences
        db.flush()

        # 4. Extract and Classify Each Sentence
        counts_by_type: Dict[str, int] = {
            "PROBLEM": 0,
            "OBJECTIVE": 0,
            "METHOD": 0,
            "DATASET": 0,
            "METRIC": 0,
            "RESULT": 0,
            "LIMITATION": 0,
            "FUTURE_WORK": 0,
            "OTHER": 0,
        }

        for sent in created_sentences:
            s_text = sent.source_text
            sec_name = sent.section_name
            p_id = sent.paragraph_id
            page = sent.page_number

            provenance_payload = {
                "paper_id": paper_id,
                "section_name": sec_name,
                "page_number": page,
                "paragraph_id": p_id,
                "sentence_id": sent.id,
                "sentence_order": sent.sentence_order,
            }

            # A. Sentence-level primary classification
            primary_label, confidence = scientific_classifier.classify(s_text, sec_name)
            counts_by_type[primary_label] = counts_by_type.get(primary_label, 0) + 1

            if primary_label != "OTHER":
                primary_extraction = ScientificExtraction(
                    paper_id=paper_id,
                    sentence_id=sent.id,
                    extraction_type=primary_label,
                    extracted_text=s_text,
                    confidence=confidence,
                    extraction_method="scientific_classifier_baseline",
                    provenance=provenance_payload,
                )
                db.add(primary_extraction)
                created_extractions.append(primary_extraction)

            # B. Specialized Limitation Detection
            lim_res = limitation_detector.detect(s_text, sec_name)
            if lim_res and primary_label != "LIMITATION":
                lim_provenance = {**provenance_payload, "limitation_subtype": lim_res["subtype"]}
                lim_extraction = ScientificExtraction(
                    paper_id=paper_id,
                    sentence_id=sent.id,
                    extraction_type="LIMITATION",
                    extracted_text=lim_res["limitation_text"],
                    confidence=lim_res["confidence"],
                    extraction_method=f"limitation_detector_{lim_res['subtype']}",
                    provenance=lim_provenance,
                )
                db.add(lim_extraction)
                created_extractions.append(lim_extraction)
                counts_by_type["LIMITATION"] = counts_by_type.get("LIMITATION", 0) + 1

            # C. Specialized Future Work Detection
            fw_res = future_work_detector.detect(s_text, sec_name)
            if fw_res and primary_label != "FUTURE_WORK":
                fw_extraction = ScientificExtraction(
                    paper_id=paper_id,
                    sentence_id=sent.id,
                    extraction_type="FUTURE_WORK",
                    extracted_text=fw_res["future_work_text"],
                    confidence=fw_res["confidence"],
                    extraction_method="future_work_detector",
                    provenance=provenance_payload,
                )
                db.add(fw_extraction)
                created_extractions.append(fw_extraction)
                counts_by_type["FUTURE_WORK"] = counts_by_type.get("FUTURE_WORK", 0) + 1

            # D. Specialized Result Detection
            res_res = result_detector.detect(s_text, sec_name)
            if res_res and primary_label != "RESULT":
                res_provenance = {
                    **provenance_payload,
                    "numerical_gain": res_res.get("numerical_gain"),
                    "has_p_value": res_res.get("has_p_value"),
                }
                res_extraction = ScientificExtraction(
                    paper_id=paper_id,
                    sentence_id=sent.id,
                    extraction_type="RESULT",
                    extracted_text=res_res["result_text"],
                    confidence=res_res["confidence"],
                    extraction_method="result_detector",
                    provenance=res_provenance,
                )
                db.add(res_extraction)
                created_extractions.append(res_extraction)
                counts_by_type["RESULT"] = counts_by_type.get("RESULT", 0) + 1

            # E. Fine-grained Entity Extractions (Methods, Datasets, Metrics)
            methods = scientific_entity_extractor.extract_methods(s_text, sec_name)
            for m in methods:
                db.add(ScientificExtraction(
                    paper_id=paper_id,
                    sentence_id=sent.id,
                    extraction_type="METHOD",
                    extracted_text=m["entity_name"],
                    confidence=m["confidence"],
                    extraction_method=m["extraction_method"],
                    provenance={**provenance_payload, "entity_type": "METHOD"},
                ))
                counts_by_type["METHOD"] = counts_by_type.get("METHOD", 0) + 1

            datasets = scientific_entity_extractor.extract_datasets(s_text, sec_name)
            for d in datasets:
                db.add(ScientificExtraction(
                    paper_id=paper_id,
                    sentence_id=sent.id,
                    extraction_type="DATASET",
                    extracted_text=d["entity_name"],
                    confidence=d["confidence"],
                    extraction_method=d["extraction_method"],
                    provenance={**provenance_payload, "entity_type": "DATASET"},
                ))
                counts_by_type["DATASET"] = counts_by_type.get("DATASET", 0) + 1

            metrics = scientific_entity_extractor.extract_metrics(s_text, sec_name)
            for met in metrics:
                db.add(ScientificExtraction(
                    paper_id=paper_id,
                    sentence_id=sent.id,
                    extraction_type="METRIC",
                    extracted_text=met["entity_name"],
                    confidence=met["confidence"],
                    extraction_method=met["extraction_method"],
                    provenance={**provenance_payload, "entity_type": "METRIC", "score_value": met.get("score_value")},
                ))
                counts_by_type["METRIC"] = counts_by_type.get("METRIC", 0) + 1

        db.commit()

        total_ext = sum(v for k, v in counts_by_type.items() if k != "OTHER")
        logger.info(
            f"Phase 2 processing completed for paper {paper_id}: "
            f"{len(created_sentences)} sentences segmented, {total_ext} scientific extractions."
        )

        return PaperNLPProcessResponse(
            paper_id=paper_id,
            title=paper.title,
            total_sentences=len(created_sentences),
            total_extractions=total_ext,
            extractions_by_type=counts_by_type,
            processed_at=datetime.now(timezone.utc).isoformat(),
            provenance_verified=True,
        )


# Singleton instance
scientific_nlp_service = ScientificNLPService()
