type FamilyEvent = { type?: string; [key: string]: unknown };
type Subscriber = {
  onEvent: (event: FamilyEvent) => void;
  onConnection: (connected: boolean) => void;
};

const subscribers = new Set<Subscriber>();
let source: EventSource | undefined;

function connect() {
  if (source) return;
  source = new EventSource("/api/tasks/events");
  source.onopen = () => subscribers.forEach(({ onConnection }) => onConnection(true));
  source.onerror = () => subscribers.forEach(({ onConnection }) => onConnection(false));
  source.onmessage = ({ data }) => {
    try {
      const event = JSON.parse(data) as FamilyEvent;
      if (event.type === "connection_error") {
        subscribers.forEach(({ onConnection }) => onConnection(false));
        return;
      }
      subscribers.forEach(({ onEvent }) => onEvent(event));
    } catch {
      subscribers.forEach(({ onConnection }) => onConnection(false));
    }
  };
}

export function subscribeFamilyEvents(subscriber: Subscriber) {
  subscribers.add(subscriber);
  connect();
  return () => {
    subscribers.delete(subscriber);
    if (subscribers.size === 0) {
      source?.close();
      source = undefined;
    }
  };
}
