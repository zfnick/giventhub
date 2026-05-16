import type { GraphCategory, GraphItem, PlaybookGraphData } from "@/components/graph/PlaybookFlowClient";

interface GraphSourcePlaybook {
  title: string;
  author?: string;
  attendees?: string;
  category?: string;
  tags?: string[];
  context?: {
    challenge?: string;
    targetAudience?: string;
    venue?: string;
    techStack?: string;
  } | null;
  assets?: {
    name: string;
    type: string;
  }[];
  participants?: {
    name: string;
    role?: string;
    organization?: string;
    email?: string;
  }[];
  features?: string[];
}

const CONNECTOR_PATTERN = /\s+(?:and|or)\s+/gi;

function clean(value: string | undefined | null): string {
  return (value ?? "").replace(/\s+/g, " ").trim();
}

function sentence(value: string | undefined | null): string {
  return clean(value).replace(/[.]$/, "");
}

function splitHumanList(value: string | undefined | null): string[] {
  const normalized = clean(value)
    .replace(/\([^)]*\)/g, "")
    .replace(/\bfrom\s+university\s+to\s+mid-senior\s+level\b/gi, "")
    .replace(/\bwith\s+strong\s+interest\s+in\s+[^,.]+/gi, "")
    .replace(CONNECTOR_PATTERN, ", ");

  return normalized
    .split(/[;,]/)
    .map((item) => sentence(item.replace(/^(and|or)\s+/i, "")))
    .filter(Boolean);
}

function splitTechStack(value: string | undefined | null): GraphItem[] {
  const stack = clean(value);
  if (!stack) return [];

  return stack
    .split(/,\s+(?=[A-Z0-9][^,]*(?:\(|$))/)
    .map((item) => item.trim())
    .filter(Boolean)
    .map((item) => {
      const match = item.match(/^([^()]+?)(?:\s*\(([^)]+)\))?$/);
      const name = clean(match?.[1] ?? item);
      const role = clean(match?.[2] ?? "Workspace surface");
      return {
        name,
        role,
        detail: role === "Workspace surface" ? "Used in the event operating stack" : role,
      };
    });
}

function addCategory(
  categories: GraphCategory[],
  category: Omit<GraphCategory, "items"> & { items: GraphItem[] },
) {
  if (category.items.length === 0) return;
  categories.push(category);
}

export function buildPlaybookGraph(playbook: GraphSourcePlaybook): PlaybookGraphData {
  const categories: GraphCategory[] = [];
  const ctx = playbook.context;

  const audienceItems = splitHumanList(ctx?.targetAudience).map((name) => ({
    name,
    role: "Audience segment",
    detail: playbook.attendees
      ? `${playbook.attendees} expected attendees`
      : sentence(ctx?.targetAudience),
  }));
  if (audienceItems.length === 0 && playbook.attendees) {
    audienceItems.push({
      name: "Attendees",
      role: "Audience size",
      detail: `${playbook.attendees} expected attendees`,
    });
  }
  if (playbook.author) {
    audienceItems.unshift({
      name: playbook.author,
      role: "Organizer",
      detail: "Playbook owner",
    });
  }
  addCategory(categories, {
    id: "audience",
    label: "Audience",
    kind: "people",
    items: audienceItems,
  });

  // Participants — the full roster of everyone involved (organizers, mentors,
  // judges, speakers, sponsors, attendees). Click the node for the full list.
  const participantItems: GraphItem[] = (playbook.participants ?? [])
    .map((person) => {
      const name = clean(person.name);
      if (!name) return null;
      const org = clean(person.organization);
      const email = clean(person.email);
      return {
        name,
        role: clean(person.role) || "Participant",
        detail: [org, email].filter(Boolean).join(" · ") || "Involved in the event",
      };
    })
    .filter((item): item is GraphItem => item !== null);
  addCategory(categories, {
    id: "participants",
    label: "Participants",
    kind: "people",
    items: participantItems,
  });

  addCategory(categories, {
    id: "assets",
    label: "Workspace Assets",
    kind: "asset",
    items: (playbook.assets ?? []).map((asset) => ({
      name: asset.name,
      role: asset.type,
      detail: `Included ${asset.type} asset`,
    })),
  });

  addCategory(categories, {
    id: "tools",
    label: "Tool Stack",
    kind: "tool",
    items: splitTechStack(ctx?.techStack),
  });

  const operations: GraphItem[] = [];
  if (ctx?.venue) {
    operations.push({
      name: "Venue",
      role: "Operations",
      detail: sentence(ctx.venue),
    });
  }
  if (ctx?.challenge) {
    operations.push({
      name: "Challenge",
      role: "Event brief",
      detail: sentence(ctx.challenge),
    });
  }
  addCategory(categories, {
    id: "operations",
    label: "Operations",
    kind: "theme",
    items: operations,
  });

  addCategory(categories, {
    id: "workflow",
    label: "Workflow",
    kind: "theme",
    items: (playbook.features ?? []).map((feature) => ({
      name: feature,
      role: "Reusable step",
      detail: "Captured from the original event playbook",
    })),
  });

  const topicItems = [
    playbook.category,
    ...(playbook.tags ?? []),
  ]
    .map(clean)
    .filter(Boolean)
    .filter((value, index, list) => list.indexOf(value) === index)
    .map((tag) => ({
      name: tag,
      role: "Topic",
      detail: "Used for discovery and matching",
    }));
  addCategory(categories, {
    id: "topics",
    label: "Topics",
    kind: "theme",
    items: topicItems,
  });

  return {
    root_label: playbook.title || "Event",
    categories,
  };
}
