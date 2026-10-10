"""
Test Script for Resume Upload & Skill Matching Endpoint
"""

import io
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_resume_upload():
    print("Testing Resume Upload Endpoint...")

    # Sample resume text containing engineering skills
    resume_content = (
        "John Doe - Computer Science Engineering Student\n"
        "Skills: Python programming, software development, data analysis, algorithms, machine learning, CAD software."
    )

    file_bytes = io.BytesIO(resume_content.encode("utf-8"))

    response = client.post(
        "/api/resume/upload",
        files={"file": ("resume_sample.txt", file_bytes, "text/plain")}
    )

    assert response.status_code == 200, f"Upload failed: {response.text}"
    data = response.json()

    print("Upload Response:", data)
    assert "matched_skills" in data, "Missing matched_skills in response"
    assert len(data["matched_skills"]) > 0, "Expected at least 1 matched ESCO skill"

    print("\nMatched ESCO Skills from Resume:")
    for skill in data["matched_skills"]:
        print(f"  - {skill['label']}")

    print("\nRESUME UPLOAD ENDPOINT PASSED VERIFICATION! [OK]")

if __name__ == "__main__":
    test_resume_upload()
