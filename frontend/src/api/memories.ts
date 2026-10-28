import { apiClient } from './client';
import { Memory, Person } from '../types';

export const memoriesApi = {
  async listMemories(patientId: string, memoryType?: string): Promise<Memory[]> {
    try {
      const params = memoryType ? { memory_type: memoryType } : {};
      const resp = await apiClient.get(`/patients/${patientId}/memories`, { params });
      return resp.data;
    } catch (error) {
      console.error('Failed to load memories:', error);
      throw error;
    }
  },
  async createMemory(patientId: string, data: Partial<Memory> & { person_ids?: string[] }): Promise<Memory> {
    try {
      const resp = await apiClient.post(`/patients/${patientId}/memories`, data);
      return resp.data;
    } catch (error) {
      console.error('Failed to create memory:', error);
      throw error;
    }
  },
  async listPeople(patientId: string): Promise<Person[]> {
    try {
      const resp = await apiClient.get(`/patients/${patientId}/people`);
      return resp.data;
    } catch (error) {
      console.error('Failed to load people:', error);
      throw error;
    }
  },
  async createPerson(patientId: string, data: Partial<Person>): Promise<Person> {
    try {
      const resp = await apiClient.post(`/patients/${patientId}/people`, data);
      return resp.data;
    } catch (error) {
      console.error('Failed to create person:', error);
      throw error;
    }
  },
};
