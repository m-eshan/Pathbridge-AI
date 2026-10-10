# Technical Design Document

**Project:** AI-Powered Personalized Career Guidance System
**Companion to:** PRD.md, Tech_Stack.md

---

## 1. System Architecture Overview

The system is organized into three functional layers:

1. **Data Collection** — psychometric assessment + conversational AI intake
2. **Processing** — NLP/scoring engine + cross-domain mapping engine (knowledge graph)
3. **Output** — recommendation engine + personalized roadmap

```
Student profile input
      │
      ▼
Psychological assessment (Big Five + RIASEC)
      │
      ▼
Conversational AI intake (adaptive follow-up)
      │
      ▼
NLP & scoring engine  ──► Trait vector
      │
      ▼
Cross-domain mapping engine (skill knowledge graph)
      │
      ▼
Recommendation engine (ranked, explained pathways)
      │
      ▼
Personalized roadmap generator
```

## 2. Component Design

### 2.1 Psychometric Assessment Module
- **Input:** none (first stage)
- **Output:** raw item responses (CSV/JSON)
- **Data:** `ipip_bigfive_50item.csv` (50 items, 5 traits), `onet_riasec_60item.csv` (60 items, 6 RIASEC categories)
- **Scoring logic:**
  - Big Five: average of 10 items per trait; reverse-score `-` keyed items as `6 - response`
  - RIASEC: sum of 10 items per category (0–10 checkbox or 0–40 five-point scale)

### 2.2 Conversational AI Intake Module
- **Input:** psychometric scores (used to steer adaptive follow-up questions)
- **Output:** free-text transcript
- **Design:** LLM-driven, prompted to ask scenario-based follow-ups probing motivation, decision-making style, and interests not fully captured by the static assessment
- **Constraint:** must work with a free-tier or local LLM (see Tech_Stack.md)

### 2.3 NLP & Scoring Engine
- **Input:** transcript + psychometric scores
- **Output:** structured trait vector, e.g.:
  ```json
  {
    "big_five": {"extraversion": 3.4, "agreeableness": 4.1, "conscientiousness": 3.8, "emotional_stability": 2.9, "intellect": 4.3},
    "riasec": {"R": 12, "I": 34, "A": 28, "S": 18, "E": 9, "C": 15},
    "emotion_signals": {"curiosity": 0.72, "confidence": 0.55, ...}
  }
  ```
- **Techniques:**
  - Rule-based scoring (assessment layer, deterministic)
  - Pretrained sentence-embedding model for semantic signal from open text
  - Pretrained emotion classifier (GoEmotions-tuned model) for motivation/tone signal from transcript

### 2.4 Knowledge Graph (Cross-Domain Mapping Engine)
- **Nodes:** skills, occupations, degree-curriculum concepts (from O*NET, ESCO, and curriculum mapping)
- **Edges:** weighted transferability links (`occupationSkillRelations` from ESCO; O*NET skill-importance ratings)
- **Validation data:** JobHop v2 (real observed occupational transitions, ESCO-coded) used to sanity-check which domain pairs the graph scores as highly transferable against real-world transition frequency

**Algorithm (see prior conversation for full pseudocode):**
```
1. Build graph G from O*NET + ESCO
2. Map trait_vector → skill-affinity vector S (via embedding similarity)
3. For each candidate domain C:
     path_score(D, C)   = weighted shortest-path traversal from degree D to C
     affinity_score(C)  = cosine_similarity(S, skill_profile(C))
     final_score(C)     = α · path_score + β · affinity_score
4. Rank domains by final_score
5. Extract bridge explanation = actual graph path
6. Compute skill_gap(C) = skills(C) − skills(D)
```

### 2.5 Recommendation Engine
- **Input:** ranked domain list + bridge explanations + skill gaps
- **Output:** top-k domains, each with: score, explanation path, transferable skills, skill gap
- **Explainability requirement:** every output field must trace back to a specific graph path or assessment signal — no unexplained scores surfaced to the student

### 2.6 Roadmap Generator
- **Input:** top recommended domain + skill gap
- **Output:** staged plan (immediate / 6-month / post-graduation), mapped to courses/certifications where determinable from ESCO qualification links

## 3. Data Models

**Trait Vector (canonical schema)**
| Field | Type | Source |
|---|---|---|
| big_five.* | float (1–5) | Assessment module |
| riasec.* | int (0–40) | Assessment module |
| emotion_signals.* | float (0–1) | NLP module |

**Graph Edge (transferability)**
| Field | Type | Source |
|---|---|---|
| source_node | string (skill/occupation URI) | ESCO/O*NET |
| target_node | string | ESCO/O*NET |
| weight | float | Relation type (essential=1.0, optional=0.5) |
| relation_type | enum | ESCO occupationSkillRelations |

## 4. Non-Functional Design Notes

- **Modularity:** each component (2.1–2.6) should be independently testable with mock inputs before full integration.
- **Reproducibility:** graph built from versioned, dated taxonomy snapshots (O*NET 30.3, ESCO latest classification) — record version numbers in the paper's methodology.
- **Explainability by design:** the recommendation engine must never return a score without an accompanying path/signal trace (architectural constraint, not just a feature).

## 5. Evaluation Design (summary — see Methodology)

1. Instrument validity check (scoring engine vs. published norms)
2. Expert panel comparison (career counselors vs. system output, same profiles)
3. JobHop-based transferability validation (do high-scored domain pairs match real transition frequency)
4. (Future work) Real student pilot study

## 6. Open Design Decisions

- α/β weighting between path-score and affinity-score — treat as a tunable hyperparameter, document sensitivity in evaluation.
- Whether curriculum-to-skill mapping is manually curated (from institution syllabi) or derived from ABET-style outcome frameworks — affects graph completeness.
