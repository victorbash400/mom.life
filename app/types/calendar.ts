export type CalendarPreferences = {
  enabled: boolean;
  reminder_method: "popup" | "email";
  reminder_minutes: 10 | 30 | 60 | 1440;
};

export type CalendarEvent = {
  id: string;
  title: string;
  start: string;
  end: string;
  all_day: boolean;
  location: string;
  url: string;
};

export type CalendarState = {
  connected: boolean;
  writable: boolean;
  events: CalendarEvent[];
  preferences: CalendarPreferences;
};
