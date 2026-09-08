export type IntakeStatus = "queued" | "processing" | "completed" | "failed";
export type IntakeAction = "record_only" | "resume_goal" | "create_goal" | "request_attention" | "";

export type IntakeActivity = {
  id: string;
  kind: string;
  summary: string;
  detail: Record<string, unknown>;
  created_at: string;
};

export type IncomingItem = {
  id: string;
  family_id: string;
  source: string;
  provider_event_id: string;
  correlation: string;
  sender: string;
  subject: string;
  content: string;
  payload: Record<string, unknown>;
  status: IntakeStatus;
  action: IntakeAction;
  reason: string;
  child_id: string;
  goal_id: string;
  attention_required: boolean;
  failure: string;
  created_at: string;
  processed_at: string | null;
  activities: IntakeActivity[];
};
