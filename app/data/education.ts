import type { ChildProfile } from "../types/dashboard";
import type { EducationOverview } from "../types/education";

const overviews: Record<string, EducationOverview> = {
  amina: {
    summary: "Amina is progressing well overall. Reading is consistent, while fractions need a little more attention this week.",
    attendance: "96%",
    subjects: [
      { name: "Reading", focus: "Comprehension", progress: "Strong" },
      { name: "Mathematics", focus: "Fractions", progress: "Needs attention" },
      { name: "Science", focus: "Plant life", progress: "On track" },
    ],
    upcoming: [
      { title: "Fractions quiz", subject: "Mathematics", due: "Friday" },
      { title: "Reading log", subject: "Reading", due: "Monday" },
    ],
  },
  noah: {
    summary: "Noah is settling into the term well. Letter sounds are improving and his number work is steady.",
    attendance: "98%",
    subjects: [
      { name: "Language", focus: "Letter sounds", progress: "On track" },
      { name: "Numbers", focus: "Counting to 50", progress: "Strong" },
      { name: "Learning together", focus: "Taking turns", progress: "On track" },
    ],
    upcoming: [
      { title: "Sound book", subject: "Language", due: "Thursday" },
      { title: "Show and tell", subject: "Learning together", due: "Tuesday" },
    ],
  },
  lila: {
    summary: "Lila is building confidence through play, songs, and simple routines. Her language and coordination are developing steadily.",
    attendance: "—",
    subjects: [
      { name: "Language", focus: "New words", progress: "On track" },
      { name: "Movement", focus: "Balance and coordination", progress: "Strong" },
      { name: "Creative play", focus: "Colour and shape", progress: "On track" },
    ],
    upcoming: [],
  },
};

const emptyOverview: EducationOverview = { summary: "No education summary has been added yet.", attendance: "—", subjects: [], upcoming: [] };

export function educationOverview(child: ChildProfile) {
  return overviews[child.name.trim().toLowerCase()] ?? emptyOverview;
}
