import { cn } from "@/lib/utils";
import {
  TransactionTypeCode,
  TRANSACTION_TYPE_INFO,
} from "./types";
import { useGetTransactionTypes, TransactionType } from "@/hooks/useGetTransactionTypes";
import { Loader2 } from "lucide-react";

interface TransactionTypeSelectorProps {
  selected: TransactionTypeCode | null;
  onSelect: (type: TransactionTypeCode) => void;
}

export function TransactionTypeSelector({
  selected,
  onSelect,
}: TransactionTypeSelectorProps) {
  // Don't block rendering on API call - show static data immediately
  const { data: transactionTypes } = useGetTransactionTypes();

  // Merge API data with static info - renders immediately with static data
  const types = Object.entries(TRANSACTION_TYPE_INFO).map(([code, info]) => {
    const apiData = transactionTypes?.find((t) => t.code === code);
    return {
      code: code as TransactionTypeCode,
      ...info,
      documentCount: apiData?.document_count,
      questionCount: apiData?.blueprint?.total_questions,
      priorityCounts: apiData?.priority_counts,
    };
  });

  return (
    <div className="grid grid-cols-3 md:grid-cols-5 gap-2">
      {types.map((type) => (
        <div
          key={type.code}
          className={cn(
            "cursor-pointer transition-all rounded-lg border px-2 py-1.5 flex items-center gap-1.5",
            selected === type.code
              ? "border-alchemyPrimaryOrange bg-orange-50 shadow-sm"
              : "border-gray-200 hover:border-gray-300 hover:bg-gray-50"
          )}
          onClick={() => onSelect(type.code)}
        >
          <span className="text-sm flex-shrink-0">{type.icon}</span>
          <span className="font-medium text-xs truncate">{type.name}</span>
        </div>
      ))}
    </div>
  );
}

interface BlueprintSummaryProps {
  transactionType: TransactionTypeCode;
}

export function BlueprintSummary({ transactionType }: BlueprintSummaryProps) {
  const { data: transactionTypes } = useGetTransactionTypes();
  const typeData = transactionTypes?.find((t) => t.code === transactionType);

  if (!typeData) return null;

  return (
    <div className="flex items-center gap-4 px-3 py-2 bg-gray-50 rounded-lg border border-gray-100">
      <span className="text-xl">{TRANSACTION_TYPE_INFO[transactionType]?.icon}</span>
      <span className="font-medium text-sm">{typeData.name}</span>
      <div className="flex gap-3 ml-auto text-xs">
        <span className="text-muted-foreground">
          <span className="font-semibold text-alchemyPrimaryOrange">{typeData.document_count}</span> docs
        </span>
        {typeData.blueprint && (
          <>
            <span className="text-muted-foreground">
              <span className="font-semibold text-alchemyPrimaryNavyBlue">{typeData.blueprint.risk_categories}</span> risk areas
            </span>
            <span className="text-muted-foreground">
              <span className="font-semibold text-alchemyPrimaryGoldenWeb">{typeData.blueprint.total_questions}</span> questions
            </span>
          </>
        )}
      </div>
    </div>
  );
}
