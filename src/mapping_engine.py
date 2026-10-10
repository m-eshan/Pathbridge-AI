"""
Cross-Domain Mapping Engine Module
Implements semantic affinity scoring, NetworkX path-score traversal,
tunable alpha/beta weighting, bridge-explanation extraction, and skill-gap analysis.
"""

import os
import sys
import logging
from typing import Dict, List, Tuple, Optional, Any
import numpy as np
import networkx as nx
from sentence_transformers import SentenceTransformer, util

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.knowledge_graph import CareerKnowledgeGraph, DEFAULT_DEGREE_CURRICULA

logger = logging.getLogger(__name__)

# Pretrained local sentence transformer model
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"


class CrossDomainMappingEngine:
    """Mapping engine connecting student degree & trait profiles to career domains."""

    def __init__(
        self,
        knowledge_graph: Optional[CareerKnowledgeGraph] = None,
        alpha: float = 0.5,
        beta: float = 0.5,
        model_name: str = EMBEDDING_MODEL_NAME
    ):
        if knowledge_graph is None:
            knowledge_graph = CareerKnowledgeGraph()
            knowledge_graph.build_graph()

        self.kg = knowledge_graph
        self.graph = knowledge_graph.graph
        self.alpha = alpha
        self.beta = beta

        logger.info(f"Loading SentenceTransformer model '{model_name}'...")
        self.encoder = SentenceTransformer(model_name)

        # Precompute occupation text representations and embeddings for fast similarity calculation
        self.candidate_occupations = []
        self.candidate_texts = []
        self.candidate_uris = []
        self.candidate_embeddings = None

    def _precompute_occupation_embeddings(self):
        """Extract all occupation nodes and pre-encode their textual descriptions with disk caching."""
        if self.candidate_embeddings is not None:
            return

        cache_path = os.path.join(self.kg.loader.data_dir, "cache_occupation_embeddings.pkl")
        if os.path.exists(cache_path):
            try:
                logger.info("Loading cached occupation embeddings from disk...")
                import pickle
                with open(cache_path, "rb") as f:
                    cached = pickle.load(f)
                    self.candidate_uris = cached["uris"]
                    self.candidate_occupations = cached["occupations"]
                    self.candidate_texts = cached["texts"]
                    self.candidate_embeddings = cached["embeddings"]
                logger.info(f"Fast init: Loaded {len(self.candidate_occupations)} pre-encoded embeddings in < 0.1s.")
                return
            except Exception as e:
                logger.warning(f"Embedding cache notice, recomputing: {e}")

        logger.info("Precomputing embeddings for all occupation nodes in the graph...")
        for node_id, data in self.graph.nodes(data=True):
            if data.get("node_type") == "occupation":
                label = data.get("label", "")
                desc = data.get("description", label)

                # Get top connected skills to enrich text profile
                neighbors = list(self.graph.neighbors(node_id))
                skills = [
                    self.graph.nodes[nbr].get("label", "")
                    for nbr in neighbors
                    if self.graph.nodes[nbr].get("node_type") == "skill"
                ]
                skills_str = ", ".join(skills[:15])

                full_text = f"Occupation: {label}. Description: {desc}. Required skills: {skills_str}."
                self.candidate_uris.append(node_id)
                self.candidate_occupations.append(label)
                self.candidate_texts.append(full_text)

        logger.info(f"Encoding {len(self.candidate_texts)} candidate occupation profiles...")
        self.candidate_embeddings = self.encoder.encode(
            self.candidate_texts, convert_to_tensor=True, show_progress_bar=False
        )

        try:
            import pickle
            with open(cache_path, "wb") as f:
                pickle.dump({
                    "uris": self.candidate_uris,
                    "occupations": self.candidate_occupations,
                    "texts": self.candidate_texts,
                    "embeddings": self.candidate_embeddings
                }, f)
            logger.info("Successfully cached occupation embeddings to disk.")
        except Exception as e:
            logger.warning(f"Could not cache embeddings to disk: {e}")

    def _trait_vector_to_text(self, trait_vector: Dict[str, Any]) -> str:
        """Convert structured trait vector into descriptive text for semantic embedding."""
        bf = trait_vector.get("big_five", {})
        riasec = trait_vector.get("riasec", {})
        emotions = trait_vector.get("emotion_signals", {})
        free_text = trait_vector.get("user_interests", "")

        text_parts = []
        if bf:
            high_bf = [t for t, score in bf.items() if score >= 3.5]
            if high_bf:
                text_parts.append(f"Personality traits include high {', '.join(high_bf)}.")

        if riasec:
            top_riasec = sorted(riasec.items(), key=lambda x: x[1], reverse=True)[:3]
            top_riasec_names = [t[0] for t in top_riasec]
            text_parts.append(f"Primary vocational interest areas: {', '.join(top_riasec_names)}.")

        if emotions:
            high_em = [e for e, score in emotions.items() if score >= 0.5]
            if high_em:
                text_parts.append(f"Motivated by {', '.join(high_em)}.")

        if free_text:
            text_parts.append(f"Expressed career goals and interests: {free_text}.")

        combined = " ".join(text_parts)
        return combined if combined else "General engineering student seeking technical career."

    def recommend_pathways(
        self,
        degree_name: str,
        trait_vector: Dict[str, Any],
        top_k: int = 5,
        alpha: Optional[float] = None,
        beta: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Rank candidate career domains for a student.
        
        Args:
            degree_name: e.g. "Degree:Computer Science Engineering"
            trait_vector: Dictionary containing big_five, riasec, emotion_signals, user_interests
            top_k: Number of pathways to return
            alpha: Custom path_score weight (overrides self.alpha)
            beta: Custom affinity_score weight (overrides self.beta)
            
        Returns:
            List of top-k recommended pathways with scores, graph bridge path, transferable skills, skill gap
        """
        w_alpha = alpha if alpha is not None else self.alpha
        w_beta = beta if beta is not None else self.beta

        # Ensure degree_name format
        if not degree_name.startswith("Degree:"):
            degree_name = f"Degree:{degree_name}"

        if degree_name not in self.graph:
            raise ValueError(f"Degree '{degree_name}' not found in Knowledge Graph.")

        # Ensure occupation embeddings are precomputed lazily
        self._precompute_occupation_embeddings()

        # 1. Compute Semantic Affinity Scores
        trait_text = self._trait_vector_to_text(trait_vector)
        student_embedding = self.encoder.encode(trait_text, convert_to_tensor=True)
        cosine_sims = util.cos_sim(student_embedding, self.candidate_embeddings)[0].cpu().numpy()

        # 2. Compute Shortest Path Scores from Degree -> All Nodes in ONE Dijkstra pass
        degree_skills = {
            nbr for nbr in self.graph.neighbors(degree_name)
            if self.graph.nodes[nbr].get("node_type") == "skill"
        }

        try:
            lengths, paths = nx.single_source_dijkstra(
                self.graph, source=degree_name, weight="distance"
            )
        except nx.NetworkXNoPath:
            lengths, paths = {}, {}

        results = []

        for idx, target_uri in enumerate(self.candidate_uris):
            affinity_score = float(cosine_sims[idx])

            if target_uri in lengths:
                path_length = lengths[target_uri]
                shortest_path = paths[target_uri]
                path_score = 1.0 / (1.0 + path_length)
            else:
                path_score = 0.0
                shortest_path = []

            final_score = (w_alpha * path_score) + (w_beta * affinity_score)

            results.append({
                "uri": target_uri,
                "title": self.candidate_occupations[idx],
                "final_score": round(final_score, 4),
                "path_score": round(path_score, 4),
                "affinity_score": round(affinity_score, 4),
                "shortest_path": shortest_path
            })

        # 3. Sort by final_score descending
        results.sort(key=lambda x: x["final_score"], reverse=True)
        top_results = results[:top_k]

        # 4. Extract Bridge Explanations & Skill Gaps for Top-K
        detailed_pathways = []
        for item in top_results:
            target_uri = item["uri"]
            shortest_path = item["shortest_path"]

            # Bridge explanation
            bridge_nodes = []
            for node_id in shortest_path:
                node_data = self.graph.nodes[node_id]
                label = node_data.get("label", node_id)
                ntype = node_data.get("node_type", "")
                bridge_nodes.append(f"{ntype.capitalize()}: {label}")

            bridge_explanation = " -> ".join(bridge_nodes)

            # Target occupation skills
            target_skills = set()
            for nbr in self.graph.neighbors(target_uri):
                if self.graph.nodes[nbr].get("node_type") == "skill":
                    target_skills.add(nbr)

            # Transferable skills & skill gap
            transferable_uris = degree_skills.intersection(target_skills)
            gap_uris = target_skills - degree_skills

            transferable_skills = [
                self.graph.nodes[u].get("label", u) for u in transferable_uris
            ]
            skill_gap = [
                self.graph.nodes[u].get("label", u) for u in gap_uris
            ]

            detailed_pathways.append({
                "title": item["title"],
                "final_score": item["final_score"],
                "path_score": item["path_score"],
                "affinity_score": item["affinity_score"],
                "bridge_explanation": bridge_explanation,
                "transferable_skills": transferable_skills,
                "skill_gap": skill_gap,
                "config": {"alpha": w_alpha, "beta": w_beta}
            })

        return detailed_pathways


def run_mapping_test():
    """Unit test Cross-Domain Mapping Engine with synthetic student profile."""
    print("Testing Cross-Domain Mapping Engine...")
    engine = CrossDomainMappingEngine()

    sample_degree = "Degree:Computer Science Engineering"
    sample_trait_vector = {
        "big_five": {
            "Extraversion": 3.2,
            "Agreeableness": 4.0,
            "Conscientiousness": 4.5,
            "Emotional Stability": 3.8,
            "Intellect/Imagination": 4.8
        },
        "riasec": {
            "Realistic": 15,
            "Investigative": 38,
            "Artistic": 22,
            "Social": 18,
            "Enterprising": 25,
            "Conventional": 30
        },
        "emotion_signals": {
            "curiosity": 0.85,
            "ambition": 0.70
        },
        "user_interests": "Interested in applying machine learning to data analysis and automation."
    }

    pathways = engine.recommend_pathways(sample_degree, sample_trait_vector, top_k=3, alpha=0.6, beta=0.4)

    assert len(pathways) == 3, "Expected top 3 pathways"
    print(f"\nTop 3 Recommended Pathways for {sample_degree}:")
    for idx, p in enumerate(pathways, 1):
        print(f"\n{idx}. {p['title']} (Final Score: {p['final_score']})")
        print(f"   Path Score: {p['path_score']} | Affinity Score: {p['affinity_score']}")
        print(f"   Bridge Explanation: {p['bridge_explanation']}")
        print(f"   Transferable Skills ({len(p['transferable_skills'])}): {p['transferable_skills'][:5]}")
        print(f"   Skill Gap ({len(p['skill_gap'])}): {p['skill_gap'][:5]}")

    print("\nCROSS-DOMAIN MAPPING ENGINE TEST PASSED SUCCESSFULLY! [OK]")


if __name__ == "__main__":
    run_mapping_test()
