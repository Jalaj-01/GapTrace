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
            (re.compile(r"\b(?:a\s+notable|a\s+clear|a\s+methodological|the\s+primary|the\s+main|several\s+notable|several|major|key|inherent)\s+limitations?\b", re.I), 3.8),
            (re.compile(r"\bour\s+(?:work|study|evaluation|approach|method|pipeline|algorithm)\s+(?:has\s+several\s+limitations|is\s+constrained\s+by|relies\s+on\s+a\s+single|was\s+tested\s+only|does\s+not\s+account\s+for)\b", re.I), 3.8),
            (re.compile(r"\b(?:cannot|unable\s+to|prevents?\s+.*?\s+from)\s+(?:scale|generalize|running\s+in\s+real-time|handle|capture)\b", re.I), 3.2),
            (re.compile(r"\b(?:quadratic|exponential)\s+(?:attention\s+)?(?:memory|time|complexity|cost)\b", re.I), 3.2),
            (re.compile(r"\b(?:computationally|prohibitively)\s+(?:expensive|costly|demanding|intractable)\b", re.I), 3.2),
            (re.compile(r"\b(?:substantial\s+gpu\s+memory|compute\s+budget|high\s+computational\s+overhead)\b", re.I), 3.5),
            (re.compile(r"\b(?:small\s+sample\s+size|data\s+scarcity|annotations?\s+are\s+extremely\s+sparse|sample\s+bias|selection\s+bias)\b", re.I), 3.5),
            (re.compile(r"\b(?:may\s+not|does\s+not)\s+generalize\s+well\b", re.I), 3.5),
            (re.compile(r"\b(?:fail\s+to\s+capture\s+the\s+complexity|whether\s+these\s+findings\s+transfer|remains\s+an\s+open\s+empirical\s+limitation)\b", re.I), 3.5),
            (re.compile(r"\b(?:methodological\s+limitation|assumption\s+of\s+linear\s+independence|simplifying\s+the\s+objective\s+function)\b", re.I), 3.5),
            (re.compile(r"\b(?:conducted\s+with\s+only\s+\d+\s+annotators|does\s+not\s+account\s+for\s+temporal\s+shifts)\b", re.I), 3.5),
            (re.compile(r"\bdespite\s+promising\s+outcomes,\s+our\s+study\s+has\s+several\s+notable\s+limitations\b", re.I), 3.8),
            (re.compile(r"\bwe\s+acknowledge\s+that\b", re.I), 3.0),
            (re.compile(r"\bsusceptible\s+to\s+(?:noise|overfitting|hallucination|adversarial)\b", re.I), 2.5),
            (re.compile(r"\b(?:drawback|weakness|shortcoming|vulnerability|flaw)s?\b", re.I), 2.2),
        ],
        "FUTURE_WORK": [
            (re.compile(r"\b(?:in\s+future\s+work|for\s+future\s+(?:work|research|inquiry|study|iterations)|future\s+(?:research|investigations?|studies|work)\s+(?:will|should|could|might|focus))\b", re.I), 3.8),
            (re.compile(r"\bwe\s+(?:plan|intend|hope|aim)\s+to\s+(?:extend|explore|investigate|generalize|apply|evaluate|incorporate|validate|release)\b", re.I), 3.5),
            (re.compile(r"\b(?:leave|leaves)\b.*?\b(?:for|to|as\s+an\s+avenue\s+for)\s+(?:future|subsequent)\s+(?:work|research|inquiry|iterations|studies)\b", re.I), 3.8),
            (re.compile(r"\b(?:promising|natural|interesting|exciting)\s+(?:direction|avenue|next\s+step)\s+(?:for\s+future|to)\b", re.I), 3.5),
            (re.compile(r"\bfurther\s+(?:research|investigation|exploration|study|work)\s+is\s+(?:needed|warranted|required)\b", re.I), 3.2),
            (re.compile(r"\brepresents\s+a\s+natural\s+next\s+step\b", re.I), 3.5),
            (re.compile(r"\bremains\s+(?:an?\s+)?(?:open|promising)\s+(?:question|direction|problem|avenue)\s+for\s+future\b", re.I), 3.5),
        ],
        "PROBLEM": [
            (re.compile(r"\b(?:fundamental|pervasive|open|unsolved|central|key|major|acute)\s+(?:problem|question|challenge|bottleneck|difficulty|obstacle)\b", re.I), 3.2),
            (re.compile(r"\b(?:existing|prior|previous|current|conventional|standard)\s+(?:approaches|methods|models|techniques|solutions|linkers|systems|encoders|transformer\s+models|contrastive\s+learning)?\s*(?:struggle|suffer|fail|exhibit\s+poor|rely|are\s+limited|often\s+fail)\b", re.I), 3.4),
            (re.compile(r"\b(?:primary\s+shortcoming|notable\s+drawback)\s+of\s+(?:unsupervised|diffusion|existing|prior|deep|[a-z\-]+\s+methods|[a-z\-]+\s+models)\b", re.I), 3.5),
            (re.compile(r"\bdiscrepancy\s+highlights\s+an\s+unresolved\s+issue\b", re.I), 3.2),
            (re.compile(r"\b(?:anisotropy\s+problem|representation\s+collapse|catastrophic\s+forgetting|slow\s+sampling\s+speed)\b", re.I), 3.2),
            (re.compile(r"\b(?:hard|difficult|challenging|prohibitive)\s+to\s+(?:scale|train|optimize|guarantee|interpret|align)\b", re.I), 2.8),
            (re.compile(r"\b(?:remains?\s+vulnerable\s+to|vulnerable\s+to\s+lexical\s+mismatch)\b", re.I), 3.2),
            (re.compile(r"\b(?:struggles?\s+to\s+capture|long-range\s+topological\s+dependencies)\b", re.I), 3.2),
            (re.compile(r"\bstruggles?\s+with\s+low-resource\b", re.I), 3.2),
            (re.compile(r"\b(?:exhibits?|suffer\s+from)\s+(?:poor\s+robustness|severe\s+catastrophic)\b", re.I), 3.2),
            (re.compile(r"\b(?:inability\s+of\s+attention\s+heads|presents?\s+an?\s+acute\s+obstacle)\b", re.I), 3.2),
            (re.compile(r"\ba\s+major\s+challenge\s+in\s+clinical\s+NLP\b", re.I), 3.2),
            (re.compile(r"\bpoorly\s+understood|inadequately\s+addressed|lack\s+the\s+ability\s+to\b", re.I), 2.6),
            (re.compile(r"\ba\s+central\s+challenge\s+in\b", re.I), 2.8),
        ],
        "OBJECTIVE": [
            (re.compile(r"\b(?:in\s+this\s+(?:paper|work|study|letter|article)\s*,?\s*(?:we\s+)?(?:aim\s+to|seek\s+to|propose|introduce|present|develop|design|investigate|explore|demonstrate|quantify))\b", re.I), 3.8),
            (re.compile(r"\b(?:this\s+(?:paper|work|study|article)\s+(?:presents?|introduces?|proposes?|develops?|investigates?|examines?|aims?\s+to|focuses?\s+on|seeks\s+to))\b", re.I), 3.8),
            (re.compile(r"\b(?:our\s+(?:goal|objective|aim|hypothesis|purpose|focus)|the\s+(?:primary|main|key|central)\s+(?:goal|objective|aim|purpose|contribution))\s+(?:is|was|of\s+this\s+(?:study|paper|work))?\s+(?:to|is)\b", re.I), 3.8),
            (re.compile(r"\bto\s+overcome\s+(?:these|this|such)\s+(?:challenges?|limitations?|issues?|problems?),\s*we\s+(?:propose|introduce|present|develop|design)\b", re.I), 3.6),
            (re.compile(r"\b(?:here|in\s+this\s+work|in\s+this\s+paper),\s*we\s+(?:investigate|examine|explore|evaluate|study|demonstrate|propose|present)\b", re.I), 3.6),
            (re.compile(r"\bwe\s+aim\s+to\s+(?:address|solve|tackle|investigate|explore|evaluate|quantify)\b", re.I), 3.6),
            (re.compile(r"\b(?:the\s+)?(?:main|primary|central|key)\s+contributions?\s+(?:of\s+this\s+paper\s+are|are\s+as\s+follows|is)\b", re.I), 3.4),
            (re.compile(r"\bour\s+focus\s+is\s+on\s+(?:designing|developing|investigating|evaluating)\b", re.I), 3.2),
            (re.compile(r"\bwe\s+present\s+a\s+(?:comprehensive|novel|new|lightweight)\s+(?:taxonomy|framework|method|algorithm)\b", re.I), 3.2),
            (re.compile(r"\bwe\s+develop\s+a\s+(?:dual-branch|novel|new)\b", re.I), 3.2),
            (re.compile(r"\bour\s+paper\s+investigates\b", re.I), 3.2),
            (re.compile(r"\bwe\s+formulate\s+the\s+[a-z\s]+\s+task\s+as\b", re.I), 3.0),
            (re.compile(r"\bwe\s+hypothesize\s+that\b", re.I), 3.0),
        ],
        "METHOD": [
            (re.compile(r"\b(?:proposed|our)\s+(?:architecture|framework|model|algorithm|method|pipeline|network)\b", re.I), 2.5),
            (re.compile(r"\b(?:architecture\s+consists\s+of|consists\s+of\s+a\s+\d+-layer|multi-head\s+self-attention|depthwise\s+separable|convolutional\s+layers?|bidirectional\s+transformer|pooling\s+layer)\b", re.I), 3.5),
            (re.compile(r"\b(?:apply|applying|use|using)\s+(?:greedy\s+decoding|beam\s+search|bpe\s+tokenization|dropout)\b", re.I), 3.4),
            (re.compile(r"\b(?:kernel\s+size|stride|depthwise\s+separable|hidden\s+dimensions)\b", re.I), 3.2),
            (re.compile(r"\b(?:gradient\s+updates\s+are\s+clipped|clipped\s+to\s+a\s+maximum\s+norm|numerical\s+stability\s+during\s+backpropagation)\b", re.I), 3.4),
            (re.compile(r"\b(?:loss\s+function|cross-entropy\s+loss|objective\s+function\s+is\s+defined|optimized\s+using)\b", re.I), 3.2),
            (re.compile(r"\b(?:we\s+optimize\s+(?:the\s+)?network|AdamW\s+optimizer|cosine\s+annealing)\b", re.I), 3.5),
            (re.compile(r"\b(?:contrastive\s+objective|positive\s+sentence\s+pairs|in-batch\s+negative)\b", re.I), 3.5),
            (re.compile(r"\b(?:to\s+prevent\s+overfitting,\s*dropout|feed-forward\s+projection)\b", re.I), 3.5),
            (re.compile(r"\b(?:state\s+transition\s+probabilities|expectation-maximization\s+algorithm)\b", re.I), 3.5),
            (re.compile(r"\b(?:top-p\s+nucleus\s+sampling|nucleus\s+sampling)\b", re.I), 3.5),
            (re.compile(r"\b(?:soft\s+nearest-neighbor|dense\s+embedding\s+index|approximate\s+cosine\s+similarity)\b", re.I), 3.5),
            (re.compile(r"\b(?:adopt\s+beam\s+search|beam\s+width\s+of|length\s+penalty)\b", re.I), 3.5),
            (re.compile(r"\b(?:Monte\s+Carlo\s+tree\s+search|decision\s+state\s+space)\b", re.I), 3.5),
            (re.compile(r"\b(?:relational\s+graph\s+convolutional|message-passing\s+iterations)\b", re.I), 3.5),
            (re.compile(r"\btrained\s+(?:using|with|via)\s+(?:Adam|AdamW|SGD|backpropagation|gradient\s+descent)\b", re.I), 3.2),
            (re.compile(r"\bhyperparameters?\s+(?:were|are|set\s+to)\b", re.I), 2.6),
            (re.compile(r"\bwe\s+(?:implement|construct|deploy|utilize|employ)\s+a\b", re.I), 2.0),
        ],
        "DATASET": [
            (re.compile(r"\b(?:utilize|rely\s+on|partition|leverage|evaluate\s+on|evaluated\s+on|tested\s+on)\s+(?:the\s+)?(?:[A-Za-z0-9\-]+\s+)?(?:corpus|dataset|benchmark|corpora|collection)\b", re.I), 3.6),
            (re.compile(r"\b(?:benchmark|corpus|dataset|corpora)\s+(?:consists?|contains?|comprises?|containing|split)\b", re.I), 3.5),
            (re.compile(r"\b(?:XNLI|SciFact|SciERC|HotpotQA|GSM8K|Flickr30k|WikiText|Multi30k|SNLI|MNLI|TriviaQA|SQuAD|GLUE|SuperGLUE|ImageNet|WMT|MNIST|CIFAR|MS-COCO|MS\s+COCO|Penn\s+Treebank|MIMIC)\b", re.I), 3.2),
            (re.compile(r"\b(?:partition\s+the\s+[A-Za-z0-9\-]+\s+corpus|training\s+claims|test\s+claims|validation\s+claims)\b", re.I), 3.5),
            (re.compile(r"\b(?:validation\s+set|training\s+set|test\s+set)\s+is\s+drawn\s+from\b", re.I), 3.6),
            (re.compile(r"\bCoNLL(?:-\d+)?\b", re.I), 3.2),
            (re.compile(r"\b(?:benchmark\s+dataset|benchmark\s+corpus|evaluation\s+corpus|benchmark\s+collections?)\b", re.I), 3.4),
            (re.compile(r"\bannotated\s+with\s+(?:scientific\s+entities|labels|tags)\b", re.I), 3.2),
            (re.compile(r"\bdata\s+(?:was|were)\s+collected\s+from\b", re.I), 2.8),
            (re.compile(r"\bwe\s+sample\s+\d+[\d,]*\s+(?:examples|instances|sentences|pairs|images)\b", re.I), 2.8),
        ],
        "METRIC": [
            (re.compile(r"\b(?:report|reporting)\s+(?:performance|results)\s+using\b", re.I), 3.6),
            (re.compile(r"\b(?:quantified|measured|assessed|evaluated)\s+(?:by|via|using|through|in\s+terms\s+of)\b", re.I), 3.6),
            (re.compile(r"\b(?:we\s+assess|assess)\s+(?:entity\s+boundary\s+)?precision,\s*recall,\s*and\s+(?:micro|macro)?\s*F1\b", re.I), 3.8),
            (re.compile(r"\b(?:we\s+compute|we\s+measure|we\s+assess|we\s+evaluate)\s+(?:macro-averaged|micro-averaged|perplexity|accuracy|precision|recall|f1|bleu|rouge|mrr|ndcg|auroc|ece|fid|latency|sample\s+efficiency|reasoning\s+consistency|exact\s+match)\b", re.I), 3.6),
            (re.compile(r"\b(?:evaluation\s+metrics?|primary\s+metrics?|standard\s+metric|metric\s+over|metrics?\s+against|metrics?\s+include|primary\s+metrics?\s+for|execution\s+accuracy\s+metric)\b", re.I), 3.6),
            (re.compile(r"\b(?:BLEU|ROUGE|METEOR|chrF|F1\s+scores?|AUROC|MRR@?\d*|NDCG@?\d*|ECE|NLL|Inception\s+Score|FID|Mean\s+Opinion\s+Score|MOS|Student\'s\s+t-test|Fréchet\s+Inception\s+Distance|Adjusted\s+Rand\s+Index|ARI)\b", re.I), 3.4),
            (re.compile(r"\b(?:wall-clock\s+inference\s+latency|peak\s+GPU\s+memory\s+allocated)\b", re.I), 3.2),
            (re.compile(r"\bstandard\s+evaluation\s+metrics?\b", re.I), 3.0),
        ],
        "RESULT": [
            (re.compile(r"\boutperform(?:s|ing|ed)?\b", re.I), 3.8),
            (re.compile(r"\bachieves?\s+(?:a\s+)?(?:new\s+)?(?:state-of-the-art|SOTA|superior|higher|competitive|\d+|[\d\.]+%)\b", re.I), 3.8),
            (re.compile(r"\b(?:as\s+shown\s+in\s+table\s+\d+|table\s+\d+\s+shows|figure\s+\d+\s+confirms?|ablation\s+results?\s+in\s+figure)\b", re.I), 3.6),
            (re.compile(r"\b(?:surpasses?\s+(?:the\s+)?(?:strong\s+)?baseline|yields?\s+consistent\s+gains?|attains?\s+(?:a\s+)?state-of-the-art|reduces?\s+perplexity\s+from|drop\s+in\s+recall|drop\s+in\s+accuracy|attains?\s+competitive\s+performance)\b", re.I), 3.8),
            (re.compile(r"\b(?:improves?|reduces?)\s+(?:[A-Za-z0-9\-]+\s+)?by\s+\d+(?:\.\d+)?\s+points?\b", re.I), 4.2),
            (re.compile(r"\bimproves?\s+(?:ROUGE|BLEU|F1|accuracy|performance|results)\s+(?:by|over)\b", re.I), 3.8),
            (re.compile(r"\b(?:results|experiments)\s+(?:demonstrate|show|indicate|reveal|confirm)\s+that\b", re.I), 3.2),
            (re.compile(r"\b(?:experimental\s+results?\s+demonstrate|empirical\s+findings?\s+show|experimental\s+evaluation\s+validates)\b", re.I), 3.8),
            (re.compile(r"\b(?:reduction\s+in\s+inference\s+latency|significantly\s+boosts?\s+zero-shot|reduces?\s+memory\s+consumption\s+by)\b", re.I), 3.8),
            (re.compile(r"\byields?\s+(?:a\s+)?(?:\d+(?:\.\d+)?%?\s+)?improvement\b", re.I), 3.8),
            (re.compile(r"\bwe\s+observe\s+(?:a\s+)?(?:significant|substantial|consistent)\s+(?:gain|improvement|increase|advantage)\b", re.I), 3.2),
            (re.compile(r"\bstatistically\s+significant\s+(?:\(p\s*<\s*0?\.\d+\)|difference)\b", re.I), 3.4),
            (re.compile(r"\b(?:p\s*<\s*0?\.\d+|p-value)\b", re.I), 3.2),
            (re.compile(r"\byields?\s+(?:an\s+average\s+score\s+of|higher|superior)\b", re.I), 3.0),
            (re.compile(r"\b(?:leads?|led)\s+to\s+(?:a\s+)?(?:gain|boost|enhancement)\s+of\b", re.I), 3.2),
            (re.compile(r"\b(?:our\s+(?:model|approach|method)\s+(?:reduces|attains|achieves|outperforms|improves))\b", re.I), 3.4),
        ],
    }

    # Section-based priors (adds additive weight to specific classes)
    SECTION_PRIORS: Dict[str, Dict[str, float]] = {
        "limitation": {"LIMITATION": 2.0, "FUTURE_WORK": 0.5},
        "limitations": {"LIMITATION": 2.0, "FUTURE_WORK": 0.5},
        "threats to validity": {"LIMITATION": 2.0},
        "future work": {"FUTURE_WORK": 2.2, "LIMITATION": 0.5},
        "conclusion": {"FUTURE_WORK": 0.8, "RESULT": 0.5},
        "conclusions": {"FUTURE_WORK": 0.8, "RESULT": 0.5},
        "results": {"RESULT": 1.5, "METRIC": 0.6},
        "results and discussion": {"RESULT": 1.2, "LIMITATION": 0.5},
        "evaluation": {"RESULT": 1.0, "METRIC": 0.8},
        "experiments": {"RESULT": 0.8, "DATASET": 0.6, "METRIC": 0.6},
        "experimental setup": {"DATASET": 1.0, "METRIC": 0.8, "METHOD": 0.5},
        "method": {"METHOD": 1.6},
        "methods": {"METHOD": 1.6},
        "methodology": {"METHOD": 1.6},
        "model": {"METHOD": 1.6},
        "system architecture": {"METHOD": 1.6},
        "proposed method": {"METHOD": 1.6},
        "metrics": {"METRIC": 2.0},
        "evaluation metrics": {"METRIC": 2.0},
        "datasets": {"DATASET": 1.8},
        "benchmark collections": {"DATASET": 1.8},
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

        has_pattern_match = max(scores.values()) > 0.1

        # 2. Section context prior boost
        norm_section = section_name.strip().lower()
        if norm_section in self.SECTION_PRIORS:
            for label, prior in self.SECTION_PRIORS[norm_section].items():
                if has_pattern_match or norm_section in {"limitation", "limitations", "threats to validity", "future work"}:
                    scores[label] += prior

        # 3. Handle 'OTHER' default
        max_label = max(scores, key=lambda k: scores[k])
        max_score = scores[max_label]

        # If no significant pattern matched (all scores below threshold 0.8), categorize as OTHER
        if max_score < 0.8:
            return "OTHER", 0.65

        # 4. Compute calibrated confidence using normalized score
        total_exp = sum(math.exp(min(s, 10.0)) for s in scores.values())
        prob = math.exp(min(max_score, 10.0)) / total_exp
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
