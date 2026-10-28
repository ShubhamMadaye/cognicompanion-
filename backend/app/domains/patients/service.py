"""
CogniCompanion — Patients Domain Service
==========================================
Business logic for user/patient CRUD and caregiver management.
"""

import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.core.security import hash_password
from app.domains.patients.models import (
    CaregiverPatient,
    Patient,
    User,
    UserRole,
)
from app.domains.patients.schemas import (
    AssignCaregiverRequest,
    CreatePatientRequest,
    UpdatePatientRequest,
)


class PatientService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ── Create ────────────────────────────────────────────────────────────────

    async def create_patient(
        self,
        data: CreatePatientRequest,
        created_by: User,
    ) -> Patient:
        """
        Create a new patient account (User + Patient profile + CaregiverPatient link).

        Only CAREGIVER or ADMIN roles can create patients.
        The creating caregiver is automatically assigned to the patient.

        All three inserts are performed in a single transaction.
        """
        # Check for duplicate email
        existing = await self._db.execute(
            select(User).where(User.email == data.email)
        )
        if existing.scalar_one_or_none():
            raise ConflictError(f"A user with email '{data.email}' already exists.")

        # 1. Create the User account
        user = User(
            email=data.email,
            full_name=data.full_name,
            hashed_password=hash_password(data.password),
            role=UserRole.PATIENT,
        )
        self._db.add(user)
        await self._db.flush()  # Get user.id without committing

        # 2. Create the Patient profile
        patient = Patient(
            user_id=user.id,
            date_of_birth=data.date_of_birth,
            preferred_language=data.preferred_language,
            emergency_contact_name=data.emergency_contact_name,
            emergency_contact_phone=data.emergency_contact_phone,
            medical_notes=data.medical_notes,
        )
        self._db.add(patient)
        await self._db.flush()  # Get patient.id

        # 3. Link the creating caregiver to this patient
        if created_by.role == UserRole.CAREGIVER:
            link = CaregiverPatient(
                caregiver_id=created_by.id,
                patient_id=patient.id,
                relationship_type=data.caregiver_relationship,
                is_primary=data.is_primary_caregiver,
            )
            self._db.add(link)

        # Commit is handled by get_db() dependency
        await self._db.flush()
        await self._db.refresh(patient, ["user", "caregiver_assignments"])
        return patient

    # ── Read ──────────────────────────────────────────────────────────────────

    async def get_patient_by_id(self, patient_id: uuid.UUID) -> Patient:
        """Fetch a patient with their user relationship loaded."""
        result = await self._db.execute(
            select(Patient)
            .options(selectinload(Patient.user))
            .where(Patient.id == patient_id)
        )
        patient = result.scalar_one_or_none()
        if not patient:
            raise NotFoundError("Patient")
        return patient

    async def get_patient_by_user_id(self, user_id: uuid.UUID) -> Patient:
        """Fetch a patient by their associated user_id (for patient self-access)."""
        result = await self._db.execute(
            select(Patient)
            .options(selectinload(Patient.user))
            .where(Patient.user_id == user_id)
        )
        patient = result.scalar_one_or_none()
        if not patient:
            raise NotFoundError("Patient profile for user")
        return patient

    async def get_or_create_patient_for_user(self, user: User) -> Patient:
        """Fetch or automatically provision a patient record for the user (guaranteeing self-access)."""
        result = await self._db.execute(
            select(Patient)
            .options(selectinload(Patient.user))
            .where(Patient.user_id == user.id)
        )
        patient = result.scalar_one_or_none()
        if patient:
            return patient

        # If user is a caregiver, check if they have any assigned patients
        if user.role == UserRole.CAREGIVER:
            assigned = await self.list_patients_for_caregiver(user.id)
            if assigned:
                return assigned[0]

        # Auto-provision a Patient record so the user can use the patient mobile app
        new_patient = Patient(
            id=uuid.uuid4(),
            user_id=user.id,
            preferred_language=PreferredLanguage.ENGLISH,
        )
        self._db.add(new_patient)
        await self._db.commit()

        # Re-fetch with user loaded
        return await self.get_patient_by_id(new_patient.id)

    async def list_patients_for_caregiver(
        self, caregiver_id: uuid.UUID
    ) -> Sequence[Patient]:
        """Return all patients assigned to the given caregiver."""
        result = await self._db.execute(
            select(Patient)
            .join(CaregiverPatient, CaregiverPatient.patient_id == Patient.id)
            .options(selectinload(Patient.user))
            .where(CaregiverPatient.caregiver_id == caregiver_id)
        )
        return result.scalars().all()

    # ── Update ────────────────────────────────────────────────────────────────

    async def update_patient(
        self,
        patient_id: uuid.UUID,
        data: UpdatePatientRequest,
    ) -> Patient:
        patient = await self.get_patient_by_id(patient_id)

        if data.full_name is not None:
            patient.user.full_name = data.full_name
        if data.date_of_birth is not None:
            patient.date_of_birth = data.date_of_birth
        if data.preferred_language is not None:
            patient.preferred_language = data.preferred_language
        if data.emergency_contact_name is not None:
            patient.emergency_contact_name = data.emergency_contact_name
        if data.emergency_contact_phone is not None:
            patient.emergency_contact_phone = data.emergency_contact_phone
        if data.medical_notes is not None:
            patient.medical_notes = data.medical_notes

        await self._db.flush()
        return patient

    # ── Caregiver Assignment ──────────────────────────────────────────────────

    async def assign_caregiver(
        self,
        patient_id: uuid.UUID,
        data: AssignCaregiverRequest,
    ) -> CaregiverPatient:
        """Assign an additional caregiver to a patient."""
        # Verify caregiver exists and has the CAREGIVER role
        result = await self._db.execute(
            select(User).where(User.id == data.caregiver_id)
        )
        caregiver = result.scalar_one_or_none()
        if not caregiver:
            raise NotFoundError("Caregiver user")
        if caregiver.role not in (UserRole.CAREGIVER, UserRole.ADMIN):
            raise ForbiddenError("The specified user does not have a caregiver role.")

        # Check for duplicate assignment
        existing = await self._db.execute(
            select(CaregiverPatient).where(
                CaregiverPatient.caregiver_id == data.caregiver_id,
                CaregiverPatient.patient_id == patient_id,
            )
        )
        if existing.scalar_one_or_none():
            raise ConflictError("This caregiver is already assigned to the patient.")

        link = CaregiverPatient(
            caregiver_id=data.caregiver_id,
            patient_id=patient_id,
            relationship_type=data.relationship_type,
            is_primary=data.is_primary,
        )
        self._db.add(link)
        await self._db.flush()
        return link

    # ── Dashboard Summary ─────────────────────────────────────────────────────

    async def get_dashboard_summary(
        self, patient_id: uuid.UUID
    ) -> "DashboardSummaryResponse":
        from datetime import date, datetime, time, timezone
        from sqlalchemy import desc, func
        from app.domains.analytics.service import AnalyticsService
        from app.domains.memories.models import Memory, Person
        from app.domains.patients.schemas import (
            AttentionSummaryItem,
            CognitiveSummaryItem,
            DashboardSummaryResponse,
            MemorySummaryItem,
            PatientResponse,
            TodaySummaryItem,
        )
        from app.domains.timeline.models import (
            Event,
            Medication,
            MedicationAdherenceLog,
            Routine,
        )

        patient = await self.get_patient_by_id(patient_id)
        today = date.today()
        start_of_day = datetime.combine(today, time.min)
        end_of_day = datetime.combine(today, time.max)

        # 1. Today's medications & adherence
        meds_res = await self._db.execute(
            select(Medication).where(
                Medication.patient_id == patient_id,
                Medication.is_active == True,
            )
        )
        active_meds = meds_res.scalars().all()

        adh_res = await self._db.execute(
            select(MedicationAdherenceLog).join(
                Medication, MedicationAdherenceLog.medication_id == Medication.id
            ).where(
                Medication.patient_id == patient_id,
                MedicationAdherenceLog.log_date == today,
                MedicationAdherenceLog.taken == True,
            )
        )
        taken_logs = adh_res.scalars().all()
        taken_med_ids = {log.medication_id for log in taken_logs}
        pending_med_names = [m.name for m in active_meds if m.id not in taken_med_ids]

        # 2. Today's routines
        routines_res = await self._db.execute(
            select(func.count(Routine.id)).where(
                Routine.patient_id == patient_id,
                Routine.is_active == True,
            )
        )
        total_routines = routines_res.scalar() or 0
        completed_routines = min(total_routines, len(taken_logs)) if total_routines > 0 else 0

        # 3. Today's events
        events_res = await self._db.execute(
            select(func.count(Event.id)).where(
                Event.patient_id == patient_id,
                Event.start_time >= start_of_day,
                Event.start_time <= end_of_day,
            )
        )
        total_events = events_res.scalar() or 0

        # 4. Cognitive Performance
        analytics_service = AnalyticsService(self._db)
        cpi_resp = await analytics_service.get_cpi_response(patient_id, today)

        # 5. Memory Engine Status
        mem_count_res = await self._db.execute(
            select(func.count(Memory.id)).where(Memory.patient_id == patient_id)
        )
        total_memories = mem_count_res.scalar() or 0

        people_count_res = await self._db.execute(
            select(func.count(Person.id)).where(
                Person.patient_id == patient_id,
                Person.is_active == True,
            )
        )
        total_people = people_count_res.scalar() or 0

        latest_mem_res = await self._db.execute(
            select(Memory)
            .where(Memory.patient_id == patient_id)
            .order_by(desc(Memory.event_date))
            .limit(1)
        )
        latest_mem = latest_mem_res.scalar_one_or_none()

        # 6. Attention / Alerts
        alerts: list[str] = []
        if pending_med_names:
            alerts.append(f"{len(pending_med_names)} scheduled medication(s) pending for today.")
        if cpi_resp.status.value == "INSUFFICIENT_DATA":
            alerts.append("Baseline cognitive data incomplete. Patient activities needed.")

        return DashboardSummaryResponse(
            patient=PatientResponse.model_validate(patient),
            today=TodaySummaryItem(
                total_medications=len(active_meds),
                taken_medications=len(taken_logs),
                pending_medications=len(pending_med_names),
                total_routines=total_routines,
                completed_routines=completed_routines,
                total_events=total_events,
            ),
            cognitive=CognitiveSummaryItem(
                status=cpi_resp.status.value,
                cpi_score=cpi_resp.cpi_score,
                cpi_delta=cpi_resp.cpi_delta,
                games_completed_today=cpi_resp.games_completed,
                disclaimer=cpi_resp.disclaimer,
            ),
            memory=MemorySummaryItem(
                total_memories=total_memories,
                total_people=total_people,
                latest_memory_title=latest_mem.title if latest_mem else None,
                latest_memory_date=latest_mem.event_date if latest_mem else None,
            ),
            attention=AttentionSummaryItem(
                pending_medication_names=pending_med_names,
                missed_medications=len(pending_med_names),
                alerts=alerts,
            ),
        )
