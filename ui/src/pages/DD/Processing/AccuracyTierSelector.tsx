/**
 * AccuracyTierSelector - Visual accuracy vs cost tradeoff selector
 *
 * Shows the conflict between accuracy and cost in a visually appealing way.
 */
import { useState } from "react";
import { Label } from "@/components/ui/label";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Zap, Scale, Target, Crown, TrendingUp, DollarSign } from "lucide-react";
import { cn } from "@/lib/utils";

export type ModelTier = "cost_optimized" | "balanced" | "high_accuracy" | "maximum_accuracy";

interface TierConfig {
  id: ModelTier;
  name: string;
  shortName: string;
  icon: React.ReactNode;
  description: string;
  costPercentage: number;    // 0-100 relative cost
  accuracyPercentage: number; // 0-100 accuracy
  costLabel: string;
  accuracyLabel: string;
  color: string;
  bgColor: string;
  borderColor: string;
}

const TIER_CONFIGS: TierConfig[] = [
  {
    id: "cost_optimized",
    name: "Economy",
    shortName: "Eco",
    icon: <Zap className="h-4 w-4" />,
    description: "Fast & affordable for routine reviews",
    costPercentage: 25,
    accuracyPercentage: 85,
    costLabel: "~R18",
    accuracyLabel: "85%",
    color: "text-emerald-600",
    bgColor: "bg-emerald-50",
    borderColor: "border-emerald-500",
  },
  {
    id: "balanced",
    name: "Balanced",
    shortName: "Bal",
    icon: <Scale className="h-4 w-4" />,
    description: "Recommended for standard DD",
    costPercentage: 45,
    accuracyPercentage: 90,
    costLabel: "~R25",
    accuracyLabel: "90%",
    color: "text-blue-600",
    bgColor: "bg-blue-50",
    borderColor: "border-blue-500",
  },
  {
    id: "high_accuracy",
    name: "High Accuracy",
    shortName: "High",
    icon: <Target className="h-4 w-4" />,
    description: "Complex deals & deal-blockers",
    costPercentage: 70,
    accuracyPercentage: 93,
    costLabel: "~R35",
    accuracyLabel: "93%",
    color: "text-orange-600",
    bgColor: "bg-orange-50",
    borderColor: "border-orange-500",
  },
  {
    id: "maximum_accuracy",
    name: "Maximum",
    shortName: "Max",
    icon: <Crown className="h-4 w-4" />,
    description: "Critical high-stakes transactions",
    costPercentage: 100,
    accuracyPercentage: 95,
    costLabel: "~R50",
    accuracyLabel: "95%",
    color: "text-purple-600",
    bgColor: "bg-purple-50",
    borderColor: "border-purple-500",
  },
];

interface AccuracyTierSelectorProps {
  value: ModelTier;
  onChange: (tier: ModelTier) => void;
  disabled?: boolean;
  compact?: boolean;
}

export function AccuracyTierSelector({
  value,
  onChange,
  disabled = false,
  compact = false,
}: AccuracyTierSelectorProps) {
  const selectedTier = TIER_CONFIGS.find((t) => t.id === value) || TIER_CONFIGS[1];

  if (compact) {
    // Compact mode with visual bars
    return (
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <Label className="text-xs font-medium text-gray-600">Analysis Accuracy</Label>
          <div className="flex items-center gap-3 text-[10px] text-gray-500">
            <span className="flex items-center gap-1">
              <TrendingUp className="h-3 w-3 text-blue-500" />
              Accuracy
            </span>
            <span className="flex items-center gap-1">
              <DollarSign className="h-3 w-3 text-emerald-500" />
              Cost
            </span>
          </div>
        </div>

        <div className="flex gap-1.5">
          {TIER_CONFIGS.map((tier) => {
            const isSelected = value === tier.id;
            return (
              <TooltipProvider key={tier.id}>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <button
                      type="button"
                      disabled={disabled}
                      onClick={() => onChange(tier.id)}
                      className={cn(
                        "flex-1 rounded-lg border-2 p-2 transition-all",
                        isSelected
                          ? `${tier.borderColor} ${tier.bgColor}`
                          : "border-gray-200 bg-white hover:border-gray-300 hover:bg-gray-50",
                        disabled && "opacity-50 cursor-not-allowed"
                      )}
                    >
                      <div className="flex flex-col items-center gap-1.5">
                        {/* Tier icon and name */}
                        <div className={cn(
                          "flex items-center gap-1",
                          isSelected ? tier.color : "text-gray-500"
                        )}>
                          {tier.icon}
                          <span className="text-xs font-medium">{tier.shortName}</span>
                        </div>

                        {/* Visual bars */}
                        <div className="w-full space-y-1">
                          {/* Accuracy bar */}
                          <div className="h-1.5 w-full bg-gray-100 rounded-full overflow-hidden">
                            <div
                              className={cn(
                                "h-full rounded-full transition-all",
                                isSelected ? "bg-blue-500" : "bg-blue-300"
                              )}
                              style={{ width: `${tier.accuracyPercentage}%` }}
                            />
                          </div>
                          {/* Cost bar */}
                          <div className="h-1.5 w-full bg-gray-100 rounded-full overflow-hidden">
                            <div
                              className={cn(
                                "h-full rounded-full transition-all",
                                isSelected ? "bg-emerald-500" : "bg-emerald-300"
                              )}
                              style={{ width: `${tier.costPercentage}%` }}
                            />
                          </div>
                        </div>

                        {/* Labels */}
                        <div className="flex justify-between w-full text-[9px]">
                          <span className={cn(
                            "font-medium",
                            isSelected ? "text-blue-600" : "text-gray-400"
                          )}>
                            {tier.accuracyLabel}
                          </span>
                          <span className={cn(
                            "font-medium",
                            isSelected ? "text-emerald-600" : "text-gray-400"
                          )}>
                            {tier.costLabel}
                          </span>
                        </div>
                      </div>
                    </button>
                  </TooltipTrigger>
                  <TooltipContent side="bottom" className="max-w-xs">
                    <div className="text-xs">
                      <div className="font-semibold">{tier.name}</div>
                      <div className="text-muted-foreground mt-0.5">{tier.description}</div>
                      <div className="mt-1.5 pt-1.5 border-t border-gray-200 grid grid-cols-2 gap-2">
                        <div>
                          <span className="text-blue-600 font-medium">{tier.accuracyLabel}</span>
                          <span className="text-gray-500"> accuracy</span>
                        </div>
                        <div>
                          <span className="text-emerald-600 font-medium">{tier.costLabel}</span>
                          <span className="text-gray-500">/100 docs</span>
                        </div>
                      </div>
                    </div>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            );
          })}
        </div>
      </div>
    );
  }

  // Full mode - larger cards with more detail
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <Label className="text-sm font-medium">Select Analysis Accuracy</Label>
        <div className="flex items-center gap-4 text-xs text-gray-500">
          <span className="flex items-center gap-1">
            <div className="w-2 h-2 rounded-full bg-blue-500" />
            Accuracy
          </span>
          <span className="flex items-center gap-1">
            <div className="w-2 h-2 rounded-full bg-emerald-500" />
            Cost
          </span>
        </div>
      </div>

      <div className="grid grid-cols-4 gap-3">
        {TIER_CONFIGS.map((tier) => {
          const isSelected = value === tier.id;
          return (
            <button
              key={tier.id}
              type="button"
              disabled={disabled}
              onClick={() => onChange(tier.id)}
              className={cn(
                "relative rounded-xl border-2 p-3 transition-all text-left",
                isSelected
                  ? `${tier.borderColor} ${tier.bgColor} shadow-md`
                  : "border-gray-200 bg-white hover:border-gray-300 hover:shadow-sm",
                disabled && "opacity-50 cursor-not-allowed"
              )}
            >
              {/* Recommended badge */}
              {tier.id === "balanced" && (
                <div className="absolute -top-2 left-1/2 -translate-x-1/2 px-2 py-0.5 bg-blue-600 text-white text-[9px] font-medium rounded-full whitespace-nowrap">
                  Recommended
                </div>
              )}

              {/* Header */}
              <div className={cn(
                "flex items-center gap-1.5 mb-2",
                isSelected ? tier.color : "text-gray-600"
              )}>
                {tier.icon}
                <span className="text-sm font-semibold">{tier.name}</span>
              </div>

              {/* Description */}
              <p className="text-[10px] text-gray-500 mb-3 line-clamp-2 h-6">
                {tier.description}
              </p>

              {/* Visual comparison */}
              <div className="space-y-2">
                {/* Accuracy */}
                <div className="space-y-0.5">
                  <div className="flex items-center justify-between text-[10px]">
                    <span className="text-gray-500">Accuracy</span>
                    <span className={cn(
                      "font-bold",
                      isSelected ? "text-blue-600" : "text-gray-600"
                    )}>
                      {tier.accuracyLabel}
                    </span>
                  </div>
                  <div className="h-2 w-full bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className={cn(
                        "h-full rounded-full transition-all duration-300",
                        isSelected ? "bg-blue-500" : "bg-blue-200"
                      )}
                      style={{ width: `${tier.accuracyPercentage}%` }}
                    />
                  </div>
                </div>

                {/* Cost */}
                <div className="space-y-0.5">
                  <div className="flex items-center justify-between text-[10px]">
                    <span className="text-gray-500">Cost</span>
                    <span className={cn(
                      "font-bold",
                      isSelected ? "text-emerald-600" : "text-gray-600"
                    )}>
                      {tier.costLabel}
                    </span>
                  </div>
                  <div className="h-2 w-full bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className={cn(
                        "h-full rounded-full transition-all duration-300",
                        isSelected ? "bg-emerald-500" : "bg-emerald-200"
                      )}
                      style={{ width: `${tier.costPercentage}%` }}
                    />
                  </div>
                </div>
              </div>
            </button>
          );
        })}
      </div>

      {/* Selected tier summary */}
      <div className={cn(
        "flex items-center justify-between p-3 rounded-lg border",
        selectedTier.bgColor,
        selectedTier.borderColor.replace('border-', 'border-')
      )}>
        <div className="flex items-center gap-2">
          <div className={selectedTier.color}>{selectedTier.icon}</div>
          <div>
            <span className={cn("text-sm font-medium", selectedTier.color)}>
              {selectedTier.name}
            </span>
            <span className="text-xs text-gray-500 ml-2">selected</span>
          </div>
        </div>
        <div className="flex items-center gap-4 text-xs">
          <div className="flex items-center gap-1">
            <TrendingUp className="h-3.5 w-3.5 text-blue-500" />
            <span className="font-semibold text-blue-600">{selectedTier.accuracyLabel}</span>
          </div>
          <div className="flex items-center gap-1">
            <DollarSign className="h-3.5 w-3.5 text-emerald-500" />
            <span className="font-semibold text-emerald-600">{selectedTier.costLabel}/100 docs</span>
          </div>
        </div>
      </div>
    </div>
  );
}

export default AccuracyTierSelector;
