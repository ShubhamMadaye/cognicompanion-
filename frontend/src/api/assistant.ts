import { apiClient } from './client';
import { AssistantResponse, ConversationTurn, ConfidenceInfo } from '../types';

// NOTE: mockData is NOT imported here.
// Rule: API failure → throw an error. The UI is responsible for showing
// an error state. There is no offline fallback with hardcoded patient data.

export const assistantApi = {
  async sendMessage(
    patientId: string,
    query: string,
    conversationId?: string,
    languageCode: string = 'en'
  ): Promise<AssistantResponse> {
    const resp = await apiClient.post<AssistantResponse>(
      `/patients/${patientId}/conversations/message`,
      {
        query,
        conversation_id: conversationId || null,
        language_code: languageCode,
      }
    );

    const data = resp.data;

    // Normalize confidence into structured ConfidenceInfo
    let confInfo: ConfidenceInfo;
    if (data.confidence_info) {
      confInfo = data.confidence_info;
    } else if (typeof data.confidence === 'object') {
      confInfo = data.confidence as ConfidenceInfo;
    } else {
      const score = typeof data.confidence === 'number' ? data.confidence : 0.85;
      confInfo = {
        score,
        level: score >= 0.75 ? 'HIGH' : score >= 0.5 ? 'MEDIUM' : 'LOW',
      };
    }

    return {
      answer: data.answer || data.reply,
      reply: data.reply || data.answer,
      intent: data.intent,
      confidence: confInfo,
      confidence_info: confInfo,
      sources: data.sources || [],
      grounded: data.grounded ?? (data.sources && data.sources.length > 0),
      conversation_id: data.conversation_id,
      created_at: data.created_at || new Date().toISOString(),
    };
    // Rule: No catch/fallback here. Errors propagate to the UI component,
    // which shows "Unable to reach the assistant. Please check your connection."
  },

  async listConversations(patientId: string): Promise<ConversationTurn[]> {
    const resp = await apiClient.get(`/patients/${patientId}/conversations`);
    const rawConvs = resp.data;

    // If backend returns list of ConversationResponse objects with messages:
    if (Array.isArray(rawConvs) && rawConvs.length > 0 && rawConvs[0].messages) {
      const turns: ConversationTurn[] = [];
      for (const conv of rawConvs) {
        const msgs = conv.messages || [];
        for (let i = 0; i < msgs.length; i += 2) {
          const userMsg = msgs[i];
          const asstMsg = msgs[i + 1];
          if (userMsg && asstMsg) {
            let rawSources: any[] = [];
            if (Array.isArray(asstMsg.sources_json)) {
              rawSources = asstMsg.sources_json;
            } else if (asstMsg.sources_json && typeof asstMsg.sources_json === 'object') {
              if (Array.isArray(asstMsg.sources_json.sources)) {
                rawSources = asstMsg.sources_json.sources;
              }
            }
            const sources = rawSources.map((s: any) => ({
              type: s?.source_type || s?.type || 'memory',
              id: s?.id || 'src',
              title: s?.title || 'Source',
              detail: s?.summary || s?.details || s?.detail || '',
            }));

            turns.push({
              id: asstMsg.id,
              conversation_id: conv.id,
              patient_id: conv.patient_id,
              timestamp: asstMsg.created_at,
              patient_query: userMsg.content,
              assistant_response: asstMsg.content,
              intent_type: asstMsg.intent_type || 'general_conversation',
              confidence_score: asstMsg.confidence_score ?? 0.9,
              sources,
            });
          }
        }
      }
      return turns;
    }

    return Array.isArray(rawConvs) ? rawConvs : [];
    // Rule: No catch/mock fallback. Errors propagate to the UI.
  },
};
