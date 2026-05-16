"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { Sparkles, Users, Calendar, MessageSquare } from "lucide-react";
import { Button } from "@/components/ui/button";
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
import PlasmaWave from "@/components/PlasmaWave";


// ── Data ─────────────────────────────────────────────────────────────────────
const playbooks = [
  {
    id: "google-genai-hackathon",
    title: "Google GenAI Hackathon",
    author: "Google Developers",
    description:
      "A comprehensive 48-hour hackathon playbook focused on generative AI. Includes registration forms, judging rubrics, and mentor matching logic.",
    attendees: "200-500",
    duration: "2 Days",
    category: "Hackathon",
    stats: "Used by 124 organizers",
  },
  {
    id: "ycombinator-demo-day",
    title: "Accelerator Demo Day",
    author: "Startup Community",
    description:
      "The gold-standard demo day architecture. Pitch schedule, investor grading sheets, and automated follow-up email templates.",
    attendees: "50-100",
    duration: "1 Day",
    category: "Showcase",
    stats: "Used by 89 organizers",
  },
  {
    id: "tech-conference-pro",
    title: "Standard Tech Conference",
    author: "DevRel Masters",
    description:
      "A 3-track tech conference blueprint. Speaker submission forms, sponsor tier structures, and multi-room scheduling.",
    attendees: "1000+",
    duration: "3 Days",
    category: "Conference",
    stats: "Used by 45 organizers",
  },
  {
    id: "university-climate-sprint",
    title: "University Climate Sprint",
    author: "EcoTech Labs",
    description:
      "A beginner-friendly design sprint focusing on climate tech. Great for high schools and universities.",
    attendees: "50-200",
    duration: "1 Day",
    category: "Sprint",
    stats: "Used by 210 organizers",
  },
];

// ── Page ─────────────────────────────────────────────────────────────────────
export default function ExplorePage() {
  const { user } = useAuth();
  const [filter, setFilter] = useState("All");

  const categories = ["All", "Hackathon", "Showcase", "Conference", "Sprint"];
  const filtered =
    filter === "All" ? playbooks : playbooks.filter((p) => p.category === filter);

  return (
    <div className="min-h-screen">
      <NavBar />

      {/* ── Hero ─────────────────────────────────────────────────────────── */}
      <section className="relative overflow-hidden bg-white border-b border-zinc-200 flex items-center justify-center min-h-[500px] py-32">
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
            scratch—fork proven playbooks from the ecosystem.
          </p>

          <div className="flex flex-col sm:flex-row items-center gap-4">
            <Link href={user ? "/onboarding/import" : "/onboarding/login"}>
              <Button className="gap-2 h-11 px-7 bg-black hover:bg-zinc-800 text-white text-sm font-semibold shadow-lg">
                <Sparkles className="h-4 w-4" />
                Import Past Event via AI
              </Button>
            </Link>
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
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setFilter(cat)}
              className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors border ${filter === cat
                ? "bg-zinc-900 text-white border-zinc-900"
                : "bg-white text-zinc-600 border-zinc-200 hover:border-zinc-400"
                }`}
            >
              {cat}
            </button>
          ))}
        </div>

        {/* Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {filtered.map((playbook) => (
            <Link href={`/playbooks/${playbook.id}`} key={playbook.id}>
              <Card className="flex flex-col h-full hover:border-zinc-300 hover:shadow-md transition-all cursor-pointer group">
                <div className="h-28 bg-zinc-100 rounded-t-lg border-b flex items-center justify-center relative overflow-hidden">
                  <div className="absolute inset-0 bg-gradient-to-br from-zinc-200/60 to-zinc-100 group-hover:scale-105 transition-transform duration-500" />
                  <span className="text-zinc-400 font-mono text-xs z-10 tracking-widest">
                    {playbook.category.toUpperCase()}
                  </span>
                </div>
                <CardHeader className="pb-3">
                  <div className="text-xs font-medium text-zinc-500 mb-1">
                    {playbook.author}
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
                <CardFooter className="pt-3 border-t flex items-center justify-between">
                  <span className="text-xs text-zinc-400">{playbook.stats}</span>
                  <Button size="sm" variant="outline" className="h-7 text-xs px-3">
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
