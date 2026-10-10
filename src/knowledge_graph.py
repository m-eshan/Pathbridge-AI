"""
Knowledge Graph Construction Module
Builds a NetworkX graph linking Occupations, Skills, and Engineering Degree Curriculums
using ESCO taxonomy and O*NET datasets.
"""

import os
import sys
import logging
import pickle
from typing import Dict, List, Set, Tuple, Optional, Any
import networkx as nx
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.data_loader import DataLoader

logger = logging.getLogger(__name__)


# Standard Engineering Curriculum Skill Mappings (Bridge mappings)
DEFAULT_DEGREE_CURRICULA = {
    "Degree:Computer Science Engineering": [
        "computer programming", "software development", "algorithms", "data structures",
        "database management", "machine learning", "data analysis", "software engineering",
        "web development", "computer networks", "operating systems", "cyber security"
    ],
    "Degree:Artificial Intelligence & Data Science": [
        "machine learning", "deep learning", "python programming", "artificial intelligence",
        "data analysis", "natural language processing", "computer vision", "statistics",
        "data mining", "algorithms", "big data"
    ],
    "Degree:Mechanical Engineering": [
        "thermodynamics", "fluid mechanics", "computer-aided design (CAD)", "mechanical engineering",
        "robotics", "finite element analysis", "manufacturing processes", "materials science",
        "statics", "dynamics", "mechatronics", "solid mechanics"
    ],
    "Degree:Civil Engineering": [
        "structural engineering", "surveying", "geotechnical engineering", "construction management",
        "computer-aided design (CAD)", "fluid mechanics", "environmental engineering",
        "transportation engineering", "building materials", "hydrology"
    ],
    "Degree:Electrical Engineering": [
        "circuit analysis", "signal processing", "embedded systems", "electromagnetics",
        "control systems", "power electronics", "microcontrollers", "electrical engineering",
        "telecommunications", "digital logic"
    ],
    "Degree:Electronics & Communication Engineering": [
        "signal processing", "telecommunications", "microcontrollers", "embedded systems",
        "circuit analysis", "digital electronics", "wireless communication", "vlsis design",
        "optical communication", "antennas"
    ],
    "Degree:Chemical Engineering": [
        "chemical engineering", "process control", "heat transfer", "mass transfer",
        "thermodynamics", "chemical reaction engineering", "fluid dynamics",
        "process safety", "industrial chemistry"
    ],
    "Degree:Aerospace & Aeronautical Engineering": [
        "aerodynamics", "flight mechanics", "propulsion", "avionics",
        "aircraft structural analysis", "fluid dynamics", "orbital mechanics", "thermodynamics"
    ],
    "Degree:Biomedical Engineering": [
        "biomedical engineering", "biomechanics", "medical imaging", "biosensors",
        "biomaterials", "tissue engineering", "signal processing", "human anatomy"
    ],
    "Degree:Mechatronics & Robotics Engineering": [
        "robotics", "mechatronics", "control systems", "microcontrollers",
        "computer-aided design (CAD)", "embedded systems", "automation", "sensors", "kinematics"
    ],
    "Degree:Information Technology": [
        "software development", "database management", "cloud computing", "computer networks",
        "cyber security", "web development", "system administration", "information systems"
    ],
    "Degree:Environmental & Sustainable Engineering": [
        "environmental engineering", "waste management", "water treatment", "sustainable design",
        "climate modeling", "renewable energy", "environmental impact assessment", "hydrology"
    ],
    "Degree:Industrial & Production Engineering": [
        "operations research", "supply chain management", "quality control", "manufacturing processes",
        "ergonomics", "lean manufacturing", "production planning", "industrial engineering"
    ],
    "Degree:Biotechnology Engineering": [
        "molecular biology", "bioprocess engineering", "bioinformatics", "genetics",
        "biochemistry", "microbiology", "cell culture", "fermentation technology"
    ]
}


class CareerKnowledgeGraph:
    """Class to build and manage the multi-domain Career Knowledge Graph."""

    def __init__(self, data_loader: Optional[DataLoader] = None):
        if data_loader is None:
            data_loader = DataLoader()
        self.loader = data_loader
        self.graph = nx.Graph()

        # Quick lookup dictionaries
        self.occupation_nodes = {}
        self.skill_nodes = {}
        self.degree_nodes = {}

    def build_graph(self) -> nx.Graph:
        """Construct the complete Graph from ESCO, O*NET, and Degree Curricula with disk caching."""
        cache_path = os.path.join(self.loader.data_dir, "cache_knowledge_graph.pkl")
        if os.path.exists(cache_path):
            try:
                logger.info("Loading cached Knowledge Graph from disk...")
                with open(cache_path, "rb") as f:
                    data = pickle.load(f)
                    self.graph = data["graph"]
                    self.occupation_nodes = data["occupation_nodes"]
                    self.skill_nodes = data["skill_nodes"]
                    self.degree_nodes = data["degree_nodes"]
                logger.info(f"Fast boot: Loaded cached Graph with {len(self.graph.nodes)} nodes, {len(self.graph.edges)} edges.")
                return self.graph
            except Exception as e:
                logger.warning(f"Cache load notice, rebuilding graph: {e}")

        logger.info("Initializing Knowledge Graph construction...")
        self.graph.clear()

        # 1. Load data
        esco_data = self.loader.load_esco_data()
        onet_data = self.loader.load_onet_data()

        occ_df = esco_data["occupations"]
        skills_df = esco_data["skills"]
        rel_df = esco_data["relations"]

        # 2. Add ESCO Skill Nodes
        logger.info("Adding ESCO skill nodes...")
        for _, row in skills_df.iterrows():
            uri = row["conceptUri"]
            label = str(row["preferredLabel"]).strip()
            desc = str(row["description"]).strip() if pd.notnull(row["description"]) else label
            skill_type = str(row["skillType"]) if pd.notnull(row["skillType"]) else "skill"

            self.graph.add_node(
                uri,
                node_type="skill",
                label=label,
                description=desc,
                skill_type=skill_type,
                source="ESCO"
            )
            self.skill_nodes[label.lower()] = uri

        # 3. Add ESCO Occupation Nodes
        logger.info("Adding ESCO occupation nodes...")
        for _, row in occ_df.iterrows():
            uri = row["conceptUri"]
            label = str(row["preferredLabel"]).strip()
            desc = str(row["description"]).strip() if pd.notnull(row["description"]) else label
            code = str(row["code"]) if pd.notnull(row["code"]) else ""

            self.graph.add_node(
                uri,
                node_type="occupation",
                label=label,
                description=desc,
                code=code,
                source="ESCO"
            )
            self.occupation_nodes[label.lower()] = uri

        # 4. Add ESCO Occupation-Skill Edges
        # Weight essential skills higher than optional
        logger.info("Adding ESCO occupation-skill edges...")
        for _, row in rel_df.iterrows():
            occ_uri = row["occupationUri"]
            skill_uri = row["skillUri"]
            rel_type = row["relationType"]  # essential or optional

            if occ_uri in self.graph and skill_uri in self.graph:
                # Essential skills get weight=1.0, optional get weight=0.5
                # Distance metric = 1.0 / weight
                weight = 1.0 if rel_type == "essential" else 0.5
                distance = 1.0 / weight

                self.graph.add_edge(
                    occ_uri,
                    skill_uri,
                    weight=weight,
                    distance=distance,
                    relation_type=rel_type,
                    source="ESCO"
                )

        # 5. Integrate O*NET Occupations and Essential Skills
        logger.info("Integrating O*NET occupations and skills data...")
        onet_occ_df = onet_data["occupations"]
        onet_skills_df = onet_data["skills"]

        # Map O*NET code -> node ID
        onet_occ_map = {}
        for _, row in onet_occ_df.iterrows():
            code = str(row["O*NET-SOC Code"]).strip()
            title = str(row["Title"]).strip()
            desc = str(row["Description"]).strip()
            node_id = f"ONET_OCC:{code}"

            self.graph.add_node(
                node_id,
                node_type="occupation",
                label=title,
                description=desc,
                code=code,
                source="ONET"
            )
            onet_occ_map[code] = node_id
            self.occupation_nodes[title.lower()] = node_id

        # Add ONET skills as skill nodes and edges
        for _, row in onet_skills_df.iterrows():
            code = str(row["O*NET-SOC Code"]).strip()
            elem_id = str(row["Element ID"]).strip()
            elem_name = str(row["Element Name"]).strip()
            scale_id = str(row["Scale ID"]).strip()
            data_val = float(row["Data Value"])

            # Filter for Importance scale (IM) or Level (LV) above threshold
            if scale_id == "IM" and data_val >= 3.0:
                skill_node_id = f"ONET_SKILL:{elem_id}"

                if skill_node_id not in self.graph:
                    self.graph.add_node(
                        skill_node_id,
                        node_type="skill",
                        label=elem_name,
                        description=elem_name,
                        skill_type="skill",
                        source="ONET"
                    )
                    self.skill_nodes[elem_name.lower()] = skill_node_id

                if code in onet_occ_map:
                    occ_node_id = onet_occ_map[code]
                    weight = data_val / 5.0  # Normalize scale 1-5 to 0.2-1.0
                    distance = 1.0 / weight
                    self.graph.add_edge(
                        occ_node_id,
                        skill_node_id,
                        weight=weight,
                        distance=distance,
                        relation_type="essential",
                        source="ONET"
                    )

        # 6. Add Degree-Curriculum Nodes and Edges
        logger.info("Adding Engineering Degree Curriculum nodes and skill bridge edges...")
        for degree_name, skills_list in DEFAULT_DEGREE_CURRICULA.items():
            self.graph.add_node(
                degree_name,
                node_type="degree",
                label=degree_name.replace("Degree:", ""),
                description=f"Undergraduate Curriculum for {degree_name}",
                source="Curriculum"
            )
            self.degree_nodes[degree_name] = degree_name

            # Connect degree node to matching skills in graph
            matched_count = 0
            for skill_query in skills_list:
                # Find matching skill nodes by string containment or exact match
                matched_skill_uris = self._find_matching_skill_nodes(skill_query)
                for skill_uri in matched_skill_uris:
                    self.graph.add_edge(
                        degree_name,
                        skill_uri,
                        weight=1.0,
                        distance=1.0,
                        relation_type="curriculum_skill",
                        source="CurriculumBridge"
                    )
                    matched_count += 1

            logger.info(f"Connected '{degree_name}' to {matched_count} skill nodes in the graph.")

        # 7. Clean up orphan nodes if any remain
        orphan_nodes = [node for node, degree in self.graph.degree() if degree == 0]
        if orphan_nodes:
            logger.info(f"Removing {len(orphan_nodes)} orphan nodes without connections.")
            self.graph.remove_nodes_from(orphan_nodes)

        logger.info(f"Knowledge Graph construction complete: {self.graph.number_of_nodes()} nodes, {self.graph.number_of_edges()} edges.")

        # Cache built graph to disk for fast subsequent server boots (< 0.2s)
        try:
            cache_path = os.path.join(self.loader.data_dir, "cache_knowledge_graph.pkl")
            with open(cache_path, "wb") as f:
                pickle.dump({
                    "graph": self.graph,
                    "occupation_nodes": self.occupation_nodes,
                    "skill_nodes": self.skill_nodes,
                    "degree_nodes": self.degree_nodes
                }, f)
            logger.info("Successfully serialized Knowledge Graph cache to disk.")
        except Exception as e:
            logger.warning(f"Could not save graph cache to disk: {e}")

        return self.graph

    def _find_matching_skill_nodes(self, query: str) -> List[str]:
        """Helper to find matching skill node URIs for a curriculum skill description."""
        query_lower = query.lower()
        matched = []

        for node_id, data in self.graph.nodes(data=True):
            if data.get("node_type") == "skill":
                label = data.get("label", "").lower()
                if query_lower in label or label in query_lower:
                    matched.append(node_id)

        # Fallback if no exact string match: find closest matching label substring
        if not matched:
            tokens = query_lower.split()
            for node_id, data in self.graph.nodes(data=True):
                if data.get("node_type") == "skill":
                    label = data.get("label", "").lower()
                    if any(tok in label for tok in tokens if len(tok) > 4):
                        matched.append(node_id)
                        if len(matched) >= 3:
                            break

        return matched

    def sanity_check(self) -> Dict[str, Any]:
        """Perform sanity checks on the constructed graph."""
        total_nodes = self.graph.number_of_nodes()
        total_edges = self.graph.number_of_edges()

        # Node breakdown
        node_types = {}
        for _, data in self.graph.nodes(data=True):
            ntype = data.get("node_type", "unknown")
            node_types[ntype] = node_types.get(ntype, 0) + 1

        # Check for orphan nodes
        orphans = [node for node, d in self.graph.degree() if d == 0]

        # Check that occupations have at least one skill edge
        occ_without_skills = []
        for node, data in self.graph.nodes(data=True):
            if data.get("node_type") == "occupation":
                neighbors = list(self.graph.neighbors(node))
                skill_neighbors = [
                    nbr for nbr in neighbors
                    if self.graph.nodes[nbr].get("node_type") == "skill"
                ]
                if not skill_neighbors:
                    occ_without_skills.append(node)

        results = {
            "total_nodes": total_nodes,
            "total_edges": total_edges,
            "node_types": node_types,
            "orphan_count": len(orphans),
            "occupations_without_skills_count": len(occ_without_skills),
            "is_valid": len(orphans) == 0 and len(occ_without_skills) == 0
        }

        logger.info(f"Graph Sanity Check Results: {results}")
        return results


def run_graph_test():
    """Run Knowledge Graph construction and verify sanity check assertions."""
    print("Building and validating Knowledge Graph...")
    kg = CareerKnowledgeGraph()
    g = kg.build_graph()
    stats = kg.sanity_check()

    assert stats["orphan_count"] == 0, f"Found {stats['orphan_count']} orphan nodes!"
    assert stats["occupations_without_skills_count"] == 0, f"Found {stats['occupations_without_skills_count']} occupations without skills!"
    assert stats["node_types"]["degree"] == len(DEFAULT_DEGREE_CURRICULA), "Missing degree nodes!"

    print("\n--- KNOWLEDGE GRAPH SUMMARY ---")
    print(f"Total Nodes: {stats['total_nodes']}")
    print(f"Total Edges: {stats['total_edges']}")
    print(f"Node Types Breakdown: {stats['node_types']}")
    print(f"Orphans: {stats['orphan_count']}")
    print(f"Occupations without skills: {stats['occupations_without_skills_count']}")
    print("KNOWLEDGE GRAPH SANITY CHECKS PASSED SUCCESSFULLY! [OK]")


if __name__ == "__main__":
    run_graph_test()
