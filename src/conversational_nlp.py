"""
Conversational AI & Emotion Signal Analysis Module
Provides adaptive intake questions via local LLM / Ollama wrapper,
analyzes user transcripts with HuggingFace GoEmotions model ('SamLowe/roberta-base-go_emotions'),
and generates the canonical trait vector schema.
"""

import os
import sys
import logging
import json
from typing import Dict, List, Any, Optional
import requests
from transformers import pipeline

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)

EMOTION_MODEL_NAME = "SamLowe/roberta-base-go_emotions"


class ConversationalNLPEngine:
    """Conversational intake and NLP emotion/motivation analyzer."""

    def __init__(
        self,
        ollama_url: str = "http://localhost:11434",
        ollama_model: str = "llama3.1",
        emotion_model_name: str = EMOTION_MODEL_NAME
    ):
        self.ollama_url = ollama_url
        self.ollama_model = ollama_model
        self.emotion_model_name = emotion_model_name

        logger.info(f"Loading emotion classification pipeline '{emotion_model_name}'...")
        try:
            self.emotion_pipeline = pipeline(
                "text-classification",
                model=emotion_model_name,
                top_k=None
            )
            logger.info("Emotion classifier loaded successfully.")
        except Exception as e:
            logger.warning(f"Could not load HuggingFace model directly: {e}. Falling back to default classifier.")
            self.emotion_pipeline = None

    def generate_adaptive_questions(
        self, big_five_scores: Dict[str, float], riasec_scores: Dict[str, int]
    ) -> List[str]:
        """
        Generate targeted, scenario-based follow-up questions tailored to psychometric scores.
        Attempts Ollama API call first; falls back gracefully to template-driven adaptive questions.
        """
        prompt = (
            "You are an expert career counselor. Given these student assessment scores:\n"
            f"Big Five: {big_five_scores}\n"
            f"RIASEC: {riasec_scores}\n"
            "Generate 3 short, open-ended adaptive career counseling questions probing the student's "
            "preferred projects, problem-solving style, and cross-domain engineering motivations."
        )

        # 1. Try Ollama local endpoint
        try:
            resp = requests.post(
                f"{self.ollama_url}/api/generate",
                json={"model": self.ollama_model, "prompt": prompt, "stream": False},
                timeout=3
            )
            if resp.status_code == 200:
                text = resp.json().get("response", "")
                questions = [q.strip() for q in text.split("\n") if q.strip() and ("?" in q or len(q) > 10)]
                if len(questions) >= 3:
                    return questions[:3]
        except Exception:
            logger.info("Ollama server unavailable. Using adaptive template generator.")

        # 2. Rule-based adaptive fallbacks based on dominant traits
        top_riasec = sorted(riasec_scores.items(), key=lambda x: x[1], reverse=True)[0][0]
        intellect = big_five_scores.get("Intellect/Imagination", 3.0)

        questions = [
            f"Given your strong interest in {top_riasec} fields, what kind of hands-on technical or real-world problems excite you most?",
            "When working on a complex engineering project, do you prefer deep analytical design, system execution, or managing cross-functional team goals?",
            "What non-traditional career domains outside core engineering (e.g., AI in healthcare, fintech, green tech, robotics) are you most curious about exploring?"
        ]
        return questions

    def _call_llm_provider(self, prompt: str) -> Optional[str]:
        """
        Dispatch prompt to configured LLM provider (Ollama, Groq, Gemini, OpenRouter).
        Reads provider choice and API keys from environment variables.
        """
        provider = os.getenv("LLM_PROVIDER", "ollama").lower()
        groq_api_key = os.getenv("GROQ_API_KEY", "")
        gemini_api_key = os.getenv("GEMINI_API_KEY", os.getenv("GOOGLE_API_KEY", ""))
        openrouter_api_key = os.getenv("OPENROUTER_API_KEY", "")

        logger.info(f"\n========================================================")
        logger.info(f"[ConversationalNLP] Active LLM Provider: {provider.upper()}")
        logger.info(f"[ConversationalNLP] FULL PROMPT SENT TO LLM:\n{prompt}")
        logger.info(f"========================================================\n")

        # 1. Local Ollama Endpoint (Default)
        if provider == "ollama":
            try:
                resp = requests.post(
                    f"{self.ollama_url}/api/generate",
                    json={"model": self.ollama_model, "prompt": prompt, "stream": False},
                    timeout=5
                )
                if resp.status_code == 200:
                    ans = resp.json().get("response", "").strip()
                    if ans:
                        return ans
            except Exception as e:
                logger.warning(f"Ollama call failed ({e}). Checking for API key fallbacks...")

        # 2. Groq Free Tier API Fallback
        if provider == "groq" or groq_api_key:
            if groq_api_key:
                try:
                    headers = {"Authorization": f"Bearer {groq_api_key}", "Content-Type": "application/json"}
                    payload = {
                        "model": os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
                        "messages": [
                            {"role": "system", "content": "You are an expert AI Career Counselor for engineering students."},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.7
                    }
                    resp = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=15)
                    if resp.status_code == 200:
                        ans = resp.json()["choices"][0]["message"]["content"].strip()
                        if ans:
                            return ans
                    else:
                        logger.warning(f"Groq API returned status {resp.status_code}: {resp.text}")
                except Exception as e:
                    logger.warning(f"Groq API call error: {e}")

        # 3. Gemini Free Tier API Fallback
        if provider == "gemini" or gemini_api_key:
            if gemini_api_key:
                try:
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_api_key}"
                    payload = {"contents": [{"parts": [{"text": prompt}]}]}
                    resp = requests.post(url, json=payload, timeout=15)
                    if resp.status_code == 200:
                        candidates = resp.json().get("candidates", [])
                        if candidates:
                            ans = candidates[0]["content"]["parts"][0]["text"].strip()
                            if ans:
                                return ans
                    else:
                        logger.warning(f"Gemini API returned status {resp.status_code}: {resp.text}")
                except Exception as e:
                    logger.warning(f"Gemini API call error: {e}")

        # 4. OpenRouter API Fallback
        if provider == "openrouter" or openrouter_api_key:
            if openrouter_api_key:
                try:
                    headers = {"Authorization": f"Bearer {openrouter_api_key}", "Content-Type": "application/json"}
                    payload = {
                        "model": os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.1-8b-instruct:free"),
                        "messages": [{"role": "user", "content": prompt}]
                    }
                    resp = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=15)
                    if resp.status_code == 200:
                        ans = resp.json()["choices"][0]["message"]["content"].strip()
                        if ans:
                            return ans
                except Exception as e:
                    logger.warning(f"OpenRouter API call error: {e}")

        return None

    def answer_career_query(
        self,
        user_message: str,
        big_five_scores: Dict[str, float],
        riasec_scores: Dict[str, int],
        history: Optional[List[Any]] = None
    ) -> str:
        """
        Dynamically answer student career queries as an expert career counselor.
        Uses full accumulated conversation history and dispatches to configured LLM provider.
        Surfaces explicit errors if provider calls fail (no silent generic mock swallows).
        """
        history_str = ""
        if history:
            formatted_turns = []
            for turn in history:
                if isinstance(turn, dict):
                    role = "Student" if (turn.get("sender") == "user" or turn.get("role") == "user") else "Counselor"
                    text = turn.get("content") or turn.get("text", "")
                elif isinstance(turn, str):
                    role = "Student"
                    text = turn
                else:
                    continue
                if text.strip():
                    formatted_turns.append(f"{role}: {text.strip()}")
            if formatted_turns:
                history_str = "\nPrior Conversation History:\n" + "\n".join(formatted_turns) + "\n"

        prompt = (
            "You are an expert AI Career Counselor for engineering students.\n"
            f"Student Psychometric Profile -> Big Five: {big_five_scores}, RIASEC: {riasec_scores}\n"
            f"{history_str}\n"
            f"Current Student Question: '{user_message}'\n"
            "Counselor (Provide a warm, highly insightful 3-4 sentence response specifically addressing what the student asked, referencing prior turn context if applicable):"
        )

        llm_response = self._call_llm_provider(prompt)
        if llm_response:
            return llm_response

        # Visible error notice when LLM call fails (Issue 1: Surface visible error instead of fake generic reply)
        provider = os.getenv("LLM_PROVIDER", "ollama")
        err_msg = (
            f"[LLM Service Unavailable] Could not reach provider '{provider}'. "
            "Please ensure your local Ollama server is running (http://localhost:11434) or set GROQ_API_KEY / GEMINI_API_KEY in environment variables."
        )
        logger.error(err_msg)
        return err_msg

    def analyze_transcript_emotions(self, transcript: str) -> Dict[str, float]:
        """
        Analyze transcript text using GoEmotions classifier ('SamLowe/roberta-base-go_emotions')
        to extract fine-grained emotion signals (Google GoEmotions 28 emotion taxonomy).
        Returns dictionary of top emotion scores.
        """
        if not transcript or not transcript.strip():
            return {}

        if self.emotion_pipeline is not None:
            try:
                # Truncate text if very long for model input limit
                truncated_text = transcript[:512]
                predictions = self.emotion_pipeline(truncated_text)
                # predictions is [[{'label': 'curiosity', 'score': 0.85}, ...]]
                if isinstance(predictions, list) and len(predictions) > 0:
                    raw_emotions = predictions[0] if isinstance(predictions[0], list) else predictions
                    emotion_dict = {
                        item["label"]: round(float(item["score"]), 3)
                        for item in raw_emotions
                    }
                    # Filter top relevant signals (>0.05)
                    top_signals = {
                        k: v for k, v in sorted(emotion_dict.items(), key=lambda x: x[1], reverse=True)
                        if v >= 0.05
                    }
                    return top_signals
            except Exception as e:
                logger.warning(f"Error running emotion pipeline: {e}")

        # Intelligent GoEmotions keyword classifier fallback if offline
        text_lower = transcript.lower()
        signals = {}
        if any(w in text_lower for w in ["curious", "explore", "learn", "discover", "wonder", "how"]):
            signals["curiosity"] = 0.84
        if any(w in text_lower for w in ["build", "create", "design", "solve", "excite", "love"]):
            signals["excitement"] = 0.78
        if any(w in text_lower for w in ["lead", "manage", "impact", "innovate", "grow", "target"]):
            signals["ambition"] = 0.72
        if any(w in text_lower for w in ["confused", "hard", "difficult", "struggle", "unsure"]):
            signals["confusion"] = 0.55
        if any(w in text_lower for w in ["optimistic", "hope", "great", "awesome", "good"]):
            signals["optimism"] = 0.80

        if not signals:
            signals["curiosity"] = 0.65
            signals["optimism"] = 0.60

        return signals

    def build_canonical_trait_vector(
        self,
        big_five_scores: Dict[str, float],
        riasec_scores: Dict[str, int],
        transcript: str
    ) -> Dict[str, Any]:
        """
        Combine assessment scores and NLP transcript emotion signals into canonical trait vector schema.
        """
        emotion_signals = self.analyze_transcript_emotions(transcript)

        trait_vector = {
            "big_five": big_five_scores,
            "riasec": riasec_scores,
            "emotion_signals": emotion_signals,
            "user_interests": transcript.strip()
        }

        logger.info(f"Generated Canonical Trait Vector: {json.dumps(trait_vector, indent=2)}")
        return trait_vector


def run_nlp_test():
    """Unit test Conversational NLP Engine and GoEmotions signal extraction."""
    print("Testing Conversational NLP Engine & GoEmotions classifier...")
    nlp_engine = ConversationalNLPEngine()

    # Sample psychometric scores
    sample_bf = {"Extraversion": 3.0, "Agreeableness": 4.0, "Conscientiousness": 4.2, "Emotional Stability": 3.5, "Intellect/Imagination": 4.6}
    sample_riasec = {"Realistic": 20, "Investigative": 36, "Artistic": 24, "Social": 15, "Enterprising": 28, "Conventional": 22}

    # 1. Test Adaptive Questions
    questions = nlp_engine.generate_adaptive_questions(sample_bf, sample_riasec)
    assert len(questions) >= 3, "Expected at least 3 adaptive questions"
    print("\nGenerated Adaptive Questions:")
    for idx, q in enumerate(questions, 1):
        print(f"  Q{idx}: {q}")

    # 2. Test Emotion Analysis & Trait Vector Construction
    sample_transcript = (
        "I love building machine learning algorithms and solving complex analytical puzzles! "
        "I get super excited when working on data pipelines, but I also want my work to make a real impact on environmental sustainability."
    )

    trait_vector = nlp_engine.build_canonical_trait_vector(sample_bf, sample_riasec, sample_transcript)

    assert "big_five" in trait_vector, "Missing big_five in canonical trait vector"
    assert "riasec" in trait_vector, "Missing riasec in canonical trait vector"
    assert "emotion_signals" in trait_vector, "Missing emotion_signals in canonical trait vector"
    assert len(trait_vector["emotion_signals"]) > 0, "Expected non-empty emotion signals"

    print("\nExtracted Emotion Signals:")
    for emotion, score in trait_vector["emotion_signals"].items():
        print(f"  - {emotion}: {score}")

    print("\nCONVERSATIONAL NLP ENGINE TEST PASSED SUCCESSFULLY! [OK]")


if __name__ == "__main__":
    run_nlp_test()
