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
  ArrowLeft,
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
  };

  return (
    <div className="min-h-screen bg-white text-zinc-900">
      <NavBar
        left={
          <Link href="/playbooks" className="text-zinc-500 hover:text-zinc-900 transition-colors">
            <ArrowLeft className="h-5 w-5" />
          </Link>
        }
      />

      {/* Page header */}
      <div className="border-b border-zinc-200 bg-white px-6 py-6">
        <div className="max-w-3xl mx-auto">
          <h1 className="text-2xl font-semibold tracking-tight">Save a new Playbook</h1>
          <p className="text-sm text-zinc-500 mt-1">
            Review and edit what the AI found before publishing to your profile.{" "}
            <span className="text-zinc-400 italic">Required fields are marked with *</span>
          </p>
        </div>
      </div>

      <div className="max-w-3xl mx-auto px-6 py-10 space-y-0">

        {/* ── Section 1: General ── */}
        <section className="flex gap-6 pb-8 border-b border-zinc-100">
          <div className="flex-shrink-0 w-7 h-7 rounded-full bg-zinc-800 text-white flex items-center justify-center text-xs font-bold mt-0.5">
            1
          </div>
          <div className="flex-1 space-y-5">
            <div>
              <h2 className="text-base font-semibold mb-1">General</h2>
              <p className="text-sm text-zinc-500">Name your playbook and give it a short summary.</p>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="title" className="text-sm font-medium">
                Playbook Name <span className="text-red-400">*</span>
              </Label>
              <Input
                id="title"
                defaultValue="Stanford AI Demo Day 2026"
                className="font-medium"
                placeholder="e.g. Stanford AI Demo Day 2026"
              />
              <p className="text-xs text-zinc-400">Great playbook names are short and memorable.</p>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="description" className="text-sm font-medium">Description</Label>
              <Textarea
                id="description"
                value={description}
                onChange={(e) => setDescription(e.target.value.slice(0, 350))}
                className="min-h-[90px] leading-relaxed resize-none"
                placeholder="What was this event about?"
              />
              <p className="text-xs text-zinc-400">{description.length} / 350 characters</p>
            </div>

            {/* Tags */}
            <div className="space-y-2">
              <Label className="text-sm font-medium">Tags</Label>
              <div className="flex flex-wrap gap-2">
                {tags.map((tag) => (
                  <span
                    key={tag}
                    className="inline-flex items-center gap-1 px-2.5 py-0.5 bg-zinc-100 border border-zinc-200 text-zinc-700 rounded-full text-xs font-medium"
                  >
                    {tag}
                    <button onClick={() => setTags(tags.filter((t) => t !== tag))} className="hover:text-zinc-900">
                      <X className="h-3 w-3" />
                    </button>
                  </span>
                ))}
                <div className="flex gap-1.5 items-center">
                  <input
                    value={tagInput}
                    onChange={(e) => setTagInput(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && addTag()}
                    placeholder="Add tag..."
                    className="h-6 text-xs border border-dashed border-zinc-300 rounded-full px-2.5 outline-none focus:border-zinc-500 bg-transparent w-24"
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
        <section className="flex gap-6 py-8 border-b border-zinc-100">
          <div className="flex-shrink-0 w-7 h-7 rounded-full bg-zinc-800 text-white flex items-center justify-center text-xs font-bold mt-0.5">
            2
          </div>
          <div className="flex-1 space-y-4">
            <div>
              <h2 className="text-base font-semibold mb-1">Event Knowledge Map</h2>
              <p className="text-sm text-zinc-500">
                The AI built this map from your Google Workspace files — participants, tools, sponsors, and more.
              </p>
            </div>
            <div className="h-[380px] rounded-xl border border-zinc-200 overflow-hidden bg-zinc-50">
              <PlaybookFlow />
            </div>
          </div>
        </section>

        {/* ── Section 3: Fill in missing info ── */}
        <section className="flex gap-6 py-8 border-b border-zinc-100">
          <div className="flex-shrink-0 w-7 h-7 rounded-full bg-zinc-800 text-white flex items-center justify-center text-xs font-bold mt-0.5">
            3
          </div>
          <div className="flex-1 space-y-4">
            <div>
              <h2 className="text-base font-semibold mb-1">Anything I missed?</h2>
              <p className="text-sm text-zinc-500">
                Paste a Google Drive link so I can pull more data, or upload a file directly.
              </p>
            </div>

            {/* Chat thread */}
            <div className="rounded-xl border border-zinc-200 bg-zinc-50 overflow-hidden">
              <div className="h-52 overflow-y-auto p-4 space-y-3">
                {messages.map((msg, i) => (
                  <div key={i} className={`flex gap-2.5 items-start ${msg.role === "user" ? "flex-row-reverse" : ""}`}>
                    <div className={`flex-shrink-0 h-6 w-6 rounded-full flex items-center justify-center text-white ${msg.role === "ai" ? "bg-zinc-800" : "bg-zinc-600"}`}>
                      {msg.role === "ai" ? <Bot className="h-3 w-3" /> : <User className="h-3 w-3" />}
                    </div>
                    <div className={`max-w-[82%] px-3 py-2 rounded-xl text-sm leading-relaxed ${msg.role === "ai" ? "bg-white border border-zinc-200 text-zinc-700" : "bg-zinc-900 text-white"}`}>
                      {msg.text}
                    </div>
                  </div>
                ))}
                <div ref={chatEndRef} />
              </div>

              {/* Input row */}
              <div className="border-t border-zinc-200 bg-white p-3 flex gap-2">
                <Input
                  placeholder="Paste a Drive link or describe what's missing..."
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && sendMessage()}
                  className="text-sm h-9 border-zinc-200"
                />
                {/* Drive link shortcut */}
                <button
                  title="Paste Drive link"
                  onClick={() => {
                    const url = navigator.clipboard.readText().then((t) => {
                      if (t.includes("drive.google.com")) sendMessage(t);
                      else setChatInput(t);
                    }).catch(() => {});
                  }}
                  className="flex-shrink-0 h-9 w-9 flex items-center justify-center rounded-lg border border-zinc-200 hover:bg-zinc-50 text-zinc-400 hover:text-zinc-700 transition-colors"
                >
                  <LinkIcon className="h-4 w-4" />
                </button>
                {/* File upload */}
                <button
                  title="Upload a file"
                  onClick={() => fileInputRef.current?.click()}
                  className="flex-shrink-0 h-9 w-9 flex items-center justify-center rounded-lg border border-zinc-200 hover:bg-zinc-50 text-zinc-400 hover:text-zinc-700 transition-colors"
                >
                  <Paperclip className="h-4 w-4" />
                </button>
                <input ref={fileInputRef} type="file" className="hidden" onChange={handleFileUpload} />
                <Button
                  onClick={() => sendMessage()}
                  size="sm"
                  className="flex-shrink-0 h-9 bg-zinc-900 hover:bg-zinc-800 text-white px-4"
                >
                  <Send className="h-3.5 w-3.5" />
                </Button>
              </div>
            </div>
          </div>
        </section>

        {/* ── Section 4: Configuration ── */}
        <section className="flex gap-6 py-8 border-b border-zinc-100">
          <div className="flex-shrink-0 w-7 h-7 rounded-full bg-zinc-800 text-white flex items-center justify-center text-xs font-bold mt-0.5">
            4
          </div>
          <div className="flex-1 space-y-3">
            <div>
              <h2 className="text-base font-semibold mb-1">Configuration</h2>
              <p className="text-sm text-zinc-500">Control who can view and adapt this playbook.</p>
            </div>

            {/* Visibility */}
            <div className="rounded-xl border border-zinc-200 divide-y divide-zinc-100 overflow-hidden">
              <div className="flex items-center justify-between px-5 py-4">
                <div>
                  <p className="text-sm font-medium">Choose visibility <span className="text-red-400">*</span></p>
                  <p className="text-xs text-zinc-500 mt-0.5">Choose who can view and adapt this playbook.</p>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => setIsPublic(true)}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-sm font-medium transition-all ${isPublic ? "bg-zinc-900 text-white border-zinc-900" : "bg-white text-zinc-600 border-zinc-200 hover:border-zinc-300"}`}
                  >
                    <Globe className="h-3.5 w-3.5" /> Public
                  </button>
                  <button
                    onClick={() => setIsPublic(false)}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-sm font-medium transition-all ${!isPublic ? "bg-zinc-800 text-white border-zinc-800" : "bg-white text-zinc-600 border-zinc-200 hover:border-zinc-300"}`}
                  >
                    <Lock className="h-3.5 w-3.5" /> Private
                  </button>
                </div>
              </div>

              {/* Allow forking */}
              <div className="flex items-center justify-between px-5 py-4">
                <div>
                  <p className="text-sm font-medium">Allow others to adapt this playbook</p>
                  <p className="text-xs text-zinc-500 mt-0.5">Others can clone and customise your playbook for their own events.</p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input type="checkbox" defaultChecked className="sr-only peer" />
                  <div className="w-10 h-5 bg-zinc-200 rounded-full peer peer-checked:bg-zinc-900 after:content-[''] after:absolute after:top-0.5 after:left-0.5 after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:after:translate-x-5" />
                </label>
              </div>

              {/* License */}
              <div className="flex items-center justify-between px-5 py-4">
                <div>
                  <p className="text-sm font-medium">Usage licence</p>
                  <p className="text-xs text-zinc-500 mt-0.5">How others can use this playbook.</p>
                </div>
                <div className="relative">
                  <select className="appearance-none text-sm border border-zinc-200 rounded-lg px-3 py-1.5 pr-8 bg-white text-zinc-700 cursor-pointer focus:outline-none focus:ring-2 focus:ring-zinc-500">
                    <option>Open for anyone</option>
                    <option>Credit required</option>
                    <option>No reuse</option>
                  </select>
                  <ChevronDown className="absolute right-2 top-2 h-4 w-4 text-zinc-400 pointer-events-none" />
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ── Publish button ── */}
        <div className="flex items-center justify-between pt-8">
          <p className="text-sm text-zinc-400">
            You can edit everything after publishing.
          </p>
          <Button
            onClick={handlePublish}
            disabled={isPushing}
            className="h-10 bg-zinc-900 hover:bg-zinc-800 text-white font-semibold gap-2 px-6 rounded-lg"
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
    </div>
  );
}
