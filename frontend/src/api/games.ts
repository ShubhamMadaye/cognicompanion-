import { apiClient } from './client';
import { GameCatalogItem, GameSession } from '../types';

// NOTE: mockData is NOT imported here.
// Rule: API failure → throw. The UI shows an error or empty state.

export const gamesApi = {
  async listGames(): Promise<GameCatalogItem[]> {
    const resp = await apiClient.get('/games');
    return Array.isArray(resp.data) ? resp.data : [];
  },

  async getHistory(patientId: string): Promise<GameSession[]> {
    const resp = await apiClient.get(`/patients/${patientId}/games/history`);
    return Array.isArray(resp.data) ? resp.data : [];
  },
};
