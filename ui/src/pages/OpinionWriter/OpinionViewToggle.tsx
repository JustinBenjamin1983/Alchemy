import { cn } from "@/lib/utils";
import { ShieldCheck, FileText, Wand2 } from "lucide-react";

export type OpinionView = "initial" | "verification" | "rewritten";

export function OpinionViewToggle({
  value,
  onChange,
  className,
}: {
  value: OpinionView;
  onChange: (v: OpinionView) => void;
  className?: string;
}) {
  const btn = (v: OpinionView, label: string, Icon: any) => (
    <button
      type="button"
      onClick={() => onChange(v)}
      className={cn(
        "flex items-center gap-2 px-3 py-1.5 rounded-md border text-xs transition-colors",
        value === v
          ? "bg-blue-600 text-white border-blue-600"
          : "bg-white hover:bg-gray-50 text-gray-700 border-gray-300"
      )}
    >
      <Icon className="w-4 h-4" />
      {label}
    </button>
  );

  return (
    <div className={cn("inline-flex items-center gap-2", className)}>
      {btn("initial", "Initial Draft", FileText)}
      {btn("verification", "Verification Report", ShieldCheck)}
      {btn("rewritten", "Rewritten Draft", Wand2)}
    </div>
  );
}
