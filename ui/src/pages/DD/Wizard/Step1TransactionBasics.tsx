import { useState } from "react";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { TransactionTypeSelector, BlueprintSummary } from "./TransactionTypeSelector";
import {
  DDProjectSetup,
  TransactionTypeCode,
  ClientRole,
  DealStructure,
  TARGET_ENTITY_LABELS,
  CLIENT_ROLE_OPTIONS,
  DEAL_STRUCTURE_OPTIONS,
  VALUE_DATE_LABELS,
} from "./types";

interface Step1Props {
  data: DDProjectSetup;
  onChange: (updates: Partial<DDProjectSetup>) => void;
}

// Format number as South African Rand currency
function formatZAR(value: number | null): string {
  if (value === null || value === 0) return "";
  return `R${value.toLocaleString("en-ZA")}`;
}

// Parse currency string back to number
function parseZAR(value: string): number | null {
  // Remove R, spaces, and commas
  const cleaned = value.replace(/[R\s,]/g, "");
  if (!cleaned) return null;
  const num = parseInt(cleaned, 10);
  return isNaN(num) ? null : num;
}

export function Step1TransactionBasics({ data, onChange }: Step1Props) {
  const [valueInput, setValueInput] = useState(formatZAR(data.estimatedValue));
  const [isValueFocused, setIsValueFocused] = useState(false);

  const handleValueChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const input = e.target.value;
    setValueInput(input);

    // Parse and update the actual value
    const parsed = parseZAR(input);
    onChange({ estimatedValue: parsed });
  };

  const handleValueBlur = () => {
    setIsValueFocused(false);
    // Format the display value on blur
    setValueInput(formatZAR(data.estimatedValue));
  };

  const handleValueFocus = () => {
    setIsValueFocused(true);
    // Show raw number when focused for easier editing
    if (data.estimatedValue) {
      setValueInput(data.estimatedValue.toString());
    }
  };

  // Get dynamic target entity label based on transaction type (with fallback for legacy types)
  const targetEntityConfig = data.transactionType
    ? TARGET_ENTITY_LABELS[data.transactionType] ?? { label: "Target Entity", placeholder: "e.g., Target Co (Pty) Ltd" }
    : { label: "Target Entity", placeholder: "Select transaction type first" };

  // Get dynamic value/date labels based on transaction type (with fallback for legacy types)
  const valueDateConfig = data.transactionType
    ? VALUE_DATE_LABELS[data.transactionType] ?? { valueLabel: "Estimated Value (ZAR)", valuePlaceholder: "e.g., R500,000,000", dateLabel: "Target Closing Date" }
    : { valueLabel: "Estimated Value (ZAR)", valuePlaceholder: "e.g., R500,000,000", dateLabel: "Target Closing Date" };

  return (
    <div className="space-y-5">
      {/* Transaction Type Section */}
      <div className="bg-slate-50 rounded-lg border border-gray-200 shadow-sm p-4">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">Transaction Type</h3>
        <TransactionTypeSelector
          selected={data.transactionType}
          onSelect={(type: TransactionTypeCode) =>
            onChange({ transactionType: type, clientRole: null, dealStructure: null })
          }
        />
        {data.transactionType && (
          <div className="mt-3">
            <BlueprintSummary transactionType={data.transactionType} />
          </div>
        )}
      </div>

      {/* Project Details Section */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-4">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">Project Details</h3>
        <div className="grid grid-cols-2 gap-x-4 gap-y-3">
        <div className="col-span-2">
          <Label htmlFor="projectName" className="text-xs text-muted-foreground mb-1 block">
            Project Name
          </Label>
          <Input
            id="projectName"
            className="h-9"
            placeholder="e.g., Project Karoo - Mining Acquisition"
            value={data.transactionName}
            onChange={(e) => onChange({ transactionName: e.target.value })}
          />
        </div>

        <div>
          <Label htmlFor="clientName" className="text-xs text-muted-foreground mb-1 block">
            Client Name
          </Label>
          <Input
            id="clientName"
            className="h-9"
            placeholder="e.g., Acme Corp (Pty) Ltd"
            value={data.clientName}
            onChange={(e) => onChange({ clientName: e.target.value })}
          />
        </div>

        <div>
          <Label htmlFor="clientRegistrationNumber" className="text-xs text-muted-foreground mb-1 block">
            Client Reg/ID Number
          </Label>
          <Input
            id="clientRegistrationNumber"
            className="h-9"
            placeholder="e.g., 2020/123456/07 or ID number"
            value={data.clientRegistrationNumber || ""}
            onChange={(e) => onChange({ clientRegistrationNumber: e.target.value })}
          />
        </div>

        <div>
          <Label htmlFor="targetEntityName" className="text-xs text-muted-foreground mb-1 block">
            {targetEntityConfig.label}
          </Label>
          <Input
            id="targetEntityName"
            className="h-9"
            placeholder={targetEntityConfig.placeholder}
            value={data.targetEntityName}
            onChange={(e) => onChange({ targetEntityName: e.target.value })}
            disabled={!data.transactionType}
          />
        </div>

        <div>
          <Label htmlFor="targetRegistrationNumber" className="text-xs text-muted-foreground mb-1 block">
            Target Reg/ID Number
          </Label>
          <Input
            id="targetRegistrationNumber"
            className="h-9"
            placeholder="e.g., 2018/654321/07 or Trust IT number"
            value={data.targetRegistrationNumber || ""}
            onChange={(e) => onChange({ targetRegistrationNumber: e.target.value })}
            disabled={!data.transactionType}
          />
        </div>

        <div>
          <Label htmlFor="clientRole" className="text-xs text-muted-foreground mb-1 block">
            Client Role
          </Label>
          <Select
            value={data.clientRole || ""}
            onValueChange={(v: ClientRole) => onChange({ clientRole: v })}
            disabled={!data.transactionType}
          >
            <SelectTrigger className="bg-white h-9 w-full">
              <SelectValue placeholder={data.transactionType ? "Select client role" : "Select transaction type first"} />
            </SelectTrigger>
            <SelectContent className="bg-white">
              {data.transactionType && CLIENT_ROLE_OPTIONS[data.transactionType]?.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div>
          <Label htmlFor="dealStructure" className="text-xs text-muted-foreground mb-1 block">
            Deal Structure
          </Label>
          <Select
            value={data.dealStructure || ""}
            onValueChange={(v: DealStructure) => onChange({ dealStructure: v })}
            disabled={!data.transactionType}
          >
            <SelectTrigger className="bg-white h-9 w-full">
              <SelectValue placeholder={data.transactionType ? "Select deal structure" : "Select transaction type first"} />
            </SelectTrigger>
            <SelectContent className="bg-white">
              {data.transactionType && DEAL_STRUCTURE_OPTIONS[data.transactionType]?.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div>
          <Label htmlFor="estimatedValue" className="text-xs text-muted-foreground mb-1 block">
            {valueDateConfig.valueLabel}
          </Label>
          <Input
            id="estimatedValue"
            type="text"
            className="h-9"
            placeholder={valueDateConfig.valuePlaceholder}
            value={valueInput}
            onChange={handleValueChange}
            onFocus={handleValueFocus}
            onBlur={handleValueBlur}
          />
        </div>

        <div>
          <Label htmlFor="targetClosingDate" className="text-xs text-muted-foreground mb-1 block">
            {valueDateConfig.dateLabel}
          </Label>
          <Input
            id="targetClosingDate"
            type="date"
            className="h-9"
            value={
              data.targetClosingDate
                ? data.targetClosingDate.toISOString().split("T")[0]
                : ""
            }
            onChange={(e) =>
              onChange({
                targetClosingDate: e.target.value
                  ? new Date(e.target.value)
                  : null,
              })
            }
          />
        </div>
      </div>
      </div>
    </div>
  );
}
