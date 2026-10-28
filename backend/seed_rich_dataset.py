"""
CogniCompanion — Comprehensive PostgreSQL Database Seeder
==========================================================
Populates realistic, clinically detailed datasets into PostgreSQL:
  - Patients: Shanti Devi (MCI/Alzheimer's), Rameshwar Nath (Vascular Dementia), Subhashini Roy
  - Caregiver: Anjali Desai (caregiver@cognicompanion.demo) assigned to all patients
  - People: Care circles with descriptions, relationships, and contacts
  - Memories: Rich episodic events with 768-dim vector embeddings for pgvector semantic search
  - Timeline: Active medications and recurring daily routines
  - Adherence: Medication logs (Taken vs Pending) for today's live timeline
  - Game Sessions: Realistic sessions for Memory Match, Sequence Recall, etc.
  - Analytics & CPI: 7 days of daily_statistics and cognitive_metrics (CPI trends)
  - Voice Conversations: Realistic assistant conversation turns with provenance sources

Run via:
    python seed_rich_dataset.py
"""

import asyncio
import math
import os
import sys
import uuid
from datetime import date, datetime, time, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.core.security import hash_password
from app.domains.analytics.models import CognitiveMetric, DailyStatistic
from app.domains.games.models import DifficultyLevel, Game, GameSession, GameType, SessionStatus
from app.domains.memories.models import Memory, MemoryType, Person
from app.domains.patients.models import (
    CaregiverPatient,
    Patient,
    PreferredLanguage,
    User,
    UserRole,
)
from app.domains.timeline.models import (
    Medication,
    MedicationAdherenceLog,
    MedicationFrequency,
    MedicationTiming,
    Routine,
    RoutineCategory,
)
from app.domains.voice.models import Conversation, ConversationMessage, MemoryEmbedding

settings = get_settings()
engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def generate_dummy_embedding(seed_text: str) -> list[float]:
    """Generates a deterministic 768-dimensional unit vector for pgvector."""
    dim = 768
    raw = [math.sin(hash(seed_text + str(i)) % 1000) for i in range(dim)]
    norm = math.sqrt(sum(x * x for x in raw)) or 1.0
    return [round(x / norm, 6) for x in raw]


async def seed_all() -> None:
    print("=" * 65)
    print("  CogniCompanion — Seeding Comprehensive PostgreSQL Dataset")
    print(f"  Target DB: {settings.DATABASE_URL.split('@')[-1]}")
    print("=" * 65)

    async with AsyncSessionLocal() as db:
        async with db.begin():
            now = datetime.now(timezone.utc)
            today = date.today()

            # ─────────────────────────────────────────────────────────────────
            # 1. Caregiver: Anjali Desai
            # ─────────────────────────────────────────────────────────────────
            res = await db.execute(
                select(User).where(User.email == "caregiver@cognicompanion.demo")
            )
            caregiver = res.scalar_one_or_none()
            if not caregiver:
                caregiver = User(
                    id=uuid.uuid4(),
                    email="caregiver@cognicompanion.demo",
                    hashed_password=hash_password("CogniDemo2024!"),
                    role=UserRole.CAREGIVER,
                    full_name="Anjali Desai",
                    is_active=True,
                    token_version=0,
                )
                db.add(caregiver)
                await db.flush()
                print("  [OK] Created Caregiver: Anjali Desai (caregiver@cognicompanion.demo)")
            else:
                print("  [EXISTS] Caregiver Anjali Desai found.")

            # ─────────────────────────────────────────────────────────────────
            # 2. Patients (Shanti Devi, Rameshwar Nath, Subhashini Roy)
            # ─────────────────────────────────────────────────────────────────
            patient_configs = [
                {
                    "email": "patient@cognicompanion.demo",
                    "name": "Shanti Devi",
                    "dob": date(1948, 4, 12),
                    "lang": PreferredLanguage.HINDI,
                    "contact_name": "Rahul Sharma (Son)",
                    "contact_phone": "+91 98765 43210",
                    "notes": (
                        "Mild cognitive impairment (MCI). Stage 4 Alzheimer's. "
                        "Retired literature teacher. Retains warm episodic memories when prompted "
                        "with familiar family photos and classical thumri melodies."
                    ),
                },
                {
                    "email": "rameshwar@cognicompanion.demo",
                    "name": "Rameshwar Nath",
                    "dob": date(1945, 11, 20),
                    "lang": PreferredLanguage.BENGALI,
                    "contact_name": "Dr. Ananya Nath (Daughter)",
                    "contact_phone": "+91 91234 56789",
                    "notes": (
                        "Early vascular dementia. Retired railway chief station master. "
                        "Strong procedural memory for train routes and chess. "
                        "Requires daily blood pressure and vitals logging."
                    ),
                },
                {
                    "email": "subhashini@cognicompanion.demo",
                    "name": "Subhashini Roy",
                    "dob": date(1943, 8, 15),
                    "lang": PreferredLanguage.ASSAMESE,
                    "contact_name": "Deepa Roy (Daughter)",
                    "contact_phone": "+91 98321 65490",
                    "notes": (
                        "Moderate Alzheimer's. Master handloom textile artist from Guwahati. "
                        "Responds warmly to tactile weaving patterns and Bihu folk tunes."
                    ),
                },
            ]

            seeded_patients: dict[str, Patient] = {}

            for p_cfg in patient_configs:
                u_res = await db.execute(select(User).where(User.email == p_cfg["email"]))
                p_user = u_res.scalar_one_or_none()
                if not p_user:
                    p_user = User(
                        id=uuid.uuid4(),
                        email=p_cfg["email"],
                        hashed_password=hash_password("CogniDemo2024!"),
                        role=UserRole.PATIENT,
                        full_name=p_cfg["name"],
                        is_active=True,
                        token_version=0,
                    )
                    db.add(p_user)
                    await db.flush()

                pat_res = await db.execute(
                    select(Patient).where(Patient.user_id == p_user.id)
                )
                patient = pat_res.scalar_one_or_none()
                if not patient:
                    patient = Patient(
                        id=uuid.uuid4(),
                        user_id=p_user.id,
                        date_of_birth=p_cfg["dob"],
                        preferred_language=p_cfg["lang"],
                        emergency_contact_name=p_cfg["contact_name"],
                        emergency_contact_phone=p_cfg["contact_phone"],
                        medical_notes=p_cfg["notes"],
                    )
                    db.add(patient)
                    await db.flush()
                seeded_patients[p_cfg["name"]] = patient

                # Link caregiver to patient
                cp_res = await db.execute(
                    select(CaregiverPatient).where(
                        CaregiverPatient.caregiver_id == caregiver.id,
                        CaregiverPatient.patient_id == patient.id,
                    )
                )
                if not cp_res.scalar_one_or_none():
                    db.add(
                        CaregiverPatient(
                            id=uuid.uuid4(),
                            caregiver_id=caregiver.id,
                            patient_id=patient.id,
                            relationship_type="primary_caregiver",
                            is_primary=True,
                        )
                    )
                    await db.flush()
                print(f"  [OK] Patient ready: {p_cfg['name']} (id={patient.id})")

            shanti = seeded_patients["Shanti Devi"]
            rameshwar = seeded_patients["Rameshwar Nath"]

            # ─────────────────────────────────────────────────────────────────
            # 3. People (Care Circles)
            # ─────────────────────────────────────────────────────────────────
            people_data = [
                # Shanti Devi
                (shanti.id, "Rahul Sharma", "son", "Elder son, 38, Civil engineer in Pune. Calls every morning, visits Sundays with fresh Alphonso mangoes and sweets.", "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=300&fit=crop&q=80"),
                (shanti.id, "Priya Nair", "daughter", "Daughter, 35, School teacher in Bangalore. Calls Wednesdays & Saturdays, visits twice a month.", "https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=300&fit=crop&q=80"),
                (shanti.id, "Pooja Sharma", "granddaughter", "Rahul's daughter, 14. Loves playing carrom on the veranda and painting watercolor sketches with grandmother.", "https://images.unsplash.com/photo-1517841905240-472988babdf9?w=300&fit=crop&q=80"),
                (shanti.id, "Dr. Alok Verma", "neurologist", "Primary neurologist at Metro Care Hospital. Monthly review every 1st Tuesday at 11:00 AM.", "https://images.unsplash.com/photo-1622253692010-333f2da6031d?w=300&fit=crop&q=80"),
                (shanti.id, "Meena Tai", "neighbor", "Next door neighbor and close friend of 30 years. Daily evening tea and courtyard companion.", "https://images.unsplash.com/photo-1567532939604-b6b5b0db2604?w=300&fit=crop&q=80"),
                (shanti.id, "Sister Joyce", "nurse", "Community visiting nurse. Checks vitals every Thursday morning and assists with pillbox organization.", "https://images.unsplash.com/photo-1559839734-2b71ea197ec2?w=300&fit=crop&q=80"),
                # Rameshwar Nath
                (rameshwar.id, "Dr. Ananya Nath", "daughter", "Pediatrician at Apollo Hospital. Visits every alternate evening and reviews his daily vitals log.", "https://images.unsplash.com/photo-1594824813572-c2cb48600d89?w=300&fit=crop&q=80"),
                (rameshwar.id, "Bikash Sen", "nurse", "Dedicated caregiver and physiotherapist. Assists with morning mobility, walks, and blood pressure monitoring.", "https://images.unsplash.com/photo-1537368910025-700350fe46c7?w=300&fit=crop&q=80"),
                (rameshwar.id, "Gourab Roy", "friend", "Retired railway officer and close friend of 40 years. Weekly Saturday balcony chess partner.", "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=300&fit=crop&q=80"),
            ]

            seeded_people = []
            for pid, name, rel, desc, photo in people_data:
                p_check = await db.execute(
                    select(Person).where(Person.patient_id == pid, Person.name == name)
                )
                if not p_check.scalar_one_or_none():
                    p_obj = Person(
                        id=uuid.uuid4(),
                        patient_id=pid,
                        name=name,
                        relationship=rel,
                        description=desc,
                        photo_url=photo,
                        is_active=True,
                        created_at=now,
                        updated_at=now,
                    )
                    db.add(p_obj)
                    seeded_people.append(p_obj)
            await db.flush()
            print(f"  [OK] Seeded {len(seeded_people)} people records.")

            # ─────────────────────────────────────────────────────────────────
            # 4. Memories with pgvector Embeddings
            # ─────────────────────────────────────────────────────────────────
            memories_data = [
                # Shanti Devi
                (
                    shanti.id,
                    MemoryType.VISIT,
                    "Rahul's Sunday Family Visit",
                    "Rahul visited Shanti yesterday afternoon and brought sweet fresh Alphonso mangoes. They sat together in the sunny garden veranda drinking masala chai. Shanti smiled warmly looking at photos from Pooja's school fair.",
                    "Garden Veranda",
                    today - timedelta(days=1),
                    True,
                ),
                (
                    shanti.id,
                    MemoryType.OUTING,
                    "Evening Walk in Empress Botanical Garden",
                    "Gentle 30-minute stroll around the rose garden with Meena Tai. Shanti pointed out blooming marigolds and reminisced about her childhood garden in Varanasi.",
                    "Empress Botanical Garden",
                    today - timedelta(days=3),
                    False,
                ),
                (
                    shanti.id,
                    MemoryType.FAMILY_STORY,
                    "Grandmother's Secret Mango Chutney Recipe",
                    "Shanti recited her mother's secret spice blend: roasted cumin seeds, pure jaggery, mustard seeds, and sundried red chilies in an earthen jar.",
                    "Kitchen",
                    today - timedelta(days=6),
                    True,
                ),
                (
                    shanti.id,
                    MemoryType.FAMILY_STORY,
                    "Pooja's 14th Birthday Terrace Celebration",
                    "Terrace garden decorated with fairy lights. Pooja touched Shanti's feet for blessings, and Shanti gifted her an embroidered Banarasi silk stole.",
                    "Terrace Garden",
                    today - timedelta(days=15),
                    True,
                ),
                (
                    shanti.id,
                    MemoryType.APPOINTMENT,
                    "Dr. Verma's Neurological Checkup",
                    "Stable cognitive profile confirmed. Donepezil 5mg dose maintained, added morning B12 and daily cognitive card game routine.",
                    "Metro Care Clinic",
                    today - timedelta(days=20),
                    False,
                ),
                # Rameshwar Nath
                (
                    rameshwar.id,
                    MemoryType.FAMILY_STORY,
                    "Howrah Railway Station Darjeeling Mail Memory",
                    "Rameshwar vividly recalled dispatching the night express steam locomotive during the monsoon storms of 1982. Enjoyed touching his vintage pocket watch.",
                    "Study Room",
                    today - timedelta(days=2),
                    True,
                ),
                (
                    rameshwar.id,
                    MemoryType.FAMILY_STORY,
                    "Ananya's Medical Convocation Day",
                    "Looked at the framed 2008 medical gold medal photograph. Smiled proudly saying 'My daughter saves little children every day'.",
                    "Living Room",
                    today - timedelta(days=10),
                    True,
                ),
            ]

            seeded_mem_count = 0
            for pid, m_type, title, desc, loc, edate, sig in memories_data:
                m_check = await db.execute(
                    select(Memory).where(Memory.patient_id == pid, Memory.title == title)
                )
                if not m_check.scalar_one_or_none():
                    mem_obj = Memory(
                        id=uuid.uuid4(),
                        patient_id=pid,
                        created_by=caregiver.id,
                        memory_type=m_type,
                        title=title,
                        description=desc,
                        location=loc,
                        event_date=edate,
                        is_significant=sig,
                        created_at=now,
                        updated_at=now,
                    )
                    db.add(mem_obj)
                    await db.flush()

                    # Add pgvector 768-dim embedding
                    emb_vector = generate_dummy_embedding(f"{title} {desc} {loc}")
                    emb_obj = MemoryEmbedding(
                        id=uuid.uuid4(),
                        memory_id=mem_obj.id,
                        embedding=emb_vector,
                        embedding_text=f"{title} {desc} {loc}",
                        model_version="models/text-embedding-004",
                        created_at=now,
                    )
                    db.add(emb_obj)
                    seeded_mem_count += 1

            await db.flush()
            print(f"  [OK] Seeded {seeded_mem_count} memories with pgvector embeddings.")

            # ─────────────────────────────────────────────────────────────────
            # 5. Medications & Adherence Logs
            # ─────────────────────────────────────────────────────────────────
            meds_data = [
                # Shanti Devi
                (shanti.id, "Donepezil", "5mg", MedicationFrequency.ONCE_DAILY, MedicationTiming.BEDTIME, time(21, 0), "Take with water right before sleep for cognitive stabilization."),
                (shanti.id, "Vitamin B12 & Folate", "500mcg", MedicationFrequency.ONCE_DAILY, MedicationTiming.AFTER_BREAKFAST, time(9, 0), "Post breakfast with water. Supports nerve protection."),
                (shanti.id, "Amlodipine", "2.5mg", MedicationFrequency.ONCE_DAILY, MedicationTiming.AFTER_BREAKFAST, time(9, 0), "Blood pressure stabilizer. Keeps systolic under 135."),
                (shanti.id, "Calcium Tablet", "500mg", MedicationFrequency.ONCE_DAILY, MedicationTiming.AFTER_LUNCH, time(13, 0), "Post lunch bone density supplement."),
                # Rameshwar Nath
                (rameshwar.id, "Memantine", "10mg", MedicationFrequency.ONCE_DAILY, MedicationTiming.AFTER_BREAKFAST, time(8, 30), "NMDA receptor blocker for vascular dementia."),
                (rameshwar.id, "Telmisartan", "40mg", MedicationFrequency.ONCE_DAILY, MedicationTiming.AFTER_BREAKFAST, time(8, 30), "Cerebrovascular blood pressure control."),
                (rameshwar.id, "Atorvastatin", "10mg", MedicationFrequency.ONCE_DAILY, MedicationTiming.BEDTIME, time(21, 0), "Bedtime lipid management for microvessels."),
            ]

            seeded_meds: list[Medication] = []
            for pid, name, dose, freq, timing, stime, notes in meds_data:
                med_check = await db.execute(
                    select(Medication).where(Medication.patient_id == pid, Medication.name == name)
                )
                med_obj = med_check.scalar_one_or_none()
                if not med_obj:
                    med_obj = Medication(
                        id=uuid.uuid4(),
                        patient_id=pid,
                        name=name,
                        dosage=dose,
                        frequency=freq,
                        timing=timing,
                        scheduled_time=stime,
                        notes=notes,
                        is_active=True,
                        created_at=now,
                        updated_at=now,
                    )
                    db.add(med_obj)
                    await db.flush()
                seeded_meds.append(med_obj)

            # Seed adherence logs for today and yesterday
            for med in seeded_meds:
                # Yesterday's dose was taken
                y_check = await db.execute(
                    select(MedicationAdherenceLog).where(
                        MedicationAdherenceLog.medication_id == med.id,
                        MedicationAdherenceLog.log_date == today - timedelta(days=1),
                    )
                )
                if not y_check.scalar_one_or_none():
                    db.add(
                        MedicationAdherenceLog(
                            id=uuid.uuid4(),
                            medication_id=med.id,
                            log_date=today - timedelta(days=1),
                            taken=True,
                            taken_at=datetime.combine(today - timedelta(days=1), med.scheduled_time, tzinfo=timezone.utc),
                            confirmed_by=caregiver.id,
                            notes="Taken on time with water.",
                        )
                    )

                # Today's dose: morning meds are taken, bedtime meds are pending
                t_check = await db.execute(
                    select(MedicationAdherenceLog).where(
                        MedicationAdherenceLog.medication_id == med.id,
                        MedicationAdherenceLog.log_date == today,
                    )
                )
                if not t_check.scalar_one_or_none():
                    is_morning = med.timing == MedicationTiming.AFTER_BREAKFAST
                    db.add(
                        MedicationAdherenceLog(
                            id=uuid.uuid4(),
                            medication_id=med.id,
                            log_date=today,
                            taken=is_morning,
                            taken_at=datetime.combine(today, med.scheduled_time, tzinfo=timezone.utc) if is_morning else None,
                            confirmed_by=caregiver.id if is_morning else None,
                            notes="Confirmed taken" if is_morning else "Scheduled for later today",
                        )
                    )
            await db.flush()
            print("  [OK] Seeded medications and adherence history.")

            # ─────────────────────────────────────────────────────────────────
            # 6. Routines
            # ─────────────────────────────────────────────────────────────────
            routines_data = [
                # Shanti Devi
                (shanti.id, "Morning Sunlight & Gentle Stretching", "15 minutes garden bench with deep Pranayama breathing.", RoutineCategory.MORNING, time(7, 30), "☀️"),
                (shanti.id, "Nutritious Breakfast & Warm Almond Milk", "Warm oats porridge with crushed almonds and fresh fruit.", RoutineCategory.MEAL, time(8, 30), "🥣"),
                (shanti.id, "Cognitive Memory Game Session", "Two rounds of Memory Card Match on tablet with voice encouragement.", RoutineCategory.COGNITIVE, time(10, 30), "🃏"),
                (shanti.id, "Wholesome Lunch & Hydration", "Steamed rice, dal, and buttermilk.", RoutineCategory.MEAL, time(13, 0), "🥗"),
                (shanti.id, "Evening Veranda Tea & Radio Melodies", "Warm herbal tea in veranda with Meena Tai; listening to All India Radio.", RoutineCategory.SOCIAL, time(17, 0), "🫖"),
                (shanti.id, "Bedtime Calming Routine & Donepezil", "Warm water wash, soft room lights, and bedtime preparation.", RoutineCategory.EVENING, time(21, 0), "🌙"),
                # Rameshwar Nath
                (rameshwar.id, "Balcony Stroll & Ankle Mobility with Bikash", "Light joint rotation and 200 steps on covered terrace.", RoutineCategory.MORNING, time(7, 0), "🚶"),
                (rameshwar.id, "Darjeeling Tea, Toast & Memantine", "Fresh tea with brown toast and morning neuroprotective dose.", RoutineCategory.MEAL, time(8, 30), "☕"),
                (rameshwar.id, "Sequence Pattern Recall on Tablet", "Route sequence and light pattern game for procedural stimulation.", RoutineCategory.COGNITIVE, time(11, 0), "🔢"),
                (rameshwar.id, "Chess Puzzle & Rabindra Sangeet Session", "Solving 2 chess endgames while listening to Tagore melodies.", RoutineCategory.SOCIAL, time(16, 30), "♟️"),
            ]

            seeded_routines_count = 0
            for pid, title, desc, cat, stime, emoji in routines_data:
                r_check = await db.execute(
                    select(Routine).where(Routine.patient_id == pid, Routine.title == title)
                )
                if not r_check.scalar_one_or_none():
                    db.add(
                        Routine(
                            id=uuid.uuid4(),
                            patient_id=pid,
                            title=title,
                            description=desc,
                            category=cat,
                            scheduled_time=stime,
                            days_of_week=127,
                            icon_emoji=emoji,
                            is_active=True,
                            created_at=now,
                            updated_at=now,
                        )
                    )
                    seeded_routines_count += 1
            await db.flush()
            print(f"  [OK] Seeded {seeded_routines_count} recurring daily routines.")

            # ─────────────────────────────────────────────────────────────────
            # 7. Game Sessions
            # ─────────────────────────────────────────────────────────────────
            games_res = await db.execute(select(Game))
            games_map = {g.game_type: g for g in games_res.scalars()}

            game_sessions_data = [
                # Shanti Devi
                (shanti.id, GameType.MEMORY_MATCH, DifficultyLevel.MEDIUM, 280, 0.88, 1850, 2, 8, 7, today - timedelta(days=1), 180),
                (shanti.id, GameType.SEQUENCE_RECALL, DifficultyLevel.EASY, 210, 0.90, 2100, 1, 6, 6, today - timedelta(days=2), 160),
                (shanti.id, GameType.PICTURE_RECALL, DifficultyLevel.EASY, 190, 0.80, 2400, 1, 5, 4, today - timedelta(days=3), 210),
                (shanti.id, GameType.MEMORY_MATCH, DifficultyLevel.EASY, 240, 0.85, 1950, 2, 6, 5, today - timedelta(days=4), 170),
                # Rameshwar Nath
                (rameshwar.id, GameType.SEQUENCE_RECALL, DifficultyLevel.MEDIUM, 260, 0.84, 2200, 2, 8, 7, today - timedelta(days=1), 240),
                (rameshwar.id, GameType.MEMORY_MATCH, DifficultyLevel.EASY, 200, 0.80, 2500, 2, 6, 5, today - timedelta(days=2), 220),
            ]

            seeded_sessions_count = 0
            for pid, gtype, diff, score, acc, rtime, mis, tot, corr, gdate, dur in game_sessions_data:
                game = games_map.get(gtype)
                if not game:
                    continue
                start_dt = datetime.combine(gdate, time(10, 30), tzinfo=timezone.utc)
                end_dt = start_dt + timedelta(seconds=dur)

                # Check if session on that day exists
                s_check = await db.execute(
                    select(GameSession).where(
                        GameSession.patient_id == pid,
                        GameSession.game_id == game.id,
                        GameSession.started_at >= start_dt - timedelta(minutes=5),
                        GameSession.started_at <= start_dt + timedelta(minutes=5),
                    )
                )
                if not s_check.scalar_one_or_none():
                    db.add(
                        GameSession(
                            id=uuid.uuid4(),
                            patient_id=pid,
                            game_id=game.id,
                            difficulty_level=diff,
                            status=SessionStatus.COMPLETED,
                            score=score,
                            accuracy=acc,
                            reaction_time_ms=rtime,
                            mistakes=mis,
                            total_items=tot,
                            correct_items=corr,
                            next_difficulty=diff,
                            started_at=start_dt,
                            completed_at=end_dt,
                            duration_seconds=dur,
                        )
                    )
                    seeded_sessions_count += 1
            await db.flush()
            print(f"  [OK] Seeded {seeded_sessions_count} game play sessions.")

            # ─────────────────────────────────────────────────────────────────
            # 8. Daily Statistics & Cognitive Metrics (7-day CPI trend)
            # ─────────────────────────────────────────────────────────────────
            for i in range(7):
                d = today - timedelta(days=6 - i)

                # Shanti Devi progression: CPI 76 -> 82
                shanti_cpi = 76.0 + (i * 1.0)
                sh_mem = round(0.80 + (i * 0.01), 3)
                sh_react = round(0.75 + (i * 0.01), 3)
                sh_comp = 0.90
                sh_eng = 0.85

                ds_check = await db.execute(
                    select(DailyStatistic).where(
                        DailyStatistic.patient_id == shanti.id,
                        DailyStatistic.stat_date == d,
                    )
                )
                if not ds_check.scalar_one_or_none():
                    db.add(
                        DailyStatistic(
                            id=uuid.uuid4(),
                            patient_id=shanti.id,
                            stat_date=d,
                            games_completed=2,
                            games_total=2,
                            average_game_accuracy=sh_mem,
                            average_reaction_time_ms=1850 - (i * 15),
                            medications_scheduled=4,
                            medications_taken=4 if i < 6 else 3,
                            medication_adherence=1.0 if i < 6 else 0.75,
                            routines_scheduled=6,
                            routines_completed=5,
                            routine_adherence=0.83,
                            assistant_interactions_count=4,
                            cpi_score=shanti_cpi,
                        )
                    )

                cm_check = await db.execute(
                    select(CognitiveMetric).where(
                        CognitiveMetric.patient_id == shanti.id,
                        CognitiveMetric.metric_date == d,
                    )
                )
                if not cm_check.scalar_one_or_none():
                    db.add(
                        CognitiveMetric(
                            id=uuid.uuid4(),
                            patient_id=shanti.id,
                            metric_date=d,
                            memory_accuracy=sh_mem,
                            reaction_performance=sh_react,
                            completion_rate=sh_comp,
                            engagement_score=sh_eng,
                            cpi_score=shanti_cpi,
                            cpi_delta=1.0 if i > 0 else 0.0,
                            notes="Positive engagement, daily memory card games improving recall latency.",
                        )
                    )

                # Rameshwar Nath progression: CPI 70 -> 74
                ramesh_cpi = 70.0 + (i * 0.6)
                r_mem = round(0.72 + (i * 0.007), 3)
                r_react = round(0.66 + (i * 0.007), 3)

                ds_r_check = await db.execute(
                    select(DailyStatistic).where(
                        DailyStatistic.patient_id == rameshwar.id,
                        DailyStatistic.stat_date == d,
                    )
                )
                if not ds_r_check.scalar_one_or_none():
                    db.add(
                        DailyStatistic(
                            id=uuid.uuid4(),
                            patient_id=rameshwar.id,
                            stat_date=d,
                            games_completed=1,
                            games_total=1,
                            average_game_accuracy=r_mem,
                            average_reaction_time_ms=2350 - (i * 10),
                            medications_scheduled=3,
                            medications_taken=3,
                            medication_adherence=1.0,
                            routines_scheduled=4,
                            routines_completed=4,
                            routine_adherence=1.0,
                            assistant_interactions_count=3,
                            cpi_score=ramesh_cpi,
                        )
                    )

                cm_r_check = await db.execute(
                    select(CognitiveMetric).where(
                        CognitiveMetric.patient_id == rameshwar.id,
                        CognitiveMetric.metric_date == d,
                    )
                )
                if not cm_r_check.scalar_one_or_none():
                    db.add(
                        CognitiveMetric(
                            id=uuid.uuid4(),
                            patient_id=rameshwar.id,
                            metric_date=d,
                            memory_accuracy=r_mem,
                            reaction_performance=r_react,
                            completion_rate=0.88,
                            engagement_score=0.75,
                            cpi_score=ramesh_cpi,
                            cpi_delta=0.6 if i > 0 else 0.0,
                            notes="Consistent blood pressure adherence. Stable procedural recall.",
                        )
                    )

            await db.flush()
            print("  [OK] Seeded 7-day DailyStatistic and CognitiveMetric trend records.")

            # ─────────────────────────────────────────────────────────────────
            # 9. Voice Conversations & Assistant Provenance Logs
            # ─────────────────────────────────────────────────────────────────
            conversations_data = [
                (
                    shanti.id,
                    "Who visited me yesterday?",
                    "Rahul visited you yesterday afternoon! He brought some fresh Alphonso mangoes and showed you pictures from Pooja's school science fair.",
                    "PERSON_VISIT_QUERY",
                    0.94,
                    [
                        {"type": "memory", "title": "Rahul's Sunday Family Visit", "detail": "Logged by Anjali Desai. Tagged Rahul & Pooja.", "relevance_score": 0.96},
                        {"type": "person", "title": "Rahul Sharma (Son)", "detail": "Elder son, visits on Sundays.", "relevance_score": 0.91},
                    ],
                ),
                (
                    shanti.id,
                    "Did I take my morning medicine?",
                    "Yes, Shanti ji! You took your morning Vitamin B12 and Amlodipine right after breakfast at 9:15 AM. Your next medicine is Calcium after lunch, and Donepezil before sleep.",
                    "MEDICATION_STATUS_QUERY",
                    0.98,
                    [
                        {"type": "medication", "title": "Vitamin B12 & Folate — Taken at 09:15", "detail": "Adherence log confirmed by caregiver Anjali Desai.", "relevance_score": 0.99},
                        {"type": "routine", "title": "Nutritious Breakfast — 08:30", "detail": "Schedule context.", "relevance_score": 0.85},
                    ],
                ),
                (
                    shanti.id,
                    "Tell me about Pooja.",
                    "Pooja is your granddaughter — she is 14 years old and Rahul's daughter. She loves playing carrom with you in the afternoon and drawing watercolor sketches!",
                    "PERSON_PROFILE_QUERY",
                    0.92,
                    [
                        {"type": "person", "title": "Pooja Sharma (Granddaughter)", "detail": "Rahul's daughter, 14. Carrom and sketching enthusiast.", "relevance_score": 0.95},
                    ],
                ),
                (
                    rameshwar.id,
                    "When is Ananya visiting me?",
                    "Ananya is visiting you this evening around 6:30 PM after her clinic at Apollo! She said she will bring your favorite sandesh sweets.",
                    "PERSON_VISIT_QUERY",
                    0.96,
                    [
                        {"type": "person", "title": "Dr. Ananya Nath (Daughter)", "detail": "Visits alternate evenings.", "relevance_score": 0.98},
                    ],
                ),
            ]

            seeded_conv_count = 0
            for pid, q_text, a_text, intent, conf, sources in conversations_data:
                conv = Conversation(
                    id=uuid.uuid4(),
                    patient_id=pid,
                    started_at=now - timedelta(minutes=45),
                    ended_at=now - timedelta(minutes=44),
                    language_code="en-IN",
                    message_count=2,
                )
                db.add(conv)
                await db.flush()

                # User turn
                db.add(
                    ConversationMessage(
                        id=uuid.uuid4(),
                        conversation_id=conv.id,
                        role="patient",
                        content=q_text,
                        created_at=now - timedelta(minutes=45),
                    )
                )

                # Assistant turn
                db.add(
                    ConversationMessage(
                        id=uuid.uuid4(),
                        conversation_id=conv.id,
                        role="assistant",
                        content=a_text,
                        intent_type=intent,
                        confidence_score=conf,
                        sources_json={"sources": sources},
                        llm_model_used="gemini-1.5-flash",
                        created_at=now - timedelta(minutes=44),
                    )
                )
                seeded_conv_count += 1

            await db.flush()
            print(f"  [OK] Seeded {seeded_conv_count} voice conversations with explainability logs.")

    print("\n" + "=" * 65)
    print("  Database Seeding Completed Successfully!")
    print("  Login as Caregiver: caregiver@cognicompanion.demo (pw: CogniDemo2024!)")
    print("  Login as Patient:   patient@cognicompanion.demo   (pw: CogniDemo2024!)")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    asyncio.run(seed_all())
