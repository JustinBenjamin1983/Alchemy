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
    <div className={cn("flex items-center gap-2", className)}>
      {/* Light Mode Label */}
      <div
        className={cn(
          "flex flex-col items-end text-[9px] font-semibold uppercase leading-tight transition-colors duration-200",
          !isDarkMode ? "text-slate-700" : "text-slate-400"
        )}
      >
        <span>Light</span>
        <span>Mode</span>
      </div>

      {/* Toggle Button - Icons Only */}
      <div
        className={cn(
          "inline-flex rounded-full p-1",
          isDarkMode ? "bg-slate-800" : "bg-slate-200"
        )}
        style={{
          boxShadow: isDarkMode
            ? "inset 3px 3px 6px rgba(0,0,0,0.4), inset -2px -2px 4px rgba(255,255,255,0.05)"
            : "inset 3px 3px 6px rgba(0,0,0,0.15), inset -2px -2px 4px rgba(255,255,255,0.7)"
        }}
      >
        {/* Light Mode Icon */}
        <button
          onClick={() => setIsDarkMode(false)}
          className={cn(
            "flex items-center justify-center p-2 rounded-full transition-all duration-200",
            !isDarkMode
              ? "bg-slate-100 text-amber-500"
              : "bg-transparent text-slate-400 hover:text-slate-300"
          )}
          style={!isDarkMode ? {
            boxShadow: "3px 3px 6px rgba(0,0,0,0.12), -2px -2px 4px rgba(255,255,255,0.8), inset 1px 1px 1px rgba(255,255,255,0.6)"
          } : {}}
        >
          <Sun className="h-4 w-4" />
        </button>

        {/* Dark Mode Icon */}
        <button
          onClick={() => setIsDarkMode(true)}
          className={cn(
            "flex items-center justify-center p-2 rounded-full transition-all duration-200",
            isDarkMode
              ? "bg-slate-600 text-blue-300"
              : "bg-transparent text-slate-500 hover:text-slate-600"
          )}
          style={isDarkMode ? {
            boxShadow: "3px 3px 6px rgba(0,0,0,0.3), -2px -2px 4px rgba(255,255,255,0.05), inset 1px 1px 1px rgba(255,255,255,0.1)"
          } : {}}
        >
          <Moon className="h-4 w-4" />
        </button>
      </div>

      {/* Dark Mode Label */}
      <div
        className={cn(
          "flex flex-col items-start text-[9px] font-semibold uppercase leading-tight transition-colors duration-200",
          isDarkMode ? "text-slate-700" : "text-slate-400"
        )}
      >
        <span>Dark</span>
        <span>Mode</span>
      </div>
    </div>
  );
};

export default DarkModeToggle;
