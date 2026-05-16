"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Sparkles, Search } from "lucide-react";

export default function ImportEventPage() {
  const [eventName, setEventName] = useState("");
  const [isSearching, setIsSearching] = useState(false);
  const router = useRouter();

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (eventName.trim()) {
      setIsSearching(true);
      // Brief pause for the "Let us search it for you" wow moment
      setTimeout(() => {
        router.push(`/onboarding/scan?name=${encodeURIComponent(eventName.trim())}`);
      }, 1800);
    }
  };

  if (isSearching) {
    return (
      <div className="min-h-screen bg-white flex flex-col items-center justify-center px-6">
        <div className="w-full max-w-md text-center space-y-6 animate-in fade-in zoom-in-95 duration-500">
          <div className="relative">
            <div className="absolute inset-0 bg-zinc-900 rounded-full blur-2xl opacity-5 animate-pulse" />
            <div className="relative inline-flex h-20 w-20 items-center justify-center rounded-2xl bg-black mb-4 transform rotate-12 transition-transform hover:rotate-0 duration-500">
              <Search className="h-10 w-10 text-white animate-pulse" />
            </div>
          </div>
          <div className="space-y-2">
            <h1 className="text-3xl font-bold tracking-tight text-zinc-900">
              {eventName}
            </h1>
            <p className="text-xl text-zinc-500 font-medium">
              Let us search it for you...
            </p>
          </div>
          <div className="flex justify-center gap-1">
            <div className="h-1.5 w-1.5 bg-zinc-900 rounded-full animate-bounce [animation-delay:-0.3s]" />
            <div className="h-1.5 w-1.5 bg-zinc-900 rounded-full animate-bounce [animation-delay:-0.15s]" />
            <div className="h-1.5 w-1.5 bg-zinc-900 rounded-full animate-bounce" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-white flex flex-col items-center justify-center px-6 py-12">
      <div className="w-full max-w-md space-y-8 animate-in fade-in zoom-in-95 duration-500">
        <div className="text-center space-y-3">
          <div className="inline-flex h-12 w-12 items-center justify-center rounded-xl bg-zinc-100 mb-2">
            <Search className="h-6 w-6 text-zinc-600" />
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-zinc-900">
            What is the name of your event?
          </h1>
          <p className="text-zinc-500">
            We&apos;ll look through your Google Workspace to find related assets.
          </p>
        </div>

        <form onSubmit={handleSearch} className="space-y-4 pt-4">
          <Input
            autoFocus
            value={eventName}
            onChange={(e) => setEventName(e.target.value)}
            placeholder="e.g., Stanford AI Demo Day 2026"
            className="h-14 text-lg px-4 bg-zinc-50 border-zinc-200 focus-visible:ring-zinc-900 rounded-xl"
          />
          <Button
            type="submit"
            disabled={!eventName.trim() || isSearching}
            className="w-full h-12 bg-black hover:bg-zinc-800 text-white gap-2 text-sm font-semibold rounded-xl shadow-lg shadow-zinc-200"
          >
            <Sparkles className="h-4 w-4" />
            Search Workspace
          </Button>
        </form>

        <div className="flex justify-center pt-2">
          <button
            onClick={() => router.push("/")}
            className="text-sm text-zinc-400 hover:text-zinc-600 underline underline-offset-4 decoration-zinc-300 hover:decoration-zinc-500 transition-colors"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
