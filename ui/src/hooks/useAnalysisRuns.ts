import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAxiosWithAuth } from "./useAxiosWithAuth";
import { reactQueryDefaults } from "./reactQuerySetup";

// Synthesis data from Pass 4
export interface SynthesisData {
  executive_summary: string;
  deal_assessment: {
    can_proceed?: boolean;
    blocking_issues?: string[];
    key_risks?: string[];
    overall_risk_rating?: "high" | "medium" | "low";
  };
  financial_exposures: {
    items?: Array<{
      source: string;
      type: string;
      amount: number;
      calculation: string;
      triggered_by: string;
      risk_level: string;
    }>;
    total?: number;
    currency?: string;
    calculation_notes?: string[];
  };
  // Comprehensive financial analysis from synthesis (based on Financial DD Checklist)
  financial_analysis?: {
    overview?: string;

    // 1. Profitability & Performance
    profitability_performance?: {
      margin_analysis?: {
        gross_margin?: { current?: number; prior?: number; trend?: string };
        operating_margin?: { current?: number; prior?: number; trend?: string };
        ebitda_margin?: { current?: number; prior?: number; trend?: string };
        net_margin?: { current?: number; prior?: number; trend?: string };
        notes?: string;
      };
      return_metrics?: {
        roe?: number;
        roa?: number;
        roic?: number;
        notes?: string;
      };
      revenue_quality?: {
        recurring_vs_one_off_pct?: number;
        customer_concentration?: {
          top_customer_pct?: number;
          top_5_customers_pct?: number;
          flag?: string;
        };
        geographic_concentration?: string;
        contract_backlog?: number;
        notes?: string;
      };
    };

    // 2. Liquidity & Solvency
    liquidity_solvency?: {
      short_term_liquidity?: {
        current_ratio?: number;
        quick_ratio?: number;
        cash_ratio?: number;
        net_working_capital?: number;
        notes?: string;
      };
      leverage_debt_service?: {
        debt_to_equity?: number;
        net_debt_to_ebitda?: number;
        interest_coverage?: number;
        debt_maturity_profile?: string;
        covenant_compliance?: {
          in_compliance?: boolean;
          headroom_pct?: number;
          historical_breaches?: string;
        };
        notes?: string;
      };
    };

    // 3. Cash Flow Health
    cash_flow_health?: {
      operating_cash_flow?: {
        ocf_current?: number;
        ocf_prior?: number;
        ocf_vs_net_income?: string;
        notes?: string;
      };
      cash_conversion_cycle?: {
        dso?: number;
        dio?: number;
        dpo?: number;
        total_ccc_days?: number;
        ccc_trend?: string;
        notes?: string;
      };
      free_cash_flow?: {
        fcf_current?: number;
        capex_maintenance?: number;
        capex_growth?: number;
        dividend_coverage_ratio?: number;
        notes?: string;
      };
    };

    // 4. Quality of Earnings
    quality_of_earnings?: {
      revenue_recognition?: {
        policy_assessment?: string;
        accrued_unbilled_revenue_trend?: string;
        deferred_revenue_trend?: string;
        notes?: string;
      };
      expense_capitalisation?: {
        capitalised_costs_concern?: boolean;
        rd_capitalisation_rate?: number;
        depreciation_policy?: string;
        notes?: string;
      };
      ebitda_adjustments?: Array<{
        adjustment_type?: string;
        amount?: number;
        assessment?: string;
        notes?: string;
      }>;
      related_party_transactions?: Array<{
        description?: string;
        amount?: number;
        assessment?: string;
      }>;
      owner_adjustments?: {
        above_market_compensation?: number;
        personal_expenses_through_business?: number;
        notes?: string;
      };
    };

    // 5. Balance Sheet Integrity
    balance_sheet_integrity?: {
      asset_quality?: {
        goodwill_to_equity_pct?: number;
        receivables_aging_concern?: string;
        inventory_obsolescence_risk?: string;
        ppe_condition?: string;
        intercompany_balances_concern?: string;
        notes?: string;
      };
      off_balance_sheet?: {
        operating_lease_commitments?: number;
        guarantees_and_commitments?: number;
        contingent_liabilities?: Array<{
          description?: string;
          amount?: number;
          probability?: string;
          notes?: string;
        }>;
        factoring_securitisation?: string;
        notes?: string;
      };
    };

    // 6. Trend Analysis
    trend_analysis?: {
      historical_performance?: {
        revenue_3yr_cagr?: number;
        ebitda_3yr_cagr?: number;
        inflection_points?: string[];
        notes?: string;
      };
      seasonality_patterns?: {
        quarterly_pattern?: string;
        hockey_stick_risk?: boolean;
        notes?: string;
      };
      forecast_credibility?: {
        historical_accuracy?: string;
        budget_variance_pattern?: string;
        notes?: string;
      };
    };

    // Summary sections
    red_flags_summary?: Array<{
      category?: string;
      flag?: string;
      severity?: "critical" | "high" | "medium";
      source?: string;
      impact?: string;
    }>;

    data_gaps?: Array<{
      missing_item?: string;
      importance?: "critical" | "high" | "medium";
      impact?: string;
    }>;
  };
  deal_blockers: Array<{
    issue?: string;
    description?: string;
    source?: string;
    why_blocking?: string;
    resolution_path?: string;
    resolution_timeline?: string;
    owner?: string;
    severity?: string;
    deal_impact?: string;
  }>;
  conditions_precedent: Array<{
    cp_number?: number;
    description?: string;
    category?: string;
    source?: string;
    responsible_party?: string;
    target_date?: string;
    status?: string;
    is_deal_blocker?: boolean;
  }>;
  // Warranties register - recommended warranties for client protection
  warranties_register?: Array<{
    warranty_number?: number;
    category?: string;
    description?: string;
    detailed_wording?: string;
    from_party?: string;
    to_party?: string;
    source_finding?: string;
    typical_cap?: string;
    survival_period?: string;
    priority?: "critical" | "high" | "medium";
    is_fundamental?: boolean;
    disclosure_required?: string;
  }>;
  // Indemnities register - recommended indemnities based on DD findings
  indemnities_register?: Array<{
    indemnity_number?: number;
    category?: string;
    description?: string;
    detailed_wording?: string;
    from_party?: string;
    to_party?: string;
    trigger_event?: string;
    source_finding?: string;
    quantified_exposure?: string;
    typical_cap?: string;
    survival_period?: string;
    priority?: "critical" | "high" | "medium";
    escrow_recommendation?: string;
  }>;
  recommendations: string[];
  // Blueprint Q&A pairs from document analysis
  blueprint_qa?: Array<{
    question: string;
    answer: string;
    finding_refs?: string[];
    source_document: string;
    folder_category?: string;
    document_id?: string;
  }>;
}

export interface AnalysisRun {
  run_id: string;
  dd_id: string;
  run_number: number;
  name: string;
  status: "pending" | "processing" | "completed" | "failed";
  selected_documents: { id: string; name: string }[];
  total_documents: number;
  documents_processed: number;
  findings_total: number;
  findings_critical: number;
  findings_high: number;
  findings_medium: number;
  findings_low: number;
  estimated_cost_usd: number;
  created_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  last_error: string | null;
  // Token/cost tracking
  total_tokens?: number;
  total_cost?: number;
  // Synthesis data from Pass 4
  synthesis_data?: SynthesisData | null;
}

interface RunsListResponse {
  runs: AnalysisRun[];
}

interface CreateRunResponse {
  run_id: string;
  dd_id: string;
  run_number: number;
  name: string;
  status: string;
  selected_document_ids: string[];
  total_documents: number;
  created_at: string;
}

// Hook to list all runs for a DD
export function useAnalysisRunsList(ddId: string | undefined, enabled = true) {
  const axios = useAxiosWithAuth();

  return useQuery<RunsListResponse>({
    queryKey: ["analysis-runs", ddId],
    queryFn: async () => {
      const { data } = await axios({
        url: `/dd-analysis-run-list?dd_id=${ddId}`,
        method: "GET",
      });
      return data;
    },
    enabled: !!ddId && enabled,
    refetchInterval: 10000, // Refresh every 10 seconds to catch status changes
    ...reactQueryDefaults,
  });
}

// Hook to create a new run
export function useCreateAnalysisRun() {
  const axios = useAxiosWithAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      ddId,
      selectedDocumentIds,
    }: {
      ddId: string;
      selectedDocumentIds: string[];
    }): Promise<CreateRunResponse> => {
      const { data } = await axios({
        url: "/dd-analysis-run-create",
        method: "POST",
        data: {
          dd_id: ddId,
          selected_document_ids: selectedDocumentIds,
        },
      });
      return data;
    },
    onSuccess: (data) => {
      // Invalidate the runs list to refresh
      queryClient.invalidateQueries({ queryKey: ["analysis-runs", data.dd_id] });
    },
  });
}

// Hook to update run name
export function useUpdateAnalysisRun() {
  const axios = useAxiosWithAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      runId,
      name,
    }: {
      runId: string;
      name: string;
    }) => {
      const { data } = await axios({
        url: "/dd-analysis-run-update",
        method: "POST",
        data: {
          run_id: runId,
          name: name,
        },
      });
      return data;
    },
    onSuccess: () => {
      // Invalidate all runs queries to refresh
      queryClient.invalidateQueries({ queryKey: ["analysis-runs"] });
    },
  });
}

// Hook to delete a run
export function useDeleteAnalysisRun() {
  const axios = useAxiosWithAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (runId: string) => {
      const { data } = await axios({
        url: "/dd-analysis-run-delete",
        method: "POST",
        data: {
          run_id: runId,
        },
      });
      return data;
    },
    onSuccess: () => {
      // Invalidate all runs queries to refresh
      queryClient.invalidateQueries({ queryKey: ["analysis-runs"] });
    },
  });
}

// Hook to start processing for a run
export function useStartRunProcessing() {
  const axios = useAxiosWithAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (runId: string) => {
      const { data } = await axios({
        url: `/dd-process-enhanced-start?run_id=${runId}`,
        method: "POST",
      });
      return data;
    },
    onSuccess: () => {
      // Invalidate runs to refresh status
      queryClient.invalidateQueries({ queryKey: ["analysis-runs"] });
    },
  });
}
