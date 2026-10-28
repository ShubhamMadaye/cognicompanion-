import { apiClient } from './client';
import { CPIMetrics } from '../types';

export const cpiApi = {
  async getCPIMetrics(patientId: string): Promise<CPIMetrics> {
    try {
      const [cpiResp, trendsResp] = await Promise.all([
        apiClient.get(`/patients/${patientId}/analytics/cpi`),
        apiClient.get(`/patients/${patientId}/analytics/cpi/trends?days=7`),
      ]);

      const data = cpiResp.data;
      const trends = trendsResp.data?.trends || [];

      // Use the patient's latest valid trend as fallback only within trend data,
      // never inject hardcoded numbers.
      const lastValidTrend = [...trends].reverse().find((t: any) => t.cpi_score !== null && t.cpi_score !== undefined);
      const score = data.cpi_score ?? (lastValidTrend ? lastValidTrend.cpi_score : null);

      let status: 'OPTIMAL' | 'STABLE' | 'ATTENTION' = 'STABLE';
      if (score != null) {
        if (score >= 80) status = 'OPTIMAL';
        else if (score < 60) status = 'ATTENTION';
      }

      const memAccuracy = data.memory_accuracy ?? (lastValidTrend ? lastValidTrend.memory_accuracy : null);
      const engScore = data.engagement_score ?? (lastValidTrend ? lastValidTrend.engagement_score : null);
      const reactPerf = data.reaction_performance ?? (lastValidTrend ? lastValidTrend.reaction_performance : null);
      const compRate = data.completion_rate ?? (lastValidTrend ? lastValidTrend.completion_rate : null);

      // Carry forward previous known score for missing trend days so graph stays smooth
      let runningCpi = score ?? 0;
      let runningMem = memAccuracy ?? 0;
      let runningEng = engScore ?? 0;
      let runningReact = reactPerf ?? 0;

      const normalizedTrends = trends.map((t: any) => {
        if (t.cpi_score !== null && t.cpi_score !== undefined) runningCpi = t.cpi_score;
        if (t.memory_accuracy !== null && t.memory_accuracy !== undefined) runningMem = t.memory_accuracy;
        if (t.engagement_score !== null && t.engagement_score !== undefined) runningEng = t.engagement_score;
        if (t.reaction_performance !== null && t.reaction_performance !== undefined) runningReact = t.reaction_performance;

        return {
          date: t.date,
          cpi: Math.round(runningCpi),
          memory: Math.round(runningMem * 100),
          sequence: Math.round(runningEng * 100),
          reaction: Math.round(runningReact * 100),
        };
      });

      return {
        overall_score: score != null ? Math.round(score) : 0,
        change_vs_last_week: data.cpi_delta ?? null,
        status,
        memory_recall: memAccuracy != null ? Math.round(memAccuracy * 100) : null,
        sequence_accuracy: engScore != null ? Math.round(engScore * 100) : null,
        reaction_time_score: reactPerf != null ? Math.round(reactPerf * 100) : null,
        completion_rate: compRate != null ? Math.round(compRate * 100) : null,
        historical_trends: normalizedTrends,
      };
    } catch (error) {
      console.error('Failed to load CPI metrics:', error);
      throw error;
    }
  },
};
