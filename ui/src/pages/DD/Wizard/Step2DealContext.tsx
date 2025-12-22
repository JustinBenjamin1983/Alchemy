import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { X } from "lucide-react";
import { Input } from "@/components/ui/input";
import { useState, KeyboardEvent } from "react";
import { DDProjectSetup } from "./types";

interface Step2Props {
  data: DDProjectSetup;
  onChange: (updates: Partial<DDProjectSetup>) => void;
}

interface TagInputProps {
  label: string;
  placeholder: string;
  tags: string[];
  onChange: (tags: string[]) => void;
  suggestions?: string[];
}

function TagInput({ label, placeholder, tags, onChange, suggestions = [] }: TagInputProps) {
  const [inputValue, setInputValue] = useState("");

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && inputValue.trim()) {
      e.preventDefault();
      if (!tags.includes(inputValue.trim())) {
        onChange([...tags, inputValue.trim()]);
      }
      setInputValue("");
    }
  };

  const removeTag = (tagToRemove: string) => {
    onChange(tags.filter((tag) => tag !== tagToRemove));
  };

  const addSuggestion = (suggestion: string) => {
    if (!tags.includes(suggestion)) {
      onChange([...tags, suggestion]);
    }
  };

  return (
    <div className="space-y-2">
      <Label>{label}</Label>
      <div className="flex flex-wrap gap-2 mb-2">
        {tags.map((tag) => (
          <Badge key={tag} variant="secondary" className="flex items-center gap-1">
            {tag}
            <X
              className="h-3 w-3 cursor-pointer hover:text-destructive"
              onClick={() => removeTag(tag)}
            />
          </Badge>
        ))}
      </div>
      <Input
        placeholder={placeholder}
        value={inputValue}
        onChange={(e) => setInputValue(e.target.value)}
        onKeyDown={handleKeyDown}
      />
      {suggestions.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-2">
          <span className="text-xs text-muted-foreground">Suggestions:</span>
          {suggestions
            .filter((s) => !tags.includes(s))
            .slice(0, 5)
            .map((suggestion) => (
              <Badge
                key={suggestion}
                variant="outline"
                className="cursor-pointer hover:bg-gray-100"
                onClick={() => addSuggestion(suggestion)}
              >
                + {suggestion}
              </Badge>
            ))}
        </div>
      )}
    </div>
  );
}

const COMMON_CONCERNS = [
  "Environmental liabilities",
  "Title issues",
  "Pending litigation",
  "Regulatory compliance gaps",
  "Change of control restrictions",
  "Tax exposures",
  "Labor union issues",
  "BEE compliance",
  "Material contract issues",
  "IP ownership unclear",
];

export function Step2DealContext({ data, onChange }: Step2Props) {
  return (
    <div className="space-y-5">
      {/* Deal Rationale Section */}
      <div className="bg-slate-50 rounded-lg border border-gray-200 shadow-sm p-4">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">Deal Rationale</h3>
        <Label htmlFor="dealRationale" className="text-xs text-muted-foreground mb-1 block">
          Why is this deal happening?
        </Label>
        <Textarea
          id="dealRationale"
          placeholder="e.g., Strategic acquisition to expand coal supply capacity, seller exiting non-core assets..."
          value={data.dealRationale}
          onChange={(e) => onChange({ dealRationale: e.target.value })}
          rows={3}
          className="bg-white"
        />
      </div>

      {/* Known Concerns Section */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-4">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">Known Concerns</h3>
        <TagInput
          label="Add concerns that should be investigated"
          placeholder="Type and press Enter..."
          tags={data.knownConcerns}
          onChange={(concerns) => onChange({ knownConcerns: concerns })}
          suggestions={COMMON_CONCERNS}
        />
      </div>
    </div>
  );
}
