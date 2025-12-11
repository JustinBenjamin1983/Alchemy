import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { X } from "lucide-react";
import { useState, KeyboardEvent } from "react";
import { DDProjectSetup, REGULATOR_SUGGESTIONS } from "./types";

interface Step4Props {
  data: DDProjectSetup;
  onChange: (updates: Partial<DDProjectSetup>) => void;
}

interface TagInputProps {
  label: string;
  description?: string;
  placeholder: string;
  tags: string[];
  onChange: (tags: string[]) => void;
  suggestions?: string[];
}

function TagInput({
  label,
  description,
  placeholder,
  tags,
  onChange,
  suggestions = [],
}: TagInputProps) {
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
      {description && (
        <p className="text-sm text-muted-foreground">{description}</p>
      )}
      <div className="flex flex-wrap gap-2 mb-2 min-h-[32px]">
        {tags.map((tag) => (
          <Badge
            key={tag}
            variant="secondary"
            className="flex items-center gap-1"
          >
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

export function Step4KeyParties({ data, onChange }: Step4Props) {
  const regulatorSuggestions = data.transactionType
    ? REGULATOR_SUGGESTIONS[data.transactionType] || []
    : [];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold mb-2">Key Parties</h2>
        <p className="text-sm text-muted-foreground mb-4">
          Identifying key parties helps flag related findings and contracts.
        </p>
      </div>

      <div className="space-y-4">
        <div>
          <Label htmlFor="targetCompanyName">Target Company Name</Label>
          <Input
            id="targetCompanyName"
            className="mt-2"
            placeholder="e.g., Karoo Mining Holdings (Pty) Ltd"
            value={data.targetCompanyName}
            onChange={(e) => onChange({ targetCompanyName: e.target.value })}
          />
        </div>

        <TagInput
          label="Key Persons to Watch For"
          description="Directors, shareholders, or individuals mentioned in key documents"
          placeholder="e.g., Hendrik van der Merwe..."
          tags={data.keyPersons}
          onChange={(persons) => onChange({ keyPersons: persons })}
        />

        <TagInput
          label="Key Counterparties"
          description="Major customers, suppliers, or partners"
          placeholder="e.g., Eskom, Standard Bank, Witklip Properties..."
          tags={data.counterparties}
          onChange={(parties) => onChange({ counterparties: parties })}
        />

        <TagInput
          label="Key Lenders/Financiers"
          description="Banks, DFIs, or financial institutions involved"
          placeholder="e.g., Standard Bank, RMB, IDC..."
          tags={data.keyLenders}
          onChange={(lenders) => onChange({ keyLenders: lenders })}
        />

        <TagInput
          label="Key Regulators"
          description="Regulatory bodies relevant to the transaction"
          placeholder="e.g., DMRE, Competition Commission..."
          tags={data.keyRegulators}
          onChange={(regulators) => onChange({ keyRegulators: regulators })}
          suggestions={regulatorSuggestions}
        />
      </div>
    </div>
  );
}
