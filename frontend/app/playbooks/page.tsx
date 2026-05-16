"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Sparkles, Users, Calendar, Plus, Lock, Globe } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { NavBar } from "@/components/NavBar";
import { EventTypeModal } from "@/components/EventTypeModal";
import { useAuth } from "@/lib/AuthContext";
import { apiFetch } from "@/lib/api";
import { Skeleton } from "@/components/ui/skeleton";

interface MyPlaybook {
  id: string;
  title: string;
  description: string;
  attendees: string;
  duration: string;
  category: string;
  visibility: "public" | "private";
}

function relativeTime(iso?: string | null): string {
  if (!iso) return "Just now";
  const then = new Date(iso).getTime();
  if (!Number.isFinite(then)) return "Just now";
  const diffSec = Math.max(0, Math.floor((Date.now() - then) / 1000));
  if (diffSec < 60) return "Just now";
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`;
  if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}h ago`;
  return `${Math.floor(diffSec / 86400)}d ago`;
}

export default function MyPlaybooksPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [myPlaybooks, setMyPlaybooks] = useState<(MyPlaybook & { updatedAt: string })[]>([]);
  const [fetching, setFetching] = useState(true);

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!loading && !user) {
      router.replace("/onboarding/login");
    }
  }, [user, loading, router]);

  useEffect(() => {
    if (!user) return;
    let cancelled = false;
    (async () => {
      setFetching(true);
      try {
        const res = await apiFetch(user, "/api/playbooks/me");
        if (cancelled) return;
        if (!res.ok) {
          console.error("Failed to load my playbooks:", res.status);
          setMyPlaybooks([]);
          return;
        }
        const data = await res.json();
        const list: (MyPlaybook & { updatedAt: string })[] = (data.playbooks ?? []).map(
          (p: MyPlaybook & { updated_at?: string | null }) => ({
            id: p.id,
            title: p.title,
            description: p.description,
            attendees: p.attendees,
            duration: p.duration,
            category: p.category,
            visibility: p.visibility,
            updatedAt: relativeTime(p.updated_at),
          }),
        );
        setMyPlaybooks(list);
      } catch (err) {
        console.error("Error loading my playbooks:", err);
        setMyPlaybooks([]);
      } finally {
        if (!cancelled) setFetching(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [user]);

  if (loading || !user || fetching) {
    return (
      <div className="min-h-screen bg-zinc-50">
        <NavBar />
        <main className="container mx-auto px-6 py-12 max-w-5xl">
          <div className="flex items-end justify-between mb-10 gap-4">
            <div>
              <Skeleton className="h-9 w-48 mb-2" />
              <Skeleton className="h-4 w-72" />
            </div>
            <Skeleton className="h-10 w-40 rounded-lg" />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[1, 2, 3].map((i) => (
              <Card key={i} className="flex flex-col h-full overflow-hidden border-zinc-200">
                <Skeleton className="h-24 rounded-none" />
                <CardHeader className="pb-3">
                  <div className="flex items-center gap-2 mb-2">
                    <Skeleton className="h-4 w-16" />
                    <Skeleton className="h-4 w-24" />
                  </div>
                  <Skeleton className="h-6 w-3/4 mb-2" />
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-4 w-2/3 mt-1" />
                </CardHeader>
                <CardContent className="flex-1">
                  <div className="space-y-2">
                    <Skeleton className="h-4 w-32" />
                    <Skeleton className="h-4 w-24" />
                  </div>
                </CardContent>
                <CardFooter className="pt-3 border-t flex justify-end bg-white/50">
                  <Skeleton className="h-7 w-16 rounded-md" />
                </CardFooter>
              </Card>
            ))}
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-zinc-50">
      <NavBar />

      <main className="container mx-auto px-6 py-12 max-w-5xl">
        {/* Header */}
        <div className="flex items-end justify-between mb-10 gap-4">
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-zinc-900">My Playbooks</h1>
            <p className="text-zinc-500 mt-1 text-sm">
              Event architectures you&apos;ve created or imported via AI.
            </p>
          </div>
          <EventTypeModal>
            <Button className="gap-2 bg-zinc-900 hover:bg-zinc-700 text-white h-10 px-5 text-sm">
              <Plus className="h-4 w-4" />
              Import New Event
            </Button>
          </EventTypeModal>
        </div>

        {myPlaybooks.length === 0 ? (
          /* Empty state */
          <div className="border-2 border-dashed border-zinc-200 rounded-2xl p-16 flex flex-col items-center text-center gap-4">
            <div className="h-14 w-14 bg-zinc-100 rounded-2xl flex items-center justify-center">
              <Sparkles className="h-7 w-7 text-zinc-400" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-zinc-800">No playbooks yet</h2>
              <p className="text-zinc-500 text-sm mt-1 max-w-xs">
                Import a past event from your Google Workspace and we&apos;ll generate a reusable playbook for you.
              </p>
            </div>
            <EventTypeModal>
              <Button className="gap-2 bg-zinc-900 hover:bg-zinc-700 text-white">
                <Plus className="h-4 w-4" />
                Import your first event
              </Button>
            </EventTypeModal>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {myPlaybooks.map((playbook) => (
              <Link href={`/playbooks/${playbook.id}`} key={playbook.id}>
                <Card className="flex flex-col h-full hover:border-zinc-300 hover:shadow-md transition-all cursor-pointer group p-0 overflow-hidden">
                  <div className="h-24 bg-zinc-900 border-b flex items-center justify-center relative overflow-hidden">
                    <div className="absolute inset-0 bg-gradient-to-br from-zinc-700 to-zinc-900 group-hover:scale-105 transition-transform duration-500" />
                  </div>
                  <CardHeader className="pb-3">
                    <div className="flex items-center gap-3 mb-1 text-[10px] font-bold uppercase tracking-widest text-zinc-500">
                      {playbook.visibility === "private" ? (
                        <div className="flex items-center gap-1">
                          <Lock className="h-3 w-3" /> Private
                        </div>
                      ) : (
                        <div className="flex items-center gap-1">
                          <Globe className="h-3 w-3" /> Public
                        </div>
                      )}
                      <span>Updated {playbook.updatedAt}</span>
                    </div>
                    <CardTitle className="text-base leading-snug">{playbook.title}</CardTitle>
                    <CardDescription className="line-clamp-2 text-sm mt-1">
                      {playbook.description}
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="flex-1">
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
                  <CardFooter className="pt-3 border-t flex justify-end bg-white">
                    <Button size="sm" className="h-7 text-xs px-3 bg-black hover:bg-zinc-800 text-white border-transparent">
                      View
                    </Button>
                  </CardFooter>
                </Card>
              </Link>
            ))}

            {/* Add new card */}
            <EventTypeModal>
              <button className="border-2 border-dashed border-zinc-200 rounded-xl h-full min-h-[240px] w-full flex flex-col items-center justify-center gap-3 text-zinc-400 hover:border-zinc-400 hover:text-zinc-600 transition-colors cursor-pointer">
                <div className="h-10 w-10 rounded-xl border-2 border-dashed border-current flex items-center justify-center">
                  <Plus className="h-5 w-5" />
                </div>
                <span className="text-sm font-medium">Import New Event</span>
              </button>
            </EventTypeModal>
          </div>
        )}
      </main>
    </div>
  );
}
