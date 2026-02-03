/**
 * DarkModeToggle - Pill-shaped toggle for light/dark mode
 *
 * Design: Two-sided pill with sun/moon icons and labels
 * - Light mode: Sun icon + "Light"
 * - Dark mode: Moon icon + "Dark"
 */
import React from "react";
import { Sun, Moon } from "lucide-react";
import { cn } from "@/lib/utils";
import { useTheme } from "@/components/theme-provider";

interface DarkModeToggleProps {
  className?: string;
}

export const DarkModeToggle: React.FC<DarkModeToggleProps> = ({ className }) => {
  const { theme, setTheme } = useTheme();
  const isDarkMode = theme === "dark";

  return (
    <div
      className={cn(
        "inline-flex rounded-full p-1",
        isDarkMode ? "bg-slate-800" : "bg-slate-200",
        className
      )}
      style={{
        boxShadow: isDarkMode
          ? "inset 3px 3px 6px rgba(0,0,0,0.4), inset -2px -2px 4px rgba(255,255,255,0.05)"
          : "inset 3px 3px 6px rgba(0,0,0,0.15), inset -2px -2px 4px rgba(255,255,255,0.7)"
      }}
    >
      {/* Light Mode Button */}
      <button
        onClick={() => setTheme("light")}
        className={cn(
          "flex items-center gap-1.5 px-2.5 py-1.5 rounded-full text-[10px] font-semibold uppercase tracking-wide transition-all duration-200",
          !isDarkMode
            ? "bg-slate-100 text-slate-700"
            : "bg-transparent text-slate-400 hover:text-slate-300"
        )}
        style={!isDarkMode ? {
          boxShadow: "3px 3px 6px rgba(0,0,0,0.12), -2px -2px 4px rgba(255,255,255,0.8), inset 1px 1px 1px rgba(255,255,255,0.6)"
        } : {}}
      >
        <Sun className="h-4 w-4" />
        <span>Light</span>
      </button>

      {/* Dark Mode Button */}
      <button
        onClick={() => setTheme("dark")}
        className={cn(
          "flex items-center gap-1.5 px-2.5 py-1.5 rounded-full text-[10px] font-semibold uppercase tracking-wide transition-all duration-200",
          isDarkMode
            ? "bg-slate-600 text-white"
            : "bg-transparent text-slate-500 hover:text-slate-600"
        )}
        style={isDarkMode ? {
          boxShadow: "3px 3px 6px rgba(0,0,0,0.3), -2px -2px 4px rgba(255,255,255,0.05), inset 1px 1px 1px rgba(255,255,255,0.1)"
        } : {}}
      >
        <Moon className="h-4 w-4" />
        <span>Dark</span>
      </button>
    </div>
  );
};

export default DarkModeToggle;
