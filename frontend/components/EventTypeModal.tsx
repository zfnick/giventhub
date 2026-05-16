"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { CalendarCheck, CalendarClock, ArrowRight } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogTrigger,
} from "@/components/ui/dialog";

type EventTiming = "past" | "upcoming" | null;

export function EventTypeModal({ children }: { children: React.ReactNode }) {
  const [timing, setTiming] = useState<EventTiming>(null);
  const [open, setOpen] = useState(false);
  const router = useRouter();

  const handleContinue = () => {
    if (!timing) return;
    setOpen(false);
    if (timing === "past") {
      router.push("/onboarding/import");
    } else {
      router.push("/event/new");
    }
  };

  return (
    <Dialog open={open} onOpenChange={(o) => { setOpen(o); if (!o) setTiming(null); }}>
      <DialogTrigger render={children as any} />
      <DialogContent
        showCloseButton
        className="max-w-md w-full p-0 overflow-hidden rounded-2xl"
      >
        <div className="px-6 pt-6 pb-2">
          <h2 className="text-lg font-bold text-zinc-900">Import a Playbook</h2>
          <p className="text-sm text-zinc-500 mt-1">
            Is this a past event you want to document, or an upcoming event you want to plan?
          </p>
        </div>

        <div className="px-6 py-4 space-y-3">
          <button
            onClick={() => setTiming("past")}
            className={`w-full flex items-center gap-4 px-4 py-4 rounded-xl border-2 text-left transition-all ${
              timing === "past"
                ? "border-zinc-900 bg-white shadow-sm"
                : "border-zinc-200 bg-zinc-50 hover:border-zinc-300"
            }`}
          >
            <div className={`p-2.5 rounded-xl shrink-0 ${timing === "past" ? "bg-zinc-900 text-white" : "bg-zinc-200 text-zinc-500"}`}>
              <CalendarCheck className="h-5 w-5" />
            </div>
            <div className="flex-1">
              <p className="text-sm font-bold text-zinc-900">Past event</p>
              <p className="text-xs text-zinc-500 mt-0.5">
                Import from Google Workspace. AI builds a reusable playbook from your files.
              </p>
            </div>
            <div className={`h-4 w-4 rounded-full border-2 shrink-0 flex items-center justify-center ${timing === "past" ? "border-zinc-900" : "border-zinc-300"}`}>
              {timing === "past" && <div className="h-2 w-2 rounded-full bg-zinc-900" />}
            </div>
          </button>

          <button
            onClick={() => setTiming("upcoming")}
            className={`w-full flex items-center gap-4 px-4 py-4 rounded-xl border-2 text-left transition-all ${
              timing === "upcoming"
                ? "border-zinc-900 bg-white shadow-sm"
                : "border-zinc-200 bg-zinc-50 hover:border-zinc-300"
            }`}
          >
            <div className={`p-2.5 rounded-xl shrink-0 ${timing === "upcoming" ? "bg-zinc-900 text-white" : "bg-zinc-200 text-zinc-500"}`}>
              <CalendarClock className="h-5 w-5" />
            </div>
            <div className="flex-1">
              <p className="text-sm font-bold text-zinc-900">Upcoming event</p>
              <p className="text-xs text-zinc-500 mt-0.5">
                Plan from a playbook or scratch. AI sets up your Workspace — forms, calendars, emails.
              </p>
            </div>
            <div className={`h-4 w-4 rounded-full border-2 shrink-0 flex items-center justify-center ${timing === "upcoming" ? "border-zinc-900" : "border-zinc-300"}`}>
              {timing === "upcoming" && <div className="h-2 w-2 rounded-full bg-zinc-900" />}
            </div>
          </button>
        </div>

        <div className="px-6 pb-6">
          <button
            onClick={handleContinue}
            disabled={!timing}
            className="w-full h-11 flex items-center justify-center gap-2 bg-zinc-900 hover:bg-zinc-800 text-white text-sm font-semibold rounded-xl transition-all disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Continue
            <ArrowRight className="h-4 w-4" />
          </button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
