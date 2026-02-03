/**
 * DarkModeToggle - Pill-shaped toggle for light/dark mode
 *
 * Design: Two-sided pill with sun/moon icons and labels
 * - Light mode: Sun icon + "LIGHT MODE"
 * - Dark mode: Moon icon + "DARK MODE"
 */
import React, { useState } from "react";
import { Sun, Moon } from "lucide-react";
import { cn } from "@/lib/utils";

interface DarkModeToggleProps {
  className?: string;
}

export const DarkModeToggle: React.FC<DarkModeToggleProps> = ({ className }) => {
  // Local state for now (not functional yet)
  const [isDarkMode, setIsDarkMode] = useState(false);

  return (
    <div
      className={cn(
        "inline-flex rounded-full p-1 shadow-md",
        isDarkMode ? "bg-slate-800" : "bg-slate-200",
        className
      )}
    >
      {/* Light Mode Button */}
      <button
        onClick={() => setIsDarkMode(false)}
        className={cn(
          "flex items-center gap-1.5 px-2.5 py-1.5 rounded-full text-[10px] font-semibold uppercase tracking-wide transition-all duration-200",
          !isDarkMode
            ? "bg-white text-slate-700 shadow-sm"
            : "bg-transparent text-slate-400 hover:text-slate-300"
        )}
      >
        <Sun className="h-3 w-3" />
        <span>Light</span>
      </button>

      {/* Dark Mode Button */}
      <button
        onClick={() => setIsDarkMode(true)}
        className={cn(
          "flex items-center gap-1.5 px-2.5 py-1.5 rounded-full text-[10px] font-semibold uppercase tracking-wide transition-all duration-200",
          isDarkMode
            ? "bg-slate-700 text-white shadow-sm"
            : "bg-transparent text-slate-500 hover:text-slate-600"
        )}
      >
        <Moon className="h-3 w-3" />
        <span>Dark</span>
      </button>
    </div>
  );
};

export default DarkModeToggle;
