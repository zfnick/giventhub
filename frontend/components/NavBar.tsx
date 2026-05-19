"use client";

import { useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { signOut } from "firebase/auth";
import { auth } from "@/lib/firebase";
import { useAuth } from "@/lib/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { BookOpen, ChevronDown, LogOut, Search, MessageSquare } from "lucide-react";
import { ReactNode } from "react";

interface NavBarProps {
  left?: ReactNode;
  hideBorder?: boolean;
  isFullWidth?: boolean;
}

export function NavBar({ left, hideBorder, isFullWidth }: NavBarProps) {
  const { user, loading } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const [query, setQuery] = useState("");
  const router = useRouter();

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      router.push(`/?q=${encodeURIComponent(query.trim())}`);
    }
  };

  return (
    <nav className={`bg-white sticky top-0 z-50 ${hideBorder ? "" : "border-b"}`}>
      <div className={`${isFullWidth ? "w-full" : "container mx-auto"} px-6 h-16 flex items-center gap-4`}>
        {/* Left: logo */}
        <div className="flex items-center gap-3 shrink-0">
          {left}
          <Link href="/" className="flex items-center">
            <Image
              src="/icon.png"
              alt="gieventhub logo"
              width={56}
              height={56}
              className="object-contain"
              priority
            />
          </Link>
        </div>

        {/* Center: search */}
        <form onSubmit={handleSearch} className="flex-1 max-w-xl mx-auto">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-zinc-400" />
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search playbooks, events, organizers..."
              className="pl-9 h-9 text-sm bg-zinc-50 border-zinc-200 focus-visible:ring-zinc-300"
            />
          </div>
        </form>

        {/* Right: actions */}
        <div className="flex items-center gap-2 shrink-0">
          {loading ? (
            <div className="h-8 w-8 rounded-full bg-zinc-100 animate-pulse" />
          ) : user ? (
            <>
              <Link href="/playbooks">
                <Button variant="ghost" size="sm" className="gap-1.5 text-sm hidden sm:flex">
                  <BookOpen className="h-3.5 w-3.5" />
                  My Playbooks
                </Button>
              </Link>

              {/* Profile avatar dropdown */}
              <div className="relative">
                <button
                  onClick={() => setMenuOpen((o) => !o)}
                  className="flex items-center gap-1.5 focus:outline-none"
                >
                  {user.photoURL ? (
                    <Image
                      src={user.photoURL}
                      alt={user.displayName ?? "Profile"}
                      width={32}
                      height={32}
                      className="rounded-full ring-2 ring-zinc-200 hover:ring-zinc-400 transition-all"
                    />
                  ) : (
                    <div className="h-8 w-8 rounded-full bg-zinc-900 text-white flex items-center justify-center text-sm font-bold ring-2 ring-zinc-200">
                      {user.displayName?.[0] ?? "U"}
                    </div>
                  )}
                  <ChevronDown className="h-3.5 w-3.5 text-zinc-400" />
                </button>

                {menuOpen && (
                  <>
                    {/* backdrop */}
                    <div
                      className="fixed inset-0 z-40"
                      onClick={() => setMenuOpen(false)}
                    />
                    <div className="absolute right-0 mt-2 w-52 bg-white border border-zinc-200 rounded-xl shadow-lg py-1 z-50">
                      <div className="px-4 py-3 border-b border-zinc-100">
                        <p className="text-sm font-semibold text-zinc-800 truncate">
                          {user.displayName}
                        </p>
                        <p className="text-xs text-zinc-400 truncate">{user.email}</p>
                      </div>
                      <button
                        onClick={async () => {
                          await signOut(auth);
                          setMenuOpen(false);
                        }}
                        className="w-full flex items-center gap-2 px-4 py-2.5 text-sm text-zinc-600 hover:bg-zinc-50 hover:text-zinc-900 transition-colors"
                      >
                        <LogOut className="h-3.5 w-3.5" />
                        Sign out
                      </button>
                    </div>
                  </>
                )}
              </div>
            </>
          ) : (
            <Link href="/onboarding/login">
              <Button size="sm" className="text-sm font-medium h-9">
                Sign In
              </Button>
            </Link>
          )}
        </div>
      </div>
    </nav>
  );
}
