"""Unit tests for Phase 2 Scientific NLP Processing pipeline.

Verifies:
- Text normalization & ligature preservation
- Sentence boundary detection (abbreviations, citations, decimals, scientific notation, bullet lists)
- 9-class scientific discourse classification
- Limitation detection across specific subtypes
- Future work and result detection
- Scientific entity extraction (methods, datasets, metrics)
- Provenance preservation (paper, section, page, paragraph, sentence_order)
"""

import pytest

from backend.app.services.nlp.future_work_detector import future_work_detector
from backend.app.services.nlp.limitation_detector import limitation_detector
from backend.app.services.nlp.result_detector import result_detector
from backend.app.services.nlp.scientific_classifier import (
    BaseScientificClassifier,
    RuleBasedScientificClassifier,
    scientific_classifier,
)
from backend.app.services.nlp.scientific_entity_extractor import scientific_entity_extractor
from backend.app.services.nlp.scientific_preprocessor import scientific_preprocessor
from backend.app.services.nlp.sentence_segmenter import sentence_segmenter


class TestScientificPreprocessor:
    """Tests non-destructive scientific text normalization."""

    def test_unicode_normalization_and_ligatures(self):
        # Ligatures: \ufb01 -> fi, \ufb02 -> fl, \ufb00 -> ff
        raw_text = "The ef\ufb01cient \ufb02ow architecture achieves high coe\ufb00icients."
        cleaned = scientific_preprocessor.clean_text(raw_text)
        assert "efficient" in cleaned
        assert "flow" in cleaned
        assert "coefficients" in cleaned

    def test_line_break_hyphenation_repair(self):
        raw_text = "The self-atten-\ntion mechanism resolves long-range dependencies."
        cleaned = scientific_preprocessor.clean_text(raw_text)
        assert "self-attention mechanism" in cleaned

    def test_zero_width_and_soft_hyphens(self):
        raw_text = "Trans\u200bformer\u00adbased architectures."
        cleaned = scientific_preprocessor.clean_text(raw_text)
        assert "Transformerbased" in cleaned or "Transformer based" in cleaned

    def test_whitespace_and_empty_handling(self):
        assert scientific_preprocessor.clean_text("") == ""
        assert scientific_preprocessor.clean_text(None) == ""
        multi_space = "Multiple   spaces \t and \n\n newlines."
        cleaned = scientific_preprocessor.clean_text(multi_space)
        assert "Multiple spaces and" in cleaned


class TestSentenceSegmenter:
    """Tests robust sentence segmentation on complex scientific literature."""

    def test_abbreviation_protection(self):
        text = (
            "Vaswani et al. (2017) introduced the Transformer, i.e., a self-attention model. "
            "As shown in Fig. 2, the error rate dropped significantly (e.g., from 12.4% to 8.2%). "
            "See Eq. 4 for formal mathematical derivations."
        )
        sentences = sentence_segmenter.segment_text(text)
        assert len(sentences) == 3
        assert "Vaswani et al." in sentences[0]
        assert "i.e.," in sentences[0]
        assert "e.g.," in sentences[1]
        assert "Eq. 4" in sentences[2]

    def test_decimals_and_scientific_notation(self):
        text = (
            "The initial learning rate was set to 1.5e-4 with beta_1 = 0.9 and beta_2 = 0.999. "
            "We observed a p-value of p < 0.01 across 1,000 bootstrap iterations."
        )
        sentences = sentence_segmenter.segment_text(text)
        assert len(sentences) == 2
        assert "1.5e-4" in sentences[0]
        assert "0.999" in sentences[0]
        assert "p < 0.01" in sentences[1]

    def test_citations_and_bracketed_references(self):
        text = (
            "Previous models suffer from quadratic complexity [1, 2]. "
            "In contrast, Linformer [3] reduces complexity to O(n)."
        )
        sentences = sentence_segmenter.segment_text(text)
        assert len(sentences) == 2
        assert "[1, 2]" in sentences[0]
        assert "[3]" in sentences[1]

    def test_bullet_list_items(self):
        text = (
            "Our contributions are threefold:\n"
            "1. A linear-time self-attention operator.\n"
            "2. Extensive experiments across 5 benchmarks.\n"
            "3. An open-source implementation."
        )
        sentences = sentence_segmenter.segment_text(text)
        assert len(sentences) == 4
        assert "threefold" in sentences[0]
        assert "linear-time" in sentences[1]
        assert "Extensive experiments" in sentences[2]
        assert "open-source" in sentences[3]

    def test_segment_section_provenance(self):
        paragraphs = [
            "We propose a novel recurrent attention architecture. It scales linearly with sequence length.",
            "Our experiments demonstrate significant speedups on long contexts.",
        ]
        records = sentence_segmenter.segment_section(
            paper_id=42,
            section_name="Methodology",
            paragraphs=paragraphs,
            page_start=3,
            page_end=4,
            start_order=10,
        )

        assert len(records) == 3
        # Check first sentence
        s1 = records[0]
        assert s1.paper_id == 42
        assert s1.section_name == "Methodology"
        assert s1.paragraph_id == 0
        assert s1.sentence_order == 10
        assert s1.page_number == 3

        # Check second sentence in paragraph 0
        s2 = records[1]
        assert s2.sentence_order == 11
        assert s2.paragraph_id == 0

        # Check sentence in paragraph 1
        s3 = records[2]
        assert s3.sentence_order == 12
        assert s3.paragraph_id == 1
        assert s3.page_number == 4


class TestScientificClassifier:
    """Tests 9-class scientific discourse classifier."""

    def test_all_classes_supported(self):
        for label in RuleBasedScientificClassifier.LABELS:
            assert label in [
                "PROBLEM",
                "OBJECTIVE",
                "METHOD",
                "DATASET",
                "METRIC",
                "RESULT",
                "LIMITATION",
                "FUTURE_WORK",
                "OTHER",
            ]

    def test_limitation_classification(self):
        sent = "A primary limitation of our approach is the quadratic memory footprint during long-sequence training."
        label, conf = scientific_classifier.classify(sent, section_name="Limitations")
        assert label == "LIMITATION"
        assert 0.0 <= conf <= 1.0

    def test_future_work_classification(self):
        sent = "In future work, we plan to extend this method to multimodal vision-language representations."
        label, conf = scientific_classifier.classify(sent, section_name="Conclusion")
        assert label == "FUTURE_WORK"
        assert conf >= 0.70

    def test_objective_classification(self):
        sent = "In this paper, we aim to investigate whether sparse attention preserves associative recall."
        label, conf = scientific_classifier.classify(sent, section_name="Introduction")
        assert label == "OBJECTIVE"

    def test_result_classification(self):
        sent = "Our proposed model achieves 89.4% accuracy, outperforming the previous state of the art by 3.2%."
        label, conf = scientific_classifier.classify(sent, section_name="Results")
        assert label == "RESULT"

    def test_method_classification(self):
        sent = "We optimize the neural network using the AdamW optimizer with cosine learning rate scheduling."
        label, conf = scientific_classifier.classify(sent, section_name="Methodology")
        assert label == "METHOD"

    def test_dataset_classification(self):
        sent = "All models are evaluated on the SQuAD 2.0 benchmark dataset and GLUE multi-task corpus."
        label, conf = scientific_classifier.classify(sent, section_name="Experiments")
        assert label == "DATASET"

    def test_abstract_classifier_interface(self):
        assert issubclass(RuleBasedScientificClassifier, BaseScientificClassifier)


class TestLimitationDetector:
    """Tests detailed scientific limitation detection and subtype categorization."""

    def test_computational_limitation(self):
        sent = "The quadratic memory complexity poses a prohibitive bottleneck for document lengths over 4096 tokens."
        res = limitation_detector.detect(sent, section_name="Discussion")
        assert res is not None
        assert res["subtype"] == "computational"
        assert res["confidence"] >= 0.70

    def test_data_scarcity_limitation(self):
        sent = "A severe limitation is the lack of labeled training data in low-resource dialect domains."
        res = limitation_detector.detect(sent, section_name="Limitations")
        assert res is not None
        assert res["subtype"] == "data_scarcity"

    def test_generalization_limitation(self):
        sent = "The classifier struggles to generalize on out-of-distribution clinical notes without fine-tuning."
        res = limitation_detector.detect(sent, section_name="Discussion")
        assert res is not None
        assert res["subtype"] == "generalization"

    def test_methodological_limitation(self):
        sent = "Our theoretical derivation relies on the strong simplifying assumption of stationary noise."
        res = limitation_detector.detect(sent, section_name="Methodology")
        assert res is not None
        assert res["subtype"] == "methodological"

    def test_non_limitation_returns_none(self):
        sent = "The Transformer architecture was introduced by Vaswani in 2017."
        res = limitation_detector.detect(sent, section_name="Background")
        assert res is None


class TestFutureWorkDetector:
    """Tests future research trajectory detection."""

    def test_explicit_author_commitment(self):
        sent = "We leave the exploration of continuous test-time adaptation for future work."
        res = future_work_detector.detect(sent, section_name="Conclusion")
        assert res is not None
        assert res["confidence"] >= 0.80

    def test_recommended_experiments(self):
        sent = "Further research is needed to explore the theoretical stability bounds of linearized attention."
        res = future_work_detector.detect(sent, section_name="Discussion")
        assert res is not None

    def test_negative_statement_returns_none(self):
        sent = "We evaluated the baseline on 10 random seeds."
        res = future_work_detector.detect(sent, section_name="Experiments")
        assert res is None


class TestScientificEntityExtractor:
    """Tests entity extraction for methods, datasets, and metrics."""

    def test_method_extraction(self):
        sent = "We evaluate Transformer, Mamba, and ResNet architectures trained using AdamW."
        extractions = scientific_entity_extractor.extract_entities(sent)
        methods = [e["entity_name"] for e in extractions if e["entity_type"] == "METHOD"]
        assert any("Transformer" in m for m in methods)
        assert any("AdamW" in m or "ResNet" in m or "Mamba" in m for m in methods)

    def test_dataset_extraction(self):
        sent = "Experiments were conducted on the ImageNet and GLUE benchmark datasets."
        extractions = scientific_entity_extractor.extract_entities(sent)
        datasets = [e["entity_name"] for e in extractions if e["entity_type"] == "DATASET"]
        assert any("ImageNet" in d for d in datasets) or any("GLUE" in d for d in datasets)

    def test_metric_extraction(self):
        sent = "The model was evaluated using accuracy, BLEU score, F1-score, and perplexity."
        extractions = scientific_entity_extractor.extract_entities(sent)
        metrics = [e["entity_name"] for e in extractions if e["entity_type"] == "METRIC"]
        assert any("accuracy" in m.lower() for m in metrics)
        assert any("bleu" in m.lower() or "f1" in m.lower() for m in metrics)
