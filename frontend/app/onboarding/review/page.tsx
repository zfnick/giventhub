"use client";

import { useState, useRef, useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { PlaybookFlowClient as PlaybookFlow, type PlaybookGraphData } from "@/components/graph/PlaybookFlowClient";
import { useAuth } from "@/lib/AuthContext";
import { apiFetch } from "@/lib/api";
import {
  Globe,
  Lock,
  X,
  Plus,
  Send,
  Bot,
  User,
  Upload,
  Paperclip,
  CalendarCheck,
  CalendarClock,
  ArrowLeft,
} from "lucide-react";

type Message = { role: "ai" | "user"; text: string };

const INITIAL_MESSAGES: Message[] = [
  {
    role: "ai",
    text: "I've built your playbook from the files I found. Is there anything I missed? You can paste a Google Drive link below and I'll pull the rest, or upload a file directly.",
  },
];

function ReviewPlaybookContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user } = useAuth();
  const timing = (searchParams.get("timing") ?? "past") as "past" | "upcoming";
  const [isPublic, setIsPublic] = useState(true);
  const [isPushing, setIsPushing] = useState(false);
  const [description, setDescription] = useState(
    "A premier showcase of student-led AI startups from Stanford. Includes registration flow, judge scoring rubric, and presentation schedule."
  );

  // Tags
  const [tags, setTags] = useState(["Hackathon", "Artificial Intelligence", "Demo Day"]);
  const [tagInput, setTagInput] = useState("");

  // Dynamic knowledge tree (draft-mode — not yet committed)
  const [graph, setGraph] = useState<PlaybookGraphData | null>(null);
  const [graphLoading, setGraphLoading] = useState(true);
  const draftTitle = "Stanford AI Demo Day 2026";
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await apiFetch(null, "/api/playbooks/graph", {
          method: "POST",
          json: {
            draft: {
              title: draftTitle,
              description,
              category: "Hackathon",
              tags,
            },
          },
        });
        if (cancelled) return;
        if (!res.ok) {
          console.error("Review graph failed:", res.status);
          setGraph(null);
          return;
        }
        setGraph(await res.json());
      } catch (err) {
        if (!cancelled) {
          console.error("Review graph error:", err);
          setGraph(null);
        }
      } finally {
        if (!cancelled) setGraphLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Chatbot
  const [messages, setMessages] = useState<Message[]>(INITIAL_MESSAGES);
  const [chatInput, setChatInput] = useState("");
  const chatEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = (overrideText?: string) => {
    const text = (overrideText ?? chatInput).trim();
    if (!text) return;
    setChatInput("");
    setMessages((prev) => [...prev, { role: "user", text }]);

    setTimeout(() => {
      const reply = text.toLowerCase().includes("drive.google.com")
        ? "Got it — I'm pulling data from that Drive link now. I'll update the knowledge map once I'm done."
        : "Noted! I've added that to the playbook. Anything else that's missing?";
      setMessages((prev) => [...prev, { role: "ai", text: reply }]);
    }, 800);
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    sendMessage(`I've uploaded a file: ${file.name}`);
  };

  const handleBack = () => {
    if (typeof window !== "undefined" && window.history.length > 1) {
      router.back();
      return;
    }
    router.push(timing === "upcoming" ? "/event/new" : "/onboarding/scan");
  };

  const backLabel = timing === "upcoming" ? "Back to planning" : "Back to import";

  const handlePublish = async () => {
    setIsPushing(true);
    try {
      if (!user) throw new Error("Not signed in");
      const idToken = await user.getIdToken();
      const res = await fetch("http://localhost:8000/api/commit", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${idToken}`,
        },
        body: JSON.stringify({
          title: "Stanford AI Demo Day 2026",
          description,
          is_public: isPublic,
          commit_message: "Initial save",
          tags,
          timing,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        router.push(`/playbooks/${data.playbook_id}`);
      } else {
        console.error("Commit failed:", res.status, await res.text());
        setIsPushing(false);
      }
    } catch (err) {
      console.error("Commit error:", err);
      setIsPushing(false);
    }
  };
  return (
    <div className="h-screen flex flex-col bg-white">
      <main className="flex-1 flex flex-col min-h-0 overflow-hidden">
        <div className="container mx-auto px-6 flex flex-1 min-h-0 overflow-hidden">
          {/* Left Panel: Configuration & Editor */}
          <div className="flex-1 overflow-y-auto border-r border-zinc-100 pr-12">
            <div className="pb-8 pt-8 space-y-10">
              {/* Page header */}
              <div className="bg-white space-y-2">
                <button
                  type="button"
                  onClick={handleBack}
                  className="inline-flex items-center gap-1.5 text-sm text-zinc-500 hover:text-zinc-900 transition-colors mb-2"
                >
                  <ArrowLeft className="h-4 w-4" />
                  {backLabel}
                </button>
                <div className="flex items-start justify-between gap-4">
                  <div className="space-y-2 min-w-0">
                    <h1 className="text-3xl font-bold tracking-tight">Save a new Playbook</h1>
                    <p className="text-sm text-zinc-500">
                      {timing === "past"
                        ? "We've extracted what happened — review and publish so others can replicate it."
                        : "We've scaffolded what you need — review the plan and publish to start running it."}
                    </p>
                  </div>
                  <div className="shrink-0 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-zinc-200 bg-zinc-50">
                    {timing === "past"
                      ? <CalendarCheck className="h-4 w-4 text-zinc-500" />
                      : <CalendarClock className="h-4 w-4 text-zinc-500" />}
                    <span className="text-xs font-semibold uppercase tracking-wider text-zinc-600">
                      {timing === "past" ? "Past event" : "Upcoming event"}
                    </span>
                  </div>
                </div>
              </div>

              {/* ── Section 1: General ── */}
              <section className="space-y-6">
                <div className="flex items-center gap-3">
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-zinc-900 text-white flex items-center justify-center text-sm font-bold">
                    1
                  </div>
                  <div>
                    <h2 className="text-lg font-bold">General</h2>
                    <p className="text-sm text-zinc-500">Name your playbook and give it a short summary.</p>
                  </div>
                </div>

                <div className="space-y-6 pl-11">
                  <div className="space-y-1.5">
                    <Label htmlFor="title" className="text-sm font-semibold">
                      Playbook Name <span className="text-red-400">*</span>
                    </Label>
                    <Input
                      id="title"
                      defaultValue="Stanford AI Demo Day 2026"
                      className="h-11 font-medium bg-zinc-50 border-zinc-200 focus-visible:ring-zinc-900 rounded-xl"
                      placeholder="e.g. Stanford AI Demo Day 2026"
                    />
                    <p className="text-xs text-zinc-400">Great playbook names are short and memorable.</p>
                  </div>

                  <div className="space-y-1.5">
                    <Label htmlFor="description" className="text-sm font-semibold">Description</Label>
                    <Textarea
                      id="description"
                      value={description}
                      onChange={(e) => setDescription(e.target.value.slice(0, 350))}
                      className="min-h-[120px] leading-relaxed resize-none bg-zinc-50 border-zinc-200 focus-visible:ring-zinc-900 rounded-xl p-3"
                      placeholder="What was this event about?"
                    />
                    <p className="text-xs text-zinc-400 font-mono">{description.length} / 350</p>
                  </div>

                  <div className="space-y-1.5">
                    <Label className="text-sm font-semibold">Topics</Label>
                    <div className="flex flex-wrap gap-2 mb-2">
                      {tags.map((tag) => (
                        <span key={tag} className="inline-flex items-center gap-1 px-3 py-1 rounded-md bg-zinc-100 text-zinc-700 text-xs font-bold border border-zinc-200">
                          {tag}
                          <button onClick={() => setTags(tags.filter(t => t !== tag))} className="hover:text-red-500">
                            <X className="h-3 w-3" />
                          </button>
                        </span>
                      ))}
                    </div>
                    <div className="relative">
                      <Input
                        value={tagInput}
                        onChange={(e) => setTagInput(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter" && tagInput.trim()) {
                            setTags([...tags, tagInput.trim()]);
                            setTagInput("");
                          }
                        }}
                        className="h-10 bg-zinc-50 border-zinc-200 focus-visible:ring-zinc-900 rounded-xl"
                        placeholder="Add topics (e.g. Hackathon, AI)..."
                      />
                      <Plus className="absolute right-3 top-3 h-4 w-4 text-zinc-400" />
                    </div>
                  </div>
                </div>
              </section>

              {/* ── Section 2: Structure ── */}
              <section className="space-y-6">
                <div className="flex items-center gap-3">
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-zinc-900 text-white flex items-center justify-center text-sm font-bold">
                    2
                  </div>
                  <div>
                    <h2 className="text-lg font-bold">Knowledge Map</h2>
                    <p className="text-sm text-zinc-500">Review the assets and relationships I&apos;ve extracted.</p>
                  </div>
                </div>

                <div className="pl-11">
                  <div className="h-[600px] w-full overflow-hidden bg-transparent">
                    <PlaybookFlow graph={graph} loading={graphLoading} />
                  </div>
                  <p className="text-[11px] text-zinc-400 mt-3 flex items-center gap-1.5 px-1">
                    <Bot className="h-3 w-3" />
                    Interactive map generated from your source files. Drag to explore.
                  </p>
                </div>
              </section>

              {/* ── Section 3: Visibility & Rights ── */}
              <section className="space-y-6">
                <div className="flex items-center gap-3">
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-zinc-900 text-white flex items-center justify-center text-sm font-bold">
                    3
                  </div>
                  <div>
                    <h2 className="text-lg font-bold">Visibility & Permissions</h2>
                    <p className="text-sm text-zinc-500">Decide who can see and adapt this playbook.</p>
                  </div>
                </div>

                <div className="pl-11 space-y-6">
                  <div className="space-y-3">
                    <button
                      onClick={() => setIsPublic(true)}
                      className={`w-full flex items-center gap-4 px-5 py-4 rounded-xl border-2 text-left transition-all ${isPublic ? "border-zinc-900 bg-white shadow-sm" : "border-zinc-200 bg-white hover:border-zinc-300"}`}
                    >
                      <div className={`p-2 rounded-lg shrink-0 ${isPublic ? "bg-zinc-900 text-white" : "bg-zinc-100 text-zinc-500"}`}>
                        <Globe className="h-5 w-5" />
                      </div>
                      <div className="flex-1">
                        <p className="text-sm font-bold text-zinc-900">Public</p>
                        <p className="text-xs text-zinc-500 mt-0.5">Anyone on the internet can see this playbook.</p>
                      </div>
                      <div className={`h-4 w-4 rounded-full border-2 shrink-0 flex items-center justify-center ${isPublic ? "border-zinc-900" : "border-zinc-300"}`}>
                        {isPublic && <div className="h-2 w-2 rounded-full bg-zinc-900" />}
                      </div>
                    </button>

                    <button
                      onClick={() => setIsPublic(false)}
                      className={`w-full flex items-center gap-4 px-5 py-4 rounded-xl border-2 text-left transition-all ${!isPublic ? "border-zinc-900 bg-white shadow-sm" : "border-zinc-200 bg-white hover:border-zinc-300"}`}
                    >
                      <div className={`p-2 rounded-lg shrink-0 ${!isPublic ? "bg-zinc-900 text-white" : "bg-zinc-100 text-zinc-500"}`}>
                        <Lock className="h-5 w-5" />
                      </div>
                      <div className="flex-1">
                        <p className="text-sm font-bold text-zinc-900">Private</p>
                        <p className="text-xs text-zinc-500 mt-0.5">You choose who can see and adapt this playbook.</p>
                      </div>
                      <div className={`h-4 w-4 rounded-full border-2 shrink-0 flex items-center justify-center ${!isPublic ? "border-zinc-900" : "border-zinc-300"}`}>
                        {!isPublic && <div className="h-2 w-2 rounded-full bg-zinc-900" />}
                      </div>
                    </button>
                  </div>

                  <div className="flex items-center justify-end pt-6">
                    <Button
                      onClick={handlePublish}
                      disabled={isPushing}
                      className="h-12 bg-black hover:bg-zinc-800 text-white font-bold gap-2 px-8 rounded-xl shadow-xl shadow-zinc-200 transition-all active:scale-95"
                    >
                      {isPushing ? (
                        <>
                          <div className="h-4 w-4 rounded-full border-2 border-white border-t-transparent animate-spin" />
                          Saving...
                        </>
                      ) : (
                        <>
                          <Upload className="h-4 w-4" />
                          Save Playbook
                        </>
                      )}
                    </Button>
                  </div>
                </div>
              </section>
            </div>
          </div>

          {/* Right Panel: AI Chat — fixed height, does not scroll at panel level */}
          <div className="w-[420px] flex flex-col pl-12 bg-white overflow-hidden">
            <div className="py-8 space-y-4 flex-1 flex flex-col min-h-0 overflow-hidden">
              <div className="shrink-0">
                <h2 className="text-lg font-bold flex items-center gap-2">
                  <Bot className="h-5 w-5 text-zinc-900" />
                  Anything I missed?
                </h2>
                <p className="text-sm text-zinc-500 mt-1 leading-relaxed">
                  Describe what&apos;s missing or paste a Google Drive link, and I&apos;ll update the playbook.
                </p>
              </div>

              <div className="flex-1 overflow-y-auto p-6 space-y-6 bg-zinc-50/50 rounded-2xl mb-4 border border-zinc-100">
                {messages.map((msg, i) => (
                  <div key={i} className={`flex gap-3 items-start ${msg.role === "user" ? "flex-row-reverse" : ""}`}>
                    <div className={`flex-shrink-0 h-8 w-8 rounded-xl flex items-center justify-center text-white shadow-sm ${msg.role === "ai" ? "bg-black" : "bg-zinc-500"}`}>
                      {msg.role === "ai" ? <Bot className="h-4 w-4" /> : <User className="h-4 w-4" />}
                    </div>
                    <div className={`max-w-[85%] px-4 py-3 rounded-2xl text-sm leading-relaxed shadow-sm ${msg.role === "ai" ? "bg-white border border-zinc-100 text-zinc-700" : "bg-zinc-900 text-white"}`}>
                      {msg.text}
                    </div>
                  </div>
                ))}
                <div ref={chatEndRef} />
              </div>

              {/* Chat Input */}
              <div className="shrink-0 pb-6 bg-white">
                <div className="relative group">
                  <Textarea
                    placeholder="Talk to AI..."
                    value={chatInput}
                    onChange={(e) => setChatInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && !e.shiftKey) {
                        e.preventDefault();
                        sendMessage();
                      }
                    }}
                    className="min-h-[100px] w-full bg-zinc-50 border-zinc-200 focus-visible:ring-zinc-900 rounded-2xl p-4 pr-12 text-sm leading-relaxed resize-none transition-all group-hover:border-zinc-300"
                  />
                  <div className="absolute bottom-3 right-3 flex gap-2">
                    <button
                      title="Upload a file"
                      onClick={() => fileInputRef.current?.click()}
                      className="h-8 w-8 flex items-center justify-center rounded-lg border border-zinc-200 bg-white hover:bg-zinc-50 text-zinc-500 transition-colors shadow-sm"
                    >
                      <Paperclip className="h-4 w-4" />
                    </button>
                    <input ref={fileInputRef} type="file" className="hidden" onChange={handleFileUpload} />
                    <Button
                      onClick={() => sendMessage()}
                      disabled={!chatInput.trim()}
                      size="sm"
                      className="h-8 w-8 p-0 bg-black hover:bg-zinc-800 text-white rounded-lg shadow-md"
                    >
                      <Send className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
                <div className="mt-3 flex gap-2 overflow-x-auto pb-1 no-scrollbar">
                  <button
                    onClick={() => sendMessage("What sponsors are missing?")}
                    className="whitespace-nowrap px-3 py-1.5 rounded-full border border-zinc-200 bg-zinc-50 text-[11px] font-bold text-zinc-600 hover:bg-zinc-100 hover:border-zinc-300 transition-all shadow-sm"
                  >
                    Find sponsors
                  </button>
                  <button
                    onClick={() => sendMessage("Generate a judging rubric")}
                    className="whitespace-nowrap px-3 py-1.5 rounded-full border border-zinc-200 bg-zinc-50 text-[11px] font-bold text-zinc-600 hover:bg-zinc-100 hover:border-zinc-300 transition-all shadow-sm"
                  >
                    Create rubric
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

export default function ReviewPlaybookPage() {
  return (
    <Suspense fallback={
      <div className="h-screen flex flex-col bg-white">
        <div className="container mx-auto px-6 py-12 flex flex-1 gap-12">
          <div className="flex-1 space-y-8">
            <div className="space-y-4">
              <div className="h-10 w-64 bg-zinc-100 animate-pulse rounded-md" />
              <div className="h-4 w-96 bg-zinc-50 animate-pulse rounded-md" />
            </div>
            <div className="h-[400px] bg-zinc-50 animate-pulse rounded-xl" />
          </div>
          <div className="w-[420px] bg-zinc-50 animate-pulse rounded-xl" />
        </div>
      </div>
    }>
      <ReviewPlaybookContent />
    </Suspense>
  );
}
