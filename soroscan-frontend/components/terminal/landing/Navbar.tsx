"use client"

import * as React from "react"
import Link from "next/link"
import { Button } from "../Button"

export function Navbar() {
  const [menuOpen, setMenuOpen] = React.useState(false)

  return (
    <nav className="border-b border-terminal-green/30 px-4 md:px-8 py-4 bg-terminal-black/50 backdrop-blur-md sticky top-0 z-50">
      <div className="flex justify-between items-center">
        <Link href="/" className="text-terminal-green text-xl font-bold tracking-tighter hover:text-terminal-cyan transition-colors">
          [SOROSCAN_PROJECT]
        </Link>

        {/* Desktop nav */}
        <div className="hidden md:flex gap-8 text-xs text-terminal-gray uppercase tracking-widest">
          <Link href="/dashboard" className="hover:text-terminal-green transition-colors">Dashboard</Link>
          <Link href="/gallery" className="hover:text-terminal-green transition-colors">Gallery</Link>
          <a href="#" className="hover:text-terminal-green transition-colors">API_Docs</a>
          <a href="#" className="hover:text-terminal-green transition-colors">GitHub</a>
        </div>

        <div className="hidden md:block">
          <Button size="sm" variant="secondary">CONNECT_WALLET</Button>
        </div>

        {/* Hamburger button (mobile only) */}
        <button
          className="md:hidden flex flex-col gap-1.5 p-2 min-w-[44px] min-h-[44px] items-center justify-center border border-terminal-green/30 text-terminal-green"
          onClick={() => setMenuOpen(!menuOpen)}
          aria-label="Toggle menu"
        >
          <span className={`block w-5 h-0.5 bg-terminal-green transition-all ${menuOpen ? "rotate-45 translate-y-2" : ""}`} />
          <span className={`block w-5 h-0.5 bg-terminal-green transition-all ${menuOpen ? "opacity-0" : ""}`} />
          <span className={`block w-5 h-0.5 bg-terminal-green transition-all ${menuOpen ? "-rotate-45 -translate-y-2" : ""}`} />
        </button>
      </div>

      {/* Mobile menu */}
      {menuOpen && (
        <div className="md:hidden mt-4 flex flex-col gap-4 text-xs text-terminal-gray uppercase tracking-widest border-t border-terminal-green/20 pt-4">
          <Link href="/dashboard" className="hover:text-terminal-green transition-colors py-2" onClick={() => setMenuOpen(false)}>Dashboard</Link>
          <Link href="/gallery" className="hover:text-terminal-green transition-colors py-2" onClick={() => setMenuOpen(false)}>Gallery</Link>
          <a href="#" className="hover:text-terminal-green transition-colors py-2">API_Docs</a>
          <a href="#" className="hover:text-terminal-green transition-colors py-2">GitHub</a>
          <Button size="sm" variant="secondary">CONNECT_WALLET</Button>
        </div>
      )}
    </nav>
  )
}