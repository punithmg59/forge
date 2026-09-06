"use client";

import Link from "next/link";
import { useState } from "react";

export function Navbar() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <>
      <nav className="nav-bar sticky top-0 z-50 flex items-center justify-between px-6 py-4 md:px-12">
        <Link href="/" className="flex items-center gap-2">
          <svg
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            className="text-amber-400"
            aria-hidden="true"
          >
            <path
              d="M12 2C12 2 7 8 7 13a5 5 0 0 0 10 0c0-2-1-4-2-5.5C14 9 13 10 12 11c0-3 0-6 0-9Z"
              fill="currentColor"
              opacity="0.9"
            />
            <path
              d="M12 14c0 1.1-.9 2-2 2s-2-.9-2-2c0-1.5 2-4 2-4s2 2.5 2 4Z"
              fill="#fbbf24"
            />
          </svg>
          <span className="text-sm font-semibold tracking-widest uppercase text-white/80">
            FORGE
          </span>
        </Link>

        {/* Desktop Navigation */}
        <div className="hidden md:flex items-center gap-8">
          <a
            href="#product"
            className="text-sm text-white/60 hover:text-white transition-colors"
          >
            Product
          </a>
          <a
            href="#how-it-works"
            className="text-sm text-white/60 hover:text-white transition-colors"
          >
            How it works
          </a>
          <a
            href="#company-brain"
            className="text-sm text-white/60 hover:text-white transition-colors"
          >
            Company Brain
          </a>
          <a
            href="#intelligence"
            className="text-sm text-white/60 hover:text-white transition-colors"
          >
            Intelligence
          </a>
        </div>

        {/* Desktop Auth */}
        <div className="hidden md:flex items-center gap-4">
          <Link
            className="text-sm text-white/60 hover:text-white transition-colors"
            href="/login"
          >
            Login
          </Link>
          <Link
            className="text-sm font-medium px-4 py-2 rounded-lg bg-violet-600/20 border border-violet-500/30 text-violet-200 hover:bg-violet-600/30 transition-colors"
            href="/signup"
          >
            Sign up
          </Link>
        </div>

        {/* Mobile menu button */}
        <button
          className="md:hidden p-2 text-white/60 hover:text-white"
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          aria-label="Toggle menu"
          aria-expanded={mobileMenuOpen}
        >
          <svg
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            {mobileMenuOpen ? (
              <path d="M6 18L18 6M6 6l12 12" strokeLinecap="round" strokeLinejoin="round" />
            ) : (
              <path d="M3 12h18M3 6h18M3 18h18" strokeLinecap="round" />
            )}
          </svg>
        </button>
      </nav>

      {/* Mobile menu */}
      {mobileMenuOpen && (
        <div className="md:hidden fixed inset-0 top-16 z-40 bg-[#07070c]/95 backdrop-blur-lg border-t border-white/8">
          <div className="flex flex-col p-6 gap-4">
            <a
              href="#product"
              className="text-base text-white/80 hover:text-white py-2"
              onClick={() => setMobileMenuOpen(false)}
            >
              Product
            </a>
            <a
              href="#how-it-works"
              className="text-base text-white/80 hover:text-white py-2"
              onClick={() => setMobileMenuOpen(false)}
            >
              How it works
            </a>
            <a
              href="#company-brain"
              className="text-base text-white/80 hover:text-white py-2"
              onClick={() => setMobileMenuOpen(false)}
            >
              Company Brain
            </a>
            <a
              href="#intelligence"
              className="text-base text-white/80 hover:text-white py-2"
              onClick={() => setMobileMenuOpen(false)}
            >
              Intelligence
            </a>
            <div className="border-t border-white/8 pt-4 mt-2">
              <Link
                className="block text-base text-white/80 hover:text-white py-2"
                href="/login"
                onClick={() => setMobileMenuOpen(false)}
              >
                Login
              </Link>
              <Link
                className="block text-base font-medium text-violet-300 py-2"
                href="/signup"
                onClick={() => setMobileMenuOpen(false)}
              >
                Sign up
              </Link>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
