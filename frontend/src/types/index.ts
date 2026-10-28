export type UserRole = 'PATIENT' | 'CAREGIVER' | 'DOCTOR' | 'ADMIN';

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  token_version: number;
}

export interface Patient {
  id: string;
  user_id: string;
  full_name: string;
  email?: string;
  date_of_birth?: string | null;
  preferred_language?: string;
  emergency_contact_name?: string | null;
  emergency_contact_phone?: string | null;
  medical_notes?: string | null;
  is_primary_caregiver?: boolean;
  caregiver_relationship?: string;
}

export interface CreatePatientInput {
  full_name: string;
  email: string;
  password: string;
  date_of_birth?: string | null;
  preferred_language?: string;
  emergency_contact_name?: string | null;
  emergency_contact_phone?: string | null;
  medical_notes?: string | null;
  caregiver_relationship?: string | null;
  is_primary_caregiver?: boolean;
}

export type MemoryType =
  | 'VISIT'
  | 'OUTING'
  | 'MEAL'
  | 'MEDICATION'
  | 'APPOINTMENT'
  | 'FAMILY_STORY'
  | 'GENERAL';

export type MediaType = 'IMAGE' | 'AUDIO' | 'VIDEO' | 'DOCUMENT';

export interface MemoryMedia {
  id: string;
  media_type: MediaType;
  file_url: string;
  original_filename?: string;
  mime_type?: string;
  caption?: string;
}

export interface Person {
  id: string;
  patient_id: string;
  name: string;
  relationship?: string;
  description?: string;
  photo_url?: string;
  is_active: boolean;
}

export interface Memory {
  id: string;
  patient_id: string;
  memory_type: MemoryType;
  title: string;
  description?: string;
  location?: string;
  event_date: string;
  is_significant: boolean;
  created_at: string;
  media?: MemoryMedia[];
  people?: Person[];
}

export type RoutineCategory =
  | 'MORNING'
  | 'AFTERNOON'
  | 'EVENING'
  | 'EXERCISE'
  | 'MEAL'
  | 'HYGIENE'
  | 'SOCIAL'
  | 'COGNITIVE'
  | 'GENERAL';

export interface Routine {
  id: string;
  patient_id: string;
  title: string;
  description?: string;
  category: RoutineCategory;
  scheduled_time: string;
  days_of_week: number;
  icon_emoji?: string;
  is_active: boolean;
}

export type MedicationFrequency =
  | 'ONCE_DAILY'
  | 'TWICE_DAILY'
  | 'THREE_TIMES_DAILY'
  | 'FOUR_TIMES_DAILY'
  | 'WEEKLY'
  | 'AS_NEEDED';

export type MedicationTiming =
  | 'BEFORE_BREAKFAST'
  | 'AFTER_BREAKFAST'
  | 'BEFORE_LUNCH'
  | 'AFTER_LUNCH'
  | 'BEFORE_DINNER'
  | 'AFTER_DINNER'
  | 'BEDTIME'
  | 'SPECIFIC_TIME';

export interface Medication {
  id: string;
  patient_id: string;
  name: string;
  dosage: string;
  frequency: MedicationFrequency;
  timing: MedicationTiming;
  scheduled_time?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  notes?: string | null;
  is_active: boolean;
}
export interface TimelineEntry {
  kind: 'routine' | 'medication' | 'event' | 'memory';
  id: string;
  title: string;
  description?: string | null;
  icon_emoji?: string | null;
  timestamp: string;
  display_time: string;
  metadata?: Record<string, any>;
}

export type GameType =
  | 'MEMORY_MATCH'
  | 'SEQUENCE_RECALL'
  | 'PICTURE_RECALL'
  | 'OBJECT_RECALL';

export type DifficultyLevel = 'EASY' | 'MEDIUM' | 'HARD';

export interface GameCatalogItem {
  id: string;
  game_type: GameType;
  name: string;
  description: string;
  instructions?: string;
  min_difficulty: DifficultyLevel;
  max_difficulty: DifficultyLevel;
  estimated_duration_seconds: number;
  icon_emoji: string;
}

export interface GameSession {
  id: string;
  patient_id: string;
  game_id: string;
  game_type?: GameType;
  status: 'IN_PROGRESS' | 'COMPLETED' | 'ABANDONED';
  difficulty_level: DifficultyLevel;
  score?: number;
  accuracy?: number;
  reaction_time_ms?: number;
  mistakes?: number;
  total_items?: number;
  correct_items?: number;
  next_difficulty?: DifficultyLevel;
  started_at: string;
  completed_at?: string;
  duration_seconds?: number;
}

export interface CPIMetrics {
  overall_score: number;
  change_vs_last_week: number | null;
  status: 'OPTIMAL' | 'STABLE' | 'ATTENTION';
  memory_recall: number | null;
  sequence_accuracy: number | null;
  reaction_time_score: number | null;
  completion_rate: number | null;
  historical_trends: {
    date: string;
    cpi: number;
    memory: number;
    sequence: number;
    reaction: number;
  }[];
}

export interface ExplainabilitySource {
  type: 'memory' | 'person' | 'routine' | 'medication' | 'event' | 'game_session' | 'cognitive_metric';
  id: string;
  title: string;
  detail?: string;
  relevance_score?: number;
}

export interface ConversationTurn {
  id: string;
  patient_id?: string;
  conversation_id: string;
  timestamp: string;
  patient_query: string;
  assistant_response: string;
  intent_type: string;
  confidence_score: number;
  llm_model_used?: string;
  sources: ExplainabilitySource[];
}

export interface ConfidenceInfo {
  score: number;
  level: 'HIGH' | 'MEDIUM' | 'LOW' | 'UNKNOWN';
  factors?: Record<string, number>;
}

export interface GroundedSource {
  source_type: string;
  id: string;
  title: string;
  summary?: string | null;
  date?: string | null;
  details?: string | null;
}

export interface AssistantResponse {
  answer: string;
  reply: string;
  intent: string;
  confidence: number | ConfidenceInfo;
  confidence_info?: ConfidenceInfo;
  sources: GroundedSource[];
  grounded: boolean;
  conversation_id: string;
  created_at: string;
}

export interface ChatMessageItem {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  intent?: string;
  confidence?: ConfidenceInfo;
  sources?: GroundedSource[];
  timestamp: string;
}

