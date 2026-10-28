import { apiClient } from './client';
import { User } from '../types';

export const authApi = {
  async login(email: string, password: string): Promise<{ access_token: string; user: User }> {
    try {
      const resp = await apiClient.post('/auth/login', { email, password });
      const { access_token, user } = resp.data;
      localStorage.setItem('cogni_token', access_token);

      if (user) {
        return { access_token, user };
      }

      // Fallback: fetch full user profile if not directly returned
      const meResp = await apiClient.get('/auth/me');
      return {
        access_token,
        user: meResp.data,
      };
    } catch (err: unknown) {
      // Re-throw if backend returned a specific error so caller can display message
      const axiosError = err as { response?: { data?: { detail?: string } } };
      if (axiosError?.response?.data?.detail) {
        throw new Error(axiosError.response.data.detail);
      }
      throw err;
    }
  },

  async register(
    email: string,
    password: string,
    fullName: string,
    role: string = 'CAREGIVER'
  ): Promise<{ access_token: string; user: User }> {
    try {
      const resp = await apiClient.post('/auth/register', {
        email,
        password,
        full_name: fullName,
        role,
      });
      const { access_token, user } = resp.data;
      localStorage.setItem('cogni_token', access_token);
      return {
        access_token,
        user,
      };
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { detail?: string } } };
      if (axiosError?.response?.data?.detail) {
        throw new Error(axiosError.response.data.detail);
      }
      throw err;
    }
  },

  async getMe(): Promise<User> {
    const resp = await apiClient.get('/auth/me');
    return resp.data;
  },

  async logout(): Promise<void> {
    try {
      await apiClient.post('/auth/logout');
    } catch {
      // Ignore network errors during logout
    } finally {
      localStorage.removeItem('cogni_token');
    }
  },
};

