"""Scientific Sentence Classifier (Phase 2).

Provides transparent rule-based classification across 9 scientific discourse labels:
PROBLEM, OBJECTIVE, METHOD, DATASET, METRIC, RESULT, LIMITATION, FUTURE_WORK, OTHER.

Includes section-context prior weighting and a modular extensible interface for
Transformer-based models (e.g. SciBERT).
"""

import math
import re
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple

from backend.app.core.logging import get_logger

logger = get_logger("app.nlp.classifier")


class BaseScientificClassifier(ABC):
    """Abstract interface allowing seamless classifier replacement."""

    @abstractmethod
    def classify(self, sentence: str, section_name: str = "") -> Tuple[str, float]:
        """Classifies a scientific sentence into one of the 9 standard discourse categories.

        Returns:
            Tuple of (label, confidence_score) where confidence is between 0.0 and 1.0.
        """
        pass


class RuleBasedScientificClassifier(BaseScientificClassifier):
    """Linguistically grounded rule-based scientific sentence classifier."""

    LABELS = [
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

    # Weighted regex pattern dictionaries per category
    # Each pattern is a tuple: (compiled_regex, score_weight)
    PATTERNS: Dict[str, List[Tuple[re.Pattern, float]]] = {
        "LIMITATION": [
            # Explicit constraint / failure expressions
            (re.compile(r"\b(?:a|the|major|key|main|potential|notable)\s+limitations?\b", re.I), 3.0),
            (re.compile(r"\b(?:suffer|suffers|suffering)\s+from\b", re.I), 2.5),
            (re.compile(r"\b(?:fails?|failed|failing)\s+to\b", re.I), 2.5),
            (re.compile(r"\b(?:cannot|can\s+not|unable\s+to|incapable\s+of)\s+(?:scale|generalize|handle|capture|model)\b", re.I), 2.8),
            (re.compile(r"\bquadratic\s+(?:time|complexity|memory|cost)\b", re.I), 2.8),
            (re.compile(r"\b(?:computationally|prohibitively)\s+(?:expensive|costly|demanding|intractable)\b", re.I), 2.8),
            (re.compile(r"\b(?:remains?|poses?)\s+a\s+(?:major\s+)?(?:bottleneck|drawback|challenge|obstacle)\b", re.I), 2.5),
            (re.compile(r"\b(?:drawback|weakness|shortcoming|vulnerability|flaw)s?\b", re.I), 2.2),
            (re.compile(r"\b(?:trade-?off|tradeoff)s?\s+between\b", re.I), 2.0),
            (re.compile(r"\b(?:lack|scarcity|absence|shortage)\s+of\s+(?:data|annotations|labels|supervision|resources)\b", re.I), 2.5),
            (re.compile(r"\b(?:does\s+not|do\s+not)\s+generalize\s+(?:well|to)\b", re.I), 2.8),
            (re.compile(r"\b(?:degrade|degrades|degradation)\s+(?:in|of)\s+performance\b", re.I), 2.2),
            (re.compile(r"\bunderperforms?\s+(?:when|in|on)\b", re.I), 2.2),
            (re.compile(r"\brestricted\s+to\s+(?:small|narrow|limited|specific)\b", re.I), 2.0),
            (re.compile(r"\bsusceptible\s+to\s+(?:noise|overfitting|hallucination|adversarial)\b", re.I), 2.5),
            (re.compile(r"\bdespite\s+(?:these|the|promising|strong)\s+results\b", re.I), 1.8),
        ],
        "FUTURE_WORK": [
            (re.compile(r"\b(?:leave|leaves)\s+(?:this|these|it|for|to)\s+(?:future|subsequent)\s+work\b", re.I), 3.5),
            (re.compile(r"\bin\s+(?:the\s+)?future\s*,\s*(?:we|one)\s+(?:plan|plans|aim|aims|intend|hope)\b", re.I), 3.2),
            (re.compile(r"\bfuture\s+(?:work|research|directions?|investigations?|studies)\b", re.I), 2.8),
            (re.compile(r"\b(?:an\s+)?interesting\s+(?:direction|avenue)\s+for\s+future\b", re.I), 3.0),
            (re.compile(r"\bwe\s+(?:plan|intend|hope)\s+to\s+(?:extend|explore|investigate|generalize|apply)\b", re.I), 2.8),
            (re.compile(r"\bfurther\s+(?:research|investigation|exploration|study)\s+is\s+(?:needed|warranted|required)\b", re.I), 2.6),
            (re.compile(r"\bremains\s+an\s+open\s+(?:question|problem|challenge)\s+for\b", re.I), 2.5),
            (re.compile(r"\bcould\s+be\s+(?:extended|applied|adapted|generalized)\s+to\b", re.I), 2.2),
        ],
        "PROBLEM": [
            (re.compile(r"\b(?:fundamental|pervasive|open|unsolved)\s+(?:problem|question|challenge)\b", re.I), 2.5),
            (re.compile(r"\bexisting\s+(?:approaches|methods|models|techniques|solutions)\s+(?:struggle|suffer|fail|rely)\b", re.I), 2.5),
            (re.compile(r"\ba\s+central\s+challenge\s+in\b", re.I), 2.5),
            (re.compile(r"\b(?:hard|difficult|challenging)\s+to\s+(?:scale|train|optimize|guarantee|interpret)\b", re.I), 2.0),
            (re.compile(r"\bpoorly\s+understood\b", re.I), 2.2),
            (re.compile(r"\bthe\s+issue\s+of\b", re.I), 1.8),
            (re.compile(r"\black\s+the\s+ability\s+to\b", re.I), 2.2),
            (re.compile(r"\binadequately\s+addressed\b", re.I), 2.2),
        ],
        "OBJECTIVE": [
            (re.compile(r"\bin\s+this\s+(?:paper|work|study|letter|article)\s*,\s*we\s+(?:propose|introduce|present|develop|design|investigate)\b", re.I), 3.2),
            (re.compile(r"\bour\s+(?:goal|objective|aim|hypothesis|purpose)\s+is\s+to\b", re.I), 3.0),
            (re.compile(r"\bwe\s+aim\s+to\s+(?:uncover|address|solve|demonstrate|evaluate|discover)\b", re.I), 2.8),
            (re.compile(r"\bthis\s+work\s+(?:seeks|aims|attempts)\s+to\b", re.I), 2.5),
            (re.compile(r"\bwe\s+hypothesize\s+that\b", re.I), 2.8),
            (re.compile(r"\bwe\s+focus\s+on\s+(?:identifying|developing|investigating)\b", re.I), 2.0),
            (re.compile(r"\bthe\s+contributions?\s+of\s+this\s+paper\b", re.I), 2.5),
        ],
        "METHOD": [
            (re.compile(r"\b(?:proposed|our)\s+(?:architecture|framework|model|algorithm|method|pipeline|network)\b", re.I), 2.4),
            (re.compile(r"\b(?:we\s+)?formulate\s+(?:the\s+problem\s+as|this\s+as)\b", re.I), 2.2),
            (re.compile(r"\bloss\s+function\s+is\s+(?:defined|optimized|computed)\b", re.I), 2.5),
            (re.compile(r"\b(?:consists?|composed)\s+of\s+\d+\s+layers\b", re.I), 2.2),
            (re.compile(r"\b(?:feed-?forward|self-?attention|convolutional|recurrent|encoder-?decoder)\s+(?:network|layer|mechanism|block)\b", re.I), 2.4),
            (re.compile(r"\btrained\s+(?:using|with|via)\s+(?:Adam|SGD|backpropagation|gradient\s+descent)\b", re.I), 2.5),
            (re.compile(r"\bhyperparameters?\s+(?:were|are|set\s+to)\b", re.I), 2.0),
            (re.compile(r"\bwe\s+(?:implement|construct|deploy|utilize|employ)\s+a\b", re.I), 1.8),
        ],
        "DATASET": [
            (re.compile(r"\b(?:benchmark|corpus|dataset|corpora)\s+(?:consists?|contains?|comprises?|containing)\b", re.I), 3.5),
            (re.compile(r"\bwe\s+(?:evaluate|test|benchmark|train)\s+(?:our\s+approach\s+)?on\s+(?:the\s+)?(?:WMT|GLUE|SQuAD|ImageNet|SuperGLUE|MNIST|CIFAR|MS-COCO|CoNLL|[A-Z0-9-]+\s+dataset)\b", re.I), 3.8),
            (re.compile(r"\btraining\s+(?:set|split|corpus)\s+(?:contains|has|consists)\b", re.I), 3.0),
            (re.compile(r"\bdata\s+(?:was|were)\s+collected\s+from\b", re.I), 2.8),
            (re.compile(r"\bannotations?\s+were\s+provided\s+by\b", re.I), 2.8),
            (re.compile(r"\bwe\s+sample\s+\d+[\d,]*\s+(?:examples|instances|sentences|pairs|images)\b", re.I), 2.8),
        ],
        "METRIC": [
            (re.compile(r"\bevaluated\s+(?:in\s+terms\s+of|using|via)\s+(?:BLEU|ROUGE|F1|Accuracy|Precision|Recall|AUC|mAP|IoU|RMSE|MAE|Perplexity)\b", re.I), 3.2),
            (re.compile(r"\bevaluation\s+metrics?\s+(?:include|are|used)\b", re.I), 3.0),
            (re.compile(r"\bwe\s+report\s+(?:accuracy|precision|recall|F1|mean\s+squared\s+error)\b", re.I), 2.8),
            (re.compile(r"\bstandard\s+(?:evaluation\s+)?metric\b", re.I), 2.5),
            (re.compile(r"\b(?:BLEU|ROUGE|F1-?score|AUC-?ROC|mAP@50|perplexity|exact\s+match)\s+score\b", re.I), 2.4),
        ],
        "RESULT": [
            (re.compile(r"\boutperforms?\b", re.I), 3.6),
            (re.compile(r"\bachieves?\s+(?:a\s+)?(?:new\s+)?(?:state-of-the-art|SOTA|superior|higher|competitive)\b", re.I), 3.5),
            (re.compile(r"\bimproves?\s+(?:performance|results|accuracy|BLEU|scores?)\s+(?:by|over)\b", re.I), 3.5),
            (re.compile(r"\b(?:results|experiments)\s+(?:demonstrate|show|indicate|reveal|confirm)\s+that\b", re.I), 3.0),
            (re.compile(r"\bwe\s+observe\s+(?:a\s+)?(?:significant|substantial|consistent)\s+(?:gain|improvement|increase)\b", re.I), 3.0),
            (re.compile(r"\bstatistically\s+significant\s+(?:\(p\s*<\s*0?\.\d+\)|difference)\b", re.I), 3.2),
            (re.compile(r"\btable\s+\d+\s+(?:shows|presents|summarizes)\s+the\s+results\b", re.I), 2.6),
            (re.compile(r"\byields?\s+(?:an\s+average\s+score\s+of|higher|superior)\b", re.I), 2.8),
            (re.compile(r"\b(?:leads?|led)\s+to\s+(?:a\s+)?(?:gain|boost|enhancement)\s+of\b", re.I), 3.0),
        ],
    }

    # Section-based priors (adds additive weight to specific classes)
    SECTION_PRIORS: Dict[str, Dict[str, float]] = {
        "limitation": {"LIMITATION": 1.5, "FUTURE_WORK": 0.5},
        "limitations": {"LIMITATION": 1.5, "FUTURE_WORK": 0.5},
        "threats to validity": {"LIMITATION": 1.5},
        "future work": {"FUTURE_WORK": 1.8, "LIMITATION": 0.5},
        "conclusion": {"FUTURE_WORK": 0.8, "RESULT": 0.5, "OBJECTIVE": 0.4},
        "conclusions": {"FUTURE_WORK": 0.8, "RESULT": 0.5, "OBJECTIVE": 0.4},
        "results": {"RESULT": 1.2, "METRIC": 0.6},
        "results and discussion": {"RESULT": 1.0, "LIMITATION": 0.5},
        "evaluation": {"RESULT": 1.0, "METRIC": 0.8},
        "experiments": {"RESULT": 0.8, "DATASET": 0.6, "METRIC": 0.6},
        "experimental setup": {"DATASET": 1.0, "METRIC": 0.8, "METHOD": 0.5},
        "method": {"METHOD": 1.4},
        "methods": {"METHOD": 1.4},
        "methodology": {"METHOD": 1.4},
        "model": {"METHOD": 1.4},
        "system architecture": {"METHOD": 1.4},
        "proposed method": {"METHOD": 1.4},
        "introduction": {"PROBLEM": 0.8, "OBJECTIVE": 0.8},
        "abstract": {"OBJECTIVE": 0.6, "RESULT": 0.5, "PROBLEM": 0.5},
        "background": {"PROBLEM": 0.5, "METHOD": 0.4},
        "related work": {"PROBLEM": 0.6, "METHOD": 0.4},
    }

    def __init__(self) -> None:
        pass

    def classify(self, sentence: str, section_name: str = "") -> Tuple[str, float]:
        """Calculates category scores, incorporates section priors, and returns (label, confidence)."""
        if not sentence or not sentence.strip():
            return "OTHER", 0.5

        scores: Dict[str, float] = {label: 0.1 for label in self.LABELS}

        # 1. Pattern matching scores
        for label, pattern_list in self.PATTERNS.items():
            for pattern, weight in pattern_list:
                if pattern.search(sentence):
                    scores[label] += weight

        # 2. Section context prior boost
        norm_section = section_name.strip().lower()
        if norm_section in self.SECTION_PRIORS:
            for label, prior in self.SECTION_PRIORS[norm_section].items():
                scores[label] += prior

        # 3. Handle 'OTHER' default
        max_label = max(scores, key=lambda k: scores[k])
        max_score = scores[max_label]

        # If no significant pattern matched (all scores below threshold 0.8), categorize as OTHER
        if max_score < 0.8:
            return "OTHER", 0.65

        # 4. Compute calibrated confidence using normalized score
        # Softmax approximation across top categories
        total_exp = sum(math.exp(min(s, 10.0)) for s in scores.values())
        prob = math.exp(min(max_score, 10.0)) / total_exp
        # Scale into intuitive 0.50 - 0.98 range
        confidence = round(min(max(prob, 0.55), 0.98), 2)

        return max_label, confidence


class TransformerScientificClassifier(BaseScientificClassifier):
    """Optional Transformer-based classifier (e.g. SciBERT) with transparent fallback.

    If transformers and pretrained weights are not installed or offline, it seamlessly
    falls back to RuleBasedScientificClassifier without failing.
    """

    def __init__(self, model_name: str = "allenai/scibert_scivocab_uncased") -> None:
        self.model_name = model_name
        self.fallback = RuleBasedScientificClassifier()
        self.pipeline = None
        self._is_transformer_active = False

        try:
            # Check if transformers is available and model can be loaded
            import transformers  # noqa: F401
            # In offline or non-GPU environments, we keep the pipeline optional
            logger.info(f"Transformer framework available. Configured model: '{model_name}'")
        except Exception:
            logger.info("Transformer framework not available. Using transparent rule-based baseline.")

    def classify(self, sentence: str, section_name: str = "") -> Tuple[str, float]:
        """Classifies using Transformer if active, otherwise delegates to rule-based."""
        if self._is_transformer_active and self.pipeline is not None:
            try:
                # Custom transformer inference logic
                res = self.pipeline(sentence)
                label = res[0]["label"].upper()
                score = float(res[0]["score"])
                if label in RuleBasedScientificClassifier.LABELS:
                    return label, round(score, 2)
            except Exception as exc:
                logger.warning(f"Transformer inference failed: {exc}. Falling back to rules.")

        return self.fallback.classify(sentence, section_name)


# Default classifier singleton (transparent baseline with modular transformer slot)
scientific_classifier = TransformerScientificClassifier()
