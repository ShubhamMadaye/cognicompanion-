"""
CogniCompanion — Live Interactive Confidence Verification
==========================================================
Executes live queries end-to-end through MemoryEngine with seeded patient data.
Prints a formatted summary showing actual calibrated confidence scores and factor breakdowns.
"""

import asyncio
from datetime import date, datetime, time, timedelta, timezone
import os
import sys
import uuid

sys.path.insert(0, os.path.abspath("."))

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.core.database import Base
from app.core.security import hash_password
from app.domains.patients.models import Patient, User, UserRole
from app.domains.memories.models import Memory, Person, MemoryType
from app.domains.timeline.models import (
    Medication,
    MedicationAdherenceLog,
    MedicationFrequency,
    MedicationTiming,
    Event,
    Routine,
    RoutineCategory,
)
from app.domains.games.models import Game, GameSession, DifficultyLevel, GameType
from app.domains.analytics.models import CognitiveMetric, DailyStatistic
from app.ai.memory_engine.memory_engine import MemoryEngine


async def main():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    Session = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with Session() as db:
        # 1. Seed Patient
        user = User(
            id=uuid.uuid4(),
            email="shanti@demo.com",
            full_name="Shanti Devi",
            hashed_password=hash_password("DemoPass123!"),
            role=UserRole.PATIENT,
        )
        db.add(user)
        await db.flush()

        patient = Patient(
            id=uuid.uuid4(),
            user_id=user.id,
            medical_notes="Early Stage Alzheimer's. Loves morning tea and listening to bhajans",
        )
        db.add(patient)
        await db.flush()

        # 2. Seed Medication & Adherence Log for today's morning
        med_donepezil = Medication(
            id=uuid.uuid4(),
            patient_id=patient.id,
            name="Donepezil",
            dosage="5mg",
            frequency=MedicationFrequency.ONCE_DAILY,
            timing=MedicationTiming.BEFORE_BREAKFAST,
            is_active=True,
        )
        db.add(med_donepezil)
        await db.flush()

        med_log = MedicationAdherenceLog(
            id=uuid.uuid4(),
            medication_id=med_donepezil.id,
            log_date=date.today(),
            taken=True,
            taken_at=datetime.now(timezone.utc),
        )
        db.add(med_log)

        # 3. Seed Game Sessions for today
        game_memory = Game(
            id=uuid.uuid4(),
            name="Memory Match",
            game_type=GameType.MEMORY_MATCH,
            min_difficulty=DifficultyLevel.EASY,
            max_difficulty=DifficultyLevel.HARD,
        )
        db.add(game_memory)
        await db.flush()

        sess1 = GameSession(
            id=uuid.uuid4(),
            patient_id=patient.id,
            game_id=game_memory.id,
            score=160,
            accuracy=0.88,
            reaction_time_ms=2100,
            difficulty_level=DifficultyLevel.EASY,
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
        )
        sess2 = GameSession(
            id=uuid.uuid4(),
            patient_id=patient.id,
            game_id=game_memory.id,
            score=190,
            accuracy=0.92,
            reaction_time_ms=1850,
            difficulty_level=DifficultyLevel.MEDIUM,
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
        )
        db.add_all([sess1, sess2])

        # 4. Seed Person (Rahul) & Visit Memory for yesterday
        person_rahul = Person(
            id=uuid.uuid4(),
            patient_id=patient.id,
            name="Rahul Sharma",
            relationship="son",
            description="Your eldest son, lives in Pune and calls every evening.",
        )
        db.add(person_rahul)
        await db.flush()

        mem_visit = Memory(
            id=uuid.uuid4(),
            patient_id=patient.id,
            title="Family Afternoon Visit",
            description="Rahul visited yesterday afternoon. You looked at family photo albums together.",
            memory_type=MemoryType.VISIT,
            event_date=date.today() - timedelta(days=1),
        )
        mem_visit.people.append(person_rahul)
        db.add(mem_visit)

        # 5. Seed Routine for Morning
        walk = Routine(
            id=uuid.uuid4(),
            patient_id=patient.id,
            title="Morning Garden Walk",
            scheduled_time=time(8, 0),
            category=RoutineCategory.MORNING,
            days_of_week=127,
        )
        db.add(walk)
        await db.commit()

        # ── Test Queries ──────────────────────────────────────────────────────────
        queries = [
            ("Did I take my morning medication?", "Case 1: Exact structured medication log"),
            ("How did I perform in today's games?", "Case 2: Exact structured game sessions"),
            ("Who is Rahul?", "Case 3: Exact person profile lookup"),
            ("What should I do this morning?", "Case 4: Daily routine schedule"),
            ("What happened yesterday?", "Case 5: Broad cross-domain temporal recall"),
            ("Did I visit London yesterday?", "Case 6: Claim-level mismatch (Rahul visit vs London visit)"),
            ("Who visited me yesterday?", "Case 7: Grounded incoming visit recall"),
        ]

        pme = MemoryEngine(db)

        print("\n" + "=" * 80)
        print("  COGNICOMPANION PME — LIVE CONFIDENCE CALIBRATION DEMO")
        print("=" * 80 + "\n")

        for query_text, description in queries:
            result = await pme.process_query(
                patient_id=patient.id,
                query=query_text,
                patient_name="Shanti ji",
            )
            pct = round(result.confidence_score * 100, 1)
            print(f"[{description}]")
            print(f"Query:      \"{query_text}\"")
            print(f"Intent:     {result.intent.value}")
            print(f"Confidence: {pct}% -> {result.confidence_level}")
            if result.confidence_factors:
                f = result.confidence_factors
                print(f"Factors:    Strength={int(f.get('evidence_strength',0)*100)}% | Relevance={int(f.get('retrieval_relevance',0)*100)}% | Coverage={int(f.get('query_coverage',0)*100)}% | Temporal={int(f.get('temporal_accuracy',0)*100)}% | EntityMatch={int(f.get('entity_match',0)*100)}% | SubjectMatch={int(f.get('subject_match',0)*100)}%")
            print(f"Sources:    {len(result.sources)} grounded source(s) {[s.title for s in result.sources]}")
            print(f"Answer:     {result.answer[:120]}..." if len(result.answer) > 120 else f"Answer:     {result.answer}")
            print("-" * 80)

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
