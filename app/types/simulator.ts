export type SimulatorProfile = { id: string; name: string; role: "adult" | "child"; phone_number?: string };
export type SimulatorConnection = { id: string; connected: boolean };
export type SimulatorMessage = { id: string; profile_id: string; direction: "incoming" | "outgoing"; body: string; sender?: string; inbox_message?: boolean; created_at: string };
export type SimulatorHealthValues = { step_count?: number; active_energy?: number; walking_running_distance?: number; heart_rate?: number; sleep_analysis?: number };
export type SimulatorState = {
  profiles: SimulatorProfile[];
  connections: SimulatorConnection[];
  messages: SimulatorMessage[];
  health: { date: string; profiles: Record<string, SimulatorHealthValues> };
};
