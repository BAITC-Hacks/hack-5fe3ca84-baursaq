export type Person = { employee_id: string; full_name: string; role?: string; grade?: string; department?: string };
export type Skill = { skill_id: string; name: string; current: number; required: number; gap: number; critical: boolean };
export type Profile = {
  employee: Person; target: {role: string; grade: string}; progress_pct: number; as_of_date: string;
  skills: Skill[]; history: {record_id: string; title: string; date: string; status: string}[];
};
export type Recommendation = {
  event_id: string; title: string; reason: string; format: string; duration_hours: number;
  evidence: {factor: string; source: string; text: string}[];
  projection: {progress_before: number; progress_after: number; changes: {name: string; before: number; after: number}[]};
};
export type Result = {mode: 'rules' | 'openai'; warning: string | null; empty_reason: string | null; duration_ms: number;
  recommendations: Recommendation[]; trace: {tool: string; summary: string; duration_ms: number}[]};
export type HR = {employee_count: number; skill_gaps: {skill_id: string; name: string; employee_count: number}[];
  no_next_step: {employee_id: string; full_name: string; reason: string}[];
  participation: {event_id: string; title: string; statuses: Record<string, number>}[]};
export type Session = {token: string; role: 'employee' | 'hr'; employee_id: string | null};
