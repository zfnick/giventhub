"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Sparkles,
  Loader2,
  ArrowRight,
  Folder,
  FileText,
  ClipboardList,
  Sheet,
  Presentation,
  Mail,
  Calendar,
  Upload,
  Check,
  X,
  ListChecks,
  ExternalLink,
} from "lucide-react";
import { useAuth } from "@/lib/AuthContext";
import { apiFetch } from "@/lib/api";

interface PlannedAsset {
  name: string;
  type: string;
}

interface AdaptPlaybookModalProps {
  playbookId: string;
  playbookTitle?: string;
  /**
   * Source-playbook asset list. When provided, the modal seeds the progress
   * feed with skeleton rows (one per asset) before the agent emits anything,
   * so the user sees the intended Workspace shape immediately and watches it
   * fill in. Order matches the source.
   */
  sourceAssets?: PlannedAsset[];
}

// ── Progress feed types ──────────────────────────────────────────────────────

type ProgressStatus = "pending" | "running" | "done" | "failed";

interface ProgressItem {
  id: number;
  /** Backend tool name, e.g. "create_google_doc". `_meta` keys are local-only. */
  name: string;
  label: string;
  subtitle?: string;
  url?: string;
  status: ProgressStatus;
}

// Asset `type` strings (from the seed data / Firestore) → ADK tool name.
// Used to convert planned assets into matching skeleton rows.
const ASSET_TYPE_TO_TOOL: Record<string, string> = {
  "Google Forms": "create_google_form",
  "Google Sheets": "create_google_sheet",
  "Google Docs": "create_google_doc",
  "Google Slides": "create_google_slide_deck",
  Form: "create_google_form",
  Sheet: "create_google_sheet",
  Doc: "create_google_doc",
  Slide: "create_google_slide_deck",
  Slides: "create_google_slide_deck",
};

function assetTypeToTool(type: string): string | null {
  return ASSET_TYPE_TO_TOOL[type] ?? null;
}

type IconType = typeof Folder;

// Maps each ADK tool call to a friendly "currently doing X" label + icon.
// Anything missing here falls through to `humanize(name)` + Sparkles.
const TOOL_UI: Record<string, { verbing: string; icon: IconType }> = {
  create_drive_folder: { verbing: "Creating Drive folder", icon: Folder },
  upload_drive_file: { verbing: "Uploading file to Drive", icon: Upload },
  upload_drive_files: { verbing: "Uploading files to Drive", icon: Upload },
  create_google_doc: { verbing: "Creating Google Doc", icon: FileText },
  update_google_doc_content: { verbing: "Writing Doc content", icon: FileText },
  create_google_form: { verbing: "Creating Google Form", icon: ClipboardList },
  update_google_form: { verbing: "Updating Form questions", icon: ClipboardList },
  create_google_sheet: { verbing: "Creating Google Sheet", icon: Sheet },
  update_google_sheet_values: { verbing: "Filling in Sheet", icon: Sheet },
  update_sheet_crm: { verbing: "Appending to CRM sheet", icon: Sheet },
  create_google_slide_deck: { verbing: "Creating Google Slides", icon: Presentation },
  update_google_slide_deck: { verbing: "Building slides", icon: Presentation },
  create_gmail_draft: { verbing: "Drafting email", icon: Mail },
  send_gmail_message: { verbing: "Sending email", icon: Mail },
  create_calendar_draft: { verbing: "Creating Calendar event", icon: Calendar },
};

function humanize(name: string): string {
  return name.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());
}

function uiFor(name: string): { verbing: string; icon: IconType } {
  return TOOL_UI[name] ?? { verbing: humanize(name), icon: Sparkles };
}

// ── Stream event types (must match backend/main.py adapt_playbook_stream) ───

type StreamEvent =
  | { type: "fork_created"; playbook_id: string; title?: string }
  | { type: "tool_call"; name: string; args?: Record<string, unknown> }
  | { type: "tool_result"; name: string; title?: string; url?: string; executed?: boolean }
  | { type: "thought"; text: string }
  | { type: "skipped"; reason: string }
  | { type: "error"; detail: string; status?: number }
  | { type: "final"; workspaceUrl?: string; playbook_id?: string };

// ── Component ────────────────────────────────────────────────────────────────

export function AdaptPlaybookModal({
  playbookId,
  playbookTitle = "Playbook",
  sourceAssets = [],
}: AdaptPlaybookModalProps) {
  const router = useRouter();
  const [prompt, setPrompt] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { user, googleAccessToken } = useAuth();

  // Live progress feed driven by the NDJSON stream from /api/adapt/stream.
  const [progress, setProgress] = useState<ProgressItem[]>([]);
  const [workspaceUrl, setWorkspaceUrl] = useState("");
  const [forkId, setForkId] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const idRef = useRef(0);

  const resetFeed = () => {
    setProgress([]);
    setWorkspaceUrl("");
    setForkId(null);
    setDone(false);
    idRef.current = 0;
  };

  /** Optimistic skeleton: the rows we expect the agent to fill in. */
  const buildSkeleton = (): ProgressItem[] => {
    const rows: ProgressItem[] = [
      {
        id: idRef.current++,
        name: "_fork",
        label: "Saving fork to your playbooks",
        status: "pending",
      },
      {
        id: idRef.current++,
        name: "create_drive_folder",
        label: uiFor("create_drive_folder").verbing,
        status: "pending",
      },
    ];
    for (const asset of sourceAssets) {
      const tool = assetTypeToTool(asset.type);
      if (!tool) continue;
      rows.push({
        id: idRef.current++,
        name: tool,
        label: uiFor(tool).verbing,
        subtitle: asset.name,
        status: "pending",
      });
    }
    return rows;
  };

  const pushItem = (item: Omit<ProgressItem, "id">) => {
    setProgress((p) => [...p, { id: idRef.current++, ...item }]);
  };

  /** Upgrade the first pending row that matches `name`, or append a new row.
   *
   * The seeded skeleton sets up rows in source order; this keeps the feed in
   * that order even when the agent fires several creates back-to-back. If the
   * agent does something we didn't predict (e.g. a follow-up `update_*`), we
   * just append it at the end so nothing is hidden.
   */
  const upgradePendingOrAppend = (
    name: string,
    patch: Partial<Omit<ProgressItem, "id" | "name">> & { status: ProgressStatus },
  ) => {
    setProgress((p) => {
      const idx = p.findIndex((it) => it.name === name && it.status === "pending");
      if (idx >= 0) {
        const next = [...p];
        next[idx] = {
          ...next[idx],
          ...patch,
          subtitle: patch.subtitle ?? next[idx].subtitle,
          url: patch.url ?? next[idx].url,
        };
        return next;
      }
      return [
        ...p,
        {
          id: idRef.current++,
          name,
          label: uiFor(name).verbing,
          subtitle: patch.subtitle,
          url: patch.url,
          status: patch.status,
        },
      ];
    });
  };

  const finishMatching = (
    name: string,
    patch: { url?: string; subtitle?: string; status: ProgressStatus },
  ) => {
    setProgress((p) => {
      // Prefer the most recent *running* row (the call we're finishing).
      for (let i = p.length - 1; i >= 0; i--) {
        if (p[i].name === name && p[i].status === "running") {
          const next = [...p];
          next[i] = {
            ...next[i],
            status: patch.status,
            url: patch.url || next[i].url,
            subtitle: patch.subtitle || next[i].subtitle,
          };
          return next;
        }
      }
      // Sometimes the tool_call event is missed and only a result lands —
      // promote the first pending skeleton with the same name straight to done.
      const pendingIdx = p.findIndex((it) => it.name === name && it.status === "pending");
      if (pendingIdx >= 0) {
        const next = [...p];
        next[pendingIdx] = {
          ...next[pendingIdx],
          status: patch.status,
          url: patch.url || next[pendingIdx].url,
          subtitle: patch.subtitle || next[pendingIdx].subtitle,
        };
        return next;
      }
      // Unrecognized result — append.
      return [
        ...p,
        {
          id: idRef.current++,
          name,
          label: uiFor(name).verbing,
          subtitle: patch.subtitle,
          url: patch.url,
          status: patch.status,
        },
      ];
    });
  };

  const handleEvent = (evt: StreamEvent) => {
    switch (evt.type) {
      case "fork_created":
        setForkId(evt.playbook_id);
        // Fills in the seeded `_fork` skeleton — falls back to an append on
        // the off-chance the skeleton wasn't built (e.g. no sourceAssets).
        upgradePendingOrAppend("_fork", {
          label: "Saved fork to your playbooks",
          subtitle: evt.title,
          status: "done",
        });
        return;

      case "tool_call": {
        const args = evt.args ?? {};
        const subtitle =
          typeof args.title === "string"
            ? args.title
            : typeof args.folder_name === "string"
              ? args.folder_name
              : undefined;
        upgradePendingOrAppend(evt.name, { subtitle, status: "running" });
        return;
      }

      case "tool_result":
        finishMatching(evt.name, {
          url: evt.url,
          subtitle: evt.title,
          status: evt.executed === false ? "failed" : "done",
        });
        return;

      case "skipped":
        pushItem({ name: "_skip", label: evt.reason, status: "done" });
        return;

      case "error":
        setError(evt.detail || "Workspace provisioning failed.");
        pushItem({
          name: "_error",
          label: evt.detail || "Workspace provisioning failed.",
          status: "failed",
        });
        return;

      case "final":
        if (evt.workspaceUrl) setWorkspaceUrl(evt.workspaceUrl);
        if (evt.playbook_id) setForkId(evt.playbook_id);
        // Any skeleton row still in `pending` state at this point is something
        // the agent declined to create — mark it failed so the UI tells the
        // truth instead of pulsing forever.
        setProgress((p) =>
          p.map((it) => (it.status === "pending" ? { ...it, status: "failed" } : it)),
        );
        setDone(true);
        return;

      // `thought` events are noisy; we intentionally drop them from the feed.
      default:
        return;
    }
  };

  const handleAdapt = async () => {
    setError(null);

    if (!prompt.trim()) {
      setError("Please describe how you want to adapt the playbook.");
      return;
    }
    if (!user) {
      setError("Please sign in to fork a playbook.");
      return;
    }

    resetFeed();
    // Seed the feed BEFORE we hit the network — the user sees the planned
    // Workspace shape (folder + each asset) immediately, instead of staring
    // at an empty modal until the first event lands.
    setProgress(buildSkeleton());
    setIsGenerating(true);

    try {
      const res = await apiFetch(user, "/api/adapt/stream", {
        method: "POST",
        json: {
          prompt,
          playbookId,
          playbookTitle,
          googleAccessToken: googleAccessToken ?? undefined,
        },
      });

      if (!res.ok || !res.body) {
        const detail = await res.text().catch(() => "");
        throw new Error(detail || `Adapt failed (${res.status}).`);
      }

      // Parse NDJSON: split on `\n`, leave the trailing partial line in the buffer.
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buf = "";

      while (true) {
        const { value, done: streamDone } = await reader.read();
        if (streamDone) break;
        buf += decoder.decode(value, { stream: true });
        const lines = buf.split("\n");
        buf = lines.pop() ?? "";
        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed) continue;
          try {
            handleEvent(JSON.parse(trimmed) as StreamEvent);
          } catch {
            // Drop non-JSON keepalive lines silently.
          }
        }
      }
      // Flush any final partial line.
      const tail = buf.trim();
      if (tail) {
        try {
          handleEvent(JSON.parse(tail) as StreamEvent);
        } catch {
          /* ignore */
        }
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "An unexpected error occurred.";
      setError(msg);
      pushItem({ name: "_error", label: msg, status: "failed" });
      setDone(true);
    } finally {
      setIsGenerating(false);
    }
  };

  const goToPlaybook = () => {
    setIsOpen(false);
    setPrompt("");
    resetFeed();
    if (forkId) {
      router.push(`/playbooks/${forkId}`);
      router.refresh();
    } else {
      router.push("/playbooks");
    }
  };

  const tokenWarning = user && !googleAccessToken;
  const showFeed = isGenerating || progress.length > 0;

  return (
    <Dialog
      open={isOpen}
      onOpenChange={(open) => {
        // Block closing mid-run — the stream is still writing to Firestore.
        if (!open && isGenerating) return;
        setIsOpen(open);
        if (!open) {
          setPrompt("");
          setError(null);
          resetFeed();
        }
      }}
    >
      <DialogTrigger render={<Button className="gap-2" />}>
        <Sparkles className="h-4 w-4" />
        Adapt Playbook
      </DialogTrigger>
      <DialogContent className="sm:max-w-[560px] p-6">
        <DialogHeader className="mb-2">
          <DialogTitle className="text-2xl font-bold flex items-center gap-2">
            <Sparkles className="h-6 w-6 text-zinc-900 dark:text-zinc-100" /> Adapt Playbook
          </DialogTitle>
          <DialogDescription className="text-zinc-600 dark:text-zinc-400 mt-2 leading-relaxed">
            {showFeed ? (
              <>
                Forking{" "}
                <span className="font-semibold text-zinc-900 dark:text-zinc-100">
                  {playbookTitle}
                </span>{" "}
                — watch the AI build your Workspace below.
              </>
            ) : (
              <>
                You are adapting{" "}
                <span className="font-semibold text-zinc-900 dark:text-zinc-100">
                  {playbookTitle}
                </span>
                . Tell our AI what kind of event you&apos;re planning — we&apos;ll fork it into your
                playbooks and provision your Google Workspace.
              </>
            )}
          </DialogDescription>
        </DialogHeader>

        {/* ── Phase 1: prompt input (hidden once we start streaming) ── */}
        {!showFeed && (
          <div className="grid gap-5 py-4">
            <div className="space-y-3">
              <Label htmlFor="prompt" className="text-sm font-semibold">
                Your Event Context
              </Label>
              <Textarea
                id="prompt"
                placeholder="e.g. Make this for high school students focusing on Climate Tech in San Francisco. Keep the event to 24 hours."
                className="h-32 resize-none p-3 text-base"
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                disabled={isGenerating}
              />
            </div>
            <div className="bg-zinc-50/80 dark:bg-zinc-900/30 text-zinc-800 dark:text-zinc-300 p-4 rounded-xl text-sm flex gap-3 border border-zinc-200 dark:border-zinc-800 leading-relaxed shadow-sm">
              <Sparkles className="h-5 w-5 shrink-0 mt-0.5 text-zinc-500" />
              <p>
                <strong>AI Action:</strong> We&apos;ll fork this playbook into your library,
                customize the registration form, generate a tailored judging rubric, and create
                a shared Google Drive folder for your team — live, step-by-step.
              </p>
            </div>
            {tokenWarning && (
              <div className="text-xs font-medium text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
                Heads up — your Google Workspace token isn&apos;t in this session, so the fork
                will be saved but Drive assets won&apos;t be provisioned. Sign in with Google
                again to grant Workspace access.
              </div>
            )}
            {error && (
              <div className="text-sm font-medium text-red-500 dark:text-red-400">{error}</div>
            )}
          </div>
        )}

        {/* ── Phase 2: streaming progress feed ── */}
        {showFeed && (
          <div className="py-2">
            <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-zinc-500 mb-2 px-1">
              <ListChecks className="h-3.5 w-3.5" />
              {done ? "Done" : "Working"}
              <span className="ml-auto font-mono text-zinc-400 normal-case tracking-normal">
                {progress.filter((p) => p.status === "done").length}/{progress.length}
              </span>
            </div>
            <ol className="space-y-1.5 max-h-[360px] overflow-y-auto pr-1">
              {progress.map((item) => (
                <ProgressRow key={item.id} item={item} />
              ))}
            </ol>
            {error && (
              <div className="mt-3 text-sm font-medium text-red-500 dark:text-red-400">
                {error}
              </div>
            )}
          </div>
        )}

        <DialogFooter className="mt-4 gap-2 sm:gap-0">
          {!showFeed && (
            <>
              <Button
                variant="outline"
                onClick={() => setIsOpen(false)}
                disabled={isGenerating}
                className="sm:mr-auto"
              >
                Cancel
              </Button>
              <Button
                onClick={handleAdapt}
                disabled={isGenerating || !prompt.trim()}
                className="bg-black hover:bg-zinc-800 dark:bg-white dark:hover:bg-zinc-200 dark:text-black text-white gap-2 font-semibold shadow-md transition-all"
              >
                Create Workspace <ArrowRight className="h-4 w-4" />
              </Button>
            </>
          )}
          {showFeed && (
            <>
              {workspaceUrl && done && (
                <a
                  href={workspaceUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 h-10 px-4 rounded-md border border-zinc-200 bg-white text-sm font-semibold text-zinc-700 hover:bg-zinc-50 transition-colors sm:mr-auto"
                >
                  <ExternalLink className="h-4 w-4" />
                  Open Drive folder
                </a>
              )}
              <Button
                onClick={goToPlaybook}
                disabled={!done}
                className="bg-black hover:bg-zinc-800 dark:bg-white dark:hover:bg-zinc-200 dark:text-black text-white gap-2 font-semibold shadow-md transition-all"
              >
                {done ? (
                  <>
                    View my playbook <ArrowRight className="h-4 w-4" />
                  </>
                ) : (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" /> Running…
                  </>
                )}
              </Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ── Subcomponent: a single row in the progress feed ─────────────────────────

function ProgressRow({ item }: { item: ProgressItem }) {
  const { icon: Icon } = uiFor(item.name);
  const isMeta = item.name.startsWith("_");
  const isPending = item.status === "pending";

  return (
    <li
      className={`flex items-center gap-3 px-3 py-2 rounded-lg border transition-colors ${
        isPending
          ? "border-zinc-100 bg-zinc-50/50 dark:bg-zinc-900/20 dark:border-zinc-800/50"
          : "border-zinc-200 bg-white dark:bg-zinc-900/40 dark:border-zinc-800"
      }`}
    >
      {/* Icon tile — desaturated + pulsing while we're still waiting on it. */}
      <div
        className={`h-7 w-7 rounded-lg flex items-center justify-center shrink-0 ${
          item.status === "failed"
            ? "bg-red-100 text-red-600"
            : item.status === "done"
              ? "bg-emerald-50 text-emerald-700"
              : isPending
                ? "bg-zinc-100/70 text-zinc-300 animate-pulse"
                : "bg-zinc-100 text-zinc-700"
        }`}
      >
        {isMeta && item.status === "done" ? (
          <Check className="h-3.5 w-3.5" />
        ) : isMeta && item.status === "failed" ? (
          <X className="h-3.5 w-3.5" />
        ) : (
          <Icon className="h-3.5 w-3.5" />
        )}
      </div>

      {/* Text — replaced with a shimmer bar pair while pending. */}
      <div className="flex-1 min-w-0">
        {isPending ? (
          <>
            <div className="h-3 w-2/3 max-w-[180px] rounded bg-zinc-200/80 dark:bg-zinc-700/40 animate-pulse" />
            <div className="mt-1.5 h-2.5 w-1/2 max-w-[120px] rounded bg-zinc-100 dark:bg-zinc-800/40 animate-pulse" />
          </>
        ) : (
          <>
            <p className="text-sm font-semibold text-zinc-900 dark:text-zinc-100 truncate">
              {item.label}
            </p>
            {item.subtitle && (
              <p className="text-xs text-zinc-500 truncate">{item.subtitle}</p>
            )}
          </>
        )}
      </div>

      {item.url && !isPending && (
        <a
          href={item.url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-zinc-400 hover:text-zinc-900 transition-colors"
          title="Open"
        >
          <ExternalLink className="h-3.5 w-3.5" />
        </a>
      )}

      <div className="w-5 flex justify-end">
        {item.status === "pending" && (
          <div className="h-1.5 w-1.5 rounded-full bg-zinc-300 animate-pulse" />
        )}
        {item.status === "running" && (
          <Loader2 className="h-4 w-4 animate-spin text-zinc-400" />
        )}
        {item.status === "done" && (
          <Check className="h-4 w-4 text-emerald-500" />
        )}
        {item.status === "failed" && <X className="h-4 w-4 text-red-500" />}
      </div>
    </li>
  );
}
