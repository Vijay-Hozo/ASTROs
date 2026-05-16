"use client";

import { useState } from "react";
import Link from "next/link";
import { Menu, X } from "lucide-react";

export default function Navbar() {
  const [open, setOpen] = useState(false);

  return (
    <header className="sticky top-0 z-40">
      <div className="backdrop-blur bg-white/60 border-b border-border">
        <div className="max-w-9xl mx-auto px-6">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white font-bold">IR</div>
              <span className="font-semibold text-lg text-textDarkBlue">Invoice Rule Engine</span>
            </div>

            <nav className="hidden md:flex items-center gap-6">
              <Link href="#features" className="text-sm hover:text-buttonBlue transition">Features</Link>
              <Link href="#how" className="text-sm hover:text-buttonBlue transition">How It Works</Link>
              <Link href="#use-cases" className="text-sm hover:text-buttonBlue transition">Use Cases</Link>
              <Link href="#pricing" className="text-sm hover:text-buttonBlue transition">Pricing</Link>
              <Link href="#docs" className="text-sm hover:text-buttonBlue transition">Docs</Link>
            </nav>

            <div className="hidden md:flex items-center gap-4">
              <Link href="/signup" className="px-4 py-2 rounded-md bg-buttonBlue text-buttonText  transition">Get Started</Link>
            </div>

            <div className="md:hidden">
              <button aria-label="menu" onClick={() => setOpen((s) => !s)} className="p-2">
                {open ? <X /> : <Menu />}
              </button>
            </div>
          </div>
        </div>
        {open && (
          <div className="md:hidden px-6 pb-6">
            <div className="flex flex-col gap-3">
              <Link href="#features" onClick={() => setOpen(false)} className="py-2">Features</Link>
              <Link href="#how" onClick={() => setOpen(false)} className="py-2">How It Works</Link>
              <Link href="#use-cases" onClick={() => setOpen(false)} className="py-2">Use Cases</Link>
              <Link href="#pricing" onClick={() => setOpen(false)} className="py-2">Pricing</Link>
              <Link href="#docs" onClick={() => setOpen(false)} className="py-2">Docs</Link>
              <Link href="/signup" onClick={() => setOpen(false)} className="mt-2 py-2 rounded-md bg-buttonBlue text-buttonText text-center">Get Started</Link>
            </div>
          </div>
        )}
      </div>
    </header>
  );
}
