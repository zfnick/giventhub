"use client";

import { useState, useRef, useEffect, useMemo } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  ArrowLeft,
  Bot,
  User,
  Send,
  Sparkles,
  Mail,
  CalendarDays,
  ClipboardList,
  Sheet,
  FileText,
  Users,
  Check,
  Wand2,
  RefreshCw,
  ChevronRight,
  MapPin,
  Building2,
  Trophy,
  Star,
  TrendingUp,
  Megaphone,
  Clock,
  Plus,
  ShieldCheck,
  Rocket,
  X,
  Layers,
  BookOpen,
  PenLine,
  ArrowRight,
  Target,
  Compass,
  Search,
} from "lucide-react";

// ── Types ────────────────────────────────────────────────────────────────────

type Message = { role: "ai" | "user"; text: string };
type Step = "mode" | "playbook" | "context" | "similar" | "plan";
type Mode = "playbook" | "scratch" | null;

type PastPlaybook = {
  id: string;
  title: string;
  category: string;
  attendees: string;
  duration: string;
  hostedBy: string;
  highlight: string;
};

type Mentor = {
  name: string;
  role: string;
  expertise: string[];
  pastEvents: number;
  initials: string;
  rating: number;
};

type Sponsor = {
  name: string;
  tier: "Platinum" | "Gold" | "Silver";
  history: string;
  initials: string;
};

type Venue = {
  name: string;
  location: string;
  capacity: string;
  vibe: string;
  pastUsage: string;
};

type Outreach = {
  name: string;
  reach: string;
  conversion: string;
  channel: string;
};

// ── Mock data ────────────────────────────────────────────────────────────────

const PAST_PLAYBOOKS: PastPlaybook[] = [
  {
    id: "google-genai-hackathon",
    title: "Google GenAI Hackathon",
    category: "Hackathon",
    attendees: "200–500",
    duration: "2 days",
    hostedBy: "Google Developers",
    highlight: "Mentor matching + judging rubric scored 4.8/5",
  },
  {
    id: "ycombinator-demo-day",
    title: "Accelerator Demo Day",
    category: "Showcase",
    attendees: "50–100",
    duration: "1 day",
    hostedBy: "Startup Community",
    highlight: "Investor follow-up pipeline closed 41% meetings",
  },
  {
    id: "tech-conference-pro",
    title: "Standard Tech Conference",
    category: "Conference",
    attendees: "1000+",
    duration: "3 days",
    hostedBy: "DevRel Masters",
    highlight: "Three-track schedule + sponsor tier structure",
  },
  {
    id: "university-climate-sprint",
    title: "University Climate Sprint",
    category: "Sprint",
    attendees: "50–200",
    duration: "1 day",
    hostedBy: "EcoTech Labs",
    highlight: "Beginner-friendly — ran 12 times across 4 unis",
  },
];

const FORMATS = ["Hackathon", "Demo Day", "Conference", "Sprint", "Workshop", "Meetup"];
const SCALES = ["<50", "50–200", "200–500", "500–1000", "1000+"];

const MENTORS: Mentor[] = [
  { name: "Sarah Chen", role: "VP Eng, Stripe", expertise: ["Payments", "Scale"], pastEvents: 3, initials: "SC", rating: 4.9 },
  { name: "Marcus Lee", role: "Founder, Pinecone", expertise: ["GenAI", "Vector DBs"], pastEvents: 2, initials: "ML", rating: 4.8 },
  { name: "Priya Raman", role: "Partner, a16z", expertise: ["Fundraising", "GTM"], pastEvents: 4, initials: "PR", rating: 5.0 },
  { name: "Jordan Kim", role: "Staff DS, OpenAI", expertise: ["LLM Ops", "Eval"], pastEvents: 2, initials: "JK", rating: 4.7 },
];

const SPONSORS: Sponsor[] = [
  { name: "Google Cloud", tier: "Platinum", history: "Sponsored last 4 events · $40k avg", initials: "GC" },
  { name: "Anthropic", tier: "Platinum", history: "First-time · warm intro via Priya", initials: "AN" },
  { name: "Stripe", tier: "Gold", history: "Sponsored 2 / past 3 · $15k avg", initials: "ST" },
  { name: "Notion", tier: "Gold", history: "Frequent — strong student brand fit", initials: "NO" },
  { name: "Vercel", tier: "Silver", history: "Loves hackathons · swag + credits", initials: "VC" },
];

const VENUES: Venue[] = [
  { name: "Stanford CodeX", location: "Palo Alto, CA", capacity: "450 cap", vibe: "Academic · Wi-Fi solid", pastUsage: "Used for last 2 demo days" },
  { name: "SOMA Loft 22", location: "San Francisco, CA", capacity: "300 cap", vibe: "Industrial · Open floor", pastUsage: "Hosted GenAI Sprint 2024" },
  { name: "Plug & Play HQ", location: "Sunnyvale, CA", capacity: "600 cap", vibe: "Corporate · A/V loaded", pastUsage: "Demo Day 2023 — 92% turnout" },
];

const OUTREACH: Outreach[] = [
  { name: "Stanford AI Society", reach: "2,400 students", conversion: "18% historical RSVP", channel: "Newsletter + Slack" },
  { name: "Berkeley AI Research", reach: "1,800 researchers", conversion: "12% RSVP", channel: "Mailing list" },
  { name: "SF AI Builders", reach: "5,200 members", conversion: "9% RSVP — high quality", channel: "Discord + Luma" },
  { name: "Past Demo Day Alumni", reach: "640 contacts", conversion: "31% RSVP — your best list", channel: "Personal email" },
];

const WORKSPACE_TOOLS = [
  { icon: CalendarDays, label: "Google Calendar", desc: "Master timeline + RSVPs", default: true },
  { icon: ClipboardList, label: "Google Forms", desc: "Registration + intake", default: true },
  { icon: Sheet, label: "Google Sheets", desc: "Roster + live scoring", default: true },
  { icon: FileText, label: "Google Docs", desc: "Run-of-show + rubrics", default: true },
  { icon: Mail, label: "Gmail Campaigns", desc: "Invitation + follow-up", default: false },
  { icon: Users, label: "Google Groups", desc: "Mentor + judge channels", default: false },
];

const TIMELINE = [
  { week: "T-6w", task: "Lock venue, sponsors, mentor list" },
  { week: "T-4w", task: "Launch registration + sponsor outreach" },
  { week: "T-2w", task: "Send confirmations, finalize rubric" },
  { week: "T-1w", task: "Brief judges, ship welcome kit" },
  { week: "Day-of", task: "Open doors, livestream, judge ops" },
  { week: "T+1w", task: "Send thank-yous, publish playbook" },
];

const QUICK_ACTIONS = [
  "Find me 3 more women mentors",
  "Who else should we pitch for Platinum sponsorship?",
  "Suggest a backup venue under $5k",
  "Draft the first sponsor outreach email",
];

// Step-aware AI greetings
const STEP_GREETING: Record<Step, string> = {
  mode: "Hey — I'm your Event Architect. Pick a starting point on the left and I'll take it from there. If you're not sure, lean toward 'from scratch' and I'll guide you.",
  playbook: "Pick a playbook and I'll fork it. I'll bring over what worked last time and re-tune the gaps based on your audience.",
  context: "Four quick details and I'll know enough to start drafting. Skip anything you're unsure of — I'll surface options later.",
  similar: "Found a few past events that look like yours. Use one as a base, or skip and I'll draft from a blank slate.",
  plan: "I pulled signal from your past 4 events. The drafts on the left are my best picks — swap, refine, or ask me to dig deeper on anything.",
};

// ── Component ─────────────────────────────────────────────────────────────────

export default function NewEventPage() {
  const router = useRouter();

  // Flow state
  const [step, setStep] = useState<Step>("mode");
  const [mode, setMode] = useState<Mode>(null);
  const [forkedPlaybookId, setForkedPlaybookId] = useState<string | null>(null);

  // Context (used by both onboarding + command center)
  const [eventName, setEventName] = useState("");
  const [eventDate, setEventDate] = useState("");
  const [eventFormat, setEventFormat] = useState("");
  const [audience, setAudience] = useState("");
  const [goal, setGoal] = useState("");

  // Command center selections
  const [lockedMentors, setLockedMentors] = useState<string[]>(MENTORS.slice(0, 3).map(m => m.name));
  const [lockedSponsors, setLockedSponsors] = useState<string[]>([SPONSORS[0].name, SPONSORS[2].name]);
  const [lockedVenue, setLockedVenue] = useState<string>(VENUES[0].name);
  const [lockedOutreach, setLockedOutreach] = useState<string[]>(OUTREACH.map(o => o.name).slice(0, 3));
  const [enabledTools, setEnabledTools] = useState<string[]>(
    WORKSPACE_TOOLS.filter(t => t.default).map(t => t.label)
  );

  // Chat
  const [messages, setMessages] = useState<Message[]>([{ role: "ai", text: STEP_GREETING.mode }]);
  const [chatInput, setChatInput] = useState("");
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Push a contextual AI message when step changes
  useEffect(() => {
    setMessages(prev => {
      const last = prev[prev.length - 1];
      if (last && last.role === "ai" && last.text === STEP_GREETING[step]) return prev;
      return [...prev, { role: "ai", text: STEP_GREETING[step] }];
    });
  }, [step]);

  // Rank similar past events given the context
  const similar = useMemo(() => {
    return PAST_PLAYBOOKS.map(pb => {
      let score = 60;
      if (eventFormat && pb.category.toLowerCase() === eventFormat.toLowerCase()) score += 30;
      if (eventFormat === "Demo Day" && pb.category === "Showcase") score += 25;
      if (eventFormat === "Sprint" && pb.category === "Hackathon") score += 10;
      if (audience.toLowerCase().includes("student") && pb.title.toLowerCase().includes("university")) score += 8;
      score = Math.min(98, score + Math.floor(Math.random() * 6));
      return { pb, score };
    }).sort((a, b) => b.score - a.score).slice(0, 3);
  }, [eventFormat, audience]);

  const completion = useMemo(() => {
    let score = 0;
    if (eventName.trim()) score += 10;
    if (eventDate) score += 10;
    if (eventFormat.trim()) score += 5;
    if (audience.trim()) score += 5;
    score += Math.min(20, lockedMentors.length * 5);
    score += Math.min(20, lockedSponsors.length * 7);
    score += lockedVenue ? 10 : 0;
    score += Math.min(10, lockedOutreach.length * 3);
    score += Math.min(10, enabledTools.length * 2);
    return Math.min(100, score);
  }, [eventName, eventDate, eventFormat, audience, lockedMentors, lockedSponsors, lockedVenue, lockedOutreach, enabledTools]);

  // ── Step transitions ────────────────────────────────────────────
  const pickMode = (m: Mode) => {
    setMode(m);
    if (m === "scratch") setForkedPlaybookId(null);
    setStep(m === "playbook" ? "playbook" : "context");
  };

  const forkPlaybook = (id: string) => {
    setForkedPlaybookId(id);
    const pb = PAST_PLAYBOOKS.find(p => p.id === id);
    if (pb) {
      setEventFormat(pb.category === "Showcase" ? "Demo Day" : pb.category);
      setAudience(pb.attendees);
    }
    setStep("context");
  };

  const goToSimilar = () => setStep("similar");
  const goToPlan = (basedOnId?: string) => {
    if (basedOnId) setForkedPlaybookId(basedOnId);
    setStep("plan");
  };
  const goBack = () => {
    if (step === "playbook") setStep("mode");
    else if (step === "context") setStep(mode === "playbook" ? "playbook" : "mode");
    else if (step === "similar") setStep("context");
    else if (step === "plan") setStep("similar");
  };

  // ── Toggles ─────────────────────────────────────────────────────
  const toggleMentor = (n: string) =>
    setLockedMentors(p => p.includes(n) ? p.filter(x => x !== n) : [...p, n]);
  const toggleSponsor = (n: string) =>
    setLockedSponsors(p => p.includes(n) ? p.filter(x => x !== n) : [...p, n]);
  const toggleOutreach = (n: string) =>
    setLockedOutreach(p => p.includes(n) ? p.filter(x => x !== n) : [...p, n]);
  const toggleTool = (n: string) =>
    setEnabledTools(p => p.includes(n) ? p.filter(x => x !== n) : [...p, n]);

  // ── Chat ─────────────────────────────────────────────────────────
  const sendMessage = (text?: string) => {
    const msg = (text ?? chatInput).trim();
    if (!msg) return;
    setChatInput("");
    setMessages(prev => [...prev, { role: "user", text: msg }]);

    setTimeout(() => {
      const lower = msg.toLowerCase();
      let reply = "On it — refining the draft now. I'll surface options on the left.";
      if (lower.includes("mentor")) reply = "Pulling from past judge rosters and your community graph. I'll add 3 fresh names to the Mentor card.";
      else if (lower.includes("sponsor")) reply = "Looking at sponsors who funded similar events. Drafting a warm intro through Priya as well.";
      else if (lower.includes("venue")) reply = "Filtering by capacity, A/V, and budget. I'll surface 2 alternates in the Venue card.";
      else if (lower.includes("email") || lower.includes("draft")) reply = "Drafting in Google Docs — I'll drop the link in the Workspace card when ready.";
      else if (lower.includes("budget")) reply = "Past events ran $32k–$48k all-in. Sponsorship covers ~70% based on the tier mix.";
      else if (step !== "plan") reply = "Got it. Tell me more on the left and I'll keep stitching the context together.";
      setMessages(prev => [...prev, { role: "ai", text: reply }]);
    }, 700);
  };

  const launch = () => router.push("/onboarding/review?timing=upcoming");
  const cancel = () => {
    if (window.confirm("Discard this event plan? Your selections will be lost.")) {
      router.push("/");
    }
  };

  // ── Render ───────────────────────────────────────────────────────
  return (
    <div className="h-screen flex flex-col bg-zinc-50 overflow-hidden">
      <main className="flex-1 flex min-h-0 overflow-hidden">
        {/* ── Left: changes per step ──────────────────────────────── */}
        <div className="flex-1 min-w-0 overflow-y-auto">
          <div className="max-w-5xl mx-auto px-8 py-10">
            {step !== "plan" && (
              <StepHeader step={step} onBack={step !== "mode" ? goBack : undefined} />
            )}

            {step === "mode" && <ModeStep onPick={pickMode} />}
            {step === "playbook" && (
              <PlaybookStep
                initialSelected={forkedPlaybookId}
                onConfirm={forkPlaybook}
              />
            )}
            {step === "context" && (
              <ContextStep
                eventName={eventName} setEventName={setEventName}
                eventDate={eventDate} setEventDate={setEventDate}
                eventFormat={eventFormat} setEventFormat={setEventFormat}
                audience={audience} setAudience={setAudience}
                goal={goal} setGoal={setGoal}
                onContinue={goToSimilar}
              />
            )}
            {step === "similar" && (
              <SimilarStep
                similar={similar}
                onUse={(id) => goToPlan(id)}
                onSkip={() => { setForkedPlaybookId(null); goToPlan(); }}
              />
            )}
            {step === "plan" && (
              <CommandCenter
                forkedPlaybook={PAST_PLAYBOOKS.find(p => p.id === forkedPlaybookId)}
                eventName={eventName} setEventName={setEventName}
                eventDate={eventDate} setEventDate={setEventDate}
                eventFormat={eventFormat} setEventFormat={setEventFormat}
                audience={audience} setAudience={setAudience}
                completion={completion}
                lockedMentors={lockedMentors} toggleMentor={toggleMentor}
                lockedSponsors={lockedSponsors} toggleSponsor={toggleSponsor}
                lockedVenue={lockedVenue} setLockedVenue={setLockedVenue}
                lockedOutreach={lockedOutreach} toggleOutreach={toggleOutreach}
                enabledTools={enabledTools} toggleTool={toggleTool}
                onLaunch={launch}
                onCancel={cancel}
              />
            )}

            <div className="h-8" />
          </div>
        </div>

        {/* ── Right: Event Architect chat (fixed, internally scrolls) ── */}
        <aside className="w-[400px] xl:w-[460px] 2xl:w-[560px] shrink-0 flex flex-col border-l border-zinc-200 bg-white">
          <div className="px-6 pt-5 pb-4 border-b border-zinc-100 shrink-0">
            <div className="flex items-center gap-2">
              <div className="h-8 w-8 rounded-xl bg-gradient-to-br from-zinc-900 to-zinc-700 flex items-center justify-center">
                <Bot className="h-4 w-4 text-white" />
              </div>
              <div>
                <h2 className="text-sm font-bold text-zinc-900">Event Architect</h2>
                <p className="text-[11px] text-zinc-500">
                  {step === "plan" ? "Refining drafts in real time" : "Guiding you through setup"}
                </p>
              </div>
            </div>
          </div>

          <div className="flex-1 min-h-0 overflow-y-auto px-5 py-4 space-y-4">
            {messages.map((msg, i) => (
              <div key={i} className={`flex gap-2.5 items-start ${msg.role === "user" ? "flex-row-reverse" : ""}`}>
                <div className={`flex-shrink-0 h-7 w-7 rounded-xl flex items-center justify-center text-white shadow-sm ${msg.role === "ai" ? "bg-zinc-900" : "bg-zinc-500"}`}>
                  {msg.role === "ai" ? <Bot className="h-3.5 w-3.5" /> : <User className="h-3.5 w-3.5" />}
                </div>
                <div className={`max-w-[85%] px-3.5 py-2.5 rounded-2xl text-sm leading-relaxed ${msg.role === "ai" ? "bg-zinc-50 border border-zinc-100 text-zinc-700" : "bg-zinc-900 text-white"}`}>
                  {msg.text}
                </div>
              </div>
            ))}
            <div ref={chatEndRef} />
          </div>

          <div className="px-5 pb-5 pt-3 border-t border-zinc-100 shrink-0 space-y-3">
            {step === "plan" && (
              <div className="flex gap-1.5 overflow-x-auto no-scrollbar">
                {QUICK_ACTIONS.map(q => (
                  <button
                    key={q}
                    onClick={() => sendMessage(q)}
                    className="whitespace-nowrap shrink-0 px-2.5 py-1 rounded-full border border-zinc-200 bg-white text-[11px] font-semibold text-zinc-600 hover:border-zinc-400 hover:bg-zinc-50 transition-all"
                  >
                    {q}
                  </button>
                ))}
              </div>
            )}

            <div className="relative">
              <Textarea
                placeholder="Ask the Architect anything..."
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    sendMessage();
                  }
                }}
                className="min-h-[72px] w-full bg-zinc-50 border-zinc-200 focus-visible:ring-zinc-900 rounded-xl p-3 pr-12 text-sm resize-none"
              />
              <Button
                onClick={() => sendMessage()}
                disabled={!chatInput.trim()}
                size="sm"
                className="absolute bottom-2.5 right-2.5 h-7 w-7 p-0 bg-zinc-900 hover:bg-zinc-800 text-white rounded-lg"
              >
                <Send className="h-3.5 w-3.5" />
              </Button>
            </div>
          </div>
        </aside>
      </main>
    </div>
  );
}

// ── Step header (progress) ──────────────────────────────────────────────────

function StepHeader({ step, onBack }: { step: Step; onBack?: () => void }) {
  const ORDER: Step[] = ["mode", "context", "similar", "plan"];
  const labels: Record<Step, string> = {
    mode: "Start", playbook: "Pick playbook", context: "Context", similar: "Similar events", plan: "Plan",
  };
  // map playbook step into the 'mode' slot visually
  const visibleStep = step === "playbook" ? "mode" : step;
  const currentIdx = ORDER.indexOf(visibleStep);

  return (
    <div className="mb-8">
      {onBack ? (
        <button
          onClick={onBack}
          className="inline-flex items-center gap-1.5 text-sm text-zinc-500 hover:text-zinc-900 transition-colors mb-5"
        >
          <ArrowLeft className="h-4 w-4" />
          Back
        </button>
      ) : (
        <Link href="/" className="inline-flex items-center gap-1.5 text-sm text-zinc-500 hover:text-zinc-900 transition-colors mb-5">
          <ArrowLeft className="h-4 w-4" />
          Back to playbooks
        </Link>
      )}

      <div className="flex items-center gap-2">
        {ORDER.map((s, i) => {
          const done = i < currentIdx;
          const active = i === currentIdx;
          return (
            <div key={s} className="flex items-center gap-2 flex-1">
              <div className={`flex items-center gap-2 px-2.5 py-1 rounded-full text-[11px] font-bold transition-all ${
                done ? "bg-zinc-900 text-white" :
                active ? "bg-white border-2 border-zinc-900 text-zinc-900" :
                "bg-zinc-100 text-zinc-400"
              }`}>
                <div className={`h-4 w-4 rounded-full flex items-center justify-center text-[10px] ${
                  done ? "bg-white text-zinc-900" :
                  active ? "bg-zinc-900 text-white" :
                  "bg-white text-zinc-400"
                }`}>
                  {done ? <Check className="h-2.5 w-2.5" /> : i + 1}
                </div>
                <span className="uppercase tracking-wider">{labels[s]}</span>
              </div>
              {i < ORDER.length - 1 && <div className="h-px flex-1 bg-zinc-200" />}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Step 0: Mode picker ──────────────────────────────────────────────────────

function ModeStep({ onPick }: { onPick: (m: Mode) => void }) {
  const [selected, setSelected] = useState<Mode>(null);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-5xl font-extrabold tracking-tight text-zinc-900 leading-[1.05]">
          Where do you want to start?
        </h1>
        <p className="text-lg text-zinc-500 mt-3 max-w-2xl leading-relaxed">
          Forking a playbook is fastest — I&apos;ll bring over what worked.
          Starting from scratch is for new shapes I haven&apos;t seen before.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <ModeCard
          icon={<BookOpen className="h-6 w-6" />}
          title="Fork a past playbook"
          subtitle="Recommended if you&apos;ve run something like this before."
          bullets={["Pre-loaded mentors, sponsors, venues", "Adapts to your audience size", "Fastest path to launch"]}
          selected={selected === "playbook"}
          onClick={() => setSelected("playbook")}
          recommended
        />
        <ModeCard
          icon={<PenLine className="h-6 w-6" />}
          title="Start from scratch"
          subtitle="Tell me the shape and I&apos;ll search your library for matches."
          bullets={["4-question context intake", "AI finds similar past events", "Land in command center with drafts"]}
          selected={selected === "scratch"}
          onClick={() => setSelected("scratch")}
        />
      </div>

      <div className="rounded-2xl bg-white border border-zinc-200 p-5 flex items-center gap-4">
        <div className="h-10 w-10 rounded-xl bg-zinc-100 flex items-center justify-center shrink-0">
          <Compass className="h-5 w-5 text-zinc-700" />
        </div>
        <div className="flex-1">
          <p className="text-sm font-bold text-zinc-900">Not sure which to pick?</p>
          <p className="text-xs text-zinc-500 mt-0.5">
            Ask the Architect on the right — describe your event in plain English and it&apos;ll route you.
          </p>
        </div>
      </div>

      <div className="flex items-center justify-end">
        <Button
          onClick={() => selected && onPick(selected)}
          disabled={!selected}
          className="h-11 bg-zinc-900 hover:bg-zinc-800 text-white font-bold gap-2 px-6 rounded-xl disabled:opacity-40"
        >
          Continue
          <ArrowRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}

function ModeCard({
  icon, title, subtitle, bullets, selected, onClick, recommended,
}: {
  icon: React.ReactNode;
  title: string;
  subtitle: string;
  bullets: string[];
  selected: boolean;
  onClick: () => void;
  recommended?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      className={`relative text-left p-6 rounded-2xl border-2 transition-all ${
        selected
          ? "border-zinc-900 bg-white shadow-md"
          : "border-zinc-200 bg-white hover:border-zinc-400"
      }`}
    >
      {recommended && (
        <span className="absolute top-4 right-4 text-[10px] font-bold uppercase tracking-wider text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-full">
          Recommended
        </span>
      )}

      <div className={`h-12 w-12 rounded-xl flex items-center justify-center mb-4 ${
        selected ? "bg-zinc-900 text-white" : "bg-zinc-100 text-zinc-700"
      }`}>
        {icon}
      </div>
      <div className="flex items-center gap-2">
        <h3 className="text-xl font-extrabold tracking-tight text-zinc-900">{title}</h3>
        {selected && (
          <div className="h-5 w-5 rounded-full bg-zinc-900 flex items-center justify-center">
            <Check className="h-3 w-3 text-white" />
          </div>
        )}
      </div>
      <p className="text-sm text-zinc-500 mt-1.5 leading-relaxed">{subtitle}</p>
      <ul className="mt-4 space-y-1.5">
        {bullets.map(b => (
          <li key={b} className="flex items-start gap-2 text-xs text-zinc-600">
            <Check className="h-3.5 w-3.5 text-emerald-600 shrink-0 mt-0.5" />
            <span>{b}</span>
          </li>
        ))}
      </ul>
    </button>
  );
}

// ── Step 1a: Playbook fork picker ────────────────────────────────────────────

function PlaybookStep({
  initialSelected,
  onConfirm,
}: {
  initialSelected: string | null;
  onConfirm: (id: string) => void;
}) {
  const [selected, setSelected] = useState<string | null>(initialSelected);
  const [query, setQuery] = useState("");
  const [activeCategory, setActiveCategory] = useState<string>("All");

  const categories = useMemo(
    () => ["All", ...Array.from(new Set(PAST_PLAYBOOKS.map(p => p.category)))],
    []
  );

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return PAST_PLAYBOOKS.filter(pb => {
      if (activeCategory !== "All" && pb.category !== activeCategory) return false;
      if (!q) return true;
      return (
        pb.title.toLowerCase().includes(q) ||
        pb.category.toLowerCase().includes(q) ||
        pb.hostedBy.toLowerCase().includes(q) ||
        pb.highlight.toLowerCase().includes(q)
      );
    });
  }, [query, activeCategory]);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-4xl font-extrabold tracking-tight text-zinc-900 leading-[1.1]">
          Which playbook are we forking?
        </h1>
        <p className="text-base text-zinc-500 mt-2 max-w-2xl">
          I&apos;ll clone its structure, then adapt mentors, sponsors, and venues to your audience.
        </p>
      </div>

      {/* Search + category filters */}
      <div className="space-y-3">
        <div className="relative">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-400 pointer-events-none" />
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by name, host, category…"
            className="h-12 pl-11 pr-10 bg-white border-zinc-200 focus-visible:ring-zinc-900 rounded-xl text-sm"
          />
          {query && (
            <button
              onClick={() => setQuery("")}
              className="absolute right-3 top-1/2 -translate-y-1/2 h-6 w-6 rounded-full flex items-center justify-center text-zinc-400 hover:bg-zinc-100 hover:text-zinc-700 transition-colors"
              aria-label="Clear search"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          )}
        </div>

        <div className="flex gap-2 flex-wrap">
          {categories.map(cat => (
            <button
              key={cat}
              onClick={() => setActiveCategory(cat)}
              className={`px-3 py-1.5 rounded-full text-xs font-semibold transition-colors border ${
                activeCategory === cat
                  ? "bg-zinc-900 text-white border-zinc-900"
                  : "bg-white text-zinc-600 border-zinc-200 hover:border-zinc-400"
              }`}
            >
              {cat}
            </button>
          ))}
        </div>

        <p className="text-xs text-zinc-400">
          {filtered.length} {filtered.length === 1 ? "playbook" : "playbooks"} found
        </p>
      </div>

      {filtered.length === 0 ? (
        <div className="border-2 border-dashed border-zinc-200 rounded-2xl px-6 py-12 flex flex-col items-center text-center gap-3">
          <div className="h-12 w-12 rounded-2xl bg-zinc-100 flex items-center justify-center">
            <Search className="h-5 w-5 text-zinc-400" />
          </div>
          <div>
            <p className="text-sm font-semibold text-zinc-700">No matching playbooks</p>
            <p className="text-xs text-zinc-500 mt-1">Try a different keyword or clear filters.</p>
          </div>
          <button
            onClick={() => { setQuery(""); setActiveCategory("All"); }}
            className="text-xs font-semibold text-zinc-900 underline underline-offset-4 hover:text-zinc-700"
          >
            Reset filters
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-4">
          {filtered.map(pb => {
            const isSel = selected === pb.id;
            return (
              <button
                key={pb.id}
                onClick={() => setSelected(pb.id)}
                className={`text-left p-5 rounded-2xl border-2 transition-all ${
                  isSel ? "border-zinc-900 bg-white shadow-md" : "border-zinc-200 bg-white hover:border-zinc-400"
                }`}
              >
                <div className="flex items-center justify-between mb-3">
                  <span className="text-[10px] font-bold uppercase tracking-widest text-zinc-500 bg-zinc-100 px-2 py-0.5 rounded">
                    {pb.category}
                  </span>
                  {isSel && (
                    <div className="h-5 w-5 rounded-full bg-zinc-900 flex items-center justify-center">
                      <Check className="h-3 w-3 text-white" />
                    </div>
                  )}
                </div>
                <h3 className="text-lg font-extrabold text-zinc-900 leading-tight">{pb.title}</h3>
                <p className="text-xs text-zinc-500 mt-1">{pb.hostedBy} · {pb.duration} · {pb.attendees}</p>
                <p className="text-sm text-zinc-600 mt-3 leading-relaxed">{pb.highlight}</p>
              </button>
            );
          })}
        </div>
      )}

      <div className="flex items-center justify-end">
        <Button
          onClick={() => selected && onConfirm(selected)}
          disabled={!selected}
          className="h-11 bg-zinc-900 hover:bg-zinc-800 text-white font-bold gap-2 px-6 rounded-xl disabled:opacity-40"
        >
          Continue
          <ArrowRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}

// ── Step 2: Context intake ───────────────────────────────────────────────────

function ContextStep({
  eventName, setEventName,
  eventDate, setEventDate,
  eventFormat, setEventFormat,
  audience, setAudience,
  goal, setGoal,
  onContinue,
}: {
  eventName: string; setEventName: (v: string) => void;
  eventDate: string; setEventDate: (v: string) => void;
  eventFormat: string; setEventFormat: (v: string) => void;
  audience: string; setAudience: (v: string) => void;
  goal: string; setGoal: (v: string) => void;
  onContinue: () => void;
}) {
  const canContinue = eventName.trim() && eventFormat;
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-4xl font-extrabold tracking-tight text-zinc-900 leading-[1.1]">
          Tell me about your event.
        </h1>
        <p className="text-base text-zinc-500 mt-2 max-w-2xl">
          Four quick details so I can pull the right context from your library.
        </p>
      </div>

      <div className="bg-white border border-zinc-200 rounded-2xl p-6 space-y-6 shadow-sm">
        <BriefField label="Event name" value={eventName} onChange={setEventName} placeholder="e.g. Stanford AI Demo Day 2026" />
        <div className="grid grid-cols-2 gap-4">
          <BriefField label="Target date" type="date" value={eventDate} onChange={setEventDate} />
          <BriefField label="Audience" value={audience} onChange={setAudience} placeholder="e.g. 250 students" />
        </div>

        <div>
          <label className="block text-[11px] font-bold uppercase tracking-wider text-zinc-500 mb-2">
            Format
          </label>
          <div className="flex flex-wrap gap-2">
            {FORMATS.map(f => (
              <button
                key={f}
                onClick={() => setEventFormat(f === eventFormat ? "" : f)}
                className={`px-3 py-1.5 rounded-full text-xs font-bold border transition-all ${
                  eventFormat === f
                    ? "bg-zinc-900 text-white border-zinc-900"
                    : "bg-white text-zinc-600 border-zinc-200 hover:border-zinc-400"
                }`}
              >
                {f}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="block text-[11px] font-bold uppercase tracking-wider text-zinc-500 mb-2">
            What&apos;s the goal? <span className="text-zinc-400 font-normal normal-case tracking-normal">(optional)</span>
          </label>
          <Textarea
            value={goal}
            onChange={e => setGoal(e.target.value)}
            placeholder="e.g. Showcase student AI startups, attract VC follow-up, build a recruiting pipeline."
            className="min-h-[80px] bg-zinc-50 border-zinc-200 focus-visible:ring-zinc-900 rounded-xl p-3 text-sm resize-none"
          />
        </div>
      </div>

      <div className="flex items-center justify-between">
        <p className="text-xs text-zinc-500 flex items-center gap-1.5">
          <Target className="h-3.5 w-3.5" />
          Next, I&apos;ll surface similar past events.
        </p>
        <Button
          onClick={onContinue}
          disabled={!canContinue}
          className="h-11 bg-zinc-900 hover:bg-zinc-800 text-white font-bold gap-2 px-6 rounded-xl disabled:opacity-40"
        >
          Find similar events
          <ArrowRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}

// ── Step 3: Similar past events ──────────────────────────────────────────────

function SimilarStep({
  similar,
  onUse,
  onSkip,
}: {
  similar: { pb: PastPlaybook; score: number }[];
  onUse: (id: string) => void;
  onSkip: () => void;
}) {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-4xl font-extrabold tracking-tight text-zinc-900 leading-[1.1]">
          These look close to what you described.
        </h1>
        <p className="text-base text-zinc-500 mt-2 max-w-2xl">
          Want to use one as a base? I&apos;ll keep what worked and swap in your details.
          You can also skip — I&apos;ll draft from a blank slate.
        </p>
      </div>

      <div className="space-y-3">
        {similar.map(({ pb, score }) => (
          <div
            key={pb.id}
            className="bg-white border border-zinc-200 rounded-2xl p-5 flex items-center gap-5 hover:border-zinc-400 hover:shadow-md transition-all"
          >
            <div className="h-14 w-14 rounded-xl bg-gradient-to-br from-zinc-900 to-zinc-700 text-white flex items-center justify-center shrink-0">
              <span className="text-lg font-extrabold">{score}%</span>
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <h3 className="text-base font-extrabold text-zinc-900">{pb.title}</h3>
                <span className="text-[10px] font-bold uppercase tracking-widest text-zinc-500 bg-zinc-100 px-1.5 py-0.5 rounded">
                  {pb.category}
                </span>
              </div>
              <p className="text-xs text-zinc-500">{pb.hostedBy} · {pb.duration} · {pb.attendees}</p>
              <p className="text-sm text-zinc-600 mt-1.5">{pb.highlight}</p>
            </div>
            <Button
              onClick={() => onUse(pb.id)}
              className="h-10 bg-zinc-900 hover:bg-zinc-800 text-white font-bold gap-2 px-5 rounded-xl shrink-0"
            >
              Use this
              <ArrowRight className="h-4 w-4" />
            </Button>
          </div>
        ))}
      </div>

      <div className="rounded-2xl border-2 border-dashed border-zinc-200 p-6 flex items-center justify-between">
        <div>
          <p className="text-sm font-bold text-zinc-900">None of these fit?</p>
          <p className="text-xs text-zinc-500 mt-0.5">Skip and I&apos;ll draft from scratch using your context.</p>
        </div>
        <button
          onClick={onSkip}
          className="text-sm font-bold text-zinc-700 hover:text-zinc-900 inline-flex items-center gap-1"
        >
          Skip and draft fresh
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}

// ── Step 4: Command Center ───────────────────────────────────────────────────

function CommandCenter({
  forkedPlaybook,
  eventName, setEventName,
  eventDate, setEventDate,
  eventFormat, setEventFormat,
  audience, setAudience,
  completion,
  lockedMentors, toggleMentor,
  lockedSponsors, toggleSponsor,
  lockedVenue, setLockedVenue,
  lockedOutreach, toggleOutreach,
  enabledTools, toggleTool,
  onLaunch,
  onCancel,
}: {
  forkedPlaybook?: PastPlaybook;
  eventName: string; setEventName: (v: string) => void;
  eventDate: string; setEventDate: (v: string) => void;
  eventFormat: string; setEventFormat: (v: string) => void;
  audience: string; setAudience: (v: string) => void;
  completion: number;
  lockedMentors: string[]; toggleMentor: (n: string) => void;
  lockedSponsors: string[]; toggleSponsor: (n: string) => void;
  lockedVenue: string; setLockedVenue: (n: string) => void;
  lockedOutreach: string[]; toggleOutreach: (n: string) => void;
  enabledTools: string[]; toggleTool: (n: string) => void;
  onLaunch: () => void;
  onCancel: () => void;
}) {
  return (
    <div className="space-y-10">
      {/* Hero */}
      <div>
        <div className="flex items-start justify-between gap-4 mb-3">
          <div>
            {forkedPlaybook && (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-white border border-zinc-200 text-[11px] font-semibold text-zinc-600">
                <Layers className="h-3 w-3" />
                Forked from &ldquo;{forkedPlaybook.title}&rdquo;
              </span>
            )}
          </div>
          <button
            onClick={onCancel}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-zinc-200 bg-white text-xs font-semibold text-zinc-500 hover:text-red-600 hover:border-red-200 hover:bg-red-50 transition-colors"
          >
            <X className="h-3.5 w-3.5" />
            Discard plan
          </button>
        </div>

        <h1 className="text-5xl font-extrabold tracking-tight text-zinc-900 leading-[1.05]">
          Event Command Center.
        </h1>
        <p className="text-lg text-zinc-500 mt-3 max-w-2xl leading-relaxed">
          Your next event, half-drafted. I&apos;ve picked the mentors, sponsors, venue, and stack
          from what worked before — you just refine, swap, and launch.
        </p>

        <div className="mt-6 flex items-center gap-4">
          <div className="flex-1 max-w-md">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-xs font-bold text-zinc-700">Plan readiness</span>
              <span className="text-xs font-mono font-bold text-zinc-900">{completion}%</span>
            </div>
            <div className="h-2 w-full rounded-full bg-zinc-200 overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-emerald-500 to-blue-500 transition-all duration-500"
                style={{ width: `${completion}%` }}
              />
            </div>
          </div>
          <Button
            onClick={onLaunch}
            disabled={completion < 50}
            className="h-11 bg-zinc-900 hover:bg-zinc-800 text-white font-bold gap-2 px-6 rounded-xl disabled:opacity-40"
          >
            <Rocket className="h-4 w-4" />
            Launch event prep
          </Button>
        </div>
      </div>

      {/* Event Brief */}
      <section className="bg-white border border-zinc-200 rounded-2xl p-6 shadow-sm">
        <div className="flex items-center justify-between mb-5">
          <div>
            <h2 className="text-lg font-bold text-zinc-900">Event brief</h2>
            <p className="text-xs text-zinc-500 mt-0.5">These four facts drive every draft below.</p>
          </div>
          <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-zinc-400">
            <Bot className="h-3 w-3" />
            Edits re-rank suggestions
          </span>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <BriefField label="Event name" value={eventName} onChange={setEventName} />
          <BriefField label="Target date" value={eventDate} onChange={setEventDate} type="date" />
          <BriefField label="Format" value={eventFormat} onChange={setEventFormat} />
          <BriefField label="Audience size" value={audience} onChange={setAudience} />
        </div>
      </section>

      {/* Drafts */}
      <section className="space-y-1">
        <div className="flex items-end justify-between mb-4">
          <div>
            <p className="text-[11px] font-bold uppercase tracking-widest text-zinc-400">AI-drafted picks</p>
            <h2 className="text-2xl font-extrabold text-zinc-900 tracking-tight mt-1">The board, set up for you.</h2>
          </div>
          <button className="text-xs font-semibold text-zinc-500 hover:text-zinc-900 inline-flex items-center gap-1.5">
            <RefreshCw className="h-3.5 w-3.5" />
            Re-roll all drafts
          </button>
        </div>

        <div className="grid grid-cols-1 gap-5">
          {/* Mentors */}
          <DraftCard
            icon={<Users className="h-4 w-4" />}
            title="Mentor & Speaker Lineup"
            badge={`${lockedMentors.length} locked · ${MENTORS.length - lockedMentors.length} suggested`}
            source="From past Demo Days '23 + '24"
          >
            <div className="grid grid-cols-2 gap-2.5">
              {MENTORS.map(m => {
                const locked = lockedMentors.includes(m.name);
                return (
                  <button
                    key={m.name}
                    onClick={() => toggleMentor(m.name)}
                    className={`flex items-start gap-3 p-3 rounded-xl border-2 text-left transition-all ${
                      locked ? "border-zinc-900 bg-white" : "border-zinc-200 bg-zinc-50/60 hover:border-zinc-300"
                    }`}
                  >
                    <div className={`h-10 w-10 shrink-0 rounded-xl flex items-center justify-center text-xs font-bold ${
                      locked ? "bg-zinc-900 text-white" : "bg-zinc-200 text-zinc-600"
                    }`}>
                      {m.initials}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1.5">
                        <p className="text-sm font-bold text-zinc-900 truncate">{m.name}</p>
                        {locked && <Check className="h-3.5 w-3.5 text-emerald-600 shrink-0" />}
                      </div>
                      <p className="text-[11px] text-zinc-500 truncate">{m.role}</p>
                      <div className="flex items-center gap-1.5 mt-1.5 flex-wrap">
                        {m.expertise.map(e => (
                          <span key={e} className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-zinc-100 text-zinc-600">
                            {e}
                          </span>
                        ))}
                      </div>
                      <div className="flex items-center gap-3 mt-1.5 text-[10px] text-zinc-400 font-medium">
                        <span className="inline-flex items-center gap-0.5">
                          <Star className="h-2.5 w-2.5 fill-amber-400 stroke-amber-400" />
                          {m.rating}
                        </span>
                        <span>· {m.pastEvents} past events</span>
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          </DraftCard>

          {/* Sponsors */}
          <DraftCard
            icon={<Trophy className="h-4 w-4" />}
            title="Sponsorship Pipeline"
            badge={`${lockedSponsors.length} confirmed · $${lockedSponsors.length * 22}k projected`}
            source="From sponsor-conversion history"
          >
            <div className="space-y-2">
              {SPONSORS.map(s => {
                const locked = lockedSponsors.includes(s.name);
                const tierColor =
                  s.tier === "Platinum" ? "bg-zinc-900 text-white" :
                  s.tier === "Gold" ? "bg-amber-100 text-amber-900 border-amber-200" :
                  "bg-zinc-100 text-zinc-700 border-zinc-200";
                return (
                  <button
                    key={s.name}
                    onClick={() => toggleSponsor(s.name)}
                    className={`w-full flex items-center gap-3 p-2.5 rounded-xl border-2 text-left transition-all ${
                      locked ? "border-zinc-900 bg-white" : "border-zinc-200 bg-zinc-50/60 hover:border-zinc-300"
                    }`}
                  >
                    <div className={`h-9 w-9 shrink-0 rounded-lg flex items-center justify-center text-[10px] font-bold ${
                      locked ? "bg-zinc-900 text-white" : "bg-zinc-200 text-zinc-600"
                    }`}>
                      {s.initials}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-bold text-zinc-900 truncate">{s.name}</p>
                      <p className="text-[10px] text-zinc-500 truncate">{s.history}</p>
                    </div>
                    <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded uppercase tracking-wider border ${tierColor}`}>
                      {s.tier}
                    </span>
                  </button>
                );
              })}
            </div>
          </DraftCard>

          {/* Venue */}
          <DraftCard
            icon={<MapPin className="h-4 w-4" />}
            title="Venue Shortlist"
            badge="3 venues matched"
            source="Filtered by capacity, AV, geo"
          >
            <div className="space-y-2">
              {VENUES.map(v => {
                const locked = lockedVenue === v.name;
                return (
                  <button
                    key={v.name}
                    onClick={() => setLockedVenue(locked ? "" : v.name)}
                    className={`w-full flex items-start gap-3 p-3 rounded-xl border-2 text-left transition-all ${
                      locked ? "border-zinc-900 bg-white" : "border-zinc-200 bg-zinc-50/60 hover:border-zinc-300"
                    }`}
                  >
                    <div className={`p-2 rounded-lg shrink-0 ${locked ? "bg-zinc-900 text-white" : "bg-zinc-200 text-zinc-600"}`}>
                      <Building2 className="h-3.5 w-3.5" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1.5">
                        <p className="text-sm font-bold text-zinc-900 truncate">{v.name}</p>
                        {locked && <Check className="h-3.5 w-3.5 text-emerald-600 shrink-0" />}
                      </div>
                      <p className="text-[11px] text-zinc-500 truncate">{v.location} · {v.capacity}</p>
                      <p className="text-[10px] text-zinc-400 truncate mt-0.5">{v.vibe} · {v.pastUsage}</p>
                    </div>
                  </button>
                );
              })}
            </div>
          </DraftCard>

          {/* Workspace */}
          <DraftCard
            icon={<Wand2 className="h-4 w-4" />}
            title="Workspace Stack"
            badge={`${enabledTools.length}/${WORKSPACE_TOOLS.length} provisioned`}
            source="One-click Google Workspace setup"
          >
            <div className="space-y-2">
              {WORKSPACE_TOOLS.map(({ icon: Icon, label, desc }) => {
                const on = enabledTools.includes(label);
                return (
                  <button
                    key={label}
                    onClick={() => toggleTool(label)}
                    className={`w-full flex items-center gap-3 p-2.5 rounded-xl border-2 text-left transition-all ${
                      on ? "border-zinc-900 bg-white" : "border-zinc-200 bg-zinc-50/60 hover:border-zinc-300"
                    }`}
                  >
                    <div className={`p-2 rounded-lg shrink-0 ${on ? "bg-zinc-900 text-white" : "bg-zinc-200 text-zinc-500"}`}>
                      <Icon className="h-3.5 w-3.5" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-bold text-zinc-900 truncate">{label}</p>
                      <p className="text-[10px] text-zinc-500 truncate">{desc}</p>
                    </div>
                    {on && <Check className="h-3.5 w-3.5 text-emerald-600 shrink-0" />}
                  </button>
                );
              })}
            </div>
          </DraftCard>

          {/* Outreach */}
          <DraftCard
            icon={<Megaphone className="h-4 w-4" />}
            title="Participant Outreach"
            badge={`${lockedOutreach.length} lists · ~${lockedOutreach.length * 380} RSVPs`}
            source="From past registration funnels"
          >
            <div className="space-y-2">
              {OUTREACH.map(o => {
                const locked = lockedOutreach.includes(o.name);
                return (
                  <button
                    key={o.name}
                    onClick={() => toggleOutreach(o.name)}
                    className={`w-full flex items-start gap-3 p-2.5 rounded-xl border-2 text-left transition-all ${
                      locked ? "border-zinc-900 bg-white" : "border-zinc-200 bg-zinc-50/60 hover:border-zinc-300"
                    }`}
                  >
                    <div className={`p-2 rounded-lg shrink-0 ${locked ? "bg-zinc-900 text-white" : "bg-zinc-200 text-zinc-600"}`}>
                      <TrendingUp className="h-3.5 w-3.5" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1.5">
                        <p className="text-sm font-bold text-zinc-900 truncate">{o.name}</p>
                        {locked && <Check className="h-3.5 w-3.5 text-emerald-600 shrink-0" />}
                      </div>
                      <p className="text-[11px] text-zinc-500 truncate">{o.reach} · {o.channel}</p>
                      <p className="text-[10px] text-emerald-700 font-bold mt-0.5">{o.conversion}</p>
                    </div>
                  </button>
                );
              })}
            </div>
          </DraftCard>

          {/* Timeline */}
          <DraftCard
            icon={<Clock className="h-4 w-4" />}
            title="Run-of-Show Timeline"
            badge="6 milestones · auto-populated"
            source="Averaged across past playbooks"
          >
            <div className="relative">
              <div className="absolute left-[7px] top-3 bottom-3 w-px bg-zinc-200" />
              <div className="space-y-3">
                {TIMELINE.map((t, i) => (
                  <div key={t.week} className="flex items-center gap-4 relative">
                    <div className="h-3.5 w-3.5 rounded-full bg-white border-2 border-zinc-900 shrink-0 relative z-10" />
                    <div className="flex-1 flex items-center justify-between min-w-0">
                      <p className="text-sm font-semibold text-zinc-700 truncate">{t.task}</p>
                      <span className="font-mono text-[11px] font-bold text-zinc-500 shrink-0 ml-3">{t.week}</span>
                    </div>
                    {i === 0 && (
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-amber-100 text-amber-900 shrink-0">
                        Start here
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </DraftCard>
        </div>
      </section>

      {/* Final CTA */}
      <section className="rounded-2xl bg-gradient-to-br from-zinc-900 to-zinc-800 p-8 text-white">
        <div className="flex items-start justify-between gap-6">
          <div className="flex-1">
            <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-white/10 border border-white/20 text-[10px] font-bold uppercase tracking-wider mb-3">
              <ShieldCheck className="h-3 w-3" />
              Ready to launch
            </div>
            <h3 className="text-2xl font-extrabold tracking-tight">Lock the plan, ship the workspace.</h3>
            <p className="text-sm text-zinc-300 mt-2 max-w-xl leading-relaxed">
              I&apos;ll provision the Google Workspace, kick off sponsor emails, and surface the playbook
              to your team. You stay in the driver&apos;s seat — I just remove the busywork.
            </p>
          </div>
          <Button
            onClick={onLaunch}
            disabled={completion < 50}
            className="h-12 bg-white hover:bg-zinc-100 text-zinc-900 font-bold gap-2 px-6 rounded-xl disabled:opacity-40 shrink-0"
          >
            <Rocket className="h-4 w-4" />
            Launch event prep
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </section>
    </div>
  );
}

// ── Subcomponents ────────────────────────────────────────────────────────────

function BriefField({
  label,
  value,
  onChange,
  type = "text",
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  type?: string;
  placeholder?: string;
}) {
  return (
    <div>
      <label className="block text-[11px] font-bold uppercase tracking-wider text-zinc-500 mb-1.5">
        {label}
      </label>
      <Input
        value={value}
        type={type}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        className="h-10 bg-zinc-50 border-zinc-200 focus-visible:ring-zinc-900 rounded-xl font-semibold"
      />
    </div>
  );
}

function DraftCard({
  icon,
  title,
  badge,
  source,
  children,
  span,
}: {
  icon: React.ReactNode;
  title: string;
  badge: string;
  source: string;
  children: React.ReactNode;
  span?: string;
}) {
  return (
    <div className={`bg-white border border-zinc-200 rounded-2xl p-5 shadow-sm flex flex-col ${span ?? ""}`}>
      <div className="flex items-start justify-between mb-1">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-zinc-900 text-white">
            {icon}
          </div>
          <h3 className="text-sm font-extrabold text-zinc-900 tracking-tight">{title}</h3>
        </div>
        <button className="text-zinc-400 hover:text-zinc-900 transition-colors" title="Refine">
          <RefreshCw className="h-3.5 w-3.5" />
        </button>
      </div>
      <div className="flex items-center gap-2 mb-4 ml-8">
        <span className="text-[10px] font-bold text-emerald-700 bg-emerald-50 border border-emerald-200 px-1.5 py-0.5 rounded">
          {badge}
        </span>
        <span className="text-[10px] text-zinc-400 truncate">· {source}</span>
      </div>
      <div className="flex-1">
        {children}
      </div>
      <button className="mt-3 text-[11px] font-bold text-zinc-500 hover:text-zinc-900 inline-flex items-center gap-1 self-start">
        <Plus className="h-3 w-3" />
        Add more from the Architect
      </button>
    </div>
  );
}
