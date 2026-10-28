"""
CogniCompanion — Personalized Memory Engine (PME)
==================================================
Public exports for intent detection, structured & semantic retrieval,
hybrid ranking, context building, confidence scoring, and response generation.
"""

from app.ai.memory_engine.confidence_engine import ConfidenceEngine
from app.ai.memory_engine.context_builder import ContextBuilder
from app.ai.memory_engine.hybrid_ranker import HybridRanker
from app.ai.memory_engine.intent_detector import PMEIntent, detect_intent
from app.ai.memory_engine.memory_engine import MemoryEngine, PMEResult
from app.ai.memory_engine.response_generator import ResponseGenerator
from app.ai.memory_engine.semantic_retriever import SemanticRetriever
from app.ai.memory_engine.structured_retriever import StructuredRetriever

__all__ = [
    "ConfidenceEngine",
    "ContextBuilder",
    "HybridRanker",
    "MemoryEngine",
    "PMEIntent",
    "PMEResult",
    "ResponseGenerator",
    "SemanticRetriever",
    "StructuredRetriever",
    "detect_intent",
]
