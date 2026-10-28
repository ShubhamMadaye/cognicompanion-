"""Initial schema — all CogniCompanion tables

Revision ID: 0001
Revises:
Create Date: 2026-08-29

Includes:
  - CREATE EXTENSION vector (pgvector)
  - All enums
  - All tables from blueprint Section 14
  - pgvector column on memory_embeddings
  - HNSW index on memory_embeddings.embedding for fast ANN search
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Enable pgvector extension (optional — skipped if not installed) ─────────
    op.execute("""
        DO $pgvec$
        BEGIN
            CREATE EXTENSION IF NOT EXISTS vector;
        EXCEPTION WHEN OTHERS THEN
            RAISE NOTICE 'pgvector not available — skipping. Semantic search will be disabled.';
        END
        $pgvec$;
    """)

    # ── Enums ─────────────────────────────────────────────────────────────────
    op.execute("""
        CREATE TYPE user_role AS ENUM ('PATIENT', 'CAREGIVER', 'DOCTOR', 'ADMIN')
    """)
    op.execute("""
        CREATE TYPE preferred_language AS ENUM ('en', 'hi', 'as', 'bn', 'mni')
    """)
    op.execute("""
        CREATE TYPE memory_type AS ENUM (
            'VISIT', 'OUTING', 'MEAL', 'MEDICATION', 'APPOINTMENT', 'FAMILY_STORY', 'GENERAL'
        )
    """)
    op.execute("""
        CREATE TYPE media_type AS ENUM ('IMAGE', 'AUDIO', 'VIDEO', 'DOCUMENT')
    """)
    op.execute("""
        CREATE TYPE storage_provider_type AS ENUM ('local', 's3', 'gcs')
    """)
    op.execute("""
        CREATE TYPE medication_frequency AS ENUM (
            'ONCE_DAILY', 'TWICE_DAILY', 'THREE_TIMES_DAILY', 'FOUR_TIMES_DAILY',
            'WEEKLY', 'AS_NEEDED'
        )
    """)
    op.execute("""
        CREATE TYPE medication_timing AS ENUM (
            'BEFORE_BREAKFAST', 'AFTER_BREAKFAST', 'BEFORE_LUNCH', 'AFTER_LUNCH',
            'BEFORE_DINNER', 'AFTER_DINNER', 'BEDTIME', 'SPECIFIC_TIME'
        )
    """)
    op.execute("""
        CREATE TYPE routine_category AS ENUM (
            'MORNING', 'AFTERNOON', 'EVENING', 'EXERCISE', 'MEAL',
            'HYGIENE', 'SOCIAL', 'COGNITIVE', 'GENERAL'
        )
    """)
    op.execute("""
        CREATE TYPE event_type AS ENUM (
            'VISIT', 'APPOINTMENT', 'OUTING', 'ACTIVITY', 'GAME_SESSION', 'GENERAL'
        )
    """)
    op.execute("""
        CREATE TYPE game_type AS ENUM (
            'MEMORY_MATCH', 'SEQUENCE_RECALL', 'PICTURE_RECALL', 'OBJECT_RECALL'
        )
    """)
    op.execute("""
        CREATE TYPE difficulty_level AS ENUM ('EASY', 'MEDIUM', 'HARD')
    """)
    op.execute("""
        CREATE TYPE session_status AS ENUM ('IN_PROGRESS', 'COMPLETED', 'ABANDONED')
    """)

    # ── users ─────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", postgresql.ENUM("PATIENT", "CAREGIVER", "DOCTOR", "ADMIN", name="user_role", create_type=False), nullable=False),
        sa.Column("full_name", sa.String(200), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("token_version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_users_email", "users", ["email"])

    # ── patients ──────────────────────────────────────────────────────────────
    op.create_table(
        "patients",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("preferred_language", postgresql.ENUM("en","hi","as","bn","mni", name="preferred_language", create_type=False), nullable=False, server_default="en"),
        sa.Column("profile_photo_url", sa.String(500), nullable=True),
        sa.Column("emergency_contact_name", sa.String(200), nullable=True),
        sa.Column("emergency_contact_phone", sa.String(20), nullable=True),
        sa.Column("medical_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # ── caregiver_patient ────────────────────────────────────────────────────
    op.create_table(
        "caregiver_patient",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("caregiver_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("patients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("relationship_type", sa.String(100), nullable=True),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("caregiver_id", "patient_id", name="uq_caregiver_patient"),
    )
    op.create_index("ix_caregiver_patient_caregiver_id", "caregiver_patient", ["caregiver_id"])
    op.create_index("ix_caregiver_patient_patient_id", "caregiver_patient", ["patient_id"])

    # ── people ────────────────────────────────────────────────────────────────
    op.create_table(
        "people",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("patients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("relationship", sa.String(100), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("photo_url", sa.String(500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_people_patient_id", "people", ["patient_id"])

    # ── memories ──────────────────────────────────────────────────────────────
    op.create_table(
        "memories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("patients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("memory_type", postgresql.ENUM("VISIT","OUTING","MEAL","MEDICATION","APPOINTMENT","FAMILY_STORY","GENERAL", name="memory_type", create_type=False), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("location", sa.String(200), nullable=True),
        sa.Column("event_date", sa.Date(), nullable=False),
        sa.Column("is_significant", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_memories_patient_id", "memories", ["patient_id"])
    op.create_index("ix_memories_event_date", "memories", ["event_date"])
    op.create_index("ix_memories_memory_type", "memories", ["memory_type"])

    # ── memory_person (association) ───────────────────────────────────────────
    op.create_table(
        "memory_person",
        sa.Column("memory_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("memories.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("person_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("people.id", ondelete="CASCADE"), primary_key=True),
    )

    # ── memory_media ──────────────────────────────────────────────────────────
    op.create_table(
        "memory_media",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("memory_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("memories.id", ondelete="CASCADE"), nullable=False),
        sa.Column("media_type", postgresql.ENUM("IMAGE","AUDIO","VIDEO","DOCUMENT", name="media_type", create_type=False), nullable=False),
        sa.Column("file_url", sa.String(500), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=True),
        sa.Column("mime_type", sa.String(100), nullable=True),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("storage_provider", postgresql.ENUM("local","s3","gcs", name="storage_provider_type", create_type=False), nullable=False, server_default="local"),
        sa.Column("checksum_sha256", sa.String(64), nullable=True),
        sa.Column("caption", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_memory_media_memory_id", "memory_media", ["memory_id"])

    # ── medications ───────────────────────────────────────────────────────────
    op.create_table(
        "medications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("patients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("dosage", sa.String(100), nullable=True),
        sa.Column("frequency", postgresql.ENUM("ONCE_DAILY","TWICE_DAILY","THREE_TIMES_DAILY","FOUR_TIMES_DAILY","WEEKLY","AS_NEEDED", name="medication_frequency", create_type=False), nullable=False),
        sa.Column("timing", postgresql.ENUM("BEFORE_BREAKFAST","AFTER_BREAKFAST","BEFORE_LUNCH","AFTER_LUNCH","BEFORE_DINNER","AFTER_DINNER","BEDTIME","SPECIFIC_TIME", name="medication_timing", create_type=False), nullable=False),
        sa.Column("scheduled_time", sa.Time(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_medications_patient_id", "medications", ["patient_id"])

    # ── medication_adherence_logs ─────────────────────────────────────────────
    op.create_table(
        "medication_adherence_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("medication_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("medications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("log_date", sa.Date(), nullable=False),
        sa.Column("taken", sa.Boolean(), nullable=False),
        sa.Column("taken_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmed_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("notes", sa.String(300), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_medication_adherence_logs_medication_id", "medication_adherence_logs", ["medication_id"])

    # ── routines ──────────────────────────────────────────────────────────────
    op.create_table(
        "routines",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("patients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", postgresql.ENUM("MORNING","AFTERNOON","EVENING","EXERCISE","MEAL","HYGIENE","SOCIAL","COGNITIVE","GENERAL", name="routine_category", create_type=False), nullable=False),
        sa.Column("scheduled_time", sa.Time(), nullable=False),
        sa.Column("days_of_week", sa.Integer(), nullable=False, server_default="127"),
        sa.Column("icon_emoji", sa.String(10), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_routines_patient_id", "routines", ["patient_id"])

    # ── events ────────────────────────────────────────────────────────────────
    op.create_table(
        "events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("patients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("event_type", postgresql.ENUM("VISIT","APPOINTMENT","OUTING","ACTIVITY","GAME_SESSION","GENERAL", name="event_type", create_type=False), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("location", sa.String(200), nullable=True),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("icon_emoji", sa.String(10), nullable=True),
        sa.Column("linked_memory_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("memories.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_events_patient_id", "events", ["patient_id"])
    op.create_index("ix_events_event_type", "events", ["event_type"])
    op.create_index("ix_events_start_time", "events", ["start_time"])

    # ── games ─────────────────────────────────────────────────────────────────
    op.create_table(
        "games",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("game_type", postgresql.ENUM("MEMORY_MATCH","SEQUENCE_RECALL","PICTURE_RECALL","OBJECT_RECALL", name="game_type", create_type=False), nullable=False, unique=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("instructions", sa.Text(), nullable=True),
        sa.Column("min_difficulty", postgresql.ENUM("EASY","MEDIUM","HARD", name="difficulty_level", create_type=False), nullable=False, server_default="EASY"),
        sa.Column("max_difficulty", postgresql.ENUM("EASY","MEDIUM","HARD", name="difficulty_level", create_type=False), nullable=False, server_default="HARD"),
        sa.Column("estimated_duration_seconds", sa.Integer(), nullable=False, server_default="180"),
        sa.Column("icon_emoji", sa.String(10), nullable=True),
    )

    # ── game_sessions ─────────────────────────────────────────────────────────
    op.create_table(
        "game_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("patients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("game_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("games.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", postgresql.ENUM("IN_PROGRESS","COMPLETED","ABANDONED", name="session_status", create_type=False), nullable=False, server_default="IN_PROGRESS"),
        sa.Column("difficulty_level", postgresql.ENUM("EASY","MEDIUM","HARD", name="difficulty_level", create_type=False), nullable=False),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("accuracy", sa.Float(), nullable=True),
        sa.Column("reaction_time_ms", sa.Integer(), nullable=True),
        sa.Column("mistakes", sa.Integer(), nullable=True),
        sa.Column("total_items", sa.Integer(), nullable=True),
        sa.Column("correct_items", sa.Integer(), nullable=True),
        sa.Column("next_difficulty", postgresql.ENUM("EASY","MEDIUM","HARD", name="difficulty_level", create_type=False), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
    )
    op.create_index("ix_game_sessions_patient_id", "game_sessions", ["patient_id"])

    # ── daily_statistics ──────────────────────────────────────────────────────
    op.create_table(
        "daily_statistics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("patients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("stat_date", sa.Date(), nullable=False),
        sa.Column("games_completed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("games_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("average_game_accuracy", sa.Float(), nullable=True),
        sa.Column("average_reaction_time_ms", sa.Integer(), nullable=True),
        sa.Column("medications_scheduled", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("medications_taken", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("medication_adherence", sa.Float(), nullable=True),
        sa.Column("routines_scheduled", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("routines_completed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("routine_adherence", sa.Float(), nullable=True),
        sa.Column("assistant_interactions_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cpi_score", sa.Float(), nullable=True),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_daily_statistics_patient_id", "daily_statistics", ["patient_id"])
    op.create_index("ix_daily_statistics_stat_date", "daily_statistics", ["stat_date"])

    # ── cognitive_metrics ─────────────────────────────────────────────────────
    op.create_table(
        "cognitive_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("patients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("metric_date", sa.Date(), nullable=False),
        sa.Column("memory_accuracy", sa.Float(), nullable=True),
        sa.Column("reaction_performance", sa.Float(), nullable=True),
        sa.Column("completion_rate", sa.Float(), nullable=True),
        sa.Column("engagement_score", sa.Float(), nullable=True),
        sa.Column("cpi_score", sa.Float(), nullable=True),
        sa.Column("cpi_delta", sa.Float(), nullable=True),
        sa.Column("notes", sa.String(500), nullable=True),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_cognitive_metrics_patient_id", "cognitive_metrics", ["patient_id"])
    op.create_index("ix_cognitive_metrics_metric_date", "cognitive_metrics", ["metric_date"])

    # ── conversations ─────────────────────────────────────────────────────────
    op.create_table(
        "conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("patients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("language_code", sa.String(10), nullable=True),
        sa.Column("message_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_conversations_patient_id", "conversations", ["patient_id"])

    # ── conversation_messages ─────────────────────────────────────────────────
    op.create_table(
        "conversation_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("audio_url", sa.String(500), nullable=True),
        sa.Column("intent_type", sa.String(50), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("sources_json", postgresql.JSONB(), nullable=True),
        sa.Column("llm_model_used", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_conversation_messages_conversation_id", "conversation_messages", ["conversation_id"])

    # ── memory_embeddings (pgvector) ──────────────────────────────────────────
    op.create_table(
        "memory_embeddings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("memory_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("memories.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("embedding_text", sa.Text(), nullable=True),
        sa.Column("model_version", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_memory_embeddings_memory_id", "memory_embeddings", ["memory_id"])

    # Add pgvector column + HNSW index (optional — skipped if pgvector is not installed)
    op.execute("""
        DO $pgvec2$
        BEGIN
            ALTER TABLE memory_embeddings ADD COLUMN embedding vector(768);

            CREATE INDEX idx_memory_embeddings_hnsw
            ON memory_embeddings
            USING hnsw (embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 64);

            RAISE NOTICE 'pgvector column and HNSW index created.';
        EXCEPTION WHEN OTHERS THEN
            RAISE NOTICE 'pgvector not installed — embedding column skipped. Semantic search disabled.';
        END
        $pgvec2$;
    """)

    # ── Seed: Insert the 4 MVP Games ──────────────────────────────────────────
    import uuid as uuid_mod
    op.execute(f"""
        INSERT INTO games (id, game_type, name, description, instructions, icon_emoji, estimated_duration_seconds)
        VALUES
        ('{uuid_mod.uuid4()}', 'MEMORY_MATCH',    'Memory Match',    'Flip cards and find matching pairs.',         'Remember the position of each card. Find all pairs to win.', '🃏', 180),
        ('{uuid_mod.uuid4()}', 'SEQUENCE_RECALL',  'Sequence Recall', 'Watch the sequence, then repeat it.',         'Watch the items appear one by one, then tap them in the same order.', '🔢', 120),
        ('{uuid_mod.uuid4()}', 'PICTURE_RECALL',   'Picture Recall',  'Study the image, then answer questions.',     'Look carefully at the scene for 30 seconds. Then answer questions about what you saw.', '🖼️', 150),
        ('{uuid_mod.uuid4()}', 'OBJECT_RECALL',    'Object Recall',   'Remember the objects shown, then recall them.', 'Look at the list of objects. Try to remember them all. Then choose which ones you saw.', '📦', 120)
    """)


def downgrade() -> None:
    # Drop tables in reverse dependency order
    op.drop_table("memory_embeddings")
    op.drop_table("conversation_messages")
    op.drop_table("conversations")
    op.drop_table("cognitive_metrics")
    op.drop_table("daily_statistics")
    op.drop_table("game_sessions")
    op.drop_table("games")
    op.drop_table("events")
    op.drop_table("routines")
    op.drop_table("medication_adherence_logs")
    op.drop_table("medications")
    op.drop_table("memory_media")
    op.drop_table("memory_person")
    op.drop_table("memories")
    op.drop_table("people")
    op.drop_table("caregiver_patient")
    op.drop_table("patients")
    op.drop_table("users")

    # Drop enums
    for enum_name in [
        "session_status", "difficulty_level", "game_type", "event_type",
        "routine_category", "medication_timing", "medication_frequency",
        "storage_provider_type", "media_type", "memory_type",
        "preferred_language", "user_role",
    ]:
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")

    op.execute("DROP EXTENSION IF EXISTS vector")
