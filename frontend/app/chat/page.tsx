"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Send,
  Loader2,
  Network,
  PanelRightClose,
  PanelRightOpen,
  Sparkles,
  Target,
  TrendingUp,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { NavBar } from "@/components/NavBar";
import { ChatMarkdown } from "@/components/ChatMarkdown";
import { useAuth } from "@/lib/AuthContext";
import { cn } from "@/lib/utils";
import { ReactFlow, Background, Controls, useNodesState, useEdgesState, MarkerType } from "@xyflow/react";
import type { Node, Edge } from "@xyflow/react";
import "@xyflow/react/dist/style.css";

// ── Types ────────────────────────────────────────────────────────────────────
interface Message {
  role: "user" | "ai";
  content: string;
}

// `explore` traces relationships across events; `match` scores past
// participants by track record — the outcome-scoring learning loop.
type ChatMode = "explore" | "match";

// ── Backend types ────────────────────────────────────────────────────────────
type NodeType = "event" | "shared" | "people" | "tool";

interface BackendNode {
  id: string;
  label: string;
  type: NodeType;
  x: number;
  y: number;
}

interface BackendEdge {
  id: string;
  source: string;
  target: string;
  label: string;
}

interface EcosystemResponse {
  status: string;
  reply: string;
  nodes: BackendNode[];
  edges: BackendEdge[];
}

interface MatchCandidate {
  name: string;
  organization: string;
  role: string;
  fit_score: number;
  engagement_score: number;
  track_record: string;
  evidence: string[];
  reason: string;
}

interface MatchResponse {
  status: string;
  reply: string;
  learned_from: number;
  candidates: MatchCandidate[];
}

// ── Node + edge styling (frontend-only concern) ──────────────────────────────
const NODE_COLORS: Record<NodeType, { bg: string; border: string; text: string }> = {
  event: { bg: "#18181b", border: "#18181b", text: "#fff" },
  shared: { bg: "#e0f2fe", border: "#0ea5e9", text: "#0369a1" },
  people: { bg: "#fef9c3", border: "#eab308", text: "#713f12" },
  tool: { bg: "#f0fdf4", border: "#22c55e", text: "#14532d" },
};

function styleNode(n: BackendNode): Node {
  const color = NODE_COLORS[n.type] ?? NODE_COLORS.shared;
  return {
    id: n.id,
    data: { label: n.label },
    position: { x: n.x, y: n.y },
    style: {
      borderRadius: 10,
      padding: "8px 14px",
      fontSize: 12,
      fontWeight: 600,
      border: "1.5px solid",
      background: color.bg,
      borderColor: color.border,
      color: color.text,
    },
  };
}

function styleEdge(e: BackendEdge): Edge {
  return {
    id: e.id,
    source: e.source,
    target: e.target,
    label: e.label,
    animated: true,
    labelStyle: { fontSize: 10, fill: "#71717a" },
    labelBgStyle: { fill: "#fff", fillOpacity: 0.9 },
    markerEnd: { type: MarkerType.ArrowClosed, color: "#a1a1aa" },
    style: { stroke: "#a1a1aa" },
  };
}

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8001";

// ── Skeleton shown while the graph is being generated ─────────────────────────
const SKELETON_NODES = [
  { left: "50%", top: "44%", w: 132, h: 46 },
  { left: "20%", top: "20%", w: 104, h: 38 },
  { left: "78%", top: "22%", w: 104, h: 38 },
  { left: "24%", top: "74%", w: 104, h: 38 },
  { left: "76%", top: "72%", w: 104, h: 38 },
  { left: "88%", top: "47%", w: 92, h: 36 },
];

function GraphSkeleton() {
  return (
    <div className="flex-1 relative bg-zinc-50 overflow-hidden">
      <svg
        className="absolute inset-0 h-full w-full"
        viewBox="0 0 100 100"
        preserveAspectRatio="none"
      >
        {SKELETON_NODES.slice(1).map((n, i) => (
          <line
            key={i}
            x1="50"
            y1="47"
            x2={parseFloat(n.left)}
            y2={parseFloat(n.top)}
            stroke="#e4e4e7"
            strokeWidth="0.4"
            strokeDasharray="1.5 1.5"
          />
        ))}
      </svg>
      {SKELETON_NODES.map((n, i) => (
        <div
          key={i}
          className="absolute -translate-x-1/2 -translate-y-1/2 rounded-xl bg-zinc-200 animate-pulse"
          style={{
            left: n.left,
            top: n.top,
            width: n.w,
            height: n.h,
            animationDelay: `${i * 120}ms`,
          }}
        />
      ))}
      <div className="absolute bottom-6 left-1/2 -translate-x-1/2 flex items-center gap-2 text-xs font-medium text-zinc-400">
        <span className="h-1.5 w-1.5 rounded-full bg-zinc-400 animate-bounce [animation-delay:0ms]" />
        <span className="h-1.5 w-1.5 rounded-full bg-zinc-400 animate-bounce [animation-delay:150ms]" />
        <span className="h-1.5 w-1.5 rounded-full bg-zinc-400 animate-bounce [animation-delay:300ms]" />
        Generating knowledge graph…
      </div>
    </div>
  );
}

// ── Smart Match panel ─────────────────────────────────────────────────────────
function ScoreBar({ label, value, icon: Icon }: { label: string; value: number; icon: LucideIcon }) {
  const pct = Math.max(0, Math.min(100, value));
  return (
    <div className="flex-1">
      <div className="flex items-center justify-between mb-1">
        <span className="flex items-center gap-1 text-[11px] font-medium text-zinc-500">
          <Icon className="h-3 w-3" />
          {label}
        </span>
        <span className="text-[11px] font-semibold text-zinc-700 tabular-nums">{pct}</span>
      </div>
      <div className="h-1.5 rounded-full bg-zinc-100 overflow-hidden">
        <div className="h-full rounded-full bg-emerald-500 transition-[width] duration-500" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function CandidateCard({ c, rank }: { c: MatchCandidate; rank: number }) {
  const initials = c.name
    .split(/\s+/)
    .map((w) => w[0])
    .filter(Boolean)
    .slice(0, 2)
    .join("")
    .toUpperCase();
  const subtitle = [c.role, c.organization].filter(Boolean).join(" · ") || "Ecosystem participant";
  return (
    <div className="rounded-xl border border-zinc-200 bg-white p-4 shadow-sm">
      <div className="flex items-start gap-3">
        <div className="h-10 w-10 shrink-0 rounded-full bg-zinc-900 text-white flex items-center justify-center text-xs font-bold">
          {initials || "?"}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <h3 className="font-semibold text-zinc-900 text-sm truncate">{c.name}</h3>
            <span className="ml-auto shrink-0 text-[11px] font-bold text-zinc-300">#{rank}</span>
          </div>
          <p className="text-xs text-zinc-500 truncate">{subtitle}</p>
        </div>
      </div>

      <div className="mt-3.5 flex gap-3">
        <ScoreBar label="Fit" value={c.fit_score} icon={Target} />
        <ScoreBar label="Track record" value={c.engagement_score} icon={TrendingUp} />
      </div>

      {c.track_record && (
        <p className="mt-3 text-xs text-emerald-800 bg-emerald-50 border border-emerald-100 rounded-lg px-2.5 py-1.5">
          {c.track_record}
        </p>
      )}
      {c.reason && <p className="mt-2 text-xs leading-relaxed text-zinc-600">{c.reason}</p>}

      {c.evidence.length > 0 && (
        <div className="mt-2.5 flex flex-wrap gap-1.5">
          {c.evidence.map((e, i) => (
            <span
              key={i}
              className="inline-flex items-center gap-1 rounded-md bg-zinc-100 px-2 py-0.5 text-[10.5px] font-medium text-zinc-600"
            >
              <Network className="h-2.5 w-2.5" />
              {e}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

function MatchSkeleton() {
  return (
    <div className="flex-1 overflow-hidden bg-zinc-50">
      <div className="p-4 space-y-3">
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            className="rounded-xl border border-zinc-200 bg-white p-4 animate-pulse"
            style={{ animationDelay: `${i * 140}ms` }}
          >
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-full bg-zinc-200" />
              <div className="flex-1 space-y-2">
                <div className="h-3 w-1/2 rounded bg-zinc-200" />
                <div className="h-2.5 w-1/3 rounded bg-zinc-100" />
              </div>
            </div>
            <div className="mt-4 flex gap-3">
              <div className="h-1.5 flex-1 rounded-full bg-zinc-100" />
              <div className="h-1.5 flex-1 rounded-full bg-zinc-100" />
            </div>
          </div>
        ))}
      </div>
      <div className="flex items-center justify-center gap-2 text-xs font-medium text-zinc-400">
        <span className="h-1.5 w-1.5 rounded-full bg-zinc-400 animate-bounce [animation-delay:0ms]" />
        <span className="h-1.5 w-1.5 rounded-full bg-zinc-400 animate-bounce [animation-delay:150ms]" />
        <span className="h-1.5 w-1.5 rounded-full bg-zinc-400 animate-bounce [animation-delay:300ms]" />
        Scoring past engagements…
      </div>
    </div>
  );
}

function MatchPanel({
  candidates,
  learnedFrom,
  hasRun,
}: {
  candidates: MatchCandidate[];
  learnedFrom: number;
  hasRun: boolean;
}) {
  if (!hasRun || candidates.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center text-zinc-400 gap-4 bg-zinc-50">
        <div className="h-16 w-16 rounded-2xl bg-emerald-50 flex items-center justify-center">
          <Sparkles className="h-8 w-8 text-emerald-400" />
        </div>
        <div className="text-center max-w-xs">
          <p className="text-sm font-medium text-zinc-500">Smart Match</p>
          <p className="text-xs text-zinc-400 mt-1">
            Describe who you need. The AI scores past participants by their track record across
            every engagement on the platform.
          </p>
        </div>
      </div>
    );
  }
  return (
    <div className="flex-1 flex flex-col bg-zinc-50 overflow-hidden">
      <div className="px-6 py-3.5 border-b bg-white flex items-center gap-2.5 shrink-0">
        <div className="h-8 w-8 rounded-lg bg-emerald-50 flex items-center justify-center shrink-0">
          <Sparkles className="h-4 w-4 text-emerald-600" />
        </div>
        <div>
          <p className="text-sm font-semibold text-zinc-900">Smart Match results</p>
          <p className="text-xs text-zinc-500">
            Scored against {learnedFrom} past engagement{learnedFrom === 1 ? "" : "s"} in the ecosystem
          </p>
        </div>
      </div>
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {candidates.map((c, i) => (
          <CandidateCard key={`${c.name}-${i}`} c={c} rank={i + 1} />
        ))}
      </div>
    </div>
  );
}

// ── Component ─────────────────────────────────────────────────────────────────
export default function ChatPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const bottomRef = useRef<HTMLDivElement>(null);

  const [chatMode, setChatMode] = useState<ChatMode>("explore");
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "ai",
      content:
        "Hi! I map relationships across the ecosystem.\n\n**Connections** traces how events link together. **Smart Match** scores past participants by track record to recommend mentors, sponsors, and partners for your next programme.",
    },
  ]);
  const [input, setInput] = useState("");
  const [thinking, setThinking] = useState(false);
  const [showGraph, setShowGraph] = useState(false);
  const [graphKey, setGraphKey] = useState(0);
  const [chatOpen, setChatOpen] = useState(true);

  // Smart Match state
  const [candidates, setCandidates] = useState<MatchCandidate[]>([]);
  const [learnedFrom, setLearnedFrom] = useState(0);
  const [matchHasRun, setMatchHasRun] = useState(false);

  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  useEffect(() => {
    if (!loading && !user) router.replace("/onboarding/login");
  }, [user, loading, router]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, thinking]);

  const sendMessage = async () => {
    const text = input.trim();
    if (!text || !user || thinking) return;

    setInput("");
    const nextHistory = [...messages, { role: "user" as const, content: text }];
    setMessages(nextHistory);
    setThinking(true);

    const apiHistory = nextHistory.map((m) => ({
      role: m.role === "ai" ? ("ai" as const) : ("user" as const),
      text: m.content,
    }));

    try {
      const idToken = await user.getIdToken();

      if (chatMode === "match") {
        const res = await fetch(`${BACKEND_URL}/api/match/recommend`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${idToken}`,
          },
          body: JSON.stringify({ query: text, role: "any", history: apiHistory }),
        });
        if (!res.ok) throw new Error(`Backend returned ${res.status}`);
        const data: MatchResponse = await res.json();

        setMessages((m) => [...m, { role: "ai", content: data.reply || "(no reply)" }]);
        setCandidates(data.candidates);
        setLearnedFrom(data.learned_from);
        setMatchHasRun(true);
      } else {
        setShowGraph(false);
        const res = await fetch(`${BACKEND_URL}/api/chat/ecosystem`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${idToken}`,
          },
          body: JSON.stringify({ query: text, history: apiHistory }),
        });
        if (!res.ok) throw new Error(`Backend returned ${res.status}`);
        const data: EcosystemResponse = await res.json();

        setMessages((m) => [...m, { role: "ai", content: data.reply || "(no reply)" }]);
        setNodes(data.nodes.map(styleNode));
        setEdges(data.edges.map(styleEdge));
        setGraphKey((k) => k + 1);
        setShowGraph(data.nodes.length > 0);
      }
    } catch (err) {
      console.error("Chat request failed:", err);
      setMessages((m) => [
        ...m,
        {
          role: "ai",
          content:
            "I couldn't reach the backend just now. Make sure the FastAPI server is running on :8000, then try again.",
        },
      ]);
    } finally {
      setThinking(false);
    }
  };

  if (loading || !user) {
    return (
      <div className="min-h-screen bg-zinc-50">
        <NavBar />
        <div className="flex justify-center items-center h-[60vh]">
          <div className="h-8 w-8 rounded-full border-2 border-zinc-300 border-t-zinc-900 animate-spin" />
        </div>
      </div>
    );
  }

  const placeholder =
    chatMode === "match"
      ? "Who should mentor my AI hackathon?"
      : "How do these two events connect?";

  return (
    <div className="h-screen bg-zinc-50 flex flex-col overflow-hidden">
      <NavBar />

      <div className="w-full flex flex-row-reverse flex-1 min-h-0 overflow-hidden">
        {/* ── Chat panel (right) ───────────────────────────────────────── */}
        <div
          className={`flex flex-col bg-white shrink-0 overflow-hidden transition-[width] duration-300 ${chatOpen ? "w-full lg:w-[420px] border-l" : "w-full lg:w-0 lg:border-0"
            }`}
        >
          {/* Header — pinned, never scrolls */}
          <div className="px-6 py-4 border-b shrink-0 bg-white">
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <h1 className="font-semibold text-zinc-900">Ecosystem Intelligence</h1>
                <p className="text-xs text-zinc-500 mt-0.5">
                  Trace relationships and score reusable connections.
                </p>
              </div>
              <button
                onClick={() => setChatOpen(false)}
                className="hidden lg:inline-flex h-8 w-8 items-center justify-center rounded-lg text-zinc-400 hover:bg-zinc-100 hover:text-zinc-700 transition-colors shrink-0"
                title="Collapse chat"
                aria-label="Collapse chat"
              >
                <PanelRightClose className="h-4 w-4" />
              </button>
            </div>

            {/* Mode toggle */}
            <div className="mt-3 inline-flex rounded-lg bg-zinc-100 p-0.5">
              {(
                [
                  { id: "explore" as ChatMode, label: "Connections", icon: Network },
                  { id: "match" as ChatMode, label: "Smart Match", icon: Sparkles },
                ]
              ).map((m) => (
                <button
                  key={m.id}
                  onClick={() => setChatMode(m.id)}
                  className={cn(
                    "inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition-colors",
                    chatMode === m.id
                      ? "bg-white text-zinc-900 shadow-sm"
                      : "text-zinc-500 hover:text-zinc-700",
                  )}
                >
                  <m.icon className="h-3.5 w-3.5" />
                  {m.label}
                </button>
              ))}
            </div>
          </div>

          {/* Messages — the only scrollable region */}
          <div className="flex-1 min-h-0 overflow-y-auto px-4 py-4 space-y-4">
            {messages.map((msg, i) => (
              <div
                key={i}
                className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
              >
                {msg.role === "ai" && (
                  <div className="h-6 w-6 bg-zinc-900 rounded-full flex items-center justify-center mr-2 mt-0.5 shrink-0">
                    <span className="text-white text-xs font-bold">g</span>
                  </div>
                )}
                <div
                  className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${msg.role === "user"
                      ? "bg-zinc-900 text-white rounded-br-sm whitespace-pre-wrap"
                      : "bg-zinc-100 text-zinc-800 rounded-bl-sm"
                    }`}
                >
                  {msg.role === "ai" ? (
                    <ChatMarkdown content={msg.content} />
                  ) : (
                    msg.content
                  )}
                </div>
              </div>
            ))}

            {thinking && (
              <div className="flex justify-start items-center gap-2">
                <div className="h-6 w-6 bg-zinc-900 rounded-full flex items-center justify-center shrink-0">
                  <span className="text-white text-xs font-bold">g</span>
                </div>
                <div className="bg-zinc-100 rounded-2xl px-4 py-3 flex items-center gap-1.5">
                  <span className="h-1.5 w-1.5 rounded-full bg-zinc-400 animate-bounce [animation-delay:0ms]" />
                  <span className="h-1.5 w-1.5 rounded-full bg-zinc-400 animate-bounce [animation-delay:150ms]" />
                  <span className="h-1.5 w-1.5 rounded-full bg-zinc-400 animate-bounce [animation-delay:300ms]" />
                </div>
              </div>
            )}

            <div ref={bottomRef} />
          </div>

          {/* Input — pinned */}
          <div className="px-4 py-4 border-t bg-white shrink-0">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                sendMessage();
              }}
              className="flex gap-2"
            >
              <Input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder={placeholder}
                className="flex-1 text-sm"
                disabled={thinking}
              />
              <Button
                type="submit"
                disabled={!input.trim() || thinking}
                size="sm"
                className="bg-zinc-900 hover:bg-zinc-700 text-white h-10 w-10 p-0 shrink-0"
              >
                {thinking ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
              </Button>
            </form>
          </div>
        </div>

        {/* ── Result panel (left) ──────────────────────────────────────── */}
        <div className="flex-1 flex-col hidden lg:flex relative">
          {!chatOpen && (
            <button
              onClick={() => setChatOpen(true)}
              className="absolute top-4 right-4 z-10 inline-flex items-center gap-1.5 rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm font-medium text-zinc-700 shadow-sm hover:bg-zinc-50 transition-colors"
            >
              <PanelRightOpen className="h-4 w-4" />
              Chat
            </button>
          )}

          {chatMode === "match" ? (
            thinking ? (
              <MatchSkeleton />
            ) : (
              <MatchPanel candidates={candidates} learnedFrom={learnedFrom} hasRun={matchHasRun} />
            )
          ) : thinking ? (
            <GraphSkeleton />
          ) : showGraph ? (
            <ReactFlow
              key={graphKey}
              nodes={nodes}
              edges={edges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              fitView
              fitViewOptions={{ padding: 0.3 }}
              className="bg-zinc-50"
              nodesConnectable={false}
            >
              <Background color="#e4e4e7" gap={20} />
              <Controls />
            </ReactFlow>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center text-zinc-400 gap-4">
              <div className="h-16 w-16 rounded-2xl bg-zinc-100 flex items-center justify-center">
                <Network className="h-8 w-8 text-zinc-300" />
              </div>
              <div className="text-center">
                <p className="text-sm font-medium text-zinc-500">Knowledge Graph</p>
                <p className="text-xs text-zinc-400 mt-1">
                  Ask about two events to see their connection visualised here.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
