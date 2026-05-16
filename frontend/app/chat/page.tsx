"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Send, Loader2, Sparkles, Network } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { NavBar } from "@/components/NavBar";
import { useAuth } from "@/lib/AuthContext";
import { ReactFlow, Background, Controls, useNodesState, useEdgesState, MarkerType } from "@xyflow/react";
import type { Node, Edge } from "@xyflow/react";
import "@xyflow/react/dist/style.css";

// ── Types ────────────────────────────────────────────────────────────────────
interface Message {
  role: "user" | "ai";
  content: string;
}

// ── Simulated AI response + graph generation ─────────────────────────────────
function generateGraphForQuery(query: string): { nodes: Node[]; edges: Edge[] } {
  // Detect keywords to produce a contextual demo graph
  const q = query.toLowerCase();

  const isHackathon = q.includes("hackathon") || q.includes("genai") || q.includes("google");
  const isDemoDay = q.includes("demo") || q.includes("accelerator") || q.includes("startup");
  const isConference = q.includes("conference") || q.includes("tech");

  const nodeStyle = {
    borderRadius: 10,
    padding: "8px 14px",
    fontSize: 12,
    fontWeight: 600,
    border: "1.5px solid",
  };

  const colors: Record<string, { bg: string; border: string; text: string }> = {
    event: { bg: "#18181b", border: "#18181b", text: "#fff" },
    shared: { bg: "#e0f2fe", border: "#0ea5e9", text: "#0369a1" },
    people: { bg: "#fef9c3", border: "#eab308", text: "#713f12" },
    tool: { bg: "#f0fdf4", border: "#22c55e", text: "#14532d" },
  };

  const mkNode = (
    id: string,
    label: string,
    x: number,
    y: number,
    type: keyof typeof colors
  ): Node => ({
    id,
    data: { label },
    position: { x, y },
    style: {
      ...nodeStyle,
      background: colors[type].bg,
      borderColor: colors[type].border,
      color: colors[type].text,
    },
  });

  const mkEdge = (
    id: string,
    source: string,
    target: string,
    label: string
  ): Edge => ({
    id,
    source,
    target,
    label,
    animated: true,
    labelStyle: { fontSize: 10, fill: "#71717a" },
    labelBgStyle: { fill: "#fff", fillOpacity: 0.9 },
    markerEnd: { type: MarkerType.ArrowClosed, color: "#a1a1aa" },
    style: { stroke: "#a1a1aa" },
  });

  if (isHackathon && isDemoDay) {
    return {
      nodes: [
        mkNode("e1", "Google GenAI Hackathon", 0, 0, "event"),
        mkNode("e2", "Accelerator Demo Day", 480, 0, "event"),
        mkNode("s1", "AI / ML Theme", 240, -140, "shared"),
        mkNode("s2", "Google Workspace Tools", 240, -20, "shared"),
        mkNode("s3", "Judging Rubric Format", 240, 100, "shared"),
        mkNode("p1", "Startup Founders", 240, 220, "people"),
        mkNode("t1", "Google Forms", -120, 140, "tool"),
        mkNode("t2", "Google Sheets", 600, 140, "tool"),
      ],
      edges: [
        mkEdge("e1-s1", "e1", "s1", "focuses on"),
        mkEdge("e2-s1", "e2", "s1", "focuses on"),
        mkEdge("e1-s2", "e1", "s2", "uses"),
        mkEdge("e2-s2", "e2", "s2", "uses"),
        mkEdge("e1-s3", "e1", "s3", "shares format"),
        mkEdge("e2-s3", "e2", "s3", "shares format"),
        mkEdge("e2-p1", "e2", "p1", "targets"),
        mkEdge("e1-t1", "e1", "t1", "registration"),
        mkEdge("e2-t2", "e2", "t2", "grading"),
      ],
    };
  }

  if (isConference) {
    return {
      nodes: [
        mkNode("e1", "Standard Tech Conference", 0, 0, "event"),
        mkNode("e2", "Google GenAI Hackathon", 440, 0, "event"),
        mkNode("s1", "Developer Community", 220, -130, "shared"),
        mkNode("s2", "Google Workspace", 220, 40, "shared"),
        mkNode("p1", "DevRel Teams", -100, 140, "people"),
        mkNode("t1", "Google Docs", 520, 140, "tool"),
      ],
      edges: [
        mkEdge("e1-s1", "e1", "s1", "attracts"),
        mkEdge("e2-s1", "e2", "s1", "attracts"),
        mkEdge("e1-s2", "e1", "s2", "uses"),
        mkEdge("e2-s2", "e2", "s2", "uses"),
        mkEdge("e1-p1", "e1", "p1", "run by"),
        mkEdge("e2-t1", "e2", "t1", "rubric in"),
      ],
    };
  }

  // Generic fallback
  return {
    nodes: [
      mkNode("e1", "Event A", 0, 0, "event"),
      mkNode("e2", "Event B", 400, 0, "event"),
      mkNode("s1", "Shared Theme", 200, -120, "shared"),
      mkNode("s2", "Common Tooling", 200, 80, "tool"),
    ],
    edges: [
      mkEdge("e1-s1", "e1", "s1", "relates to"),
      mkEdge("e2-s1", "e2", "s1", "relates to"),
      mkEdge("e1-s2", "e1", "s2", "uses"),
      mkEdge("e2-s2", "e2", "s2", "uses"),
    ],
  };
}

function simulateResponse(query: string): string {
  const q = query.toLowerCase();
  if (q.includes("hackathon") && q.includes("demo")) {
    return `Yes — there's a strong connection between the **Google GenAI Hackathon** and the **Accelerator Demo Day** playbooks.\n\n**Shared elements:**\n- Both center on an AI/ML theme and target builders & founders\n- Both use Google Workspace (Docs, Sheets, Forms) for logistics\n- They share a similar judging rubric format (criteria-based scoring)\n- Startup founders who participate in hackathons are often the same cohort that presents at Demo Days\n\nThe knowledge graph shows how these two events are connected through shared themes, tools, and people. You could **fork** the Hackathon playbook and adapt it into a Demo Day with minimal changes.`;
  }
  if (q.includes("conference")) {
    return `The **Standard Tech Conference** and **Google GenAI Hackathon** share a significant overlap:\n\n- Both attract the same developer community\n- Both use Google Workspace as operational tooling\n- DevRel teams often run both types of events\n\nThe graph highlights these shared nodes. Consider adapting the Conference's CFP process into your Hackathon's team submission flow.`;
  }
  return `I can see some potential connections between those events. The knowledge graph above highlights shared themes, tools, and communities. Try asking about specific pairs like *"How does the GenAI Hackathon connect to the Accelerator Demo Day?"* for a more detailed analysis.`;
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
    if (!text) return;

    setInput("");
    setMessages((m) => [...m, { role: "user", content: text }]);
    setThinking(true);
    setShowGraph(false);

    // Simulate network delay
    await new Promise((r) => setTimeout(r, 1600));

    const response = simulateResponse(text);
    const graph = generateGraphForQuery(text);

    setMessages((m) => [...m, { role: "ai", content: response }]);
    setNodes(graph.nodes);
    setEdges(graph.edges);
    setGraphKey((k) => k + 1);
    setThinking(false);
    setShowGraph(true);
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
    <div className="min-h-screen bg-zinc-50 flex flex-col">
      <NavBar />

      <div className="container mx-auto px-6 flex flex-1 overflow-hidden" style={{ height: "calc(100vh - 64px)" }}>
        {/* ── Chat panel ───────────────────────────────────────────────── */}
        <div className="w-full lg:w-[420px] flex flex-col border-r bg-white shrink-0">
          {/* Header */}
          <div className="px-6 py-5 border-b">
            <div className="flex items-center gap-2 mb-1">
              <div className="h-7 w-7 bg-zinc-900 rounded-lg flex items-center justify-center">
                <Sparkles className="h-3.5 w-3.5 text-white" />
              </div>
              <h1 className="font-semibold text-zinc-900">Explore Connections</h1>
            </div>
            <p className="text-xs text-zinc-500">
              Ask about event relationships and see the knowledge graph.
            </p>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
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
                  className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed whitespace-pre-wrap ${
                    msg.role === "user"
                      ? "bg-zinc-900 text-white rounded-br-sm"
                      : "bg-zinc-100 text-zinc-800 rounded-bl-sm"
                  }`}
                  dangerouslySetInnerHTML={{
                    __html: msg.content
                      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
                      .replace(/\n/g, "<br/>"),
                  }}
                />
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

          {/* Input */}
          <div className="px-4 py-4 border-t bg-white">
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

        {/* ── Graph panel ──────────────────────────────────────────────── */}
        <div className="flex-1 flex flex-col hidden lg:flex">
          {showGraph ? (
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
