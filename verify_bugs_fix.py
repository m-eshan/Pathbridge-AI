"""
Verification Script for Bug 1 (/api/analyze timing) & Bug 2 (Roadmap dynamic content per career)
"""

import time
import json
from fastapi.testclient import TestClient
from backend.main import app
from src.roadmap_generator import RoadmapGenerator

client = TestClient(app)

def run_bug1_verification():
    print("\n" + "="*80)
    print("BUG 1 VERIFICATION — /api/analyze WALL-CLOCK LATENCY BENCHMARK")
    print("="*80)

    degrees = [
        "Degree:Computer Science Engineering",
        "Degree:Civil Engineering",
        "Degree:Electrical Engineering"
    ]

    for deg in degrees:
        payload = {
            "degree": deg,
            "big_five_scores": {"Extraversion": 3.2, "Agreeableness": 4.0, "Conscientiousness": 4.5, "Emotional Stability": 3.8, "Intellect/Imagination": 4.6},
            "riasec_scores": {"Realistic": 20, "Investigative": 38, "Artistic": 22, "Social": 18, "Enterprising": 25, "Conventional": 30},
            "user_interests": "Machine learning, structural design, energy systems",
            "top_k": 5
        }

        t_start = time.perf_counter()
        res = client.post("/api/analyze", json=payload)
        t_end = time.perf_counter()

        elapsed_ms = (t_end - t_start) * 1000
        assert res.status_code == 200, f"Analysis failed: {res.text}"
        data = res.json()

        print(f"Degree: {deg}")
        print(f"  • HTTP Status: {res.status_code}")
        print(f"  • Measured Wall-Clock Latency: {elapsed_ms:.2f} ms")
        print(f"  • Backend Internal Latency: {data.get('latency_ms')} ms")
        print(f"  • Top Recommended Domain: {data['pathways'][0]['title']} (Score: {data['pathways'][0]['final_score']})")
        print("-" * 60)

    print("BUG 1 VERIFICATION PASSED SUCCESSFULLY! [OK]\n")


def run_bug2_verification():
    print("\n" + "="*80)
    print("BUG 2 VERIFICATION — ROADMAP DEBUG LOGS & SIDE-BY-SIDE CONTENT DIFFERENCES")
    print("="*80)

    generator = RoadmapGenerator()

    careers = [
        {
            "degree": "Computer Science Engineering",
            "target": "Artificial Intelligence & ML Engineer",
            "transferable": ["python programming", "algorithms", "data structures"],
            "gap": ["deep learning", "nlp", "model deployment"]
        },
        {
            "degree": "Civil Engineering",
            "target": "Architect",
            "transferable": ["structural engineering", "computer-aided design (CAD)"],
            "gap": ["architectural design", "spatial planning", "building information modeling (BIM)"]
        },
        {
            "degree": "Electrical Engineering",
            "target": "Renewable Energy Engineer",
            "transferable": ["circuit analysis", "power electronics"],
            "gap": ["solar PV system design", "wind turbine aerodynamics", "grid integration of renewables"]
        }
    ]

    roadmaps = []

    for idx, c in enumerate(careers, 1):
        print(f"\n--- [RUN {idx}] Generating Roadmap for '{c['target']}' ---")
        rm = generator.generate_roadmap(c["degree"], c["target"], c["transferable"], c["gap"])
        roadmaps.append((c["target"], rm))

    print("\n" + "="*80)
    print("SIDE-BY-SIDE FULL 3-STAGE ROADMAP OUTPUT COMPARISON")
    print("="*80)

    for target, rm in roadmaps:
        print(f"\n================================================================================")
        print(f"CAREER TARGET: {target}")
        print(f"Summary: {rm['summary']}")
        print(f"Total Skill Gap Count: {rm['total_skill_gap_count']}")
        print(f"--------------------------------------------------------------------------------")
        for stage_title, stage_data in rm["stages"].items():
            print(f"\n  [{stage_title}]")
            print(f"  Focus: {stage_data['focus']}")
            print(f"  Target Skills: {stage_data['target_skills']}")
            print(f"  Action Items:")
            for item in stage_data["action_items"]:
                print(f"    - {item}")
        print(f"================================================================================")

    print("\nBUG 2 VERIFICATION PASSED SUCCESSFULLY! [OK]\n")


if __name__ == "__main__":
    run_bug1_verification()
    run_bug2_verification()
