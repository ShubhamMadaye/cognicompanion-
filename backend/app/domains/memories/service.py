"""
CogniCompanion — Memories Domain Service
==========================================
Business logic for People, Memories, and MemoryMedia.

Publishes:
  - MemoryCreatedEvent → event bus → embedding generation (Phase 4)
                                   → timeline entry creation
"""

import hashlib
import uuid
from datetime import date
from typing import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ConflictError, NotFoundError
from app.core.storage import storage
from app.domains.memories.models import (
    MediaType,
    Memory,
    MemoryMedia,
    Person,
    StorageProviderType,
)
from app.domains.memories.schemas import (
    CreateMemoryRequest,
    CreatePersonRequest,
    UpdateMemoryRequest,
    UpdatePersonRequest,
)
from app.domains.patients.models import User
from app.events.bus import MemoryCreatedEvent, event_bus


# ── People ────────────────────────────────────────────────────────────────────

class PeopleService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create_person(
        self, patient_id: uuid.UUID, data: CreatePersonRequest
    ) -> Person:
        person = Person(
            patient_id=patient_id,
            name=data.name,
            relationship=data.relationship,
            description=data.description,
        )
        self._db.add(person)
        await self._db.flush()
        return person

    async def list_people(self, patient_id: uuid.UUID) -> Sequence[Person]:
        result = await self._db.execute(
            select(Person)
            .where(Person.patient_id == patient_id, Person.is_active == True)  # noqa: E712
            .order_by(Person.name)
        )
        return result.scalars().all()

    async def get_person(
        self, patient_id: uuid.UUID, person_id: uuid.UUID
    ) -> Person:
        result = await self._db.execute(
            select(Person).where(
                Person.id == person_id,
                Person.patient_id == patient_id,
            )
        )
        person = result.scalar_one_or_none()
        if not person:
            raise NotFoundError("Person")
        return person

    async def update_person(
        self,
        patient_id: uuid.UUID,
        person_id: uuid.UUID,
        data: UpdatePersonRequest,
    ) -> Person:
        person = await self.get_person(patient_id, person_id)
        if data.name is not None:
            person.name = data.name
        if data.relationship is not None:
            person.relationship = data.relationship
        if data.description is not None:
            person.description = data.description
        if data.is_active is not None:
            person.is_active = data.is_active
        await self._db.flush()
        return person

    async def upload_person_photo(
        self,
        patient_id: uuid.UUID,
        person_id: uuid.UUID,
        file_bytes: bytes,
        filename: str,
    ) -> Person:
        person = await self.get_person(patient_id, person_id)
        file_url = await storage.save(file_bytes, filename, folder="people")
        person.photo_url = file_url
        await self._db.flush()
        return person


# ── Memories ──────────────────────────────────────────────────────────────────

class MemoryService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create_memory(
        self,
        patient_id: uuid.UUID,
        data: CreateMemoryRequest,
        created_by: User,
    ) -> Memory:
        memory = Memory(
            patient_id=patient_id,
            created_by=created_by.id,
            memory_type=data.memory_type,
            title=data.title,
            description=data.description,
            location=data.location,
            event_date=data.event_date,
            is_significant=data.is_significant,
        )
        self._db.add(memory)
        await self._db.flush()  # get memory.id

        # Link people — insert directly into association table to avoid lazy-load
        if data.person_ids:
            from app.domains.memories.models import memory_person as memory_person_table
            people_result = await self._db.execute(
                select(Person).where(
                    Person.id.in_(data.person_ids),
                    Person.patient_id == patient_id,
                )
            )
            people = people_result.scalars().all()
            for person in people:
                await self._db.execute(
                    memory_person_table.insert().values(
                        memory_id=memory.id,
                        person_id=person.id,
                    )
                )

        await self._db.flush()

        # Publish domain event — triggers embedding generation + timeline update
        await event_bus.publish(
            MemoryCreatedEvent(
                memory_id=str(memory.id),
                patient_id=str(patient_id),
                memory_type=data.memory_type.value,
            )
        )

        await self._db.refresh(memory, ["media", "people"])
        return memory

    async def list_memories(
        self,
        patient_id: uuid.UUID,
        memory_type: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        significant_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[Memory]:
        query = (
            select(Memory)
            .options(selectinload(Memory.media), selectinload(Memory.people))
            .where(Memory.patient_id == patient_id)
        )
        if memory_type:
            query = query.where(Memory.memory_type == memory_type)
        if start_date:
            query = query.where(Memory.event_date >= start_date)
        if end_date:
            query = query.where(Memory.event_date <= end_date)
        if significant_only:
            query = query.where(Memory.is_significant == True)  # noqa: E712
        query = query.order_by(Memory.event_date.desc()).limit(limit).offset(offset)
        result = await self._db.execute(query)
        return result.scalars().all()

    async def get_memory(
        self, patient_id: uuid.UUID, memory_id: uuid.UUID
    ) -> Memory:
        result = await self._db.execute(
            select(Memory)
            .options(selectinload(Memory.media), selectinload(Memory.people))
            .where(Memory.id == memory_id, Memory.patient_id == patient_id)
        )
        memory = result.scalar_one_or_none()
        if not memory:
            raise NotFoundError("Memory")
        return memory

    async def update_memory(
        self,
        patient_id: uuid.UUID,
        memory_id: uuid.UUID,
        data: UpdateMemoryRequest,
    ) -> Memory:
        memory = await self.get_memory(patient_id, memory_id)
        if data.title is not None:
            memory.title = data.title
        if data.description is not None:
            memory.description = data.description
        if data.location is not None:
            memory.location = data.location
        if data.event_date is not None:
            memory.event_date = data.event_date
        if data.is_significant is not None:
            memory.is_significant = data.is_significant
        if data.person_ids is not None:
            people_result = await self._db.execute(
                select(Person).where(
                    Person.id.in_(data.person_ids),
                    Person.patient_id == patient_id,
                )
            )
            memory.people = list(people_result.scalars().all())
        await self._db.flush()
        return memory

    async def delete_memory(
        self, patient_id: uuid.UUID, memory_id: uuid.UUID
    ) -> None:
        memory = await self.get_memory(patient_id, memory_id)
        await self._db.delete(memory)

    async def attach_media(
        self,
        patient_id: uuid.UUID,
        memory_id: uuid.UUID,
        file_bytes: bytes,
        filename: str,
        mime_type: str,
        media_type: MediaType,
        caption: str | None = None,
    ) -> MemoryMedia:
        # Verify memory belongs to patient
        await self.get_memory(patient_id, memory_id)

        file_url = await storage.save(file_bytes, filename, folder="memories")
        checksum = hashlib.sha256(file_bytes).hexdigest()

        media = MemoryMedia(
            memory_id=memory_id,
            media_type=media_type,
            file_url=file_url,
            original_filename=filename,
            mime_type=mime_type,
            file_size_bytes=len(file_bytes),
            storage_provider=StorageProviderType.LOCAL,
            checksum_sha256=checksum,
            caption=caption,
        )
        self._db.add(media)
        await self._db.flush()
        return media

    async def delete_media(
        self,
        patient_id: uuid.UUID,
        memory_id: uuid.UUID,
        media_id: uuid.UUID,
    ) -> None:
        # Verify memory ownership
        await self.get_memory(patient_id, memory_id)

        result = await self._db.execute(
            select(MemoryMedia).where(
                MemoryMedia.id == media_id,
                MemoryMedia.memory_id == memory_id,
            )
        )
        media = result.scalar_one_or_none()
        if not media:
            raise NotFoundError("Media")

        # Remove file from storage
        await storage.delete(media.file_url)
        await self._db.delete(media)
