"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Send, Loader2, Network, PanelRightClose, PanelRightOpen } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { NavBar } from "@/components/NavBar";
import { ChatMarkdown } from "@/components/ChatMarkdown";
import { useAuth } from "@/lib/AuthContext";
import { ReactFlow, Background, Controls, useNodesState, useEdgesState, MarkerType } from "@xyflow/react";
import type { Node, Edge } from "@xyflow/react";
import "@xyflow/react/dist/style.css";

// ── Types ────────────────────────────────────────────────────────────────────
interface Message {
  role: "user" | "ai";
  content: string;
}

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

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000";

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

// ── Component ─────────────────────────────────────────────────────────────────
export default function ChatPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const bottomRef = useRef<HTMLDivElement>(null);

  const [messages, setMessages] = useState<Message[]>([
    {
      role: "ai",
      content:
        "Hi! I can help you discover connections between events in the ecosystem. Try asking something like:\n\n**\"How does the Google GenAI Hackathon connect to the Accelerator Demo Day?\"**",
    },
  ]);
  const [input, setInput] = useState("");
  const [thinking, setThinking] = useState(false);
  const [showGraph, setShowGraph] = useState(false);
  const [graphKey, setGraphKey] = useState(0);
  const [chatOpen, setChatOpen] = useState(true);

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
    if (!text || !user) return;

    setInput("");
    const nextHistory = [...messages, { role: "user" as const, content: text }];
    setMessages(nextHistory);
    setThinking(true);
    setShowGraph(false);

    try {
      const idToken = await user.getIdToken();
      const res = await fetch(`${BACKEND_URL}/api/chat/ecosystem`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${idToken}`,
        },
        body: JSON.stringify({
          query: text,
          history: nextHistory.map((m) => ({
            role: m.role === "ai" ? "ai" : "user",
            text: m.content,
          })),
        }),
      });

      if (!res.ok) throw new Error(`Backend returned ${res.status}`);
      const data: EcosystemResponse = await res.json();

      setMessages((m) => [...m, { role: "ai", content: data.reply || "(no reply)" }]);
      setNodes(data.nodes.map(styleNode));
      setEdges(data.edges.map(styleEdge));
      setGraphKey((k) => k + 1);
      setShowGraph(data.nodes.length > 0);
    } catch (err) {
      console.error("Ecosystem chat failed:", err);
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

  return (
    <div className="h-screen bg-zinc-50 flex flex-col overflow-hidden">
      <NavBar />

      <div className="w-full flex flex-row-reverse flex-1 min-h-0 overflow-hidden">
        {/* ── Chat panel (right) ───────────────────────────────────────── */}
        <div
          className={`flex flex-col bg-white shrink-0 overflow-hidden transition-[width] duration-300 ${
            chatOpen ? "w-full lg:w-[420px] border-l" : "w-full lg:w-0 lg:border-0"
          }`}
        >
          {/* Header — pinned, never scrolls */}
          <div className="px-6 py-4 border-b flex items-start justify-between gap-2 shrink-0 bg-white">
            <div className="min-w-0">
              <h1 className="font-semibold text-zinc-900">Explore Connections</h1>
              <p className="text-xs text-zinc-500 mt-0.5">
                Ask about event relationships and see the knowledge graph.
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
                  className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
                    msg.role === "user"
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
                placeholder="How do these two events connect?"
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

        {/* ── Graph panel (left) ───────────────────────────────────────── */}
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
          {thinking ? (
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
