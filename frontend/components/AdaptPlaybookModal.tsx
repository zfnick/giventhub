"use client";

import { useState } from "react";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Sparkles, Loader2, ArrowRight } from "lucide-react";

export function AdaptPlaybookModal({ playbookTitle = "Google AI Hackathon" }: { playbookTitle?: string }) {
  const [prompt, setPrompt] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleAdapt = async () => {
    setError(null);
    if (!prompt.trim()) {
      setError("Please provide some context for your event.");
      return;
    }
    
    setIsGenerating(true);
    
    try {
      // Call backend API
      const response = await fetch('http://localhost:8000/api/adapt', { 
        method: 'POST', 
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ prompt, playbookTitle }) 
      });
      
      if (!response.ok) {
        throw new Error("Failed to generate playbook. Please try again.");
      }
      
      const data = await response.json();
      
      setIsOpen(false);
      // In a real app we would navigate to a new workspace link
      alert(`Playbook generated! Workspace: ${data.workspaceUrl}`);
    } catch (err: any) {
      setError(err.message || "An unexpected error occurred. Please try again.");
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger render={<Button className="gap-2" />}>
        <Sparkles className="h-4 w-4" />
        Adapt Playbook
      </DialogTrigger>
      <DialogContent className="sm:max-w-[520px] p-6">
        <DialogHeader className="mb-2">
          <DialogTitle className="text-2xl font-bold flex items-center gap-2">
            <Sparkles className="h-6 w-6 text-zinc-900 dark:text-zinc-100" /> Adapt Playbook
          </DialogTitle>
          <DialogDescription className="text-zinc-600 dark:text-zinc-400 mt-2 leading-relaxed">
            You are adapting <span className="font-semibold text-zinc-900 dark:text-zinc-100">{playbookTitle}</span>. 
            Tell our AI what kind of event you're planning, and we'll generate a tailored playbook and setup your Google Workspace.
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-5 py-4">
          <div className="space-y-3">
            <Label htmlFor="prompt" className="text-sm font-semibold">Your Event Context</Label>
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
              <strong>AI Action:</strong> We will fork this playbook, customize the registration form, generate a tailored judging rubric, and create a shared Google Drive folder for your team.
            </p>
          </div>
          {error && (
            <div className="text-sm font-medium text-red-500 dark:text-red-400">
              {error}
            </div>
          )}
        </div>
        <DialogFooter className="mt-4 gap-2 sm:gap-0">
          <Button variant="outline" onClick={() => setIsOpen(false)} disabled={isGenerating} className="sm:mr-auto">
            Cancel
          </Button>
          <Button 
            onClick={handleAdapt} 
            disabled={isGenerating || !prompt.trim()}
            className="bg-black hover:bg-zinc-800 dark:bg-white dark:hover:bg-zinc-200 dark:text-black text-white gap-2 font-semibold shadow-md transition-all"
          >
            {isGenerating ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" /> Generating...
              </>
            ) : (
              <>
                Create Workspace <ArrowRight className="h-4 w-4" />
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
