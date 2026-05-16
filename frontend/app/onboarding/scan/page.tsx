"use client";

import { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Image from "next/image";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Sparkles, Clock, Files, CheckCircle2, CalendarCheck, CalendarClock } from "lucide-react";

// ─── Types ───────────────────────────────────────────────────────────────────

type Phase = {
  label: string;
  sublabel: string;
  targetPct: number;    // bar fills up to this % during this phase
  durationMs: number;   // how long to stay in this phase
  skeleton: "files" | "graph" | "summary" | "done";
};

// ─── Phase definitions ───────────────────────────────────────────────────────

const PHASES: Phase[] = [
  {
    label: "Scanning your Workspace",
    sublabel: "Looking through your recent Google Drive files...",
    targetPct: 15,
    durationMs: 1600,
    skeleton: "files",
  },
  {
    label: "Found an event cluster!",
    sublabel: "Looks like there's a group of related files here.",
    targetPct: 30,
    durationMs: 1600,
    skeleton: "files",
  },
  {
    label: "Reading the data",
    sublabel: "Parsing docs, sheets, and slides in detail...",
    targetPct: 45,
    durationMs: 1600,
    skeleton: "files",
  },
  {
    label: "Getting relevant information",
    sublabel: "Pulling metadata, participants, and timestamps...",
    targetPct: 60,
    durationMs: 1600,
    skeleton: "graph",
  },
  {
    label: "Structuring the data",
    sublabel: "Mapping relationships and building the knowledge tree...",
    targetPct: 80,
    durationMs: 1600,
    skeleton: "summary",
  },
  {
    label: "Generating summary",
    sublabel: "Writing the playbook draft from what was found...",
    targetPct: 95,
    durationMs: 1600,
    skeleton: "summary",
  },
  {
    label: "Done!",
    sublabel: "Your event playbook is ready to review.",
    targetPct: 100,
    durationMs: 800,
    skeleton: "done",
  },
];

// ─── File type config ─────────────────────────────────────────────────────────

const FILE_TYPE_CONFIG: Record<string, { color: string; bg: string; icon: string }> = {
  Form: { color: "text-violet-600", bg: "bg-violet-50", icon: "/google-icons/google-forms.svg" },
  Sheet: { color: "text-emerald-600", bg: "bg-emerald-50", icon: "/google-icons/google-sheets.svg" },
  Doc: { color: "text-blue-600", bg: "bg-blue-50", icon: "/google-icons/google-docs.svg" },
  Slide: { color: "text-amber-600", bg: "bg-amber-50", icon: "/google-icons/google-slides.svg" },
};

const FILES = [
  { name: "Demo Day Registration", type: "Form", size: "2 pages" },
  { name: "Master Roster & Check-in", type: "Sheet", size: "143 rows" },
  { name: "Judge Scoring Rubric", type: "Doc", size: "5 pages" },
  { name: "Opening Ceremony Deck", type: "Slide", size: "18 slides" },
];

// ─── Skeleton components ──────────────────────────────────────────────────────

function Shimmer({ className }: { className: string }) {
  return (
    <div
      className={`bg-zinc-200 rounded animate-pulse ${className}`}
      style={{ backgroundImage: "linear-gradient(90deg, #e4e4e7 25%, #f4f4f5 50%, #e4e4e7 75%)", backgroundSize: "200% 100%", animation: "shimmer 1.5s infinite" }}
    />
  );
}

function SkeletonFiles({ phaseIndex }: { phaseIndex: number }) {
  // Reveal files as phases progress. 
  // Phase 0: 1 file, Phase 1: 2 files, Phase 2: 4 files.
  let visible = 1;
  if (phaseIndex === 1) visible = 2;
  if (phaseIndex >= 2) visible = FILES.length;
  return (
    <div className="space-y-2.5 w-full">
      {Array.from({ length: 4 }).map((_, i) => (
        <div
          key={i}
          className={`flex items-center gap-3 p-3 rounded-xl border border-zinc-100 bg-zinc-50 transition-all duration-500 ${i < visible ? "opacity-100" : "opacity-30"}`}
        >
          {i < visible ? (
            <>
              <div className={`p-2 rounded-lg ${FILE_TYPE_CONFIG[FILES[i].type].bg} flex-shrink-0`}>
                <Image src={FILE_TYPE_CONFIG[FILES[i].type].icon} alt={FILES[i].type} width={20} height={20} />
              </div>
              <div className="flex-1">
                <p className="text-sm font-semibold text-zinc-800">{FILES[i].name}</p>
                <p className="text-xs text-zinc-400">{FILES[i].size}</p>
              </div>
              <span className={`text-xs font-semibold px-2 py-0.5 rounded-md ${FILE_TYPE_CONFIG[FILES[i].type].bg} ${FILE_TYPE_CONFIG[FILES[i].type].color}`}>
                {FILES[i].type}
              </span>
            </>
          ) : (
            <>
              <Shimmer className="h-8 w-8 rounded-lg" />
              <div className="flex-1 space-y-1.5">
                <Shimmer className="h-3 w-3/4" />
                <Shimmer className="h-2.5 w-1/3" />
              </div>
              <Shimmer className="h-5 w-12 rounded-md" />
            </>
          )}
        </div>
      ))}
    </div>
  );
}

function SkeletonGraph() {
  return (
    <div className="w-full space-y-3">
      {/* Fake node graph */}
      <div className="flex items-center justify-center gap-3">
        <Shimmer className="h-14 w-14 rounded-full" />
        <div className="flex flex-col gap-2">
          <Shimmer className="h-8 w-8 rounded-full" />
          <Shimmer className="h-8 w-8 rounded-full" />
        </div>
        <div className="flex flex-col gap-2">
          <Shimmer className="h-6 w-6 rounded-full" />
          <Shimmer className="h-6 w-6 rounded-full" />
          <Shimmer className="h-6 w-6 rounded-full" />
        </div>
      </div>
      <div className="space-y-2 pt-2">
        {[70, 55, 85].map((w, i) => (
          <Shimmer key={i} className="h-2.5 rounded" style={{ width: `${w}%` } as React.CSSProperties} />
        ))}
      </div>
    </div>
  );
}

function SkeletonSummary() {
  return (
    <div className="w-full space-y-3">
      <div className="flex items-center gap-3">
        <Shimmer className="h-10 w-10 rounded-full" />
        <div className="flex-1 space-y-1.5">
          <Shimmer className="h-3.5 w-2/3" />
          <Shimmer className="h-2.5 w-1/2" />
        </div>
      </div>
      <Shimmer className="h-12 w-full rounded-xl" />
      <div className="space-y-2">
        <Shimmer className="h-2.5 w-full" />
        <Shimmer className="h-2.5 w-5/6" />
        <Shimmer className="h-2.5 w-3/4" />
      </div>
      <div className="flex gap-2 pt-1">
        <Shimmer className="h-6 w-20 rounded-full" />
        <Shimmer className="h-6 w-24 rounded-full" />
        <Shimmer className="h-6 w-16 rounded-full" />
      </div>
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

function ScanWorkspaceContent() {
  const [scanState, setScanState] = useState<"scanning" | "found">("scanning");
  const [phaseIndex, setPhaseIndex] = useState(0);
  const [progress, setProgress] = useState(0);
  const [eventTiming, setEventTiming] = useState<"past" | "upcoming" | null>(null);
  const router = useRouter();
  const searchParams = useSearchParams();
  const eventName = searchParams.get("name") || "Stanford AI Demo Day 2026";

  const phase = PHASES[phaseIndex];

  // Drive progress toward current phase target
  useEffect(() => {
    if (scanState !== "scanning") return;

    const target = phase.targetPct;
    const tick = setInterval(() => {
      setProgress((p) => {
        if (p >= target) return p;
        const step = Math.random() * 3 + 1;
        return Math.min(p + step, target);
      });
    }, 250);

    return () => clearInterval(tick);
  }, [phaseIndex, scanState, phase.targetPct]);

  // Advance phases on a timer (independent of API)
  useEffect(() => {
    if (scanState !== "scanning") return;
    if (phaseIndex >= PHASES.length - 1) return;

    const t = setTimeout(() => {
      setPhaseIndex((i) => i + 1);
    }, phase.durationMs);

    return () => clearTimeout(t);
  }, [phaseIndex, scanState, phase.durationMs]);

  // Real API call — on success, jump to last phase then "found"
  useEffect(() => {
    const run = async () => {
      try {
        const start = Date.now();
        const res = await fetch("http://localhost:8000/api/scan", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ userId: "user123", eventName }),
        });
        
        // Labor illusion: ensure the UI plays for at least 5.5 seconds 
        // to show the scanning animations properly before jumping.
        const elapsed = Date.now() - start;
        if (elapsed < 5500) {
          await new Promise((r) => setTimeout(r, 5500 - elapsed));
        }

        if (res.ok) finishScan();
      } catch {
        // fallback: let the phase timer naturally complete
      }
    };

    const totalDuration = PHASES.slice(0, -1).reduce((s, p) => s + p.durationMs, 0);
    const fallback = setTimeout(finishScan, totalDuration + 800);
    run();
    return () => clearTimeout(fallback);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function finishScan() {
    setPhaseIndex(PHASES.length - 1);
    setProgress(100);
    setTimeout(() => setScanState("found"), 700);
  }

  // Which skeleton to render
  const currentSkeleton = phase.skeleton;

  return (
    <div className={`flex-1 flex flex-col items-center justify-center w-full px-6 py-8 ${scanState === "scanning" ? "max-w-lg" : "max-w-5xl"}`}>
      {scanState === "scanning" ? (
        <div className="w-full space-y-8">

          {/* Phase heading */}
          <div className="text-center space-y-1.5">
            <h1 className="text-2xl font-bold text-zinc-900 transition-all duration-500">
              {phase.label}
            </h1>
            <p className="text-sm text-zinc-500 transition-all duration-500">
              {phase.sublabel}
            </p>
          </div>

          {/* Progress bar */}
          <div className="space-y-2">
            <div className="flex justify-between text-xs text-zinc-400 font-mono">
              <span>Step {phaseIndex + 1} of {PHASES.length}</span>
              <span>{Math.round(progress)}%</span>
            </div>
            <div className="h-1.5 w-full bg-zinc-100 rounded-full overflow-hidden">
              <div
                className="h-full bg-zinc-900 rounded-full transition-all duration-300 ease-out"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>

          {/* Skeleton screen — contextual per phase */}
          <div className={`bg-zinc-50 rounded-2xl border border-zinc-200 p-5 min-h-[220px] w-full flex flex-col ${currentSkeleton === "done" ? "items-center justify-center" : "items-start"}`}>
            {currentSkeleton === "files" && <SkeletonFiles phaseIndex={phaseIndex} />}
            {currentSkeleton === "graph" && <SkeletonGraph />}
            {currentSkeleton === "summary" && <SkeletonSummary />}
            {currentSkeleton === "done" && (
              <div className="flex flex-col items-center justify-center gap-3 text-center">
                <div className="h-12 w-12 rounded-full bg-green-100 flex items-center justify-center flex-shrink-0">
                  <CheckCircle2 className="h-6 w-6 text-green-600" />
                </div>
                <p className="text-sm font-semibold text-zinc-700">Playbook ready</p>
              </div>
            )}
          </div>

          {/* Escape — bottom */}
          <div className="flex justify-center pt-2">
            <button
              onClick={() => router.push("/")}
              className="text-xs text-zinc-400 hover:text-zinc-600 underline underline-offset-4 decoration-zinc-300 hover:decoration-zinc-500 transition-colors"
            >
              I don&apos;t want to upload an event right now
            </button>
          </div>
        </div>

      ) : (
        /* ── FOUND STATE ── */
        <div className="w-full animate-in fade-in zoom-in-95 duration-500 grid grid-cols-1 md:grid-cols-2 gap-6 items-stretch">

          {/* ── LEFT PANEL ── */}
          <div className="bg-white rounded-2xl border border-zinc-200 shadow-sm flex flex-col overflow-hidden">
            <div className="px-6 py-5 border-b border-zinc-100 bg-gradient-to-r from-zinc-100/60 to-white">
              <h2 className="text-xl font-bold tracking-tight text-zinc-900">Event Detected</h2>
              <p className="text-zinc-500 text-sm mt-1">
                AI found a cluster of documents that look like a recently planned event.
              </p>
            </div>

            <div className="px-6 py-4 border-b border-zinc-100">
              <div className="flex items-center justify-between mb-2">
                <Badge className="bg-zinc-100 text-zinc-900 hover:bg-zinc-200 font-medium text-xs px-2.5 py-0.5">
                  Hackathon
                </Badge>
                <span className="flex items-center gap-1.5 text-xs text-zinc-400 font-medium">
                  <Clock className="h-3 w-3" />
                  Last active: 2 days ago
                </span>
              </div>
              <h3 className="text-lg font-bold text-zinc-900">{eventName}</h3>
              <p className="text-xs text-zinc-500 mt-0.5 flex items-center gap-1.5">
                <Files className="h-3 w-3" />
                4 related files found in a shared Google Drive folder
              </p>
            </div>

            <div className="px-6 py-5 space-y-4 flex-1 flex flex-col">
              <p className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">Is this a past or upcoming event?</p>

              <div className="grid grid-cols-2 gap-3">
                <button
                  onClick={() => setEventTiming("past")}
                  className={`flex flex-col items-start gap-2 p-3 rounded-xl border-2 text-left transition-all ${eventTiming === "past" ? "border-zinc-900 bg-white shadow-sm" : "border-zinc-200 bg-zinc-50 hover:border-zinc-300"}`}
                >
                  <div className={`p-1.5 rounded-lg ${eventTiming === "past" ? "bg-zinc-900 text-white" : "bg-zinc-200 text-zinc-500"}`}>
                    <CalendarCheck className="h-4 w-4" />
                  </div>
                  <div>
                    <p className="text-sm font-bold text-zinc-900">Past event</p>
                    <p className="text-xs text-zinc-500 mt-0.5 leading-relaxed">Document what happened so others can replicate it.</p>
                  </div>
                </button>

                <button
                  onClick={() => setEventTiming("upcoming")}
                  className={`flex flex-col items-start gap-2 p-3 rounded-xl border-2 text-left transition-all ${eventTiming === "upcoming" ? "border-zinc-900 bg-white shadow-sm" : "border-zinc-200 bg-zinc-50 hover:border-zinc-300"}`}
                >
                  <div className={`p-1.5 rounded-lg ${eventTiming === "upcoming" ? "bg-zinc-900 text-white" : "bg-zinc-200 text-zinc-500"}`}>
                    <CalendarClock className="h-4 w-4" />
                  </div>
                  <div>
                    <p className="text-sm font-bold text-zinc-900">Upcoming event</p>
                    <p className="text-xs text-zinc-500 mt-0.5 leading-relaxed">AI will help you prepare forms, schedules, and comms.</p>
                  </div>
                </button>
              </div>

              {eventTiming && (
                <div className="rounded-xl bg-zinc-50 border border-zinc-200 px-4 py-3 text-xs text-zinc-600 leading-relaxed animate-in fade-in duration-200">
                  {eventTiming === "past"
                    ? "We'll extract what happened — participants, outcomes, assets — and turn it into a reusable playbook."
                    : "We'll scaffold what you need — registration forms, schedules, and communications — ready to launch."}
                </div>
              )}

              <div className="mt-auto space-y-2 pt-2">
                <Button
                  onClick={() => router.push(`/onboarding/review?timing=${eventTiming}`)}
                  disabled={!eventTiming}
                  className="w-full h-11 bg-black hover:bg-zinc-800 text-white gap-2 text-sm font-semibold rounded-xl shadow-sm shadow-zinc-200 disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  <Sparkles className="h-4 w-4" />
                  {eventTiming === "upcoming" ? "Plan this event" : "Build playbook"}
                </Button>

                <button
                  onClick={() => router.push("/")}
                  className="w-full text-xs text-zinc-400 hover:text-zinc-600 underline underline-offset-4 decoration-zinc-300 transition-colors py-1"
                >
                  Go back to explore
                </button>
              </div>
            </div>
          </div>

          {/* ── RIGHT PANEL — FILES ── */}
          <div className="bg-white rounded-2xl border border-zinc-200 shadow-sm flex flex-col overflow-hidden">
            <div className="px-6 py-5 border-b border-zinc-100 bg-gradient-to-r from-zinc-100/60 to-white">
              <div className="flex items-center gap-2">
                <Files className="h-4 w-4 text-zinc-500" />
                <h3 className="text-sm font-semibold text-zinc-900 uppercase tracking-wider">Found Files</h3>
              </div>
              <p className="text-xs text-zinc-500 mt-1">Documents pulled from your shared Drive folder.</p>
            </div>

            <div className="px-5 py-4 space-y-2 flex-1">
              {FILES.map(({ name, type, size }) => {
                const cfg = FILE_TYPE_CONFIG[type];
                return (
                  <div
                    key={name}
                    className="flex items-center gap-3 p-3 rounded-xl bg-zinc-50 border border-zinc-100 hover:border-zinc-200 transition-colors"
                  >
                    <div className={`p-2 rounded-lg ${cfg.bg} flex-shrink-0`}>
                      <Image src={cfg.icon} alt={type} width={20} height={20} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-semibold text-zinc-800 truncate">{name}</p>
                      <p className="text-xs text-zinc-400">{size}</p>
                    </div>
                    <span className={`text-xs font-semibold px-2 py-0.5 rounded-md ${cfg.bg} ${cfg.color}`}>
                      {type}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function ScanWorkspacePage() {
  return (
    <div className="min-h-screen bg-white flex flex-col items-center">
      <Suspense fallback={<div className="flex-1 flex flex-col items-center justify-center w-full max-w-lg px-6 py-12"><div className="w-8 h-8 rounded-full border-4 border-zinc-200 border-t-zinc-900 animate-spin" /></div>}>
        <ScanWorkspaceContent />
      </Suspense>
    </div>
  );
}
