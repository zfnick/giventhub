"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Sparkles, Lock, FileText, Database, Shield, Loader2 } from "lucide-react";
import { auth, googleProvider } from "@/lib/firebase";
import { signInWithPopup } from "firebase/auth";

export default function LoginPage() {
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();

  const handleGoogleSignIn = async () => {
    setIsLoading(true);
    try {
      const result = await signInWithPopup(auth, googleProvider);
      // Success, you can access result.user here if needed
      console.log("Logged in as:", result.user.email);
      router.push("/onboarding/scan");
    } catch (error) {
      console.error("Error signing in with Google:", error);
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-zinc-50 text-zinc-900 flex items-center justify-center relative overflow-hidden transition-colors duration-300">
      {/* Background gradients */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-indigo-500/10 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-purple-500/10 rounded-full blur-[100px] pointer-events-none mix-blend-multiply" />

      <div className="relative z-10 w-full max-w-md p-8 bg-white/70 backdrop-blur-xl rounded-3xl border border-zinc-200 shadow-xl">
        <div className="flex justify-center mb-8">
          <div className="h-16 w-16 bg-zinc-900 rounded-2xl flex items-center justify-center shadow-lg transform -rotate-6">
            <span className="text-3xl font-bold text-white tracking-tighter">g.</span>
          </div>
        </div>

        <div className="text-center space-y-3 mb-8">
          <h1 className="text-3xl font-bold tracking-tight">Welcome to gieventhub</h1>
          <p className="text-zinc-600 text-sm leading-relaxed">
            Connect your Google Workspace. Our AI will securely analyze your past files to help you build and open-source your event playbooks.
          </p>
        </div>

        <div className="space-y-4 mb-8">
          <div className="flex items-center gap-3 p-4 rounded-xl bg-zinc-100/80 border border-zinc-200">
            <div className="p-2 bg-blue-100 text-blue-600 rounded-lg">
              <FileText className="h-5 w-5" />
            </div>
            <div className="text-sm">
              <p className="font-medium text-zinc-900">Read access to Docs & Sheets</p>
              <p className="text-zinc-500 text-xs">To analyze event rubrics and schedules.</p>
            </div>
          </div>
          
          <div className="flex items-center gap-3 p-4 rounded-xl bg-zinc-100/80 border border-zinc-200">
            <div className="p-2 bg-purple-100 text-purple-600 rounded-lg">
              <Database className="h-5 w-5" />
            </div>
            <div className="text-sm">
              <p className="font-medium text-zinc-900">Read access to Drive</p>
              <p className="text-zinc-500 text-xs">To map relationships between your event assets.</p>
            </div>
          </div>
        </div>

        <div className="flex flex-col gap-4">
          <Button 
            onClick={handleGoogleSignIn} 
            disabled={isLoading}
            className="w-full h-12 bg-white hover:bg-zinc-50 text-zinc-900 border border-zinc-200 shadow-sm font-semibold text-base gap-2 rounded-xl transition-all disabled:opacity-50"
          >
            {isLoading ? (
              <Loader2 className="h-5 w-5 animate-spin" />
            ) : (
              <svg className="h-5 w-5" viewBox="0 0 24 24">
                <path
                  d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                  fill="#4285F4"
                />
                <path
                  d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                  fill="#34A853"
                />
                <path
                  d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                  fill="#FBBC05"
                />
                <path
                  d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                  fill="#EA4335"
                />
              </svg>
            )}
            {isLoading ? "Connecting..." : "Continue with Google"}
          </Button>
          
          <div className="flex items-center justify-center gap-2 text-xs text-zinc-500">
            <Shield className="h-3 w-3" />
            <span>Your data remains private. AI is used securely.</span>
          </div>
        </div>
      </div>
    </div>
  );
}


