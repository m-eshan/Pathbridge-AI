"""
Full Pipeline Integration & End-to-End Execution Script
Wires together Psychometric Assessment, Conversational NLP, Knowledge Graph,
Cross-Domain Mapping Engine, and Roadmap Generator.
Executes end-to-end recommendations on synthetic student profiles spanning diverse engineering degrees.
"""

import os
import sys
import logging
import json
from typing import Dict, List, Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data_loader import DataLoader
from src.assessment import PsychometricScorer
from src.conversational_nlp import ConversationalNLPEngine
from src.knowledge_graph import CareerKnowledgeGraph
from src.mapping_engine import CrossDomainMappingEngine
from src.roadmap_generator import RoadmapGenerator

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class CareerGuidancePipeline:
    """Integrated End-to-End AI Career Guidance System Pipeline."""

    def __init__(self, alpha: float = 0.5, beta: float = 0.5):
        logger.info("Initializing complete Career Guidance Pipeline...")
        self.data_loader = DataLoader()
        self.scorer = PsychometricScorer(self.data_loader)
        self.nlp_engine = ConversationalNLPEngine()
        self.kg = CareerKnowledgeGraph(self.data_loader)
        self.kg.build_graph()
        self.mapping_engine = CrossDomainMappingEngine(self.kg, alpha=alpha, beta=beta)
        self.roadmap_generator = RoadmapGenerator()

    def process_student_profile(
        self,
        degree_name: str,
        bf_responses: Dict[str, int],
        riasec_responses: Dict[str, int],
        transcript: str,
        top_k: int = 3
    ) -> Dict[str, Any]:
        """
        Run full end-to-end career guidance pipeline for a student.
        
        Steps:
        1. Score Big Five and RIASEC assessment responses.
        2. Generate adaptive intake follow-up questions.
        3. Analyze transcript using GoEmotions NLP classifier.
        4. Construct canonical Trait Vector.
        5. Query Cross-Domain Mapping Engine for graph path-scored & affinity-scored pathways.
        6. Generate 3-Stage Roadmap for top pathway.
        """
        logger.info(f"\n========================================================")
        logger.info(f"PROCESSING STUDENT PROFILE: Degree = {degree_name}")
        logger.info(f"========================================================")

        # 1. Score psychometric assessments
        bf_scores = self.scorer.score_bigfive(bf_responses)
        riasec_scores = self.scorer.score_riasec(riasec_responses)

        # 2. Generate adaptive questions
        adaptive_questions = self.nlp_engine.generate_adaptive_questions(bf_scores, riasec_scores)

        # 3. Canonical Trait Vector with emotion signals
        trait_vector = self.nlp_engine.build_canonical_trait_vector(bf_scores, riasec_scores, transcript)

        # 4. Cross-Domain Pathways mapping
        pathways = self.mapping_engine.recommend_pathways(
            degree_name=degree_name,
            trait_vector=trait_vector,
            top_k=top_k
        )

        # Confirm explainability invariant: every output must have non-empty graph path bridge explanation
        for p in pathways:
            assert p["bridge_explanation"], f"Explainability failure: missing graph path for {p['title']}"

        # 5. Generate Roadmap for top pathway
        top_pathway = pathways[0]
        roadmap = self.roadmap_generator.generate_roadmap(
            degree_name=degree_name,
            target_domain=top_pathway["title"],
            transferable_skills=top_pathway["transferable_skills"],
            skill_gap=top_pathway["skill_gap"]
        )

        full_output = {
            "degree": degree_name,
            "big_five_scores": bf_scores,
            "riasec_scores": riasec_scores,
            "emotion_signals": trait_vector["emotion_signals"],
            "adaptive_questions": adaptive_questions,
            "recommended_pathways": pathways,
            "top_roadmap": roadmap
        }

        return full_output


# Define 4 Synthetic Student Profiles
SYNTHETIC_PROFILES = [
    {
        "degree": "Degree:Computer Science Engineering",
        "name": "Alex - Computer Science Engineering",
        "transcript": "I love building artificial intelligence models, processing big data, and creating automated software. I want to apply machine learning to solve real-world industrial or healthcare challenges.",
        "bf_responses": {f"IPIP{i:03d}": 5 if i in [17, 19, 9, 11] else 3 for i in range(1, 21)},
        "riasec_responses": {f"RIASEC{i:03d}": 4 if 6 <= i <= 10 or 26 <= i <= 30 else 1 for i in range(1, 31)}
    },
    {
        "degree": "Degree:Mechanical Engineering",
        "name": "Maya - Mechanical Engineering",
        "transcript": "I am passionate about robotics, smart mechatronic systems, and automated production. I want to bridge traditional mechanical cad design with intelligent sensor-driven robotics.",
        "bf_responses": {f"IPIP{i:03d}": 5 if i in [1, 3, 9, 11, 17, 19] else 3 for i in range(1, 21)},
        "riasec_responses": {f"RIASEC{i:03d}": 4 if 1 <= i <= 5 or 6 <= i <= 10 else 1 for i in range(1, 31)}
    },
    {
        "degree": "Degree:Civil Engineering",
        "name": "Jordan - Civil Engineering",
        "transcript": "I want to leverage geospatial data, surveying, and environmental engineering to build sustainable smart cities and green transport infrastructure.",
        "bf_responses": {f"IPIP{i:03d}": 5 if i in [5, 7, 9, 11, 17, 19] else 3 for i in range(1, 21)},
        "riasec_responses": {f"RIASEC{i:03d}": 4 if 16 <= i <= 20 or 26 <= i <= 30 else 1 for i in range(1, 31)}
    },
    {
        "degree": "Degree:Electrical Engineering",
        "name": "Sam - Electrical Engineering",
        "transcript": "I am super excited about clean energy, power electronics, microcontrollers, and launching tech startups in renewable energy systems.",
        "bf_responses": {f"IPIP{i:03d}": 5 if i in [1, 3, 17, 19, 21, 22] else 3 for i in range(1, 21)},
        "riasec_responses": {f"RIASEC{i:03d}": 4 if 21 <= i <= 25 or 6 <= i <= 10 else 1 for i in range(1, 31)}
    }
]


def run_end_to_end_test():
    """Run full pipeline on synthetic student profiles."""
    pipeline = CareerGuidancePipeline(alpha=0.5, beta=0.5)

    all_results = []

    for profile in SYNTHETIC_PROFILES:
        output = pipeline.process_student_profile(
            degree_name=profile["degree"],
            bf_responses=profile["bf_responses"],
            riasec_responses=profile["riasec_responses"],
            transcript=profile["transcript"],
            top_k=3
        )
        all_results.append((profile["name"], output))

    print("\n\n" + "="*80)
    print("END-TO-END PIPELINE SYNTHETIC PROFILES RESULTS DEMO")
    print("="*80)

    for name, res in all_results:
        print(f"\n----------------------------------------------------------------")
        print(f"PROFILE: {name}")
        print(f"----------------------------------------------------------------")
        print(f"Big Five Scores: {res['big_five_scores']}")
        print(f"Top Emotion Signals: {res['emotion_signals']}")
        print(f"\nTop 3 Cross-Domain Recommended Pathways:")
        for idx, p in enumerate(res["recommended_pathways"], 1):
            print(f"  [{idx}] {p['title'].upper()} (Final Score: {p['final_score']})")
            print(f"      Path Score: {p['path_score']} | Affinity Score: {p['affinity_score']}")
            print(f"      EXPLANATION (Graph Path Bridge): {p['bridge_explanation']}")
            print(f"      Transferable Skills ({len(p['transferable_skills'])}): {p['transferable_skills'][:4]}")
            print(f"      Skill Gap ({len(p['skill_gap'])}): {p['skill_gap'][:4]}")

        top_r = res["top_roadmap"]
        print(f"\nStaged Transition Roadmap for Top Target: {top_r['target_domain']}")
        for stage_title, stage_body in top_r["stages"].items():
            print(f"  {stage_title}: {stage_body['focus']}")
            print(f"    Target Skills: {stage_body['target_skills'][:3]}")

    print("\n" + "="*80)
    print("END-TO-END PIPELINE EXECUTION PASSED PERFECTLY! [OK]")
    print("="*80)


if __name__ == "__main__":
    run_end_to_end_test()
