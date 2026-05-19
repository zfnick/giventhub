"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";
import { Button } from "@/components/ui/button";
import { Sparkles, Lock, Shield, Loader2 } from "lucide-react";

function GoogleDocsIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 47 65" xmlns="http://www.w3.org/2000/svg">
      <path
        d="M29.375 0H4.40625C1.98281 0 0 1.98281 0 4.40625V60.5938C0 63.0172 1.98281 65 4.40625 65H42.5938C45.0172 65 47 63.0172 47 60.5938V17.625L36.7188 10.2812L29.375 0Z"
        fill="#4285F4"
      />
      <path d="M29.375 0V13.2188C29.375 15.6437 31.3578 17.625 33.7812 17.625H47L29.375 0Z" fill="#A1C2FA" />
      <path
        d="M11.75 33.7812H35.25V36.7188H11.75V33.7812ZM11.75 39.6562H35.25V42.5938H11.75V39.6562ZM11.75 45.5312H35.25V48.4688H11.75V45.5312ZM11.75 51.4062H27.9375V54.3438H11.75V51.4062Z"
        fill="white"
      />
    </svg>
  );
}

function GoogleDriveIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 87.3 78" xmlns="http://www.w3.org/2000/svg">
      <path
        d="M6.6 66.85l3.85 6.65c.8 1.4 1.95 2.5 3.3 3.3L27.5 53H0c0 1.55.4 3.1 1.2 4.5l5.4 9.35z"
        fill="#0066da"
      />
      <path
        d="M43.65 25L29.9 1.2c-1.35.8-2.5 1.9-3.3 3.3L1.2 48.5c-.8 1.4-1.2 2.95-1.2 4.5h27.5l16.15-28z"
        fill="#00ac47"
      />
      <path
        d="M73.55 76.8c1.35-.8 2.5-1.9 3.3-3.3l1.6-2.75 7.65-13.25c.8-1.4 1.2-2.95 1.2-4.5h-27.5l5.85 11.5 7.9 12.3z"
        fill="#ea4335"
      />
      <path
        d="M43.65 25L57.4 1.2C56.05.4 54.5 0 52.9 0H34.4c-1.6 0-3.15.45-4.5 1.2L43.65 25z"
        fill="#00832d"
      />
      <path
        d="M59.8 53H27.5L13.75 76.8c1.35.8 2.9 1.2 4.5 1.2h50.8c1.6 0 3.15-.45 4.5-1.2L59.8 53z"
        fill="#2684fc"
      />
      <path
        d="M73.4 26.5L60.75 4.5c-.8-1.4-1.95-2.5-3.3-3.3L43.65 25l16.15 28h27.45c0-1.55-.4-3.1-1.2-4.5L73.4 26.5z"
        fill="#ffba00"
      />
    </svg>
  );
}
import { auth, googleProvider } from "@/lib/firebase";
import { signInWithPopup, GoogleAuthProvider } from "firebase/auth";
import { useAuth } from "@/lib/AuthContext";

export default function LoginPage() {
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();
  const { setGoogleAccessToken } = useAuth();

  const handleGoogleSignIn = async () => {
    setIsLoading(true);
    try {
      const result = await signInWithPopup(auth, googleProvider);
      // Capture the Workspace OAuth access token — it's only exposed on the
      // sign-in result, never on the persisted Firebase User. The ai-service
      // needs it to read Drive / write Docs / send Gmail on the user's behalf.
      const credential = GoogleAuthProvider.credentialFromResult(result);
      setGoogleAccessToken(credential?.accessToken ?? null);
      console.log("Logged in as:", result.user.email);
      router.push("/");
    } catch (error) {
      console.error("Error signing in with Google:", error);
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-zinc-50 text-zinc-900 flex items-center justify-center relative overflow-hidden transition-colors duration-300">
      {/* Background gradients */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-zinc-200/20 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-zinc-300/20 rounded-full blur-[100px] pointer-events-none mix-blend-multiply" />

      <div className="relative z-10 w-full max-w-md p-8 bg-white/70 backdrop-blur-xl rounded-3xl border border-zinc-200 shadow-xl">
        <div className="flex justify-center mb-8">
          <div className="relative h-8 w-8 transform -rotate-6">
            <Image
              src="/icon.png"
              alt="gieventhub logo"
              fill
              className="object-contain"
              priority
            />
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
            <div className="p-2 bg-white rounded-lg flex items-center justify-center">
              <GoogleDocsIcon className="h-5 w-5" />
            </div>
            <div className="text-sm">
              <p className="font-medium text-zinc-900">Read access to Docs & Sheets</p>
              <p className="text-zinc-500 text-xs">To analyze event rubrics and schedules.</p>
            </div>
          </div>

          <div className="flex items-center gap-3 p-4 rounded-xl bg-zinc-100/80 border border-zinc-200">
            <div className="p-2 bg-white rounded-lg flex items-center justify-center">
              <GoogleDriveIcon className="h-5 w-5" />
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
            className="w-full h-12 bg-black hover:bg-zinc-800 text-white shadow-lg shadow-zinc-200 font-semibold text-base gap-3 rounded-xl transition-all disabled:opacity-50"
          >
            {isLoading ? (
              <Loader2 className="h-5 w-5 animate-spin" />
            ) : (
              <div className="bg-white p-1 rounded-lg">
                <svg className="h-4 w-4" viewBox="0 0 24 24">
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
              </div>
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


