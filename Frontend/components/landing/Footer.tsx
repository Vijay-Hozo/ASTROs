"use client"
import Link from "next/link";
import { Github, Twitter, Linkedin } from "lucide-react";

export default function Footer() {
  return (
    <footer className="mt-12 border-t border-border bg-secondaryBackground">
      <div className="max-w-6xl mx-auto px-6 py-8 flex flex-col md:flex-row items-center justify-between gap-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white font-bold">IR</div>
          <div>
            <div className="font-semibold text-textDarkBlue">Invoice Rule Engine</div>
            {/* <div className="text-sm text-textDarkBlue/70">© {new Date().getFullYear()} Invoice Rule Engine</div> */}
          </div>
        </div>

        <nav className="flex items-center gap-4">
          <Link href="#features" className="text-sm">Features</Link>
          <Link href="#how" className="text-sm">How It Works</Link>
          <Link href="#pricing" className="text-sm">Pricing</Link>
        </nav>

        <div className="flex items-center gap-3">
          <a href="#" aria-label="github" className="p-2 rounded-md hover:bg-white/5"><Github /></a>
          <a href="#" aria-label="twitter" className="p-2 rounded-md hover:bg-white/5"><Twitter /></a>
          <a href="#" aria-label="linkedin" className="p-2 rounded-md hover:bg-white/5"><Linkedin /></a>
        </div>
      </div>
    </footer>
  );
}
