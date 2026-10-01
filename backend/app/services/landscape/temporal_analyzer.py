"""Temporal Topic Dynamics & Evolution Analyzer (Phase 4).

Computes:
- Longitudinal publication trends by year per topic
- Mathematical classification of topic trajectories:
  * EMERGING: Rapidly accelerating adoption in recent years
  * DECLINING: Significant downward trajectory compared to historical peak
  * PERSISTENT: Sustained, steady presence across multiple consecutive years
  * MAJOR: Dominant themes with large share of collection
  * OUTLIER: Residual unclustered papers
"""

from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from backend.app.core.logging import get_logger

logger = get_logger("app.landscape.temporal")


class TemporalTopicAnalyzer:
    """Longitudinal trend analyzer and trajectory classification engine."""

    @staticmethod
    def compute_yearly_distribution(years: List[Optional[int]]) -> Dict[str, int]:
        """Aggregate paper count by year, grouping None/missing as 'Unknown'."""
        dist: Dict[str, int] = {}
        for yr in years:
            if yr is not None and yr > 0:
                key = str(int(yr))
            else:
                key = "Unknown"
            dist[key] = dist.get(key, 0) + 1
        return dict(sorted(dist.items(), key=lambda x: (x[0] == "Unknown", x[0])))

    @classmethod
    def classify_topic_trajectory(
        cls,
        yearly_counts: Dict[str, int],
        topic_id: int,
        total_corpus_papers: int = 1,
    ) -> str:
        """Classify a topic trajectory into EMERGING, DECLINING, PERSISTENT, or OUTLIER.

        Mathematical Formulation:
        -------------------------
        Let valid numeric years be Y = [y_1, y_2, ..., y_m] with counts C = [c_1, c_2, ..., c_m].
        Let N = sum(C).
        Let y_max = max(Y) across the observed corpus.

        1. Outlier Condition:
           If topic_id == -1, status = 'OUTLIER'.

        2. Linear Growth Slope (beta):
           beta = sum((y_i - mean(Y)) * (c_i - mean(C))) / sum((y_i - mean(Y))^2)

        3. Recent Volume Concentration (R_recent):
           R_recent = sum_{y >= y_max - 1} c(y) / N

        Classification Rules:
        - EMERGING:
            (beta >= 0.25 and R_recent >= 0.50) or (len(Y) <= 2 and min(Y) >= y_max - 1 and N >= 2)
        - DECLINING:
            beta <= -0.20 and R_recent <= 0.20 and max(C) >= 2
        - PERSISTENT:
            len(Y) >= 2 and span(Y) >= 2 and not EMERGING and not DECLINING
        """
        if topic_id == -1:
            return "OUTLIER"

        numeric_years = []
        counts = []
        for yr_str, cnt in yearly_counts.items():
            if yr_str != "Unknown":
                try:
                    numeric_years.append(int(yr_str))
                    counts.append(cnt)
                except ValueError:
                    pass

        total_papers = sum(counts)
        if total_papers == 0 or len(numeric_years) == 0:
            return "PERSISTENT"

        if len(numeric_years) == 1:
            # Single year observed
            return "EMERGING" if numeric_years[0] >= 2024 else "PERSISTENT"

        # Sort chronologically
        sorted_pairs = sorted(zip(numeric_years, counts), key=lambda x: x[0])
        Y = np.array([p[0] for p in sorted_pairs], dtype=np.float64)
        C = np.array([p[1] for p in sorted_pairs], dtype=np.float64)

        y_max = np.max(Y)
        recent_cutoff = y_max - 1.0
        recent_mask = Y >= recent_cutoff
        recent_vol = np.sum(C[recent_mask])
        r_recent = recent_vol / total_papers if total_papers > 0 else 0.0

        # Calculate slope beta
        var_y = np.var(Y)
        if var_y > 1e-6:
            cov = np.cov(Y, C)[0, 1]
            beta = float(cov / var_y)
        else:
            beta = 0.0

        # Rule evaluations
        # Emerging: strong positive slope or high recent concentration
        if (beta >= 0.20 and r_recent >= 0.45) or (r_recent >= 0.70 and total_papers >= 2):
            return "EMERGING"

        # Declining: negative slope, peak in past, minimal recent activity
        peak_idx = int(np.argmax(C))
        peak_year = Y[peak_idx]
        if (beta <= -0.15 and r_recent <= 0.25 and peak_year <= recent_cutoff - 1) or (
            r_recent == 0.0 and len(Y) >= 2
        ):
            return "DECLINING"

        # Persistent: active across multiple years without sharp one-sided bias
        return "PERSISTENT"

    @classmethod
    def format_trend_points(
        cls,
        yearly_counts: Dict[str, int],
        all_yearly_totals: Optional[Dict[str, int]] = None,
    ) -> List[Dict[str, Any]]:
        """Format yearly counts into visualization-ready timeseries points with percentages."""
        trends = []
        for yr_str, cnt in sorted(yearly_counts.items(), key=lambda x: (x[0] == "Unknown", x[0])):
            if yr_str == "Unknown":
                continue
            yr_int = int(yr_str)
            total_in_yr = (all_yearly_totals or {}).get(yr_str, cnt)
            pct = round((cnt / total_in_yr * 100.0) if total_in_yr > 0 else 0.0, 2)
            trends.append({
                "year": yr_int,
                "paper_count": cnt,
                "percentage": pct,
            })
        return trends
