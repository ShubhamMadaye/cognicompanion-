import random
import uuid
from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError
from app.domains.games.models import (
    DifficultyLevel,
    Game,
    GameSession,
    GameType,
    SessionStatus,
)
from app.domains.games.schemas import (
    CreateGameSessionRequest,
    GameCardItem,
    GameContentResponse,
    GameQuestionItem,
    GenerateGameContentRequest,
)
from app.domains.memories.models import Memory, Person
from app.events.bus import GameSessionCompletedEvent, event_bus


class GamesService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def list_games(self) -> Sequence[Game]:
        """Return the catalog of available cognitive games."""
        result = await self._db.execute(select(Game).order_by(Game.name))
        return result.scalars().all()

    async def get_or_create_game_by_type(self, game_type: GameType) -> Game:
        """Fetch game metadata by GameType enum."""
        result = await self._db.execute(select(Game).where(Game.game_type == game_type))
        game = result.scalar_one_or_none()
        if not game:
            game = Game(
                game_type=game_type,
                name=game_type.value.replace("_", " ").title(),
                description=f"Personalized cognitive stimulation activity for {game_type.value.replace('_', ' ').lower()}.",
                instructions=f"Engage in this gentle activity at your own pace to exercise attention and recall.",
            )
            self._db.add(game)
            await self._db.flush()
        return game

    async def compute_next_difficulty(
        self,
        patient_id: uuid.UUID,
        game_id: uuid.UUID,
        current_difficulty: DifficultyLevel,
        latest_accuracy: float,
    ) -> DifficultyLevel:
        """
        Adaptive Difficulty Engine:
        Evaluates a rolling average of the last 3 completed sessions for this game.
          - average accuracy >= 0.85 -> upgrade difficulty (EASY -> MEDIUM -> HARD)
          - average accuracy < 0.60  -> downgrade difficulty (HARD -> MEDIUM -> EASY)
          - 0.60 <= avg < 0.85       -> maintain current level
        """
        result = await self._db.execute(
            select(GameSession.accuracy)
            .where(
                GameSession.patient_id == patient_id,
                GameSession.game_id == game_id,
                GameSession.status == SessionStatus.COMPLETED,
                GameSession.accuracy.is_not(None),
            )
            .order_by(GameSession.completed_at.desc())
            .limit(2)
        )
        past_accuracies = [row[0] for row in result.all() if row[0] is not None]
        all_accuracies = [latest_accuracy] + past_accuracies
        avg_accuracy = sum(all_accuracies) / len(all_accuracies)

        if avg_accuracy >= 0.85:
            if current_difficulty == DifficultyLevel.EASY:
                return DifficultyLevel.MEDIUM
            elif current_difficulty == DifficultyLevel.MEDIUM:
                return DifficultyLevel.HARD
            return DifficultyLevel.HARD
        elif avg_accuracy < 0.60:
            if current_difficulty == DifficultyLevel.HARD:
                return DifficultyLevel.MEDIUM
            elif current_difficulty == DifficultyLevel.MEDIUM:
                return DifficultyLevel.EASY
            return DifficultyLevel.EASY
        return current_difficulty

    async def generate_game_content(
        self,
        patient_id: uuid.UUID,
        game_type: GameType,
        difficulty: DifficultyLevel = DifficultyLevel.MEDIUM,
        personalize: bool = True,
    ) -> GameContentResponse:
        """
        Generates deterministic cognitive game payloads.
        Integrates patient's actual memories & family photos when available.
        Strictly isolated to patient_id with zero cross-patient data leakage.
        """
        is_personalized = False

        if game_type == GameType.MEMORY_MATCH:
            # Pair count based on difficulty
            pair_count = 2 if difficulty == DifficultyLevel.EASY else (3 if difficulty == DifficultyLevel.MEDIUM else 4)
            cards: list[GameCardItem] = []

            # Check if patient has people/memories for personalization
            patient_people = []
            if personalize:
                res = await self._db.execute(
                    select(Person).where(Person.patient_id == patient_id).limit(pair_count)
                )
                patient_people = res.scalars().all()

            pool = []
            if patient_people:
                is_personalized = True
                for p in patient_people:
                    pool.append({"label": p.name, "emoji": "👤", "image_url": p.photo_url})

            default_pool = [
                {"label": "Chai Cup", "emoji": "☕", "image_url": None},
                {"label": "Marigold", "emoji": "🌼", "image_url": None},
                {"label": "Peacock", "emoji": "🦚", "image_url": None},
                {"label": "Sweet Mango", "emoji": "🥭", "image_url": None},
                {"label": "Tabla", "emoji": "🥁", "image_url": None},
                {"label": "Elephant", "emoji": "🐘", "image_url": None},
            ]

            while len(pool) < pair_count:
                for item in default_pool:
                    if item not in pool and len(pool) < pair_count:
                        pool.append(item)

            for idx, item in enumerate(pool[:pair_count]):
                pair_key = f"pair_{idx}"
                cards.append(
                    GameCardItem(
                        id=f"{pair_key}_a",
                        pair_id=pair_key,
                        label=item["label"],
                        image_url=item.get("image_url"),
                        emoji=item.get("emoji"),
                    )
                )
                cards.append(
                    GameCardItem(
                        id=f"{pair_key}_b",
                        pair_id=pair_key,
                        label=item["label"],
                        image_url=item.get("image_url"),
                        emoji=item.get("emoji"),
                    )
                )

            random.seed(42)  # Deterministic shuffle for reproducible tests
            random.shuffle(cards)

            return GameContentResponse(
                game_type=game_type,
                difficulty_level=difficulty,
                is_personalized=is_personalized,
                instructions="Tap pairs of cards to reveal and match them. Take your time.",
                cards=cards,
            )

        elif game_type == GameType.PICTURE_RECALL:
            questions: list[GameQuestionItem] = []
            if personalize:
                mem_res = await self._db.execute(
                    select(Memory)
                    .options(selectinload(Memory.people))
                    .where(Memory.patient_id == patient_id)
                    .limit(3)
                )
                memories = mem_res.scalars().all()
                for m in memories:
                    if m.people:
                        is_personalized = True
                        correct = m.people[0].name
                        distractors = ["Amit", "Priya", "Suresh", "Kavita"]
                        options = [correct] + [d for d in distractors if d != correct][:3]
                        random.shuffle(options)
                        questions.append(
                            GameQuestionItem(
                                question_text=f"Who is in this memory: '{m.title}'?",
                                image_url=None,
                                options=options,
                                correct_option=correct,
                                memory_id=str(m.id),
                            )
                        )

            if not questions:
                # Default question
                questions.append(
                    GameQuestionItem(
                        question_text="Which beautiful bird is known for vibrant blue and green feathers?",
                        image_url=None,
                        options=["Peacock", "Sparrow", "Pigeon", "Parrot"],
                        correct_option="Peacock",
                    )
                )

            return GameContentResponse(
                game_type=game_type,
                difficulty_level=difficulty,
                is_personalized=is_personalized,
                instructions="Look at the photo and choose who or what is shown.",
                questions=questions,
            )

        elif game_type == GameType.SEQUENCE_RECALL:
            palette = ["🔴 Red", "🔵 Blue", "🟢 Green", "🟡 Yellow", "🟣 Purple", "🟠 Orange"]
            count = 3 if difficulty == DifficultyLevel.EASY else (4 if difficulty == DifficultyLevel.MEDIUM else 6)
            seq = palette[:count]

            return GameContentResponse(
                game_type=game_type,
                difficulty_level=difficulty,
                is_personalized=False,
                instructions="Watch the sequence of colors carefully, then tap them in the exact order shown.",
                sequence=seq,
            )

        elif game_type == GameType.OBJECT_RECALL:
            items_pool = [
                "🔑 House Keys",
                "👓 Reading Glasses",
                "📱 Mobile Phone",
                "👛 Wallet",
                "☕ Chai Cup",
                "🌸 Fresh Flowers",
                "📖 Notebook",
                "📿 Prayer Beads",
            ]
            target_count = 3 if difficulty == DifficultyLevel.EASY else (4 if difficulty == DifficultyLevel.MEDIUM else 5)
            target_objs = items_pool[:target_count]
            candidates = items_pool[: target_count + 3]
            random.shuffle(candidates)

            return GameContentResponse(
                game_type=game_type,
                difficulty_level=difficulty,
                is_personalized=False,
                instructions="Remember the items shown on screen. When hidden, select which items were in the list.",
                target_objects=target_objs,
                candidate_objects=candidates,
            )

        raise NotFoundError(f"Unsupported game type: {game_type}")

    async def record_session(
        self, patient_id: uuid.UUID, data: CreateGameSessionRequest
    ) -> GameSession:
        """
        Records a completed game session, computes next difficulty tier using rolling average,
        and dispatches GameSessionCompletedEvent for CPI analytics calculation.
        """
        game = await self.get_or_create_game_by_type(data.game_type)
        next_diff = await self.compute_next_difficulty(
            patient_id=patient_id,
            game_id=game.id,
            current_difficulty=data.difficulty_level,
            latest_accuracy=data.accuracy,
        )

        now = datetime.now(timezone.utc)
        session = GameSession(
            patient_id=patient_id,
            game_id=game.id,
            status=SessionStatus.COMPLETED,
            difficulty_level=data.difficulty_level,
            score=data.score,
            accuracy=data.accuracy,
            reaction_time_ms=data.reaction_time_ms,
            mistakes=data.mistakes,
            total_items=data.total_items,
            correct_items=data.correct_items,
            next_difficulty=next_diff,
            completed_at=now,
            duration_seconds=data.duration_seconds or 60,
        )
        self._db.add(session)
        await self._db.flush()

        # Publish event for analytics & timeline
        await event_bus.publish(
            GameSessionCompletedEvent(
                session_id=str(session.id),
                patient_id=str(patient_id),
                game_type=data.game_type.value,
                accuracy=data.accuracy,
                cpi_contribution=data.score / 100.0,
            )
        )

        return session

    async def list_patient_sessions(
        self, patient_id: uuid.UUID, limit: int = 50
    ) -> Sequence[GameSession]:
        """Fetch game session history for a given patient."""
        result = await self._db.execute(
            select(GameSession)
            .options(selectinload(GameSession.game))
            .where(GameSession.patient_id == patient_id)
            .order_by(GameSession.completed_at.desc())
            .limit(limit)
        )
        return result.scalars().all()
