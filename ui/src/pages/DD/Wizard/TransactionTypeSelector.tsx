import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
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
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
      {types.map((type) => (
        <Card
          key={type.code}
          className={cn(
            "cursor-pointer transition-all hover:shadow-md",
            selected === type.code
              ? "ring-2 ring-alchemyPrimaryOrange bg-orange-50"
              : "hover:bg-gray-50"
          )}
          onClick={() => onSelect(type.code)}
        >
          <CardContent className="p-4 text-center">
            <div className="text-3xl mb-2">{type.icon}</div>
            <h3 className="font-semibold text-sm">{type.name}</h3>
            <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
              {type.description}
            </p>
            {(type.documentCount || type.questionCount) && (
              <div className="flex gap-1 justify-center mt-2 flex-wrap">
                {type.documentCount && (
                  <Badge variant="secondary" className="text-xs">
                    {type.documentCount} docs
                  </Badge>
                )}
                {type.questionCount && (
                  <Badge variant="outline" className="text-xs">
                    {type.questionCount} Q's
                  </Badge>
                )}
              </div>
            )}
          </CardContent>
        </Card>
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
    <div className="bg-gray-50 rounded-lg p-4 mt-4">
      <div className="flex items-center gap-4">
        <div className="text-3xl">
          {TRANSACTION_TYPE_INFO[transactionType]?.icon}
        </div>
        <div className="flex-1">
          <h4 className="font-semibold">{typeData.name}</h4>
          <p className="text-sm text-muted-foreground">
            {typeData.blueprint?.description || TRANSACTION_TYPE_INFO[transactionType]?.description}
          </p>
        </div>
        <div className="flex gap-4 text-center">
          <div>
            <div className="text-2xl font-bold text-alchemyPrimaryOrange">
              {typeData.document_count}
            </div>
            <div className="text-xs text-muted-foreground">Expected Docs</div>
          </div>
          {typeData.blueprint && (
            <>
              <div>
                <div className="text-2xl font-bold text-alchemyPrimaryNavyBlue">
                  {typeData.blueprint.risk_categories}
                </div>
                <div className="text-xs text-muted-foreground">Risk Areas</div>
              </div>
              <div>
                <div className="text-2xl font-bold text-alchemyPrimaryGoldenWeb">
                  {typeData.blueprint.total_questions}
                </div>
                <div className="text-xs text-muted-foreground">Questions</div>
              </div>
            </>
          )}
        </div>
      </div>
      {typeData.priority_counts && (
        <div className="flex gap-2 mt-3">
          <Badge variant="destructive">
            {typeData.priority_counts.critical} Critical
          </Badge>
          <Badge variant="secondary">
            {typeData.priority_counts.required} Required
          </Badge>
          <Badge variant="outline">
            {typeData.priority_counts.recommended} Recommended
          </Badge>
        </div>
      )}
    </div>
  );
}
