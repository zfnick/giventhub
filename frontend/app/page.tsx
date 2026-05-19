"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { Sparkles, Users, Calendar, MessageSquare } from "lucide-react";
import { Button } from "@/components/ui/button";
import { EventTypeModal } from "@/components/EventTypeModal";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { NavBar } from "@/components/NavBar";
import { useAuth } from "@/lib/AuthContext";
import { apiFetch } from "@/lib/api";
import PlasmaWave from "@/components/PlasmaWave";

interface PublicPlaybook {
  id: string;
  title: string;
  author: string;
  description: string;
  attendees: string;
  duration: string;
  category: string;
  stats: string;
  imageUrl?: string | null;
}

const PLAYBOOK_PLACEHOLDER_IMAGES = [
  "/playbook-placeholders/hackathon.jpg",
  "/playbook-placeholders/showcase.jpg",
  "/playbook-placeholders/conference.jpg",
  "/playbook-placeholders/workshop.jpg",
  "/playbook-placeholders/meetup.jpg",
];

const PLAYBOOK_IMAGE_BY_CATEGORY: Record<string, string> = {
  bootcamp: PLAYBOOK_PLACEHOLDER_IMAGES[3],
  conference: PLAYBOOK_PLACEHOLDER_IMAGES[2],
  "demo day": PLAYBOOK_PLACEHOLDER_IMAGES[1],
  hackathon: PLAYBOOK_PLACEHOLDER_IMAGES[0],
  meetup: PLAYBOOK_PLACEHOLDER_IMAGES[4],
  "pitch night": PLAYBOOK_PLACEHOLDER_IMAGES[1],
  showcase: PLAYBOOK_PLACEHOLDER_IMAGES[1],
  sprint: PLAYBOOK_PLACEHOLDER_IMAGES[3],
  summit: PLAYBOOK_PLACEHOLDER_IMAGES[2],
  workshop: PLAYBOOK_PLACEHOLDER_IMAGES[3],
};

function hashString(value: string): number {
  return Array.from(value).reduce((sum, char) => sum + char.charCodeAt(0), 0);
}

function getPlaybookImage(playbook: PublicPlaybook): string {
  if (playbook.imageUrl) return playbook.imageUrl;
  const categoryKey = playbook.category.toLowerCase();
  return (
    PLAYBOOK_IMAGE_BY_CATEGORY[categoryKey] ??
    PLAYBOOK_PLACEHOLDER_IMAGES[hashString(playbook.id) % PLAYBOOK_PLACEHOLDER_IMAGES.length]
  );
}

// ── Page ─────────────────────────────────────────────────────────────────────
export default function ExplorePage() {
  const { user } = useAuth();
  const [filter, setFilter] = useState("All");
  const [playbooks, setPlaybooks] = useState<PublicPlaybook[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await apiFetch(null, "/api/playbooks");
        if (cancelled) return;
        if (!res.ok) {
          console.error("Failed to load playbooks:", res.status);
          setPlaybooks([]);
          return;
        }
        const data = await res.json();
        setPlaybooks(data.playbooks ?? []);
      } catch (err) {
        console.error("Error loading playbooks:", err);
        setPlaybooks([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const categories = useMemo(() => {
    const set = new Set<string>();
    playbooks.forEach((p) => p.category && set.add(p.category));
    return ["All", ...Array.from(set).sort()];
  }, [playbooks]);

  const filtered =
    filter === "All" ? playbooks : playbooks.filter((p) => p.category === filter);

  return (
    <div className="min-h-screen">
      <NavBar />

      {/* ── Hero ─────────────────────────────────────────────────────────── */}
      <section className="h-[400px] relative overflow-hidden bg-white border-b border-zinc-200 flex items-center justify-center py-32">
        {/* Plasma-wave animated background */}
        <PlasmaWave
          colors={["#10b981", "#3b82f6"]}
          rotationDeg={198}
          bend1={2.0}
          bend2={1.6}
          dir2={-0.5}
          focalLength={1.65}
        />

        {/* Light overlay to keep text readable */}
        <div className="absolute inset-0 bg-white/40 z-[1]" />

        {/* Content */}
        <div className="relative z-10 container mx-auto px-6 flex flex-col items-center text-center gap-8">
          <h1 className="text-6xl sm:text-7xl lg:text-8xl font-extrabold tracking-tight text-zinc-900 max-w-4xl leading-tight">
            Community Playbooks
          </h1>

          <p className="text-xl sm:text-2xl text-zinc-600 max-w-3xl leading-relaxed">
            Discover and adapt successful event architectures. Don&apos;t start from
            scratch - adapt proven playbooks from the ecosystem.
          </p>

          <div className="flex flex-col sm:flex-row items-center gap-4">
            <EventTypeModal>
              <Button className="gap-2 h-11 px-7 bg-black hover:bg-zinc-800 text-white text-sm font-semibold shadow-lg">
                <Sparkles className="h-4 w-4" />
                Import a Playbook
              </Button>
            </EventTypeModal>
            <Link href={user ? "/chat" : "/onboarding/login"}>
              <Button variant="outline" className="gap-2 h-11 px-7 bg-white hover:bg-zinc-50 text-zinc-900 border-zinc-200 text-sm font-semibold shadow-sm">
                <MessageSquare className="h-4 w-4" />
                Chat
              </Button>
            </Link>
          </div>
        </div>
      </section>


      {/* ── Featured Event Templates ───────────────────────────────────────── */}
      <main className="container mx-auto px-6 py-14">
        <div className="mb-10">
          <h2 className="text-3xl font-bold tracking-tight text-zinc-900 mb-2">
            Featured Playbook Templates
          </h2>
          <p className="text-zinc-500 text-lg">
            Kickstart your next event with these proven blueprints.
          </p>
        </div>

        {/* Filter pills */}
        <div className="flex gap-2 mb-8 flex-wrap">
          {loading
            ? Array.from({ length: 5 }).map((_, i) => (
              <div
                key={i}
                className="h-8 w-20 rounded-full bg-zinc-100 animate-pulse"
                style={{ width: `${64 + ((i * 17) % 56)}px` }}
              />
            ))
            : categories.map((cat) => (
              <button
                key={cat}
                onClick={() => setFilter(cat)}
                className={`px-4 py-1.5 rounded-lg text-xs font-bold uppercase tracking-wider transition-colors border ${filter === cat
                  ? "bg-zinc-900 text-white border-zinc-900"
                  : "bg-white text-zinc-500 border-zinc-200 hover:border-zinc-400 hover:text-zinc-900"
                  }`}
              >
                {cat}
              </button>
            ))}
        </div>

        {/* Loading skeleton */}
        {loading && (
          <div
            className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6"
            aria-busy="true"
            aria-live="polite"
          >
            {Array.from({ length: 8 }).map((_, i) => (
              <div
                key={i}
                className="flex flex-col rounded-xl border border-zinc-200 bg-white overflow-hidden"
              >
                <div className="h-28 bg-zinc-100 border-b border-zinc-200 animate-pulse" />
                <div className="p-6 pb-3 flex flex-col gap-2">
                  <div className="h-3 w-20 rounded bg-zinc-100 animate-pulse" />
                  <div className="h-4 w-3/4 rounded bg-zinc-200 animate-pulse" />
                  <div className="h-3 w-full rounded bg-zinc-100 animate-pulse mt-1" />
                  <div className="h-3 w-5/6 rounded bg-zinc-100 animate-pulse" />
                </div>
                <div className="px-6 pb-4 flex-1 flex flex-col gap-2">
                  <div className="h-3 w-1/2 rounded bg-zinc-100 animate-pulse" />
                  <div className="h-3 w-1/3 rounded bg-zinc-100 animate-pulse" />
                </div>
                <div className="px-6 py-3 border-t border-zinc-200 flex items-center justify-between">
                  <div className="h-3 w-16 rounded bg-zinc-100 animate-pulse" />
                  <div className="h-6 w-12 rounded bg-zinc-100 animate-pulse" />
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Empty state */}
        {!loading && filtered.length === 0 && (
          <div className="border-2 border-dashed border-zinc-200 rounded-2xl p-16 flex flex-col items-center text-center gap-4">
            <div className="h-14 w-14 bg-zinc-100 rounded-2xl flex items-center justify-center">
              <Sparkles className="h-7 w-7 text-zinc-400" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-zinc-800">No public playbooks yet</h2>
              <p className="text-zinc-500 text-sm mt-1 max-w-xs">
                Publish a playbook with visibility set to Public and it will appear here.
              </p>
            </div>
          </div>
        )}

        {/* Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {!loading && filtered.map((playbook) => (
            <Link href={`/playbooks/${playbook.id}`} key={playbook.id}>
              <Card className="flex flex-col h-full hover:border-zinc-300 hover:shadow-md transition-all cursor-pointer group p-0 pt-0 gap-0 overflow-hidden">
                <div className="h-32 bg-zinc-100 border-b flex items-center justify-center relative overflow-hidden">
                  <Image
                    src={getPlaybookImage(playbook)}
                    alt={`${playbook.title} event preview`}
                    fill
                    sizes="(min-width: 1280px) 25vw, (min-width: 1024px) 33vw, (min-width: 768px) 50vw, 100vw"
                    className="object-cover transition-transform duration-500 group-hover:scale-105"
                  />
                  <div className="absolute inset-0 bg-zinc-950/35" />
                </div>
                <CardHeader className="pt-6 pb-3">
                  <CardTitle className="text-base leading-snug">{playbook.title}</CardTitle>
                  <CardDescription className="line-clamp-2 text-sm mt-1">
                    {playbook.description}
                  </CardDescription>
                </CardHeader>
                <CardContent className="flex-1 pb-6">
                  <div className="flex flex-col gap-1.5 text-xs text-zinc-500">
                    <div className="flex items-center gap-2">
                      <Users className="h-3.5 w-3.5" />
                      <span>{playbook.attendees} attendees</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Calendar className="h-3.5 w-3.5" />
                      <span>{playbook.duration}</span>
                    </div>
                  </div>
                </CardContent>
                <CardFooter className="pt-3 border-t flex items-center justify-between bg-white">
                  <span className="text-xs text-zinc-400">{playbook.stats}</span>
                  <Button size="sm" className="h-7 text-xs px-3 bg-black hover:bg-zinc-800 text-white border-transparent">
                    View
                  </Button>
                </CardFooter>
              </Card>
            </Link>
          ))}
        </div>
      </main>
    </div>
  );
}
