import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { X, AlertCircle } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { useState, KeyboardEvent } from "react";
import { DDProjectSetup, TRANSACTION_TYPE_INFO } from "./types";

interface Step3Props {
  data: DDProjectSetup;
  onChange: (updates: Partial<DDProjectSetup>) => void;
}

// Risk categories by transaction type
const RISK_CATEGORIES: Record<string, string[]> = {
  mining_resources: [
    "Mining Rights & Regulatory",
    "Environmental",
    "BEE & Transformation",
    "Labor & Community",
    "Offtake & Commercial",
    "Technical & Reserves",
  ],
  ma_corporate: [
    "Corporate Structure",
    "Material Contracts",
    "Financial",
    "Intellectual Property",
    "Employment",
    "Litigation & Disputes",
  ],
  banking_finance: [
    "Existing Debt",
    "Security Package",
    "Regulatory Compliance",
    "Asset Quality",
    "Covenant Compliance",
  ],
  real_estate: [
    "Title & Ownership",
    "Zoning & Planning",
    "Leases",
    "Environmental",
    "Building Condition",
    "Municipal Compliance",
  ],
  competition_regulatory: [
    "Market Definition",
    "Competition Analysis",
    "Public Interest",
    "Regulatory Approvals",
  ],
  employment_labor: [
    "Employment Contracts",
    "Union Relations",
    "Benefits & Pensions",
    "Section 197 Transfer",
    "Pending Claims",
  ],
  ip_technology: [
    "Patents & Trademarks",
    "Software & Licenses",
    "Data Privacy (POPIA)",
    "Cybersecurity",
    "IP Disputes",
  ],
  bee_transformation: [
    "Ownership Structure",
    "Flow-Through Analysis",
    "Verification",
    "Mining Charter",
    "Transaction Structure",
  ],
  energy_power: [
    "Generation License",
    "PPA & Offtake",
    "Grid Connection",
    "REIPPPP Compliance",
    "Technical Performance",
    "ED Obligations",
  ],
  infrastructure_ppp: [
    "Concession Agreement",
    "Treasury Approvals",
    "Revenue & Tariffs",
    "Construction Status",
    "Operations & Lifecycle",
    "Lender Documents",
  ],
};

interface TagInputProps {
  placeholder: string;
  tags: string[];
  onChange: (tags: string[]) => void;
}

function TagInput({ placeholder, tags, onChange }: TagInputProps) {
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

  return (
    <div className="space-y-2">
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
    </div>
  );
}

export function Step3FocusAreas({ data, onChange }: Step3Props) {
  const riskCategories = data.transactionType
    ? RISK_CATEGORIES[data.transactionType] || []
    : [];

  const togglePriority = (category: string) => {
    const current = data.criticalPriorities;
    if (current.includes(category)) {
      onChange({
        criticalPriorities: current.filter((c) => c !== category),
      });
    } else {
      onChange({
        criticalPriorities: [...current, category],
      });
    }
  };

  const toggleDeprioritize = (category: string) => {
    const current = data.deprioritizedAreas;
    if (current.includes(category)) {
      onChange({
        deprioritizedAreas: current.filter((c) => c !== category),
      });
    } else {
      // Remove from critical if adding to deprioritized
      onChange({
        deprioritizedAreas: [...current, category],
        criticalPriorities: data.criticalPriorities.filter((c) => c !== category),
      });
    }
  };

  return (
    <div className="space-y-5">
      {/* Discussion Notice */}
      <Alert className="bg-amber-50 border-amber-200 shadow-sm">
        <AlertCircle className="h-4 w-4 text-amber-600" />
        <AlertDescription className="text-amber-800">
          <strong>For Discussion:</strong> These focus area options are presented for discussion purposes only and are not yet functional.
          The DD assessment currently analyzes all risk categories with equal depth regardless of selections made here.
        </AlertDescription>
      </Alert>

      {/* Greyed out content */}
      <div className="opacity-50 pointer-events-none select-none space-y-5">
        {/* Risk Categories Section */}
        {riskCategories.length > 0 && (
          <div className="bg-slate-50 rounded-lg border border-gray-200 shadow-sm p-4">
            <h3 className="text-sm font-semibold text-gray-700 mb-3">
              Risk Categories for{" "}
              {data.transactionType
                ? TRANSACTION_TYPE_INFO[data.transactionType]?.name
                : ""}
            </h3>
            <p className="text-xs text-muted-foreground mb-3">
              Check categories that are critical priorities. Areas marked as critical
              will receive deeper analysis.
            </p>
            <div className="grid grid-cols-2 gap-3">
              {riskCategories.map((category) => {
                const isCritical = data.criticalPriorities.includes(category);
                const isDeprioritized = data.deprioritizedAreas.includes(category);

                return (
                  <div
                    key={category}
                    className={`p-3 border rounded-lg transition-all bg-white ${
                      isCritical
                        ? "bg-orange-50 border-alchemyPrimaryOrange"
                        : isDeprioritized
                        ? "bg-gray-100 opacity-60"
                        : "hover:bg-gray-50"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        <Checkbox
                          id={`priority-${category}`}
                          checked={isCritical}
                          disabled={true}
                        />
                        <Label
                          htmlFor={`priority-${category}`}
                          className={`font-normal ${
                            isDeprioritized ? "line-through text-muted-foreground" : ""
                          }`}
                        >
                          {category}
                        </Label>
                      </div>
                      {!isCritical && (
                        <Badge
                          variant={isDeprioritized ? "secondary" : "outline"}
                          className="text-xs"
                        >
                          {isDeprioritized ? "Deprioritized" : "Deprioritize"}
                        </Badge>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Deal Breakers Section */}
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-4">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">Deal Breakers</h3>
          <Label htmlFor="dealBreakers" className="text-xs text-muted-foreground mb-1 block">
            Issues that would cause the deal to fall through
          </Label>
          <Textarea
            id="dealBreakers"
            placeholder="e.g., If mining right cannot be transferred, deal cannot proceed. If Eskom terminates CSA, walk away..."
            disabled
            rows={3}
            className="bg-white"
          />
        </div>

        {/* Deprioritize Section */}
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-4">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">Areas to Deprioritize</h3>
          <Label className="text-xs text-muted-foreground mb-1 block">
            Other areas that are not material for this deal
          </Label>
          <Input
            placeholder="e.g., IP (not material for this deal)..."
            disabled
            className="bg-white"
          />
        </div>
      </div>
    </div>
  );
}
