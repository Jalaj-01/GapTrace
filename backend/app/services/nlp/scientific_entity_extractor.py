"""Scientific Entity Extractor (Phase 2).

Extracts methods, architectures, datasets, benchmarks, and evaluation metrics
from scientific sentences using linguistic templates, contextual cues, and scientific NER patterns.
"""

import re
from typing import Any, Dict, List, Optional

from backend.app.core.logging import get_logger

logger = get_logger("app.nlp.entity_extractor")


class ScientificEntityExtractor:
    """Extracts scientific methods, datasets, and metrics with contextual grounding."""

    # --------------------------------------------------------------------------
    # 1. Scientific Methods & Architectures Patterns
    # --------------------------------------------------------------------------
    METHOD_TEMPLATES = [
        re.compile(r"\b(?:we\s+propose|we\s+introduce|we\s+present)\s+(?:the|a\s+novel)?\s*([A-Z][a-zA-Z0-9_\-]+(?:\s+[A-Z][a-zA-Z0-9_\-]+)?)\b"),
        re.compile(r"\b([A-Z][a-zA-Z0-9_\-]+(?:\s+[A-Z][a-zA-Z0-9_\-]+)?)\s+(?:model|architecture|framework|algorithm|network|mechanism|approach)\b"),
        re.compile(r"\b(?:using|with|via)\s+(?:the\s+)?([A-Z][a-zA-Z0-9_\-]+)\s+(?:algorithm|optimizer|loss|layer)\b"),
        re.compile(r"\bbased\s+on\s+(?:the\s+)?([A-Z][a-zA-Z0-9_\-]+(?:\s+[A-Z][a-zA-Z0-9_\-]+)?)\s+(?:architecture|model)\b"),
    ]

    CANONICAL_METHODS = {
        "transformer",
        "self-attention",
        "multi-head attention",
        "attention mechanism",
        "lstm",
        "bilstm",
        "gru",
        "rnn",
        "recurrent neural network",
        "cnn",
        "convolutional neural network",
        "bert",
        "roberta",
        "scibert",
        "gpt",
        "gpt-2",
        "gpt-3",
        "gpt-4",
        "llama",
        "resnet",
        "vgg",
        "densenet",
        "gcn",
        "gat",
        "graph neural network",
        "adam",
        "adamw",
        "sgd",
        "backpropagation",
        "beam search",
        "dropout",
        "layernorm",
        "batchnorm",
        "lora",
        "flashattention",
        "contrastive learning",
        "diffusion model",
        "encoder-decoder",
    }

    # --------------------------------------------------------------------------
    # 2. Datasets & Benchmarks Patterns
    # --------------------------------------------------------------------------
    DATASET_TEMPLATES = [
        re.compile(r"\b([A-Z0-9][a-zA-Z0-9_\-]*(?:\s+[A-Za-z0-9_\-]+){0,3})\s+(?:dataset|benchmark|corpus|corpora|database|testbed)\b"),
        re.compile(r"\b(?:evaluate|evaluated|benchmark|benchmarked|test|tested)\s+on\s+(?:the\s+)?([A-Z0-9][a-zA-Z0-9_\-]+(?:\s+[A-Za-z0-9_\-]+)?)\b"),
        re.compile(r"\b(?:train|trained|fine-tuned)\s+on\s+(?:the\s+)?([A-Z0-9][a-zA-Z0-9_\-]+(?:\s+[A-Za-z0-9_\-]+)?)\b"),
    ]

    CANONICAL_DATASETS = {
        "wmt",
        "wmt 2014",
        "wmt14",
        "glue",
        "superglue",
        "squad",
        "squad 2.0",
        "imagenet",
        "cifar-10",
        "cifar-100",
        "mnist",
        "ms coco",
        "coco",
        "conll",
        "penn treebank",
        "multi30k",
        "bookcorpus",
        "wikipedia",
        "pubmed",
        "arxiv",
        "triviaqa",
        "natural questions",
        "snli",
        "mnli",
        "smlmt",
        "ag news",
    }

    # --------------------------------------------------------------------------
    # 3. Evaluation Metrics Patterns
    # --------------------------------------------------------------------------
    METRIC_TEMPLATES = [
        re.compile(r"\b(BLEU(?:-[1-4])?|ROUGE(?:-[12L])?|F1(?:-score)?|Accuracy|Precision|Recall|AUC(?:-ROC)?|mAP(?:@\d+)?|IoU|RMSE|MAE|Perplexity|PPL|Exact\s+Match|EM)\b(?:\s*(?:of|=|:)?\s*(\d+(?:\.\d+)?%?))?", re.I),
        re.compile(r"\b(mean\s+squared\s+error|cross-entropy\s+loss|error\s+rate|top-[15]\s+accuracy)\b(?:\s*(?:of|=|:)?\s*(\d+(?:\.\d+)?%?))?", re.I),
    ]

    def __init__(self) -> None:
        pass

    def extract_methods(self, sentence: str, section_name: str = "") -> List[Dict[str, Any]]:
        """Extracts candidate methods, models, architectures, and algorithms."""
        extracted: List[Dict[str, Any]] = []
        seen = set()

        # 1. Regex template extraction
        for pat in self.METHOD_TEMPLATES:
            for match in pat.finditer(sentence):
                term = match.group(1).strip()
                term_clean = re.sub(r"^[Tt]he\s+|^[Aa]n?\s+", "", term)
                if len(term_clean) >= 3 and term_clean.lower() not in seen:
                    # Ignore common stop words caught by templates
                    if term_clean.lower() not in {"this", "that", "these", "such", "previous", "existing", "our"}:
                        seen.add(term_clean.lower())
                        extracted.append({
                            "entity_name": term_clean,
                            "entity_type": "METHOD",
                            "confidence": 0.85,
                            "extraction_method": "linguistic_template",
                        })

        # 2. Canonical scientific dictionary lookup
        sent_lower = sentence.lower()
        for canonical in self.CANONICAL_METHODS:
            pattern = r"\b" + re.escape(canonical) + r"\b"
            if re.search(pattern, sent_lower) and canonical not in seen:
                # Find exact case from original sentence
                match = re.search(pattern, sentence, re.I)
                orig_term = match.group(0) if match else canonical.title()
                seen.add(canonical)
                extracted.append({
                    "entity_name": orig_term,
                    "entity_type": "METHOD",
                    "confidence": 0.92,
                    "extraction_method": "canonical_dictionary",
                })

        return self._deduplicate_entities(extracted)

    def extract_datasets(self, sentence: str, section_name: str = "") -> List[Dict[str, Any]]:
        """Extracts dataset and benchmark mentions."""
        extracted: List[Dict[str, Any]] = []
        seen = set()

        # 1. Regex template extraction
        for pat in self.DATASET_TEMPLATES:
            for match in pat.finditer(sentence):
                term = match.group(1).strip()
                term_clean = re.sub(r"^[Tt]he\s+", "", term)
                if len(term_clean) >= 3 and term_clean.lower() not in seen:
                    if term_clean.lower() not in {"our", "this", "each", "both", "all", "small", "large", "new", "test", "training"}:
                        seen.add(term_clean.lower())
                        extracted.append({
                            "entity_name": term_clean,
                            "entity_type": "DATASET",
                            "confidence": 0.84,
                            "extraction_method": "linguistic_template",
                        })

        # 2. Canonical dataset lookup
        sent_lower = sentence.lower()
        for canonical in self.CANONICAL_DATASETS:
            pattern = r"\b" + re.escape(canonical) + r"\b"
            if re.search(pattern, sent_lower) and canonical not in seen:
                match = re.search(pattern, sentence, re.I)
                orig_term = match.group(0) if match else canonical.upper()
                seen.add(canonical)
                extracted.append({
                    "entity_name": orig_term,
                    "entity_type": "DATASET",
                    "confidence": 0.94,
                    "extraction_method": "canonical_dictionary",
                })

        return self._deduplicate_entities(extracted)

    @staticmethod
    def _deduplicate_entities(entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Removes redundant shorter substrings of longer extracted entities."""
        sorted_entities = sorted(entities, key=lambda e: len(e["entity_name"]), reverse=True)
        deduped: List[Dict[str, Any]] = []
        for item in sorted_entities:
            name_lower = item["entity_name"].lower()
            if not any(name_lower in d["entity_name"].lower() and name_lower != d["entity_name"].lower() for d in deduped):
                deduped.append(item)
        return deduped

    def extract_metrics(self, sentence: str, section_name: str = "") -> List[Dict[str, Any]]:
        """Extracts evaluation metrics and any associated scores."""
        extracted: List[Dict[str, Any]] = []
        seen = set()

        for pat in self.METRIC_TEMPLATES:
            for match in pat.finditer(sentence):
                metric_name = match.group(1).strip()
                score_val = match.group(2).strip() if match.group(2) else None
                key = metric_name.lower()
                if key not in seen:
                    seen.add(key)
                    extracted.append({
                        "entity_name": metric_name,
                        "entity_type": "METRIC",
                        "score_value": score_val,
                        "confidence": 0.92 if score_val else 0.86,
                        "extraction_method": "regex_metric_template",
                    })

        return extracted


# Singleton instance
scientific_entity_extractor = ScientificEntityExtractor()
