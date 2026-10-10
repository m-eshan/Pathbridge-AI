"""
Assessment Scoring Module
Implements Big Five (50-item IPIP) and RIASEC (60-item O*NET) scoring logic,
including reverse keying and trait aggregation.
"""

import os
import sys
from typing import Dict, List, Any
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.data_loader import DataLoader


class PsychometricScorer:
    """Scoring engine for Big Five and RIASEC instruments."""

    def __init__(self, data_loader: DataLoader = None):
        if data_loader is None:
            data_loader = DataLoader()
        self.bigfive_meta = data_loader.load_bigfive_items()
        self.riasec_meta = data_loader.load_riasec_items()

    def score_bigfive(self, responses: Dict[str, int]) -> Dict[str, float]:
        """
        Score Big Five assessment responses.
        
        Args:
            responses: Dict mapping item_id (e.g., 'IPIP001') -> response (1 to 5)
            
        Returns:
            Dict mapping trait name -> average score (1.0 to 5.0)
        """
        trait_scores = {}
        trait_counts = {}

        for _, row in self.bigfive_meta.iterrows():
            item_id = row["item_id"]
            trait = row["trait"]
            keying = row["keying"]

            raw_resp = responses.get(item_id, 3) # default neutral if item omitted
            if not (1 <= raw_resp <= 5):
                raw_resp = 3

            # Apply reverse scoring for '-' keyed items
            scored_val = raw_resp if keying == "+" else (6 - raw_resp)

            trait_scores[trait] = trait_scores.get(trait, 0.0) + scored_val
            trait_counts[trait] = trait_counts.get(trait, 0) + 1

        final_scores = {}
        for trait, total_score in trait_scores.items():
            count = trait_counts[trait]
            final_scores[trait] = round(total_score / count, 2)

        return final_scores

    def score_riasec(self, responses: Dict[str, int]) -> Dict[str, int]:
        """
        Score RIASEC assessment responses.
        Handles full (60 items) or partial response sets.
        """
        category_scores = {}
        category_counts = {}

        for _, row in self.riasec_meta.iterrows():
            item_id = row["item_id"]
            trait = row["trait"]

            raw_resp = responses.get(item_id, 2) # default moderate interest if omitted
            category_scores[trait] = category_scores.get(trait, 0) + raw_resp
            category_counts[trait] = category_counts.get(trait, 0) + 1

        return category_scores


def run_unit_tests():
    """Unit test scoring against hand-computed sample responses."""
    print("Running Psychometric Scorer Unit Tests...")
    scorer = PsychometricScorer()

    # Hand-computed Test Case 1: Big Five all 5s
    n_items = len(scorer.bigfive_meta)
    all_fives = {f"IPIP{i:03d}": 5 for i in range(1, n_items + 1)}
    bf_scores_all_fives = scorer.score_bigfive(all_fives)
    for trait, score in bf_scores_all_fives.items():
        assert 1.0 <= score <= 5.0, f"Score out of range for {trait}: {score}"

    # Hand-computed Test Case 2: Big Five perfect scores
    # For '+' items: respond 5. For '-' items: respond 1.
    perfect_responses = {}
    for _, row in scorer.bigfive_meta.iterrows():
        perfect_responses[row["item_id"]] = 5 if row["keying"] == "+" else 1

    bf_scores_perfect = scorer.score_bigfive(perfect_responses)
    for trait, score in bf_scores_perfect.items():
        assert score == 5.0, f"Expected 5.0 for perfect responses on {trait}, got {score}"

    # Hand-computed Test Case 3: RIASEC scoring
    n_riasec = len(scorer.riasec_meta)
    riasec_fours = {f"RIASEC{i:03d}": 4 for i in range(1, n_riasec + 1)}
    riasec_scores = scorer.score_riasec(riasec_fours)
    expected_categories = {"Realistic", "Investigative", "Artistic", "Social", "Enterprising", "Conventional"}
    assert set(riasec_scores.keys()) == expected_categories
    items_per_cat = n_riasec // 6
    expected_sum = items_per_cat * 4
    for cat, score in riasec_scores.items():
        assert score == expected_sum, f"Expected {expected_sum} for RIASEC category {cat}, got {score}"

    print("ALL PSYCHOMETRIC SCORER UNIT TESTS PASSED SUCCESSFULLY! [OK]")


if __name__ == "__main__":
    run_unit_tests()
