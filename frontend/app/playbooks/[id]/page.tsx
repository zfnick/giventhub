import Link from "next/link";
import Image from "next/image";
import { notFound } from "next/navigation";
import { ArrowLeft, Sparkles, Clock, Users, GitFork } from "lucide-react";
import { Button } from "@/components/ui/button";
import { PlaybookFlowClient as PlaybookFlow } from "@/components/graph/PlaybookFlowClient";
import {
  Card,
  CardContent,
  CardDescription,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { AdaptPlaybookModal } from "@/components/AdaptPlaybookModal";
import { NavBar } from "@/components/NavBar";

// Mock data
const playbooksData = {
  "google-genai-hackathon": {
    id: "google-genai-hackathon",
    title: "Google GenAI Hackathon",
    author: "Google Developers",
    description: "A comprehensive 48-hour hackathon playbook focused on generative AI. Includes registration forms, judging rubrics, and mentor matching logic.",
    attendees: "200-500",
    duration: "2 Days",
    category: "Hackathon",
    stats: "Used by 124 organizers",
    context: {
      challenge: "Build a functioning generative AI prototype using Google Gemini APIs that solves a real-world problem in education, climate, or health.",
      targetAudience: "Full-stack developers, AI researchers, and UX designers from university to mid-senior level.",
      venue: "Google Campus (or Hybrid), POC: Sarah Jane (Events Lead, sarah@example.com)",
      techStack: "Google Forms (Registration), Google Sheets (Roster & Mentor Matches), Google Docs (Rulebook), Google Meet (Virtual Mentorship)"
    },
    assets: [
      { name: "Registration Form",    type: "Google Forms",  icon: "/google-icons/google-forms.svg" },
      { name: "Participant Roster",    type: "Google Sheets", icon: "/google-icons/google-sheets.svg" },
      { name: "Judging Rubric",        type: "Google Docs",   icon: "/google-icons/google-docs.svg" },
    ],
    features: [
      "Automated Slack invites upon registration",
      "Dynamic mentor-team matching algorithm",
      "Pre-configured judging criteria for AI projects",
      "Certificate generation workflow"
    ]
  },
  "ycombinator-demo-day": {
    id: "ycombinator-demo-day",
    title: "Accelerator Demo Day",
    author: "Startup Community",
    description: "The gold-standard demo day architecture. Pitch schedule, investor grading sheets, and automated follow-up email templates.",
    attendees: "50-100",
    duration: "1 Day",
    category: "Showcase",
    stats: "Used by 89 organizers",
    context: {
      challenge: "Startups pitch their latest progress to an exclusive audience of top-tier angel investors and venture capitalists to raise seed funding.",
      targetAudience: "Pre-seed and seed stage founders, Angel Investors, and Venture Capital Partners.",
      venue: "Downtown Convention Center, POC: Mike Smith (mike@example.com)",
      techStack: "Google Forms (Startup Intake), Google Sheets (Investor CRM & Live Grading), Mailchimp (Follow-ups)"
    },
    assets: [
      { name: "Startup Intake Form", type: "Google Forms",  icon: "/google-icons/google-forms.svg" },
      { name: "Investor CRM",         type: "Google Sheets", icon: "/google-icons/google-sheets.svg" },
      { name: "Pitch Grading Sheet",  type: "Google Sheets", icon: "/google-icons/google-sheets.svg" },
    ],
    features: [
      "Automated investor outreach tracking",
      "Real-time pitch grading aggregation",
      "Post-event follow-up automation"
    ]
  },
  "tech-conference-pro": {
    id: "tech-conference-pro",
    title: "Standard Tech Conference",
    author: "DevRel Masters",
    description: "A 3-track tech conference blueprint. Speaker submission forms, sponsor tier structures, and multi-room scheduling.",
    attendees: "1000+",
    duration: "3 Days",
    category: "Conference",
    stats: "Used by 45 organizers",
    context: {
      challenge: "A multi-day, multi-track conference focusing on cutting-edge software engineering, DevOps, and cloud architecture.",
      targetAudience: "Software Engineers, CTOs, and DevOps practitioners.",
      venue: "Grand Hotel Expo, POC: Alice Wong (alice@example.com)",
      techStack: "Google Forms (CFP), Google Sheets (Master Schedule), Google Docs (Sponsor Prospectus)"
    },
    assets: [
      { name: "Speaker CFP",       type: "Google Forms",  icon: "/google-icons/google-forms.svg" },
      { name: "Master Schedule",    type: "Google Sheets", icon: "/google-icons/google-sheets.svg" },
      { name: "Sponsor Prospectus", type: "Google Docs",   icon: "/google-icons/google-docs.svg" },
    ],
    features: [
      "Speaker CFP management and voting",
      "Sponsor onboarding workflow",
      "Attendee ticketing sync"
    ]
  },
  "university-climate-sprint": {
    id: "university-climate-sprint",
    title: "University Climate Sprint",
    author: "EcoTech Labs",
    description: "A beginner-friendly design sprint focusing on climate tech. Great for high schools and universities.",
    attendees: "50-200",
    duration: "1 Day",
    category: "Sprint",
    stats: "Used by 210 organizers",
    context: {
      challenge: "Design an innovative conceptual solution or app mockup aimed at reducing carbon footprints in urban environments.",
      targetAudience: "University students, high school coders, and design enthusiasts.",
      venue: "University Main Library, POC: Prof. Davis (davis@example.edu)",
      techStack: "Google Forms (Sign-up), Google Sheets (Team Formation), Google Docs (Sprint Guide)"
    },
    assets: [
      { name: "Sign-up Form",       type: "Google Forms",  icon: "/google-icons/google-forms.svg" },
      { name: "Team Formation",      type: "Google Sheets", icon: "/google-icons/google-sheets.svg" },
      { name: "Design Sprint Guide", type: "Google Docs",   icon: "/google-icons/google-docs.svg" },
    ],
    features: [
      "Beginner-friendly step-by-step instructions",
      "Pre-filled templates for ideation",
      "Simple judging rubrics"
    ]
  },
  "stanford-demo-day-2026": {
    id: "stanford-demo-day-2026",
    title: "Stanford AI Demo Day 2026",
    author: "You",
    description: "A premier showcase of student-led AI startups from Stanford.",
    attendees: "150-300",
    duration: "1 Day",
    category: "Hackathon",
    stats: "Private Repository",
    context: {
      challenge: "A showcase event for final year students to present their applied AI projects to local founders and VCs.",
      targetAudience: "Computer Science students, alumni, and local venture capitalists.",
      venue: "Stanford CS Building, POC: You",
      techStack: "Google Forms (Registration), Google Sheets (Check-in), Google Docs (Rubrics)"
    },
    assets: [
      { name: "Demo Day Registration",  type: "Google Forms",  icon: "/google-icons/google-forms.svg" },
      { name: "Master Roster & Check-in", type: "Google Sheets", icon: "/google-icons/google-sheets.svg" },
      { name: "Judge Scoring Rubric",    type: "Google Docs",   icon: "/google-icons/google-docs.svg" },
      { name: "Opening Ceremony Deck",   type: "Google Slides", icon: "/google-icons/google-slides.svg" },
    ],
    features: [
      "Automated team registration",
      "Real-time judge scoring sheet",
      "Template presentation deck"
    ]
  }
};

export default function PlaybookPage({ params }: { params: { id: string } }) {
  // Use the mocked data or default to the first one if not found
  const playbook = playbooksData[params.id as keyof typeof playbooksData] || playbooksData["google-genai-hackathon"];

  return (
    <div className="min-h-screen bg-zinc-50/50">
      <NavBar
        left={
          <Link href="/" className="text-zinc-500 hover:text-zinc-900 transition-colors">
            <ArrowLeft className="h-5 w-5" />
          </Link>
        }
      />

      <main className="container mx-auto px-6 py-12 max-w-6xl">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-12">
          
          {/* Left Column: Details */}
          <div className="lg:col-span-1 space-y-8">
            <div>
              <div className="flex items-center gap-2 mb-4">
                <Badge variant="secondary" className="font-mono">{playbook.category.toUpperCase()}</Badge>
                <span className="text-sm text-zinc-500 flex items-center gap-1">
                  <GitFork className="h-3 w-3" />
                  {playbook.stats}
                </span>
              </div>
              <h1 className="text-4xl font-semibold tracking-tight mb-4">{playbook.title}</h1>
              <p className="text-lg text-zinc-600 dark:text-zinc-400">
                {playbook.description}
              </p>
            </div>

            <div className="flex items-center gap-4 text-sm text-zinc-600 dark:text-zinc-400">
              <div className="flex items-center gap-2">
                <Users className="h-4 w-4" />
                <span className="font-medium">{playbook.attendees}</span>
              </div>
              <div className="flex items-center gap-2">
                <Clock className="h-4 w-4" />
                <span className="font-medium">{playbook.duration}</span>
              </div>
            </div>

            {/* Context Section */}
            {playbook.context && (
              <>
                <Separator />
                <div className="space-y-5">
                  <div>
                    <h3 className="font-semibold text-zinc-900 dark:text-zinc-100 mb-1">The Challenge</h3>
                    <p className="text-sm text-zinc-600 dark:text-zinc-400 leading-relaxed">
                      {playbook.context.challenge}
                    </p>
                  </div>
                  <div>
                    <h3 className="font-semibold text-zinc-900 dark:text-zinc-100 mb-1">Target Audience</h3>
                    <p className="text-sm text-zinc-600 dark:text-zinc-400 leading-relaxed">
                      {playbook.context.targetAudience}
                    </p>
                  </div>
                  <div>
                    <h3 className="font-semibold text-zinc-900 dark:text-zinc-100 mb-1">Venue & Operations</h3>
                    <p className="text-sm text-zinc-600 dark:text-zinc-400 leading-relaxed">
                      {playbook.context.venue}
                    </p>
                  </div>
                </div>
              </>
            )}

            <Separator />

            <div>
              <h3 className="font-semibold mb-4 text-lg">Included Assets</h3>
              <div className="space-y-3">
                {playbook.assets.map((asset, i) => (
                  <div key={i} className="flex items-center gap-3 p-3 rounded-lg border bg-white shadow-sm">
                    <div className="h-8 w-8 rounded bg-zinc-50 flex items-center justify-center flex-shrink-0 p-1">
                      <Image src={asset.icon} alt={asset.type} width={24} height={24} />
                    </div>
                    <div>
                      <p className="text-sm font-medium">{asset.name}</p>
                      <p className="text-xs text-zinc-500">{asset.type}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div>
              <h3 className="font-semibold mb-4 text-lg">Key Features</h3>
              <ul className="space-y-2">
                {playbook.features.map((feature, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-zinc-600 dark:text-zinc-400">
                    <div className="mt-1.5 h-1.5 w-1.5 rounded-full bg-zinc-300 dark:bg-zinc-700 flex-shrink-0" />
                    <span className="leading-snug">{feature}</span>
                  </li>
                ))}
              </ul>
            </div>
            
          </div>

          {/* Right Column: Visualization */}
          <div className="lg:col-span-2 space-y-6">
            <div className="flex flex-col gap-2">
              <h2 className="text-2xl font-semibold tracking-tight">Event Architecture</h2>
              <p className="text-zinc-500 dark:text-zinc-400 text-sm">
                This blueprint visualizes the data flow and automation steps of the playbook.
              </p>
            </div>
            <Card className="overflow-hidden shadow-sm border-zinc-200 dark:border-zinc-800">
              <PlaybookFlow />
            </Card>

            <Card className="bg-white text-zinc-900 border border-zinc-200 shadow-xl mt-12 overflow-hidden relative">
              <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/5 via-purple-500/5 to-pink-500/5" />
              <CardContent className="relative z-10 py-6 flex flex-col sm:flex-row sm:items-center gap-6">
                <div className="flex-1">
                  <CardTitle className="flex items-center gap-2 text-xl mb-2">
                    <Sparkles className="h-5 w-5 text-indigo-500" />
                    Clone & Customize
                  </CardTitle>
                  <CardDescription className="text-zinc-500 text-base">
                    Adapt this playbook for your specific needs using AI. We'll automatically provision the Google Workspace assets for you.
                  </CardDescription>
                </div>
                <AdaptPlaybookModal playbookTitle={playbook.title}>
                  <Button className="w-full sm:w-auto bg-zinc-900 text-white hover:bg-zinc-800 font-semibold h-11 px-8 shrink-0">
                    Adapt Playbook
                  </Button>
                </AdaptPlaybookModal>
              </CardContent>
            </Card>
          </div>
          
        </div>
      </main>
    </div>
  );
}
