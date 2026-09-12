export type Automation = { id: string; goal_id: string; task_text: string; child_id: string; task_status: string; instruction: string; trigger: "time" | "health" | "incoming"; schedule: string; timezone: string; enabled: boolean; scheduler_state: string; failure: string; last_checked_at: string | null; last_result: string };
export type AutomationNotification = { id: string; goal_id: string; message: string; read_at: string | null };
export type AutomationState = { automations: Automation[]; notifications: AutomationNotification[]; scheduler_ready: boolean; events_connected: boolean };
