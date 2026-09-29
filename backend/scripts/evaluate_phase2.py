"""Scientific NLP Pipeline Evaluation Script (Phase 2).

Evaluates:
1. Sentence segmentation robustness on scientific test passages.
2. 9-class scientific sentence discourse classification (Precision, Recall, F1, Support).
3. Binary limitation detection and limitation subtype categorization.
4. Binary future work detection.

Outputs machine-readable metrics to data/evaluation/phase2_metrics.json and prints
a formatted evaluation summary.
"""

from collections import Counter, defaultdict
import json
from pathlib import Path
import sys
from typing import Any, Dict, List

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.services.nlp.future_work_detector import future_work_detector
from backend.app.services.nlp.limitation_detector import limitation_detector
from backend.app.services.nlp.scientific_classifier import scientific_classifier
from backend.app.services.nlp.scientific_preprocessor import scientific_preprocessor
from backend.app.services.nlp.sentence_segmenter import sentence_segmenter

DATASET_PATH = REPO_ROOT / "data" / "evaluation" / "phase2_annotated_sentences.json"
METRICS_OUTPUT_PATH = REPO_ROOT / "data" / "evaluation" / "phase2_metrics.json"

CLASSES = [
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


def evaluate_segmentation() -> Dict[str, Any]:
    """Evaluates sentence segmentation on academic test passages with challenging syntax."""
    test_cases = [
        {
            "id": "abbreviations_and_citations",
            "text": "Vaswani et al. (2017) introduced the Transformer, i.e., a self-attention model. "
            "As shown in Fig. 2, the error rate dropped significantly (e.g., from 12.4% to 8.2%). "
            "See Eq. 4 for formal mathematical derivations.",
            "expected_count": 3,
        },
        {
            "id": "decimals_and_scientific_notation",
            "text": "The learning rate was set to 1.5e-4 with beta_1 = 0.9 and beta_2 = 0.999. "
            "We observed a p-value of p < 0.01 across 1,000 bootstrap iterations.",
            "expected_count": 2,
        },
        {
            "id": "bulleted_list_and_colons",
            "text": "Our contributions are threefold: "
            "1. A linear-time self-attention operator. "
            "2. Extensive experiments across 5 benchmarks. "
            "3. An open-source implementation.",
            "expected_count": 4,
        },
    ]

    results = []
    all_passed = True
    for case in test_cases:
        cleaned = scientific_preprocessor.preprocess(case["text"])
        segments = sentence_segmenter.segment_text(cleaned)
        actual_count = len(segments)
        passed = actual_count == case["expected_count"]
        if not passed:
            all_passed = False
        results.append(
            {
                "case_id": case["id"],
                "expected_count": case["expected_count"],
                "actual_count": actual_count,
                "passed": passed,
                "segmented_texts": segments,
            }
        )

    return {
        "all_cases_passed": all_passed,
        "total_test_cases": len(test_cases),
        "passed_test_cases": sum(1 for r in results if r["passed"]),
        "cases": results,
    }


def evaluate_pipeline(data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Runs end-to-end evaluation against annotated gold sentences."""
    # 9-class confusion matrix and metrics
    confusion: Dict[str, Dict[str, int]] = {c: {c2: 0 for c2 in CLASSES} for c in CLASSES}
    class_support = Counter([item["gold_label"] for item in data])

    # Binary metrics tracking
    lim_tp = lim_fp = lim_tn = lim_fn = 0
    subtype_correct = 0
    subtype_total = 0

    fw_tp = fw_fp = fw_tn = fw_fn = 0

    detailed_predictions = []

    for item in data:
        text = item["text"]
        section = item.get("section_name", "")
        gold_class = item["gold_label"]
        gold_lim = item.get("is_limitation", False)
        gold_subtype = item.get("limitation_subtype")
        gold_fw = item.get("is_future_work", False)

        # Preprocess text
        cleaned_text = scientific_preprocessor.preprocess(text)

        # 1. Discourse classification
        pred_class, conf = scientific_classifier.classify(cleaned_text, section_name=section)
        confusion[gold_class][pred_class] += 1

        # 2. Limitation detection
        lim_res = limitation_detector.detect(cleaned_text, section_name=section)
        pred_lim = lim_res is not None
        pred_subtype = lim_res["subtype"] if lim_res else None

        if pred_lim and gold_lim:
            lim_tp += 1
            if gold_subtype:
                subtype_total += 1
                if pred_subtype == gold_subtype:
                    subtype_correct += 1
        elif pred_lim and not gold_lim:
            lim_fp += 1
        elif not pred_lim and gold_lim:
            lim_fn += 1
        else:
            lim_tn += 1

        # 3. Future work detection
        fw_res = future_work_detector.detect(cleaned_text, section_name=section)
        pred_fw = fw_res is not None
        if pred_fw and gold_fw:
            fw_tp += 1
        elif pred_fw and not gold_fw:
            fw_fp += 1
        elif not pred_fw and gold_fw:
            fw_fn += 1
        else:
            fw_tn += 1

        detailed_predictions.append(
            {
                "id": item["id"],
                "text": text,
                "section": section,
                "gold_class": gold_class,
                "pred_class": pred_class,
                "class_correct": pred_class == gold_class,
                "gold_lim": gold_lim,
                "pred_lim": pred_lim,
                "gold_subtype": gold_subtype,
                "pred_subtype": pred_subtype,
                "gold_fw": gold_fw,
                "pred_fw": pred_fw,
            }
        )

    # Compute per-class Precision, Recall, F1
    per_class_metrics = {}
    macro_p_sum = macro_r_sum = macro_f1_sum = 0.0
    total_correct = sum(confusion[c][c] for c in CLASSES)
    total_samples = len(data)

    for c in CLASSES:
        tp = confusion[c][c]
        fp = sum(confusion[c_other][c] for c_other in CLASSES if c_other != c)
        fn = sum(confusion[c][c_other] for c_other in CLASSES if c_other != c)
        support = class_support[c]

        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0

        per_class_metrics[c] = {
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1": round(f1, 4),
            "support": support,
        }

        macro_p_sum += prec
        macro_r_sum += rec
        macro_f1_sum += f1

    num_classes = len(CLASSES)
    macro_metrics = {
        "macro_precision": round(macro_p_sum / num_classes, 4),
        "macro_recall": round(macro_r_sum / num_classes, 4),
        "macro_f1": round(macro_f1_sum / num_classes, 4),
        "accuracy": round(total_correct / total_samples, 4),
        "total_samples": total_samples,
    }

    # Binary Limitation metrics
    lim_prec = lim_tp / (lim_tp + lim_fp) if (lim_tp + lim_fp) > 0 else 0.0
    lim_rec = lim_tp / (lim_tp + lim_fn) if (lim_tp + lim_fn) > 0 else 0.0
    lim_f1 = (2 * lim_prec * lim_rec) / (lim_prec + lim_rec) if (lim_prec + lim_rec) > 0 else 0.0
    subtype_acc = subtype_correct / subtype_total if subtype_total > 0 else 0.0

    limitation_metrics = {
        "precision": round(lim_prec, 4),
        "recall": round(lim_rec, 4),
        "f1": round(lim_f1, 4),
        "true_positives": lim_tp,
        "false_positives": lim_fp,
        "true_negatives": lim_tn,
        "false_negatives": lim_fn,
        "subtype_accuracy": round(subtype_acc, 4),
        "subtype_correct": subtype_correct,
        "subtype_total": subtype_total,
    }

    # Binary Future Work metrics
    fw_prec = fw_tp / (fw_tp + fw_fp) if (fw_tp + fw_fp) > 0 else 0.0
    fw_rec = fw_tp / (fw_tp + fw_fn) if (fw_tp + fw_fn) > 0 else 0.0
    fw_f1 = (2 * fw_prec * fw_rec) / (fw_prec + fw_rec) if (fw_prec + fw_rec) > 0 else 0.0

    future_work_metrics = {
        "precision": round(fw_prec, 4),
        "recall": round(fw_rec, 4),
        "f1": round(fw_f1, 4),
        "true_positives": fw_tp,
        "false_positives": fw_fp,
        "true_negatives": fw_tn,
        "false_negatives": fw_fn,
    }

    return {
        "discourse_classification": {
            "per_class": per_class_metrics,
            "macro_averages": macro_metrics,
            "confusion_matrix": confusion,
        },
        "limitation_detection": limitation_metrics,
        "future_work_detection": future_work_metrics,
        "detailed_predictions": detailed_predictions,
    }


def main():
    print("=" * 80)
    print(" ResearchGapX - Phase 2 Scientific NLP Pipeline Evaluation")
    print("=" * 80)

    # 1. Segmentation Evaluation
    print("\n--- 1. Sentence Segmentation Robustness ---")
    seg_res = evaluate_segmentation()
    print(f"Passed: {seg_res['passed_test_cases']} / {seg_res['total_test_cases']}")
    for c in seg_res["cases"]:
        status_str = "PASS" if c["passed"] else "FAIL"
        print(f"  [{status_str}] {c['case_id']}: expected {c['expected_count']}, got {c['actual_count']}")

    # 2. Pipeline Evaluation
    print(f"\n--- 2. Discourse Classification & Detector Evaluation ({DATASET_PATH.name}) ---")
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    eval_results = evaluate_pipeline(data)
    discourse = eval_results["discourse_classification"]
    per_class = discourse["per_class"]
    macros = discourse["macro_averages"]

    print("\nDiscourse Classification Performance:")
    print(f"{'Class':<14} {'Precision':<10} {'Recall':<10} {'F1-Score':<10} {'Support':<8}")
    print("-" * 54)
    for c in CLASSES:
        m = per_class[c]
        print(f"{c:<14} {m['precision']:<10.4f} {m['recall']:<10.4f} {m['f1']:<10.4f} {m['support']:<8}")
    print("-" * 54)
    print(f"{'Macro Avg':<14} {macros['macro_precision']:<10.4f} {macros['macro_recall']:<10.4f} {macros['macro_f1']:<10.4f} {macros['total_samples']:<8}")
    print(f"Overall Accuracy: {macros['accuracy'] * 100:.2f}%\n")

    lim = eval_results["limitation_detection"]
    print("Limitation Detection Performance:")
    print(f"  Precision: {lim['precision']:.4f} | Recall: {lim['recall']:.4f} | F1: {lim['f1']:.4f}")
    print(f"  Subtype Accuracy: {lim['subtype_accuracy'] * 100:.2f}% ({lim['subtype_correct']}/{lim['subtype_total']})")
    print(f"  Confusion: TP={lim['true_positives']} FP={lim['false_positives']} FN={lim['false_negatives']} TN={lim['true_negatives']}\n")

    fw = eval_results["future_work_detection"]
    print("Future Work Detection Performance:")
    print(f"  Precision: {fw['precision']:.4f} | Recall: {fw['recall']:.4f} | F1: {fw['f1']:.4f}")
    print(f"  Confusion: TP={fw['true_positives']} FP={fw['false_positives']} FN={fw['false_negatives']} TN={fw['true_negatives']}\n")

    # Combine into full report
    full_output = {
        "metadata": {
            "dataset": str(DATASET_PATH.relative_to(REPO_ROOT)),
            "num_annotated_sentences": len(data),
            "classes": CLASSES,
        },
        "segmentation_evaluation": seg_res,
        "discourse_classification": discourse,
        "limitation_detection": lim,
        "future_work_detection": fw,
        "detailed_predictions": eval_results["detailed_predictions"],
    }

    METRICS_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(METRICS_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(full_output, f, indent=2)

    print(f"Evaluation metrics written to {METRICS_OUTPUT_PATH}")
    print("=" * 80)


if __name__ == "__main__":
    main()
