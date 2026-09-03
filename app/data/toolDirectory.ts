import { CalendarDays, CheckSquare2, FileText, Mail, NotebookPen, ShoppingBasket, type LucideIcon } from "lucide-react";

export type ToolGroup = "Family essentials" | "Planning";
export type ToolDefinition = { id: string; name: string; description: string; group: ToolGroup; color: string; icon: LucideIcon; permissions: string[] };

export const toolDirectory: ToolDefinition[] = [
  { id: "google-calendar", name: "Google Calendar", description: "Plan appointments, school, and family events", group: "Family essentials", color: "#4b8bf4", icon: CalendarDays, permissions: ["View calendars you choose", "Create and update family events"] },
  { id: "gmail", name: "Gmail", description: "Find and manage important family email", group: "Family essentials", color: "#d85c52", icon: Mail, permissions: ["Search messages you allow", "Draft messages for your approval"] },
  { id: "google-drive", name: "Google Drive", description: "Work with family documents and files", group: "Family essentials", color: "#51a96b", icon: FileText, permissions: ["Find files you choose", "Create and update family documents"] },
  { id: "notion", name: "Notion", description: "Keep family notes and shared plans together", group: "Planning", color: "#4b4743", icon: NotebookPen, permissions: ["Search connected pages", "Create and update approved notes"] },
  { id: "todoist", name: "Todoist", description: "Coordinate lists and household tasks", group: "Planning", color: "#db655b", icon: CheckSquare2, permissions: ["Read selected projects", "Create and update tasks"] },
  { id: "instacart", name: "Instacart", description: "Build and manage household shopping lists", group: "Planning", color: "#4c9b52", icon: ShoppingBasket, permissions: ["Search products", "Prepare shopping carts for approval"] },
];
