import { apiClient } from './client';
import { Patient, CreatePatientInput } from '../types';

export const patientsApi = {
  async listPatients(): Promise<Patient[]> {
    const resp = await apiClient.get('/patients/');

    return (resp.data || []).map((p: any) => ({
      id: p.id,
      user_id: p.user_id,
      full_name: p.user?.full_name || p.full_name,
      email: p.user?.email || p.email,
      date_of_birth: p.date_of_birth,
      preferred_language: p.preferred_language,
      emergency_contact_name: p.emergency_contact_name,
      emergency_contact_phone: p.emergency_contact_phone,
      medical_notes: p.medical_notes,
    }));
  },

  async createPatient(data: CreatePatientInput): Promise<Patient> {
    const payload = {
      ...data,
      date_of_birth: data.date_of_birth || null,
      emergency_contact_name: data.emergency_contact_name || null,
      emergency_contact_phone: data.emergency_contact_phone || null,
      medical_notes: data.medical_notes || null,
      caregiver_relationship: data.caregiver_relationship || null,
      is_primary_caregiver: data.is_primary_caregiver ?? true,
    };
    const resp = await apiClient.post('/patients/', payload);
    const p = resp.data;
    return {
      id: p.id,
      user_id: p.user_id,
      full_name: p.user?.full_name || p.full_name,
      email: p.user?.email || p.email,
      date_of_birth: p.date_of_birth,
      preferred_language: p.preferred_language,
      emergency_contact_name: p.emergency_contact_name,
      emergency_contact_phone: p.emergency_contact_phone,
      medical_notes: p.medical_notes,
    };
  },

  async getPatient(id: string): Promise<Patient> {
    const resp = await apiClient.get(`/patients/${id}`);
    const p = resp.data;
    return {
      id: p.id,
      user_id: p.user_id,
      full_name: p.user?.full_name || p.full_name,
      email: p.user?.email || p.email,
      date_of_birth: p.date_of_birth,
      preferred_language: p.preferred_language,
      emergency_contact_name: p.emergency_contact_name,
      emergency_contact_phone: p.emergency_contact_phone,
      medical_notes: p.medical_notes,
    };
  },

  async getDashboardSummary(id: string): Promise<any> {
    const resp = await apiClient.get(`/patients/${id}/dashboard-summary`);
    return resp.data;
  },
};
