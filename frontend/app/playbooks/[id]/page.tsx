"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import Image from "next/image";
import { ArrowLeft, Sparkles, Clock, Users, GitFork, Lock, Globe } from "lucide-react";
import { Button } from "@/components/ui/button";
import { PlaybookFlowClient as PlaybookFlow, type PlaybookGraphData } from "@/components/graph/PlaybookFlowClient";
import {
  Card,
  CardContent,
  CardDescription,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { AdaptPlaybookModal } from "@/components/AdaptPlaybookModal";
import { NavBar } from "@/components/NavBar";
import { apiFetch } from "@/lib/api";
import { buildPlaybookGraph } from "@/lib/playbookGraph";

interface PlaybookContext {
  challenge: string;
  targetAudience: string;
  venue: string;
  techStack: string;
}

interface PlaybookAsset {
  name: string;
  type: string;
  icon?: string | null;
}

interface PlaybookParticipant {
  name: string;
  role: string;
  organization: string;
  email: string;
}

interface Playbook {
  id: string;
  title: string;
  author: string;
  description: string;
  attendees: string;
  duration: string;
  category: string;
  stats: string;
  visibility: "public" | "private";
  tags: string[];
  context: PlaybookContext;
  assets: PlaybookAsset[];
  participants: PlaybookParticipant[];
  features: string[];
}

export default function PlaybookPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [playbook, setPlaybook] = useState<Playbook | null>(null);
  const [status, setStatus] = useState<"loading" | "ok" | "missing" | "error">("loading");
  const graph: PlaybookGraphData | null = useMemo(
    () => (playbook ? buildPlaybookGraph(playbook) : null),
    [playbook],
  );

  useEffect(() => {
    if (!params?.id) return;
    let cancelled = false;
    (async () => {
      try {
        const res = await apiFetch(null, `/api/playbooks/${params.id}`);
        if (cancelled) return;
        if (res.status === 404) {
          setStatus("missing");
          return;
        }
        if (!res.ok) {
          setStatus("error");
          return;
        }
        setPlaybook(await res.json());
        setStatus("ok");
      } catch (err) {
        if (!cancelled) {
          console.error("Failed to load playbook:", err);
          setStatus("error");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [params?.id]);

  if (status === "loading") {
    return (
      <div className="min-h-screen bg-white">
        <NavBar />
        <main className="container mx-auto px-6 py-12 max-w-6xl space-y-12">
          <div className="space-y-4">
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-12 w-3/4" />
            <Skeleton className="h-6 w-1/2" />
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-16">
            <div className="lg:col-span-1 space-y-10">
              <Skeleton className="h-[400px] rounded-3xl" />
              <Skeleton className="h-[200px] rounded-3xl" />
            </div>
            <div className="lg:col-span-2 space-y-10">
              <Skeleton className="h-[600px] rounded-3xl" />
            </div>
          </div>
        </main>
      </div>
    );
  }

  if (status === "missing" || !playbook) {
    return (
      <div className="min-h-screen bg-zinc-50/50">
        <NavBar />
        <main className="container mx-auto px-6 py-20 max-w-2xl text-center space-y-4">
          <h1 className="text-3xl font-bold">Playbook not found</h1>
          <p className="text-zinc-500">
            {status === "error"
              ? "We couldn't reach the backend. Is the FastAPI server running on :8000?"
              : "This playbook doesn't exist or was removed."}
          </p>
          <Button onClick={() => router.push("/")} variant="outline">
            <ArrowLeft className="h-4 w-4 mr-1.5" />
            Back to gallery
          </Button>
        </main>
      </div>
    );
  }

  const ctx = playbook.context;
  const hasContext =
    ctx && (ctx.challenge || ctx.targetAudience || ctx.venue || ctx.techStack);

  return (
    <div className="min-h-screen bg-zinc-50/50">
      <NavBar />

      <main className="container mx-auto px-6 py-12 max-w-6xl">
        <Link
          href="/"
          className="inline-flex items-center gap-1.5 text-sm text-zinc-500 hover:text-zinc-900 transition-colors mb-8"
        >
          <ArrowLeft className="h-4 w-4" />
          Back
        </Link>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-16">
          {/* Left Column: Details */}
          <div className="lg:col-span-1 space-y-10">
            <div>
              <div className="flex items-center gap-4 text-xs font-semibold text-zinc-500 mb-2 uppercase tracking-wider">
                <div className="flex items-center gap-1.5 px-0 py-0.5">
                  {playbook.visibility === "private" ? (
                    <Lock className="h-3 w-3" />
                  ) : (
                    <Globe className="h-3 w-3" />
                  )}
                  {playbook.visibility}
                </div>
                {playbook.stats && (
                  <span className="flex items-center gap-1">
                    <GitFork className="h-3 w-3" />
                    {playbook.stats}
                  </span>
                )}
              </div>
              <h1 className="text-4xl font-semibold tracking-tight mb-4">
                {playbook.title}
              </h1>
              {playbook.description && (
                <p className="text-lg text-zinc-600 dark:text-zinc-400">
                  {playbook.description}
                </p>
              )}
              {playbook.author && (
                <p className="text-sm text-zinc-500 mt-3">By {playbook.author}</p>
              )}
            </div>

            {(playbook.attendees || playbook.duration) && (
              <div className="flex items-center gap-4 text-sm text-zinc-600 dark:text-zinc-400">
                <div className="flex items-center gap-2">
                  <Users className="h-4 w-4" />
                  <span>{playbook.attendees}</span>
                </div>
                <div className="flex items-center gap-2">
                  <Clock className="h-4 w-4" />
                  <span>{playbook.duration}</span>
                </div>
              </div>
            )}

            {hasContext && (
              <>
                <Separator />
                <div className="space-y-5">
                  {ctx.challenge && (
                    <div>
                      <h3 className="font-semibold text-zinc-900 dark:text-zinc-100 mb-1">
                        The Challenge
                      </h3>
                      <p className="text-sm text-zinc-600 dark:text-zinc-400 leading-relaxed">
                        {ctx.challenge}
                      </p>
                    </div>
                  )}
                  {ctx.targetAudience && (
                    <div>
                      <h3 className="font-semibold text-zinc-900 dark:text-zinc-100 mb-1">
                        Target Audience
                      </h3>
                      <p className="text-sm text-zinc-600 dark:text-zinc-400 leading-relaxed">
                        {ctx.targetAudience}
                      </p>
                    </div>
                  )}
                  {ctx.venue && (
                    <div>
                      <h3 className="font-semibold text-zinc-900 dark:text-zinc-100 mb-1">
                        Venue & Operations
                      </h3>
                      <p className="text-sm text-zinc-600 dark:text-zinc-400 leading-relaxed">
                        {ctx.venue}
                      </p>
                    </div>
                  )}
                </div>
              </>
            )}

            {playbook.assets.length > 0 && (
              <>
                <Separator />
                <div>
                  <h3 className="font-semibold mb-4 text-lg">Included Assets</h3>
                  <div className="space-y-3">
                    {playbook.assets.map((asset, i) => (
                      <div
                        key={i}
                        className="flex items-center gap-3 p-3 rounded-lg border bg-white shadow-sm"
                      >
                        {asset.icon && (
                          <div className="h-8 w-8 rounded bg-zinc-50 flex items-center justify-center flex-shrink-0 p-1">
                            <Image
                              src={asset.icon}
                              alt={asset.type}
                              width={24}
                              height={24}
                            />
                          </div>
                        )}
                        <div>
                          <p className="text-sm font-medium">{asset.name}</p>
                          <p className="text-xs text-zinc-500">{asset.type}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </>
            )}

            {playbook.features.length > 0 && (
              <div>
                <h3 className="font-semibold mb-4 text-lg">Key Features</h3>
                <ul className="space-y-2">
                  {playbook.features.map((feature, i) => (
                    <li
                      key={i}
                      className="flex items-start gap-2 text-sm text-zinc-600 dark:text-zinc-400"
                    >
                      <div className="mt-1.5 h-1.5 w-1.5 rounded-full bg-zinc-300 dark:bg-zinc-700 flex-shrink-0" />
                      <span className="leading-snug">{feature}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}


          </div>

          {/* Right Column: Visualization */}
          <div className="lg:col-span-2 space-y-6">
            <div className="flex flex-col gap-2">
              <h2 className="text-2xl font-semibold tracking-tight">Event Architecture</h2>
              <p className="text-zinc-500 dark:text-zinc-400 text-sm">
                This blueprint visualizes the data flow and automation steps of the playbook.
              </p>
            </div>
            <div className="h-[700px] w-full overflow-hidden bg-transparent">
              <PlaybookFlow graph={graph} loading={false} />
            </div>

            <Card className="bg-white text-zinc-900 border border-zinc-200 shadow-xl mt-12 overflow-hidden relative">
              <div className="absolute inset-0 bg-gradient-to-br from-zinc-100/50 via-zinc-50/30 to-white" />
              <CardContent className="relative z-10 py-6 flex flex-col sm:flex-row sm:items-center gap-6">
                <div className="flex-1">
                  <CardTitle className="flex items-center gap-2 text-xl mb-2">
                    <Sparkles className="h-5 w-5 text-zinc-900" />
                    Clone & Customize
                  </CardTitle>
                  <CardDescription className="text-zinc-500 text-base">
                    Adapt this playbook for your specific needs using AI. We&apos;ll
                    automatically provision the Google Workspace assets for you.
                  </CardDescription>
                </div>
                <AdaptPlaybookModal playbookTitle={playbook.title} />
              </CardContent>
            </Card>
          </div>
        </div>
      </main>
    </div>
  );
}
