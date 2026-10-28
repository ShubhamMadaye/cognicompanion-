import { apiClient } from './client';
import { Medication, Routine, TimelineEntry } from '../types';

/* -------------------------------------------------------------------------- */
/* Request Types                                                              */
/* -------------------------------------------------------------------------- */

export interface CreateMedicationData {
  name: string;
  dosage?: string;
  frequency:
  | 'ONCE_DAILY'
  | 'TWICE_DAILY'
  | 'THREE_TIMES_DAILY'
  | 'FOUR_TIMES_DAILY'
  | 'WEEKLY'
  | 'AS_NEEDED';
  timing:
  | 'BEFORE_BREAKFAST'
  | 'AFTER_BREAKFAST'
  | 'BEFORE_LUNCH'
  | 'AFTER_LUNCH'
  | 'BEFORE_DINNER'
  | 'AFTER_DINNER'
  | 'BEDTIME'
  | 'SPECIFIC_TIME';
  scheduled_time?: string;
  start_date?: string;
  end_date?: string;
  notes?: string;
}

export interface UpdateMedicationData {
  name?: string;
  dosage?: string;
  frequency?:
  | 'ONCE_DAILY'
  | 'TWICE_DAILY'
  | 'THREE_TIMES_DAILY'
  | 'FOUR_TIMES_DAILY'
  | 'WEEKLY'
  | 'AS_NEEDED';
  timing?:
  | 'BEFORE_BREAKFAST'
  | 'AFTER_BREAKFAST'
  | 'BEFORE_LUNCH'
  | 'AFTER_LUNCH'
  | 'BEFORE_DINNER'
  | 'AFTER_DINNER'
  | 'BEDTIME'
  | 'SPECIFIC_TIME';
  scheduled_time?: string;
  start_date?: string;
  end_date?: string;
  notes?: string;
  is_active?: boolean;
}

export interface LogMedicationData {
  log_date: string;
  taken: boolean;
  taken_at?: string;
  notes?: string;
}

export interface CreateRoutineData {
  title: string;
  description?: string;
  category:
  | 'MORNING'
  | 'AFTERNOON'
  | 'EVENING'
  | 'EXERCISE'
  | 'MEAL'
  | 'HYGIENE'
  | 'SOCIAL'
  | 'COGNITIVE'
  | 'GENERAL';
  scheduled_time: string;
  days_of_week?: number;
  icon_emoji?: string;
}

export interface UpdateRoutineData {
  title?: string;
  description?: string;
  category?:
  | 'MORNING'
  | 'AFTERNOON'
  | 'EVENING'
  | 'EXERCISE'
  | 'MEAL'
  | 'HYGIENE'
  | 'SOCIAL'
  | 'COGNITIVE'
  | 'GENERAL';
  scheduled_time?: string;
  days_of_week?: number;
  icon_emoji?: string;
  is_active?: boolean;
}

/* -------------------------------------------------------------------------- */
/* Timeline API                                                               */
/* -------------------------------------------------------------------------- */

export const timelineApi = {
  /* ------------------------------------------------------------------------ */
  /* Timeline                                                                 */
  /* ------------------------------------------------------------------------ */

  /**
   * Get the patient's unified timeline for a specific day.
   *
   * GET /patients/{patientId}/timeline
   */
  async getDayTimeline(
    patientId: string,
    day?: string
  ): Promise<TimelineEntry[]> {
    try {
      const params = day ? { day } : {};

      const resp = await apiClient.get(
        `/patients/${patientId}/timeline`,
        { params }
      );

      return resp.data;
    } catch (error) {
      console.error('Failed to load timeline:', error);
      throw error;
    }
  },

  /* ------------------------------------------------------------------------ */
  /* Medications                                                              */
  /* ------------------------------------------------------------------------ */

  /**
   * Get all active medications for the patient.
   *
   * GET /patients/{patientId}/medications
   */
  async listMedications(patientId: string): Promise<Medication[]> {
    try {
      const resp = await apiClient.get(
        `/patients/${patientId}/medications`
      );

      return resp.data;
    } catch (error) {
      console.error('Failed to load medications:', error);
      throw error;
    }
  },

  /**
   * Create a medication for the patient.
   *
   * POST /patients/{patientId}/medications
   */
  async createMedication(
    patientId: string,
    data: CreateMedicationData
  ): Promise<Medication> {
    try {
      const resp = await apiClient.post(
        `/patients/${patientId}/medications`,
        data
      );

      return resp.data;
    } catch (error) {
      console.error('Failed to create medication:', error);
      throw error;
    }
  },

  /**
   * Update a medication.
   *
   * PATCH /patients/{patientId}/medications/{medicationId}
   */
  async updateMedication(
    patientId: string,
    medicationId: string,
    data: UpdateMedicationData
  ): Promise<Medication> {
    try {
      const resp = await apiClient.patch(
        `/patients/${patientId}/medications/${medicationId}`,
        data
      );

      return resp.data;
    } catch (error) {
      console.error('Failed to update medication:', error);
      throw error;
    }
  },

  /**
   * Enable or disable a medication.
   *
   * The backend does not expose a DELETE medication endpoint.
   * Setting is_active=false effectively deactivates it.
   */
  async setMedicationActive(
    patientId: string,
    medicationId: string,
    isActive: boolean
  ): Promise<Medication> {
    try {
      const resp = await apiClient.patch(
        `/patients/${patientId}/medications/${medicationId}`,
        {
          is_active: isActive,
        }
      );

      return resp.data;
    } catch (error) {
      console.error('Failed to change medication status:', error);
      throw error;
    }
  },

  /**
   * Log whether a medication was taken.
   *
   * POST /patients/{patientId}/medications/{medicationId}/log
   */
  async logMedication(
    patientId: string,
    medicationId: string,
    data: LogMedicationData
  ) {
    try {
      const resp = await apiClient.post(
        `/patients/${patientId}/medications/${medicationId}/log`,
        data
      );

      return resp.data;
    } catch (error) {
      console.error('Failed to log medication adherence:', error);
      throw error;
    }
  },

  /* ------------------------------------------------------------------------ */
  /* Routines                                                                 */
  /* ------------------------------------------------------------------------ */

  /**
   * Get all active routines for the patient.
   *
   * GET /patients/{patientId}/routines
   */
  async listRoutines(patientId: string): Promise<Routine[]> {
    try {
      const resp = await apiClient.get(
        `/patients/${patientId}/routines`
      );

      return resp.data;
    } catch (error) {
      console.error('Failed to load routines:', error);
      throw error;
    }
  },

  /**
   * Create a recurring routine.
   *
   * POST /patients/{patientId}/routines
   */
  async createRoutine(
    patientId: string,
    data: CreateRoutineData
  ): Promise<Routine> {
    try {
      const resp = await apiClient.post(
        `/patients/${patientId}/routines`,
        data
      );

      return resp.data;
    } catch (error) {
      console.error('Failed to create routine:', error);
      throw error;
    }
  },

  /**
   * Update a routine.
   *
   * PATCH /patients/{patientId}/routines/{routineId}
   */
  async updateRoutine(
    patientId: string,
    routineId: string,
    data: UpdateRoutineData
  ): Promise<Routine> {
    try {
      const resp = await apiClient.patch(
        `/patients/${patientId}/routines/${routineId}`,
        data
      );

      return resp.data;
    } catch (error) {
      console.error('Failed to update routine:', error);
      throw error;
    }
  },

  /**
   * Enable or disable a routine.
   *
   * The backend does not expose a DELETE routine endpoint.
   * Setting is_active=false effectively deactivates it.
   */
  async setRoutineActive(
    patientId: string,
    routineId: string,
    isActive: boolean
  ): Promise<Routine> {
    try {
      const resp = await apiClient.patch(
        `/patients/${patientId}/routines/${routineId}`,
        {
          is_active: isActive,
        }
      );

      return resp.data;
    } catch (error) {
      console.error('Failed to change routine status:', error);
      throw error;
    }
  },
};