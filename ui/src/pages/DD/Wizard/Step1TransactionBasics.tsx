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

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-sm font-medium text-muted-foreground mb-2">Transaction Type</h3>
        <TransactionTypeSelector
          selected={data.transactionType}
          onSelect={(type: TransactionTypeCode) =>
            onChange({ transactionType: type })
          }
        />
        {data.transactionType && (
          <div className="mt-2">
            <BlueprintSummary transactionType={data.transactionType} />
          </div>
        )}
      </div>

      <div className="grid grid-cols-2 gap-x-4 gap-y-3 pt-3">
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
          <Label htmlFor="clientRole" className="text-xs text-muted-foreground mb-1 block">
            Client Role
          </Label>
          <Select
            value={data.clientRole || ""}
            onValueChange={(v: ClientRole) => onChange({ clientRole: v })}
          >
            <SelectTrigger className="bg-white h-9 w-full">
              <SelectValue placeholder="Select client role" />
            </SelectTrigger>
            <SelectContent className="bg-white">
              <SelectItem value="buyer">Buyer / Acquirer</SelectItem>
              <SelectItem value="seller">Seller / Vendor</SelectItem>
              <SelectItem value="target">Target Company</SelectItem>
              <SelectItem value="advisor">Independent Advisor</SelectItem>
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
          >
            <SelectTrigger className="bg-white h-9 w-full">
              <SelectValue placeholder="Select deal structure" />
            </SelectTrigger>
            <SelectContent className="bg-white">
              <SelectItem value="share_purchase">Share Purchase</SelectItem>
              <SelectItem value="asset_purchase">Asset Purchase</SelectItem>
              <SelectItem value="merger">Merger</SelectItem>
              <SelectItem value="scheme">Scheme of Arrangement</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div>
          <Label htmlFor="estimatedValue" className="text-xs text-muted-foreground mb-1 block">
            Estimated Value (ZAR)
          </Label>
          <Input
            id="estimatedValue"
            type="text"
            className="h-9"
            placeholder="e.g., R500,000,000"
            value={valueInput}
            onChange={handleValueChange}
            onFocus={handleValueFocus}
            onBlur={handleValueBlur}
          />
        </div>

        <div>
          <Label htmlFor="targetClosingDate" className="text-xs text-muted-foreground mb-1 block">
            Target Closing Date
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
  );
}
