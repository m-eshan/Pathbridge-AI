"""
Unit Test Script for FastAPI Backend Endpoints
Verifies that all API routes execute cleanly and connect to the underlying src/ modules.
"""

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_api_routes():
    print("Testing FastAPI Backend Endpoints...")

    # 1. Health check
    res = client.get("/api/health")
    assert res.status_code == 200, f"Health check failed: {res.text}"
    print("Health check response:", res.json())

    # 2. Get Assessment Items
    res = client.get("/api/assessment/items")
    assert res.status_code == 200
    data = res.json()
    assert len(data["big_five_items"]) == 20, f"Expected 20 Mini-IPIP items, got {len(data['big_five_items'])}"
    assert len(data["riasec_items"]) == 30, f"Expected 30 Mini-IP items, got {len(data['riasec_items'])}"
    print(f"Loaded {len(data['big_five_items'])} Big Five and {len(data['riasec_items'])} RIASEC items via API.")

    # 3. Submit Assessment
    bf_resp = {item["item_id"]: 4 for item in data["big_five_items"]}
    riasec_resp = {item["item_id"]: 3 for item in data["riasec_items"]}
    res = client.post("/api/assessment/submit", json={
        "big_five_responses": bf_resp,
        "riasec_responses": riasec_resp
    })
    assert res.status_code == 200
    sub_data = res.json()
    session_id = sub_data["session_id"]
    assert session_id, "Missing session_id"
    print(f"Submitted assessment via API, session_id: {session_id}")

    # 4. Conversation Message
    res = client.post("/api/conversation/message", json={
        "session_id": session_id,
        "message": "I love building artificial intelligence models and data pipelines!"
    })
    assert res.status_code == 200
    conv_data = res.json()
    assert "reply" in conv_data
    print("Conversation API response:", conv_data["reply"])

    # 5. Analyze Pathways
    res = client.post("/api/analyze", json={
        "degree": "Degree:Computer Science Engineering",
        "big_five_scores": sub_data["big_five_scores"],
        "riasec_scores": sub_data["riasec_scores"],
        "user_interests": "Machine Learning and Artificial Intelligence",
        "top_k": 3
    })
    assert res.status_code == 200
    ana_data = res.json()
    assert len(ana_data["pathways"]) == 3
    top_target = ana_data["pathways"][0]
    print(f"Top API Recommendation: {top_target['title']} (Score: {top_target['final_score']})")

    # 6. Skill Graph Subgraph
    target_uri = top_target["bridge_explanation"].split(" -> ")[-1].replace("Occupation: ", "")
    res = client.get(f"/api/skill-graph?path_id={target_uri}&degree=Computer Science Engineering")
    assert res.status_code == 200
    graph_data = res.json()
    assert "nodes" in graph_data and "links" in graph_data
    print(f"Extracted Skill Graph Subgraph: {len(graph_data['nodes'])} nodes, {len(graph_data['links'])} links.")

    # 7. Roadmap
    res = client.post("/api/roadmap", json={
        "degree": "Computer Science Engineering",
        "target_domain": top_target["title"],
        "transferable_skills": top_target["transferable_skills"],
        "skill_gap": top_target["skill_gap"]
    })
    assert res.status_code == 200
    road_data = res.json()
    assert "stages" in road_data
    print(f"Roadmap generated for target '{road_data['target_domain']}' across {len(road_data['stages'])} stages.")

    print("\nALL FASTAPI BACKEND ENDPOINTS PASSED VERIFICATION! [OK]")

if __name__ == "__main__":
    test_api_routes()
