"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { PlaybookFlowClient as PlaybookFlow } from "@/components/graph/PlaybookFlowClient";
import { NavBar } from "@/components/NavBar";
import {
  Globe,
  Lock,
  X,
  Plus,
  Send,
  Bot,
  User,
  Upload,
  Link as LinkIcon,
  Paperclip,
  ChevronDown,
} from "lucide-react";

type Message = { role: "ai" | "user"; text: string };

const INITIAL_MESSAGES: Message[] = [
  {
    role: "ai",
    text: "I've built your playbook from the files I found. Is there anything I missed? You can paste a Google Drive link below and I'll pull the rest, or upload a file directly.",
  },
];

export default function ReviewPlaybookPage() {
  const router = useRouter();
  const [isPublic, setIsPublic] = useState(true);
  const [isPushing, setIsPushing] = useState(false);
  const [description, setDescription] = useState(
    "A premier showcase of student-led AI startups from Stanford. Includes registration flow, judge scoring rubric, and presentation schedule."
  );

  // Tags
  const [tags, setTags] = useState(["Hackathon", "Artificial Intelligence", "Demo Day"]);
  const [tagInput, setTagInput] = useState("");

  // Chatbot
  const [messages, setMessages] = useState<Message[]>(INITIAL_MESSAGES);
  const [chatInput, setChatInput] = useState("");
  const chatEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const addTag = () => {
    const trimmed = tagInput.trim();
    if (trimmed && !tags.includes(trimmed)) setTags([...tags, trimmed]);
    setTagInput("");
  };

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

  const handlePublish = async () => {
    setIsPushing(true);
    try {
      const res = await fetch("http://localhost:8000/api/commit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: "Stanford AI Demo Day 2026",
          description,
          is_public: isPublic,
          commit_message: "Initial save",
        }),
      });
      if (res.ok) {
        const data = await res.json();
        router.push(`/playbooks/${data.playbook_id}`);
      } else setIsPushing(false);
    } catch {
      setTimeout(() => router.push("/playbooks/stanford-demo-day-2026"), 1500);
    }
  };  return (
    <div className="h-screen flex flex-col bg-white text-zinc-900 overflow-hidden">
      <NavBar hideBorder />

      <main className="container mx-auto flex-1 flex overflow-hidden">
        {/* Left Panel: Configuration & Editor */}
        <div className="flex-1 overflow-y-auto border-r border-zinc-100 pl-6 pr-12">
          <div className="py-8 space-y-10">
            {/* Page header */}
            <div className="bg-white">
              <h1 className="text-3xl font-bold tracking-tight">Save a new Playbook</h1>
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

                {/* Tags */}
                <div className="space-y-3">
                  <Label className="text-sm font-semibold">Tags</Label>
                  <div className="flex flex-wrap gap-2">
                    {tags.map((tag) => (
                      <span
                        key={tag}
                        className="inline-flex items-center gap-1.5 px-3 py-1 bg-zinc-100 border border-zinc-200 text-zinc-700 rounded-lg text-xs font-semibold"
                      >
                        {tag}
                        <button onClick={() => setTags(tags.filter((t) => t !== tag))} className="hover:text-zinc-900 transition-colors">
                          <X className="h-3 w-3" />
                        </button>
                      </span>
                    ))}
                    <div className="flex gap-1.5 items-center bg-zinc-50 border border-dashed border-zinc-300 rounded-lg px-2.5 py-1">
                      <input
                        value={tagInput}
                        onChange={(e) => setTagInput(e.target.value)}
                        onKeyDown={(e) => e.key === "Enter" && addTag()}
                        placeholder="Add tag..."
                        className="text-xs outline-none bg-transparent w-20"
                      />
                      <button onClick={addTag} className="text-zinc-400 hover:text-zinc-700">
                        <Plus className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </section>

            {/* ── Section 2: Knowledge Map ── */}
            <section className="space-y-6">
              <div className="flex items-center gap-3">
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-zinc-900 text-white flex items-center justify-center text-sm font-bold">
                  2
                </div>
                <div>
                  <h2 className="text-lg font-bold">Event Knowledge Map</h2>
                  <p className="text-sm text-zinc-500">
                    Relationships found in your Google Workspace files.
                  </p>
                </div>
              </div>
              <div className="pl-11">
                <div className="h-[400px] rounded-2xl border border-zinc-200 overflow-hidden bg-zinc-50 shadow-inner">
                  <PlaybookFlow />
                </div>
              </div>
            </section>

            {/* ── Section 4: Configuration ── */}
            <section className="space-y-6">
              <div className="flex items-center gap-3">
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-zinc-900 text-white flex items-center justify-center text-sm font-bold">
                  3
                </div>
                <div>
                  <h2 className="text-lg font-bold">Configuration</h2>
                  <p className="text-sm text-zinc-500">Control access and distribution.</p>
                </div>
              </div>

              <div className="pl-11 space-y-4">
                <div className="rounded-2xl border border-zinc-200 divide-y divide-zinc-100 overflow-hidden bg-white shadow-sm">
                  <div className="flex items-center justify-between px-5 py-5">
                    <div>
                      <p className="text-sm font-bold">Visibility <span className="text-red-400">*</span></p>
                      <p className="text-xs text-zinc-500 mt-0.5">Who can view and adapt this playbook.</p>
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={() => setIsPublic(true)}
                        className={`flex items-center gap-1.5 px-4 py-2 rounded-xl border text-xs font-bold transition-all ${isPublic ? "bg-black text-white border-black shadow-md" : "bg-white text-zinc-600 border-zinc-200 hover:border-zinc-300"}`}
                      >
                        <Globe className="h-3.5 w-3.5" /> Public
                      </button>
                      <button
                        onClick={() => setIsPublic(false)}
                        className={`flex items-center gap-1.5 px-4 py-2 rounded-xl border text-xs font-bold transition-all ${!isPublic ? "bg-black text-white border-black shadow-md" : "bg-white text-zinc-600 border-zinc-200 hover:border-zinc-300"}`}
                      >
                        <Lock className="h-3.5 w-3.5" /> Private
                      </button>
                    </div>
                  </div>

                  <div className="flex items-center justify-between px-5 py-5">
                    <div>
                      <p className="text-sm font-bold">Allow Adapting</p>
                      <p className="text-xs text-zinc-500 mt-0.5">Others can clone and customize your work.</p>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input type="checkbox" defaultChecked className="sr-only peer" />
                      <div className="w-11 h-6 bg-zinc-200 rounded-full peer peer-checked:bg-black after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-zinc-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:after:translate-x-full peer-checked:after:border-white" />
                    </label>
                  </div>

                  <div className="flex items-center justify-between px-5 py-5">
                    <div>
                      <p className="text-sm font-bold">Usage Licence</p>
                      <p className="text-xs text-zinc-500 mt-0.5">Permissions for re-use.</p>
                    </div>
                    <div className="relative">
                      <select className="appearance-none text-xs font-bold border border-zinc-200 rounded-xl px-4 py-2 pr-10 bg-zinc-50 text-zinc-900 cursor-pointer focus:outline-none focus:ring-2 focus:ring-zinc-900 transition-all">
                        <option>Open for anyone</option>
                        <option>Credit required</option>
                        <option>No reuse</option>
                      </select>
                      <ChevronDown className="absolute right-3 top-2.5 h-4 w-4 text-zinc-400 pointer-events-none" />
                    </div>
                  </div>
                </div>

                <div className="flex items-center justify-between pt-6 pb-12">
                  <p className="text-sm text-zinc-400">
                    You can edit everything after publishing.
                  </p>
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

        {/* Right Panel: AI Chat */}
        <div className="w-[420px] flex flex-col pl-12 pr-6 bg-white">
          <div className="py-8 space-y-6">
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
          <div className="pb-6 bg-white">
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
      </main>
    </div>
  );
}
