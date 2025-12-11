import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ExternalLink } from "lucide-react";

type SafliiCase = {
  name: string;
  url: string;
  description?: string;
  relevance?: string;
  citation?: string;
};

type SafliiPayload = {
  cases?: SafliiCase[];
  total?: number;
  search_summary?: string;
};

// Legacy (old LLM) item shape adapter (best-effort; old payload often had no URLs)
type LegacyItem = {
  title_of_precedent?: string;
  why_it_is_relevant?: string;
  url?: string;
};

// Normalize any backend payload (new or legacy) to a list of cases
function normalizeCases(input: any): { cases: SafliiCase[]; summary?: string } {
  if (!input) return { cases: [] };

  // New shape
  if (Array.isArray(input.cases)) {
    const cases: SafliiCase[] = input.cases
      .filter((c: any) => c && typeof c === "object")
      .map((c: any) => ({
        name: c.name ?? c.case_name ?? "Case",
        url: c.url ?? "",
        description: c.description ?? c.legal_principle ?? "",
        relevance: c.relevance ?? "",
        citation: c.citation ?? "",
      }));
    return { cases, summary: input.search_summary };
  }

  // Legacy fallback: combine both buckets if they exist
  const fromBucket = (arr?: LegacyItem[]) =>
    (Array.isArray(arr) ? arr : []).map((x) => ({
      name: x.title_of_precedent ?? "Case",
      url: x.url ?? "", // often missing in legacy payload
      description: x.why_it_is_relevant ?? "",
      relevance: x.why_it_is_relevant ?? "",
    }));

  const legacyCases = [
    ...fromBucket(input.other),
    ...fromBucket(input.companies_act_or_king_iv),
  ];

  return { cases: legacyCases, summary: undefined };
}

export default function PrecedentsListing({
  precedentData,
}: {
  precedentData?: SafliiPayload | any; // keep loose for backward-compat
}) {
  const { cases, summary } = normalizeCases(precedentData);

  if (!precedentData) {
    return (
      <div className="p-4 text-sm text-gray-600">No case law results yet.</div>
    );
  }

  return (
    <div className="p-4 space-y-3">
      {summary ? (
        <div className="text-sm text-gray-600 bg-muted/50 border rounded-md p-3">
          {summary}
        </div>
      ) : null}

      <div className="text-xs text-gray-500">
        {cases.length} result{cases.length === 1 ? "" : "s"} from SAFLII
      </div>

      <div className="max-h-[450px] overflow-y-auto pr-2">
        {cases.length === 0 ? (
          <div className="text-sm text-gray-600">No SAFLII cases found.</div>
        ) : (
          cases.map((item, idx) => (
            <Card key={item.url || idx} className="mb-4">
              <CardContent className="p-4 space-y-2">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <a
                      href={item.url || "#"}
                      target="_blank"
                      rel="noopener noreferrer"
                      className={`text-base font-semibold ${
                        item.url
                          ? "underline"
                          : "opacity-60 pointer-events-none"
                      }`}
                      title={item.url ? "Open on SAFLII" : "No URL available"}
                    >
                      {item.name}
                    </a>
                    {item.citation ? (
                      <div className="text-sm text-gray-600 mt-0.5">
                        {item.citation}
                      </div>
                    ) : null}
                  </div>

                  {item.url ? (
                    <Button asChild variant="outline" size="sm">
                      <a
                        href={item.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        title="Open on SAFLII"
                      >
                        <ExternalLink className="w-4 h-4 mr-2" />
                        Open
                      </a>
                    </Button>
                  ) : (
                    <Button variant="outline" size="sm" disabled>
                      <ExternalLink className="w-4 h-4 mr-2" />
                      No URL
                    </Button>
                  )}
                </div>

                {item.description ? (
                  <p className="text-sm text-gray-800">{item.description}</p>
                ) : null}

                {item.relevance ? (
                  <p className="text-sm text-gray-700">
                    <span className="font-medium">Why relevant: </span>
                    {item.relevance}
                  </p>
                ) : null}
              </CardContent>
            </Card>
          ))
        )}
      </div>
    </div>
  );
}
