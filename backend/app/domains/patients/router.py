"""
CogniCompanion — Patients Router
===================================
Patient management endpoints for caregivers.

Authorization:
  - List/Create:  requires CAREGIVER or ADMIN
  - Read/Update:  requires CAREGIVER or ADMIN + must be assigned to patient
  - Assign caregiver: ADMIN only
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.domains.auth.dependencies import (
    get_current_caregiver,
    get_current_user,
    require_role,
    verify_caregiver_patient_access,
    verify_patient_self_or_caregiver_access,
)
from app.domains.patients.models import User, UserRole
from app.domains.patients.schemas import (
    AssignCaregiverRequest,
    CaregiverAssignmentResponse,
    CreatePatientRequest,
    DashboardSummaryResponse,
    PatientListResponse,
    PatientResponse,
    UpdatePatientRequest,
)
from app.domains.patients.service import PatientService

router = APIRouter(prefix="/patients", tags=["Patients"])


@router.post("/", response_model=PatientResponse, status_code=201, summary="Create a new patient")
async def create_patient(
    body: CreatePatientRequest,
    caregiver: Annotated[User, Depends(get_current_caregiver)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PatientResponse:
    """Create a patient account and link the authenticated caregiver to them."""
    service = PatientService(db)
    patient = await service.create_patient(data=body, created_by=caregiver)
    return PatientResponse.model_validate(patient)


@router.get("/me", response_model=PatientResponse, summary="Get current patient's profile")
async def get_my_patient_profile(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PatientResponse:
    """Return profile for the currently authenticated patient user (auto-provisioning if needed)."""
    service = PatientService(db)
    patient = await service.get_or_create_patient_for_user(current_user)
    return PatientResponse.model_validate(patient)


@router.get("/", response_model=list[PatientListResponse], summary="List my patients")
async def list_my_patients(
    caregiver: Annotated[User, Depends(get_current_caregiver)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[PatientListResponse]:
    """Return all patients assigned to the authenticated caregiver."""
    service = PatientService(db)
    patients = await service.list_patients_for_caregiver(caregiver.id)
    return [PatientListResponse.model_validate(p) for p in patients]


@router.get("/{patient_id}", response_model=PatientResponse, summary="Get patient details")
async def get_patient(
    patient_id: Annotated[uuid.UUID, Depends(verify_patient_self_or_caregiver_access)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PatientResponse:
    """Return detailed patient profile. Accessible by the patient themselves or their assigned caregivers."""
    service = PatientService(db)
    patient = await service.get_patient_by_id(patient_id)
    return PatientResponse.model_validate(patient)


@router.get(
    "/{patient_id}/dashboard-summary",
    response_model=DashboardSummaryResponse,
    summary="Get aggregated dashboard summary for caregiver",
)
async def get_patient_dashboard_summary(
    patient_id: Annotated[uuid.UUID, Depends(verify_patient_self_or_caregiver_access)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DashboardSummaryResponse:
    """
    Returns an aggregated overview of patient status, today's schedule,
    medication adherence, cognitive performance, and memory engine state.
    Strictly verifies caregiver-patient authorization.
    """
    service = PatientService(db)
    return await service.get_dashboard_summary(patient_id)


@router.patch("/{patient_id}", response_model=PatientResponse, summary="Update patient profile")
async def update_patient(
    patient_id: Annotated[uuid.UUID, Depends(verify_caregiver_patient_access)],
    body: UpdatePatientRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PatientResponse:
    """Update patient profile fields. Partial updates supported."""
    service = PatientService(db)
    patient = await service.update_patient(patient_id=patient_id, data=body)
    return PatientResponse.model_validate(patient)


@router.post(
    "/{patient_id}/caregivers",
    response_model=CaregiverAssignmentResponse,
    status_code=201,
    summary="Assign an additional caregiver",
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def assign_caregiver(
    patient_id: uuid.UUID,
    body: AssignCaregiverRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CaregiverAssignmentResponse:
    """Assign an additional caregiver to the patient. ADMIN only."""
    service = PatientService(db)
    link = await service.assign_caregiver(patient_id=patient_id, data=body)
    return CaregiverAssignmentResponse.model_validate(link)
