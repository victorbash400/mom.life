import type { IncomingItem } from "./intake";

export type SecurityAlertLevel = "urgent" | "important" | "all";
export type SecurityStatus = "queued" | "processing" | "completed" | "failed";

export type SecuritySettings = {
  family_id: string;
  enabled: boolean;
  alert_level: SecurityAlertLevel;
  instructions: string;
  sources: string[];
  child_ids: string[];
  depth: "item" | "recent";
  review_mode: "incoming" | "manual";
  channel: "in_app";
  updated_at: string;
};

export type SecurityActivity = {
  id: string;
  kind: string;
  summary: string;
  detail: Record<string, unknown>;
  created_at: string;
};

export type SecurityReview = {
  id: string;
  family_id: string;
  incoming_id: string;
  status: SecurityStatus;
  action: "" | "ignore" | "alert";
  severity: "" | "low" | "moderate" | "high" | "critical";
  category: string;
  summary: string;
  reason: string;
  child_id: string;
  dismissed: boolean;
  failure: string;
  created_at: string;
  processed_at: string | null;
  incoming: IncomingItem | null;
  activities: SecurityActivity[];
};

export type SecuritySnapshot = { settings: SecuritySettings; reviews: SecurityReview[] };
