// File: ui/src/pages/OpinionWriter/CompilationModeToggle.tsx
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";

export type CompilationMode = "lawyer" | "client";

interface CompilationModeToggleProps {
  value: CompilationMode;
  onChange: (mode: CompilationMode) => void;
}

export function CompilationModeToggle({
  value,
  onChange,
}: CompilationModeToggleProps) {
  return (
    <div className="bg-white rounded-lg border p-4">
      <Label className="text-sm font-medium mb-3 block">Compilation Mode</Label>
      <RadioGroup
        value={value}
        onValueChange={(v) => onChange(v as CompilationMode)}
        className="flex gap-4"
      >
        <div className="flex items-center space-x-2">
          <RadioGroupItem value="lawyer" id="mode-lawyer" />
          <Label
            htmlFor="mode-lawyer"
            className="text-sm font-normal cursor-pointer"
          >
            <div className="font-medium">Lawyer Centric</div>
            <div className="text-xs text-gray-500">Technical legal opinion</div>
          </Label>
        </div>
        <div className="flex items-center space-x-2">
          <RadioGroupItem value="client" id="mode-client" />
          <Label
            htmlFor="mode-client"
            className="text-sm font-normal cursor-pointer"
          >
            <div className="font-medium">Client Centric</div>
            <div className="text-xs text-gray-500">
              Client-focused, comprehensive explanation
            </div>
          </Label>
        </div>
      </RadioGroup>
    </div>
  );
}
