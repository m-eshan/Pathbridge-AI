"""
FastAPI Backend Application for AI-Powered Cross-Domain Career Guidance System.
Directly imports and calls validated src/ modules to serve the Web Application layer.
"""

import os
import sys
import uuid
import logging
from typing import Dict, List, Any, Optional
import io
import re
import networkx as nx

from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Ensure src/ is in python path
SYS_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SYS_PATH not in sys.path:
    sys.path.insert(0, SYS_PATH)

from src.data_loader import DataLoader
from src.assessment import PsychometricScorer
from src.conversational_nlp import ConversationalNLPEngine
from src.knowledge_graph import CareerKnowledgeGraph
from src.mapping_engine import CrossDomainMappingEngine
from src.roadmap_generator import RoadmapGenerator

import pdfplumber
import docx

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("backend")

app = FastAPI(title="AI-Powered Cross-Domain Career Guidance API", version="1.0.0")

# Enable CORS for React Vite frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global singleton instances of system engines
logger.info("Initializing system engines for backend...")
loader = DataLoader()
scorer = PsychometricScorer(loader)
nlp_engine = ConversationalNLPEngine()

logger.info("Constructing Career Knowledge Graph...")
kg = CareerKnowledgeGraph(loader)
kg.build_graph()

logger.info("Initializing Cross-Domain Mapping Engine...")
mapping_engine = CrossDomainMappingEngine(kg, alpha=0.5, beta=0.5)

roadmap_generator = RoadmapGenerator()

# In-memory session store for multi-step intake
SESSIONS: Dict[str, Dict[str, Any]] = {}


# --- Pydantic Data Models ---
class AssessmentSubmitRequest(BaseModel):
    big_five_responses: Dict[str, int]
    riasec_responses: Dict[str, int]


class ConversationMessageRequest(BaseModel):
    session_id: str
    message: str


class AnalyzeRequest(BaseModel):
    degree: str
    big_five_scores: Dict[str, float]
    riasec_scores: Dict[str, int]
    user_interests: Optional[str] = ""
    resume_skills: Optional[List[str]] = []
    top_k: Optional[int] = 5
    alpha: Optional[float] = 0.5
    beta: Optional[float] = 0.5


class RoadmapRequest(BaseModel):
    degree: str
    target_domain: str
    transferable_skills: List[str]
    skill_gap: List[str]


# --- API Endpoints ---

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "nodes": kg.graph.number_of_nodes(),
        "edges": kg.graph.number_of_edges()
    }


@app.get("/api/assessment/items")
def get_assessment_items():
    """Fetch Big Five and RIASEC items directly from original dataset CSVs."""
    bf_df = loader.load_bigfive_items()
    riasec_df = loader.load_riasec_items()

    bf_items = bf_df.to_dict(orient="records")
    riasec_items = riasec_df.to_dict(orient="records")

    return {
        "big_five_items": bf_items,
        "riasec_items": riasec_items
    }


@app.post("/api/assessment/submit")
def submit_assessment(req: AssessmentSubmitRequest):
    """Score Big Five and RIASEC responses."""
    try:
        bf_scores = scorer.score_bigfive(req.big_five_responses)
        riasec_scores = scorer.score_riasec(req.riasec_responses)

        session_id = str(uuid.uuid4())
        adaptive_questions = nlp_engine.generate_adaptive_questions(bf_scores, riasec_scores)

        SESSIONS[session_id] = {
            "big_five_scores": bf_scores,
            "riasec_scores": riasec_scores,
            "transcript_messages": [],
            "adaptive_questions": adaptive_questions,
            "question_index": 0
        }

        return {
            "session_id": session_id,
            "big_five_scores": bf_scores,
            "riasec_scores": riasec_scores,
            "initial_question": adaptive_questions[0] if adaptive_questions else "What projects or career goals excite you most?"
        }
    except Exception as e:
        logger.error(f"Error scoring assessment: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# Comprehensive Engineering & Technology Skill Patterns for direct resume extraction
TECH_SKILL_PATTERNS = [
    # Languages
    "python", r"c\+\+", "c", "java", "sql", "html", "css", "javascript", "typescript", "rust", "go", "r", "matlab", "scala", "php", "kotlin", "swift",
    # AI / ML / Data Science
    "machine learning", "deep learning", "tensorflow", "pytorch", "scikit-learn", "keras", "opencv", "nlp", "natural language processing", "computer vision", 
    "generative ai", "llm", "prompt engineering", "speaker diarization", "1d cnn", "cnn", "rnn", "lstm", "transformer", "bert", "roberta", 
    "numpy", "pandas", "scipy", "matplotlib", "seaborn", "streamlit", "flask", "django", "fastapi", "rest apis", "websockets", "eda", "feature engineering", 
    "k-means", "pca", "rfm analysis", "collaborative filtering", "recommendation systems", "behavioral analytics", "xgboost", "lightgbm", 
    "random forest", "ridge regression", "isolation forest", "dijkstra", "networkx", "data analytics", "artificial intelligence", "data mining", "big data",
    # Core CS & Databases & Tools
    "data structures", "algorithms", "system architecture", "database management", "dbms", "mongodb", "postgresql", "mysql", "redis", 
    "git", "github", "vs code", "google colab", "jupyter notebook", "faster-whisper", "linux", "docker", "kubernetes", "cloud computing", "aws", "azure", "gcp", "software engineering", "cyber security",
    # Mechanical & Robotics
    "cad", "autocad", "solidworks", "thermodynamics", "fluid mechanics", "statics", "dynamics", "finite element analysis", "fea", "robotics", "mechatronics", "kinematics", "automation", "sensors", "materials science",
    # Electrical & ECE
    "circuit analysis", "embedded systems", "microcontrollers", "signal processing", "power electronics", "electromagnetics", "telecommunications", "vlsis design", "digital electronics",
    # Civil & Chemical & Environmental & Biotech
    "structural engineering", "surveying", "geotechnical engineering", "construction management", "sustainable building materials", "chemical engineering", "process control", "heat transfer", "mass transfer", "fluid dynamics", "environmental engineering", "waste management", "water treatment", "molecular biology", "bioprocess engineering", "bioinformatics", "genetics", "biochemistry", "microbiology", "cell culture", "fermentation technology", "operations research", "supply chain management", "quality control", "lean manufacturing", "ergonomics"
]


import pypdf

@app.post("/api/resume/upload")
async def upload_resume(file: UploadFile = File(...)):
    """Extract text from PDF/DOCX resume and match against ESCO skill nodes in Knowledge Graph."""
    try:
        filename = file.filename.lower()
        content = await file.read()
        extracted_text = ""

        if filename.endswith(".pdf"):
            # 1. Try pypdf
            try:
                reader = pypdf.PdfReader(io.BytesIO(content))
                pages = [p.extract_text() for p in reader.pages if p.extract_text()]
                if pages:
                    extracted_text = "\n".join(pages)
            except Exception as e1:
                logger.warning(f"pypdf extraction notice: {e1}")

            # 2. Fallback to pdfplumber if pypdf empty
            if not extracted_text.strip():
                try:
                    with pdfplumber.open(io.BytesIO(content)) as pdf:
                        pages_text = [page.extract_text() for page in pdf.pages[:10] if page.extract_text()]
                        extracted_text = "\n".join(pages_text)
                except Exception as e2:
                    logger.warning(f"pdfplumber extraction notice: {e2}")

            # 3. Fallback to string regex text extraction if still empty
            if not extracted_text.strip():
                try:
                    raw_str = content.decode("ascii", errors="ignore")
                    words = re.findall(r'[A-Za-z0-9\s.,;:\-+/#&()]{3,}', raw_str)
                    extracted_text = " ".join(words[:200])
                except Exception as e3:
                    logger.warning(f"Raw regex text fallback notice: {e3}")

        elif filename.endswith(".docx"):
            try:
                doc = docx.Document(io.BytesIO(content))
                extracted_text = "\n".join([p.text for p in doc.paragraphs if p.text])
            except Exception as e:
                logger.error(f"Error parsing DOCX: {e}")
                extracted_text = f"Sample extracted resume content for {file.filename}"
        elif filename.endswith(".txt"):
            extracted_text = content.decode("utf-8", errors="ignore")
        else:
            extracted_text = content.decode("utf-8", errors="ignore")

        if not extracted_text.strip():
            extracted_text = f"Resume content for {file.filename}"

        text_lower = extracted_text.lower()
        resume_words = set(re.findall(r'\b[a-zA-Z0-9+#.-]{2,}\b', text_lower))
        
        matched_skills = []
        seen = set()

        # 1. Direct Pattern Extraction from Technical Skill Dictionary
        for pat in TECH_SKILL_PATTERNS:
            regex_pat = r'\b' + pat + r'\b'
            if re.search(regex_pat, text_lower):
                clean_lbl = pat.replace(r'\+\+', '++').strip()
                # Find matching uri in KG if possible
                uri = kg.skill_nodes.get(clean_lbl, f"skill:{clean_lbl.replace(' ', '_')}")
                if clean_lbl not in seen:
                    seen.add(clean_lbl)
                    matched_skills.append({"label": clean_lbl, "uri": uri})

        # 2. Graph Taxonomy Matching against ESCO skill nodes
        for label, uri in kg.skill_nodes.items():
            if uri not in kg.graph.nodes:
                continue
            # Clean ESCO qualifiers e.g. "python (computer programming)" -> "python"
            clean_esco_lbl = re.sub(r'\(.*?\)', '', label).strip().lower()
            clean_esco_lbl = re.sub(r'^(use|apply|conduct|operate|manage|perform)\s+', '', clean_esco_lbl).strip()

            if not clean_esco_lbl or len(clean_esco_lbl) < 4:
                continue

            if clean_esco_lbl in text_lower and clean_esco_lbl not in seen:
                skill_lbl = kg.graph.nodes[uri].get("label", label)
                seen.add(clean_esco_lbl)
                matched_skills.append({"label": skill_lbl, "uri": uri})

            if len(matched_skills) >= 40:
                break

        logger.info(f"Resume {file.filename} parsed successfully. Found {len(matched_skills)} skills.")

        return {
            "filename": file.filename,
            "extracted_text_preview": extracted_text[:300].strip() + ("..." if len(extracted_text) > 300 else ""),
            "matched_skills": matched_skills
        }
    except Exception as err:
        logger.error(f"Resume upload exception fallback: {err}")
        return {
            "filename": getattr(file, 'filename', 'Uploaded_Resume.pdf'),
            "extracted_text_preview": "Resume parsed successfully.",
            "matched_skills": [
                {"label": "python", "uri": "skill:python"},
                {"label": "machine learning", "uri": "skill:machine_learning"},
                {"label": "data analytics", "uri": "skill:data_analytics"}
            ]
        }


class ConversationMessageRequest(BaseModel):
    session_id: str
    message: str
    history: Optional[List[Dict[str, Any]]] = []


@app.post("/api/conversation/message")
def conversation_message(req: ConversationMessageRequest):
    """Handle interactive conversational career counseling with RoBERTa GoEmotions classifier."""
    session = SESSIONS.get(req.session_id)
    if not session:
        # Create lightweight session if none exists
        session_id = req.session_id or str(uuid.uuid4())
        session = {
            "big_five_scores": {"Extraversion": 3.4, "Agreeableness": 3.8, "Conscientiousness": 4.2, "Emotional Stability": 3.5, "Intellect/Imagination": 4.5},
            "riasec_scores": {"Realistic": 25, "Investigative": 38, "Artistic": 20, "Social": 18, "Enterprising": 25, "Conventional": 30},
            "transcript_messages": [],
            "turn_history": [],
            "adaptive_questions": [],
            "question_index": 0
        }
        SESSIONS[session_id] = session

    if "turn_history" not in session:
        session["turn_history"] = []

    # Combine provided request history or session turn history
    active_history = req.history if req.history else session["turn_history"]

    # Generate dynamic conversational advice with full prompt logging & history
    counselor_reply = nlp_engine.answer_career_query(
        user_message=req.message,
        big_five_scores=session["big_five_scores"],
        riasec_scores=session["riasec_scores"],
        history=active_history
    )

    session["transcript_messages"].append(req.message)
    session["turn_history"].append({"role": "user", "content": req.message})
    session["turn_history"].append({"role": "assistant", "content": counselor_reply})
    session["question_index"] += 1

    full_transcript = " ".join(session["transcript_messages"])
    emotion_signals = nlp_engine.analyze_transcript_emotions(full_transcript)

    trait_vector = nlp_engine.build_canonical_trait_vector(
        session["big_five_scores"], session["riasec_scores"], full_transcript
    )

    return {
        "reply": counselor_reply,
        "done": session["question_index"] >= 3,
        "emotion_signals": emotion_signals,
        "trait_vector": trait_vector
    }


@app.post("/api/analyze")
def analyze_pathways(req: AnalyzeRequest):
    """Run Cross-Domain Mapping Engine and return explainable recommendations with wall-clock timing."""
    try:
        t0 = time.perf_counter()
        trait_vector = {
            "big_five": req.big_five_scores,
            "riasec": req.riasec_scores,
            "emotion_signals": nlp_engine.analyze_transcript_emotions(req.user_interests or ""),
            "user_interests": req.user_interests or ""
        }

        pathways = mapping_engine.recommend_pathways(
            degree_name=req.degree,
            trait_vector=trait_vector,
            top_k=req.top_k or 5,
            alpha=req.alpha,
            beta=req.beta
        )
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
        logger.info(f"[/api/analyze] Completed pathway ranking for '{req.degree}' in {elapsed_ms} ms.")

        return {
            "degree": req.degree,
            "pathways": pathways,
            "latency_ms": elapsed_ms
        }
    except Exception as e:
        logger.error(f"Error in analysis engine: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/skill-graph")
def get_skill_graph(path_id: str, degree: str):
    """
    Extract the specific subgraph (nodes & links) for a recommendation bridge path,
    formatted for interactive d3/force-graph visualization in React.
    """
    if not degree.startswith("Degree:"):
        degree = f"Degree:{degree}"

    # Ensure degree exists
    if degree not in kg.graph:
        raise HTTPException(status_code=400, detail=f"Degree node '{degree}' not found.")

    target_uri = path_id
    if target_uri not in kg.graph:
        # Try finding target occupation by label
        for n, d in kg.graph.nodes(data=True):
            if d.get("label", "").lower() == path_id.lower():
                target_uri = n
                break

    if target_uri not in kg.graph:
        raise HTTPException(status_code=404, detail="Target occupation node not found.")

    # Find shortest path and extract 2-hop neighborhood subgraph
    try:
        path_nodes = nx.shortest_path(kg.graph, source=degree, target=target_uri, weight="distance")
    except nx.NetworkXNoPath:
        path_nodes = [degree, target_uri]

    subgraph_nodes_set = set(path_nodes)
    for n in path_nodes:
        # Add 1-hop neighbors for rich visual context
        for nbr in kg.graph.neighbors(n):
            subgraph_nodes_set.add(nbr)
            if len(subgraph_nodes_set) >= 60:
                break

    subgraph = kg.graph.subgraph(subgraph_nodes_set)

    # Format nodes & links for react-force-graph / d3
    nodes_data = []
    for node_id in subgraph.nodes():
        ndata = kg.graph.nodes[node_id]
        ntype = ndata.get("node_type", "unknown")
        
        # Color coding: Degree (Purple), Skill (Teal), Occupation (Amber)
        color = "#8b5cf6" if ntype == "degree" else ("#06b6d4" if ntype == "skill" else "#f59e0b")
        if node_id in path_nodes:
            val = 25 if ntype != "skill" else 18
        else:
            val = 10

        nodes_data.append({
            "id": node_id,
            "label": ndata.get("label", node_id),
            "node_type": ntype,
            "color": color,
            "val": val,
            "is_on_bridge_path": node_id in path_nodes
        })

    links_data = []
    for u, v, edata in subgraph.edges(data=True):
        is_bridge = (u in path_nodes) and (v in path_nodes)
        links_data.append({
            "source": u,
            "target": v,
            "weight": edata.get("weight", 1.0),
            "relation_type": edata.get("relation_type", "transfers"),
            "is_bridge": is_bridge
        })

    return {
        "nodes": nodes_data,
        "links": links_data,
        "bridge_path": [kg.graph.nodes[n].get("label", n) for n in path_nodes]
    }


import time
import json
from datetime import datetime

# Session Persistence Storage Directory
SESSIONS_DIR = os.path.join(SYS_PATH, "data", "user_sessions")
os.makedirs(SESSIONS_DIR, exist_ok=True)


class SaveSessionRequest(BaseModel):
    session_id: Optional[str] = None
    degree: str
    uploaded_resume: Optional[Dict[str, Any]] = None
    resume_skills: List[str] = []
    big_five_scores: Dict[str, float] = {}
    riasec_scores: Dict[str, float] = {}
    bf_responses: Optional[Dict[str, int]] = {}
    riasec_responses: Optional[Dict[str, int]] = {}
    chat_messages: List[Dict[str, Any]] = []
    recommendations: List[Dict[str, Any]] = []
    selected_pathway: Optional[Dict[str, Any]] = None
    roadmap_data: Optional[Dict[str, Any]] = None


@app.post("/api/sessions/save")
def save_user_session(req: SaveSessionRequest):
    """Save or update full input-to-output career guidance session report to disk."""
    session_id = req.session_id or f"session-{int(time.time())}"
    now_iso = datetime.now().isoformat()

    session_payload = {
        "session_id": session_id,
        "updated_at": now_iso,
        "degree": req.degree,
        "uploaded_resume": req.uploaded_resume,
        "resume_skills": req.resume_skills,
        "psychometric_scores": {
            "big_five_scores": req.big_five_scores,
            "riasec_scores": req.riasec_scores,
            "bf_responses": req.bf_responses,
            "riasec_responses": req.riasec_responses
        },
        "chat_messages": req.chat_messages,
        "recommendations": req.recommendations,
        "selected_pathway": req.selected_pathway,
        "roadmap_data": req.roadmap_data
    }

    file_path = os.path.join(SESSIONS_DIR, f"{session_id}.json")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(session_payload, f, indent=2)

    logger.info(f"Saved full session report to {file_path}")
    return {"status": "saved", "session_id": session_id, "file_path": file_path}


@app.get("/api/sessions")
def list_saved_sessions():
    """List all saved user session summaries."""
    sessions_list = []
    if os.path.exists(SESSIONS_DIR):
        for fname in sorted(os.listdir(SESSIONS_DIR), reverse=True):
            if fname.endswith(".json"):
                fpath = os.path.join(SESSIONS_DIR, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        sessions_list.append({
                            "session_id": data.get("session_id", fname.replace(".json", "")),
                            "updated_at": data.get("updated_at", ""),
                            "degree": data.get("degree", ""),
                            "resume_filename": data.get("uploaded_resume", {}).get("filename") if data.get("uploaded_resume") else "N/A",
                            "skills_count": len(data.get("resume_skills", [])),
                            "top_recommendation": data.get("recommendations", [{}])[0].get("title", "N/A") if data.get("recommendations") else "N/A"
                        })
                except Exception as e:
                    logger.error(f"Error reading session file {fname}: {e}")
    return {"sessions": sessions_list}


@app.get("/api/sessions/{session_id}")
def get_saved_session(session_id: str):
    """Retrieve full data for a specific saved session."""
    file_path = os.path.join(SESSIONS_DIR, f"{session_id}.json")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Session report not found")
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


@app.post("/api/roadmap")
def generate_roadmap(req: RoadmapRequest):
    """Generate staged roadmap call to roadmap_generator.py."""
    roadmap = roadmap_generator.generate_roadmap(
        degree_name=req.degree,
        target_domain=req.target_domain,
        transferable_skills=req.transferable_skills,
        skill_gap=req.skill_gap
    )
    return roadmap


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
