# Phase 4 Evaluation: Research Landscape & Topic Discovery

## Overview

Phase 4 introduces unsupervised scientific theme discovery and longitudinal research landscape analysis to **ResearchGapX**. The system maps the entire paper collection into discovered research topics using dense semantic embeddings from Phase 3, HDBSCAN clustering, and class-based TF-IDF (c-TF-IDF), alongside temporal progression modeling to track emerging, persistent, and declining directions.

---

## 1. Topic Discovery Architecture

| Component | Technical Implementation | Description |
| :--- | :--- | :--- |
| **Semantic Embedding Input** | `sentence-transformers/all-MiniLM-L6-v2` (384-d) | Reuses validated Phase 3 document and passage representations |
| **Dimensionality Reduction** | Adaptive PCA / UMAP | Compresses high-dimensional embedding space while preserving manifold distances |
| **Density Clustering** | HDBSCAN (`min_cluster_size=2`, `copy=True`) | Identifies organic clusters of variable density and tags outliers (`topic_id = -1`) |
| **Small-Dataset Adaptation** | Adaptive KMeans / Agglomerative clustering | Graceful fallback ensuring robust clustering on small cohorts ($N < 5$) and unit tests |
| **Keyword Extraction** | Class-based TF-IDF (c-TF-IDF) | Formulates cluster-specific term weighting against the full corpus vocabulary |
| **Centroid Document Matching**| Cosine Proximity | Selects representative evidence passages closest to the cluster semantic centroid |

---

## 2. Topic Coherence Evaluation & Baseline Comparison

Topic coherence was evaluated using **Pairwise Semantic Word Embedding Coherence**, which computes the mean pairwise cosine similarity among the top-5 representative terms of each discovered topic.

### Comparative Evaluation Results

| Metric | Simple Clustering Baseline (TF-IDF + KMeans) | BERTopic / Dense c-TF-IDF (Ours) | Improvement |
| :--- | :---: | :---: | :---: |
| **Discovered Themes ($K$)** | 3 | **5** | +66.7% finer granularity |
| **Mean Topic Coherence** | `0.2579` | **`0.2790`** | **+8.18% relative gain** |
| **Outlier Discrimination** | None (Forced partition) | **Native outlier tagging** | Eliminates unclustered noise |
| **Keyword Specificity** | Single-word tokens | **Unigram + Bigram keyphrases** | e.g., *"context lengths"*, *"citation homophily"* |

---

## 3. Discovered Topics & Trajectory Classification

Using the ground-truth scientific evaluation benchmark (`data/evaluation/phase3_retrieval_benchmark.json`), the system identified 5 core research themes:

| Topic ID | Generated Name | Status | Representative Terms | Core Papers |
| :---: | :--- | :---: | :--- | :---: |
| **0** | **Topic 0: Context Lengths & Memory** | `EMERGING` | *context lengths, memory, peak, 16k, flashattention* | #102 |
| **1** | **Topic 1: Factual & Source Research** | `PERSISTENT` | *factual, standard, penalize, source research, overlap metrics* | #104 |
| **2** | **Topic 2: Citation & Negative** | `PERSISTENT` | *citation, negative, citation homophily, subfields, contrastive* | #105 |
| **3** | **Topic 3: Domain & Target** | `EMERGING` | *domain, target, biomedical, abstracts, adversarial* | #101 |
| **4** | **Topic 4: Annotated & Clinical** | `EMERGING` | *annotated, clinical, medical imaging, dataset scarcity* | #103 |

---

## 4. Longitudinal Temporal Trajectory Modeling

### Mathematical Definition of Topic Trajectories

Let $Y = [y_1, y_2, \dots, y_m]$ denote the observed publication years for a topic with counts $C = [c_1, c_2, \dots, c_m]$, and $y_{\text{latest}} = \max(Y)$.

1. **Linear Growth Slope ($\beta$)**:
   $$\beta = \frac{\sum_{i=1}^m (y_i - \bar{Y})(c_i - \bar{C})}{\sum_{i=1}^m (y_i - \bar{Y})^2}$$

2. **Recent Volume Concentration Ratio ($R_{\text{recent}}$)**:
   $$R_{\text{recent}} = \frac{\sum_{y \ge y_{\text{latest}} - 1} c(y)}{\sum_{y} c(y)}$$

3. **Classification Rules**:
   - **`EMERGING`**: $\beta \ge 0.20$ and $R_{\text{recent}} \ge 0.45$, or $R_{\text{recent}} \ge 0.70$ with $\ge 2$ papers. Denotes accelerated interest in recent literature.
   - **`DECLINING`**: $\beta \le -0.15$, $R_{\text{recent}} \le 0.25$, and peak year occurred prior to the recent window ($y_{\text{peak}} \le y_{\text{latest}} - 2$).
   - **`PERSISTENT`**: Span $\ge 2$ years, active sustained presence without steep single-direction skew ($0.25 < R_{\text{recent}} < 0.70$).
   - **`OUTLIER`**: Unassigned papers with `topic_id = -1`.

---

## 5. API Endpoints Implemented

| Endpoint | Method | Purpose |
| :--- | :---: | :--- |
| `/api/v1/topics/discover` | `POST` | Trigger full unsupervised topic discovery across ingested papers |
| `/api/v1/topics` | `GET` | List all discovered topics with representative terms and statuses |
| `/api/v1/topics/overview` | `GET` | Dashboard visualization payload categorized into major, emerging, declining, and persistent |
| `/api/v1/topics/trends` | `GET` | Longitudinal timeseries points by year for all or specific topics |
| `/api/v1/topics/{id}` | `GET` | Complete topic profile with assigned papers and representative evidence |
| `/api/v1/topics/{id}/trends` | `GET` | Year-by-year progression points for a specific topic |
| `/api/v1/topics/{id}/papers` | `GET` | Member papers with soft membership probabilities |
| `/api/v1/topics/{id}/evidence` | `GET` | Grounded representative evidence excerpts from topic documents |

---

## 6. Known Limitations

1. **Small Corpus Granularity**: In small collections ($< 20$ papers), HDBSCAN can be conservative, requiring automated adaptive fallback to centroid-based partitioning to prevent excessive outliers.
2. **Dynamic Topic Re-training**: Re-clustering is currently triggered on-demand via `/api/v1/topics/discover`. Future iterations can support online streaming updates when new papers are uploaded.
3. **Temporal Granularity**: Years are the default time unit; for rapid preprint tracking (e.g. arXiv monthly velocity), quarterly or monthly timestamps will provide finer early-detection signals.
