"use client";

import { useEffect } from "react";
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

// Mock: in production this would be fetched from Firestore by user ID
const myPlaybooks = [
  {
    id: "stanford-demo-day-2026",
    title: "Stanford AI Demo Day 2026",
    description: "A premier showcase of student-led AI startups from Stanford.",
    attendees: "150-300",
    duration: "1 Day",
    category: "Hackathon",
    visibility: "private",
    updatedAt: "2 days ago",
  },
];

export default function MyPlaybooksPage() {
  const { user, loading } = useAuth();
  const router = useRouter();

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!loading && !user) {
      router.replace("/onboarding/login");
    }
  }, [user, loading, router]);

  if (loading || !user) {
    return (
      <div className="min-h-screen bg-zinc-50">
        <NavBar />
        <div className="container mx-auto px-6 py-20 flex items-center justify-center">
          <div className="h-8 w-8 rounded-full border-2 border-zinc-300 border-t-zinc-900 animate-spin" />
        </div>
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
                <Card className="flex flex-col h-full hover:border-zinc-300 hover:shadow-md transition-all cursor-pointer group">
                  <div className="h-24 bg-zinc-900 rounded-t-lg border-b flex items-center justify-center relative overflow-hidden">
                    <div className="absolute inset-0 bg-gradient-to-br from-zinc-700 to-zinc-900 group-hover:scale-105 transition-transform duration-500" />
                    <span className="text-zinc-400 font-mono text-xs z-10 tracking-widest">
                      {playbook.category.toUpperCase()}
                    </span>
                  </div>
                  <CardHeader className="pb-3">
                    <div className="flex items-center gap-2 mb-1">
                      {playbook.visibility === "private" ? (
                        <Badge variant="outline" className="text-xs gap-1 py-0">
                          <Lock className="h-2.5 w-2.5" /> Private
                        </Badge>
                      ) : (
                        <Badge variant="outline" className="text-xs gap-1 py-0">
                          <Globe className="h-2.5 w-2.5" /> Public
                        </Badge>
                      )}
                      <span className="text-xs text-zinc-400">Updated {playbook.updatedAt}</span>
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
                  <CardFooter className="pt-3 border-t flex justify-end">
                    <Button size="sm" variant="outline" className="h-7 text-xs px-3">
                      Open
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
