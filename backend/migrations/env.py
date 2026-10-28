"""
CogniCompanion — Alembic Migration Environment
================================================
Reads DATABASE_URL from settings so migrations always use the right DB.
Uses synchronous SQLAlchemy URL (psycopg2) because Alembic doesn't support async.
"""

import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Ensure the backend/ directory is on the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Import Base so Alembic can autogenerate from all models
from app.core.database import Base
from app.core.config import get_settings

# Import all domain models so their tables are registered on Base.metadata
from app.domains.patients.models import User, Patient, CaregiverPatient  # noqa: F401
from app.domains.memories.models import Person, Memory, MemoryMedia, memory_person  # noqa: F401
from app.domains.timeline.models import Medication, MedicationAdherenceLog, Routine, Event  # noqa: F401
from app.domains.games.models import Game, GameSession  # noqa: F401
from app.domains.analytics.models import DailyStatistic, CognitiveMetric  # noqa: F401
from app.domains.voice.models import Conversation, ConversationMessage, MemoryEmbedding  # noqa: F401

config = context.config
settings = get_settings()

# Override alembic.ini URL with the one from settings
config.set_main_option("sqlalchemy.url", settings.SYNC_DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (SQL script output, no DB connection)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (connect to DB and apply)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
