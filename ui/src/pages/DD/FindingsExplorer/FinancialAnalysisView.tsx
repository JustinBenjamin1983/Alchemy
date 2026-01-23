/**
 * FinancialAnalysisView - Comprehensive Financial Analysis Display
 *
 * Based on the Financial DD Checklist with 6 major sections:
 * 1. Profitability & Performance (Margins, Returns, Revenue Quality)
 * 2. Liquidity & Solvency (Short-term Liquidity, Leverage & Debt Service)
 * 3. Cash Flow Health (OCF, Cash Conversion Cycle, Free Cash Flow)
 * 4. Quality of Earnings (Revenue Recognition, Expense Capitalisation, EBITDA Adjustments)
 * 5. Balance Sheet Integrity (Asset Quality, Off-Balance Sheet)
 * 6. Trend Analysis (Historical Performance, Seasonality, Forecast Credibility)
 */

import React, { useState } from 'react';
import { SynthesisData } from '@/hooks/useAnalysisRuns';

// Icons
const TrendUpIcon = () => (
  <svg className="w-4 h-4 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
  </svg>
);

const TrendDownIcon = () => (
  <svg className="w-4 h-4 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 17h8m0 0V9m0 8l-8-8-4 4-6-6" />
  </svg>
);

const TrendStableIcon = () => (
  <svg className="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14" />
  </svg>
);

const AlertIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
  </svg>
);

const ChartIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
  </svg>
);

const ChevronDownIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
  </svg>
);

interface FinancialAnalysisViewProps {
  synthesisData: SynthesisData;
}

// Helper functions
const formatCurrency = (amount: number | undefined, currency = 'ZAR') => {
  if (amount === undefined || amount === null) return '-';
  return new Intl.NumberFormat('en-ZA', {
    style: 'currency',
    currency: currency,
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  }).format(amount);
};

const formatPercent = (value: number | undefined) => {
  if (value === undefined || value === null) return '-';
  return `${value.toFixed(1)}%`;
};

const formatRatio = (value: number | undefined) => {
  if (value === undefined || value === null) return '-';
  return `${value.toFixed(2)}x`;
};

const getTrendIcon = (trend?: string) => {
  if (!trend) return <TrendStableIcon />;
  const lower = trend.toLowerCase();
  if (lower.includes('increas') || lower.includes('improv')) return <TrendUpIcon />;
  if (lower.includes('decreas') || lower.includes('declin') || lower.includes('deterior')) return <TrendDownIcon />;
  return <TrendStableIcon />;
};

const getSeverityBadge = (severity?: string) => {
  switch (severity) {
    case 'critical':
      return <span className="px-2 py-0.5 text-xs bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400 rounded font-medium">Critical</span>;
    case 'high':
      return <span className="px-2 py-0.5 text-xs bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400 rounded font-medium">High</span>;
    case 'medium':
      return <span className="px-2 py-0.5 text-xs bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400 rounded font-medium">Medium</span>;
    default:
      return null;
  }
};

const getFlagColor = (flag?: string) => {
  if (!flag) return 'text-gray-500';
  const lower = flag.toLowerCase();
  if (lower.includes('critical') || lower.includes('concern') || lower.includes('significant')) return 'text-red-600 dark:text-red-400';
  if (lower.includes('warning') || lower.includes('moderate')) return 'text-amber-600 dark:text-amber-400';
  return 'text-green-600 dark:text-green-400';
};

// Collapsible Section Component
const Section: React.FC<{
  title: string;
  icon: React.ReactNode;
  children: React.ReactNode;
  defaultOpen?: boolean;
  count?: number;
  color?: 'blue' | 'green' | 'purple' | 'amber' | 'red';
}> = ({ title, icon, children, defaultOpen = true, count, color = 'blue' }) => {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  const colorClasses = {
    blue: 'border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-900/10',
    green: 'border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-900/10',
    purple: 'border-purple-200 dark:border-purple-800 bg-purple-50 dark:bg-purple-900/10',
    amber: 'border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-900/10',
    red: 'border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/10',
  };

  const iconColorClasses = {
    blue: 'text-blue-600 dark:text-blue-400',
    green: 'text-green-600 dark:text-green-400',
    purple: 'text-purple-600 dark:text-purple-400',
    amber: 'text-amber-600 dark:text-amber-400',
    red: 'text-red-600 dark:text-red-400',
  };

  return (
    <div className={`rounded-lg border ${colorClasses[color]}`}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between p-4 hover:bg-white/50 dark:hover:bg-gray-800/50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <span className={iconColorClasses[color]}>{icon}</span>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">{title}</h3>
          {count !== undefined && (
            <span className="px-2 py-0.5 text-xs bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-300 rounded-full">
              {count}
            </span>
          )}
        </div>
        <ChevronDownIcon className={`w-5 h-5 text-gray-500 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>
      {isOpen && <div className="px-4 pb-4">{children}</div>}
    </div>
  );
};

// Metric Row Component
const MetricRow: React.FC<{
  label: string;
  value: React.ReactNode;
  notes?: string;
  trend?: string;
  isRatio?: boolean;
}> = ({ label, value, notes, trend, isRatio }) => (
  <div className="flex justify-between items-center py-2 border-b border-gray-200/50 dark:border-gray-700/50 last:border-0">
    <span className="text-sm text-gray-600 dark:text-gray-400">{label}</span>
    <div className="flex items-center gap-2">
      <span className={`text-sm font-medium ${notes ? getFlagColor(notes) : 'text-gray-900 dark:text-gray-100'}`}>
        {value}
      </span>
      {trend && getTrendIcon(trend)}
    </div>
  </div>
);

// Card Component
const Card: React.FC<{ title: string; children: React.ReactNode; className?: string }> = ({ title, children, className = '' }) => (
  <div className={`bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4 ${className}`}>
    <h4 className="font-semibold text-gray-900 dark:text-gray-100 mb-3 text-sm uppercase tracking-wider">{title}</h4>
    {children}
  </div>
);

export const FinancialAnalysisView: React.FC<FinancialAnalysisViewProps> = ({ synthesisData }) => {
  const analysis = synthesisData.financial_analysis;

  if (!analysis || Object.keys(analysis).length === 0) {
    return (
      <div className="flex items-center justify-center h-64 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-300 dark:border-gray-600">
        <div className="text-center">
          <div className="text-blue-500 mb-2"><ChartIcon /></div>
          <p className="text-gray-600 dark:text-gray-400">No financial analysis available</p>
          <p className="text-sm text-gray-400 dark:text-gray-500">
            Financial analysis will be generated when financial documents are included in the DD
          </p>
        </div>
      </div>
    );
  }

  const pp = analysis.profitability_performance;
  const ls = analysis.liquidity_solvency;
  const cf = analysis.cash_flow_health;
  const qe = analysis.quality_of_earnings;
  const bs = analysis.balance_sheet_integrity;
  const ta = analysis.trend_analysis;

  return (
    <div className="space-y-6">
      {/* Overview */}
      {analysis.overview && (
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-300 dark:border-gray-600 p-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4 flex items-center gap-2">
            <span className="text-blue-500"><ChartIcon /></span>
            Financial Overview
          </h3>
          <p className="text-gray-700 dark:text-gray-300 whitespace-pre-wrap leading-relaxed">
            {analysis.overview}
          </p>
        </div>
      )}

      {/* 1. Profitability & Performance */}
      {pp && (
        <Section title="1. Profitability & Performance" icon={<ChartIcon />} color="blue">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Margin Analysis */}
            {pp.margin_analysis && (
              <Card title="Margin Analysis">
                {pp.margin_analysis.gross_margin && (
                  <MetricRow
                    label="Gross Margin"
                    value={formatPercent(pp.margin_analysis.gross_margin.current)}
                    trend={pp.margin_analysis.gross_margin.trend}
                  />
                )}
                {pp.margin_analysis.operating_margin && (
                  <MetricRow
                    label="Operating Margin"
                    value={formatPercent(pp.margin_analysis.operating_margin.current)}
                    trend={pp.margin_analysis.operating_margin.trend}
                  />
                )}
                {pp.margin_analysis.ebitda_margin && (
                  <MetricRow
                    label="EBITDA Margin"
                    value={formatPercent(pp.margin_analysis.ebitda_margin.current)}
                    trend={pp.margin_analysis.ebitda_margin.trend}
                  />
                )}
                {pp.margin_analysis.net_margin && (
                  <MetricRow
                    label="Net Margin"
                    value={formatPercent(pp.margin_analysis.net_margin.current)}
                    trend={pp.margin_analysis.net_margin.trend}
                  />
                )}
                {pp.margin_analysis.notes && (
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-3 pt-2 border-t border-gray-200 dark:border-gray-700">
                    {pp.margin_analysis.notes}
                  </p>
                )}
              </Card>
            )}

            {/* Return Metrics */}
            {pp.return_metrics && (
              <Card title="Return Metrics">
                <MetricRow label="ROE (Return on Equity)" value={formatPercent(pp.return_metrics.roe)} />
                <MetricRow label="ROA (Return on Assets)" value={formatPercent(pp.return_metrics.roa)} />
                <MetricRow label="ROIC (Return on Invested Capital)" value={formatPercent(pp.return_metrics.roic)} />
                {pp.return_metrics.notes && (
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-3 pt-2 border-t border-gray-200 dark:border-gray-700">
                    {pp.return_metrics.notes}
                  </p>
                )}
              </Card>
            )}

            {/* Revenue Quality */}
            {pp.revenue_quality && (
              <Card title="Revenue Quality">
                <MetricRow label="Recurring Revenue %" value={formatPercent(pp.revenue_quality.recurring_vs_one_off_pct)} />
                {pp.revenue_quality.customer_concentration && (
                  <>
                    <MetricRow
                      label="Top Customer %"
                      value={formatPercent(pp.revenue_quality.customer_concentration.top_customer_pct)}
                      notes={pp.revenue_quality.customer_concentration.flag}
                    />
                    <MetricRow
                      label="Top 5 Customers %"
                      value={formatPercent(pp.revenue_quality.customer_concentration.top_5_customers_pct)}
                    />
                  </>
                )}
                {pp.revenue_quality.contract_backlog !== undefined && (
                  <MetricRow label="Contract Backlog" value={formatCurrency(pp.revenue_quality.contract_backlog)} />
                )}
                {pp.revenue_quality.geographic_concentration && (
                  <p className="text-xs text-gray-600 dark:text-gray-400 mt-2">
                    <span className="font-medium">Geographic:</span> {pp.revenue_quality.geographic_concentration}
                  </p>
                )}
                {pp.revenue_quality.notes && (
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-3 pt-2 border-t border-gray-200 dark:border-gray-700">
                    {pp.revenue_quality.notes}
                  </p>
                )}
              </Card>
            )}
          </div>
        </Section>
      )}

      {/* 2. Liquidity & Solvency */}
      {ls && (
        <Section title="2. Liquidity & Solvency" icon={<ChartIcon />} color="green">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Short-term Liquidity */}
            {ls.short_term_liquidity && (
              <Card title="Short-term Liquidity">
                <MetricRow label="Current Ratio" value={formatRatio(ls.short_term_liquidity.current_ratio)} />
                <MetricRow label="Quick Ratio (Acid Test)" value={formatRatio(ls.short_term_liquidity.quick_ratio)} />
                <MetricRow label="Cash Ratio" value={formatRatio(ls.short_term_liquidity.cash_ratio)} />
                <MetricRow label="Net Working Capital" value={formatCurrency(ls.short_term_liquidity.net_working_capital)} />
                {ls.short_term_liquidity.notes && (
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-3 pt-2 border-t border-gray-200 dark:border-gray-700">
                    {ls.short_term_liquidity.notes}
                  </p>
                )}
              </Card>
            )}

            {/* Leverage & Debt Service */}
            {ls.leverage_debt_service && (
              <Card title="Leverage & Debt Service">
                <MetricRow label="Debt-to-Equity" value={formatRatio(ls.leverage_debt_service.debt_to_equity)} />
                <MetricRow label="Net Debt / EBITDA" value={formatRatio(ls.leverage_debt_service.net_debt_to_ebitda)} />
                <MetricRow label="Interest Coverage" value={formatRatio(ls.leverage_debt_service.interest_coverage)} />
                {ls.leverage_debt_service.covenant_compliance && (
                  <MetricRow
                    label="Covenant Compliance"
                    value={ls.leverage_debt_service.covenant_compliance.in_compliance ? 'Yes' : 'No'}
                    notes={ls.leverage_debt_service.covenant_compliance.in_compliance ? '' : 'concern'}
                  />
                )}
                {ls.leverage_debt_service.debt_maturity_profile && (
                  <p className="text-xs text-gray-600 dark:text-gray-400 mt-2">
                    <span className="font-medium">Maturity Profile:</span> {ls.leverage_debt_service.debt_maturity_profile}
                  </p>
                )}
                {ls.leverage_debt_service.notes && (
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-3 pt-2 border-t border-gray-200 dark:border-gray-700">
                    {ls.leverage_debt_service.notes}
                  </p>
                )}
              </Card>
            )}
          </div>
        </Section>
      )}

      {/* 3. Cash Flow Health */}
      {cf && (
        <Section title="3. Cash Flow Health" icon={<ChartIcon />} color="purple">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Operating Cash Flow */}
            {cf.operating_cash_flow && (
              <Card title="Operating Cash Flow">
                <MetricRow label="OCF (Current)" value={formatCurrency(cf.operating_cash_flow.ocf_current)} />
                <MetricRow label="OCF (Prior)" value={formatCurrency(cf.operating_cash_flow.ocf_prior)} />
                {cf.operating_cash_flow.ocf_vs_net_income && (
                  <div className="mt-2">
                    <span className="text-xs font-medium text-gray-600 dark:text-gray-400">OCF vs Net Income:</span>
                    <p className={`text-xs mt-1 ${getFlagColor(cf.operating_cash_flow.ocf_vs_net_income)}`}>
                      {cf.operating_cash_flow.ocf_vs_net_income}
                    </p>
                  </div>
                )}
                {cf.operating_cash_flow.notes && (
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-3 pt-2 border-t border-gray-200 dark:border-gray-700">
                    {cf.operating_cash_flow.notes}
                  </p>
                )}
              </Card>
            )}

            {/* Cash Conversion Cycle */}
            {cf.cash_conversion_cycle && (
              <Card title="Cash Conversion Cycle">
                <MetricRow label="DSO (Days Sales Outstanding)" value={`${cf.cash_conversion_cycle.dso || '-'} days`} />
                <MetricRow label="DIO (Days Inventory Outstanding)" value={`${cf.cash_conversion_cycle.dio || '-'} days`} />
                <MetricRow label="DPO (Days Payables Outstanding)" value={`${cf.cash_conversion_cycle.dpo || '-'} days`} />
                <MetricRow
                  label="Total CCC"
                  value={`${cf.cash_conversion_cycle.total_ccc_days || '-'} days`}
                  trend={cf.cash_conversion_cycle.ccc_trend}
                />
                {cf.cash_conversion_cycle.notes && (
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-3 pt-2 border-t border-gray-200 dark:border-gray-700">
                    {cf.cash_conversion_cycle.notes}
                  </p>
                )}
              </Card>
            )}

            {/* Free Cash Flow */}
            {cf.free_cash_flow && (
              <Card title="Free Cash Flow & CapEx">
                <MetricRow label="Free Cash Flow" value={formatCurrency(cf.free_cash_flow.fcf_current)} />
                <MetricRow label="CapEx (Maintenance)" value={formatCurrency(cf.free_cash_flow.capex_maintenance)} />
                <MetricRow label="CapEx (Growth)" value={formatCurrency(cf.free_cash_flow.capex_growth)} />
                <MetricRow label="Dividend Coverage" value={formatRatio(cf.free_cash_flow.dividend_coverage_ratio)} />
                {cf.free_cash_flow.notes && (
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-3 pt-2 border-t border-gray-200 dark:border-gray-700">
                    {cf.free_cash_flow.notes}
                  </p>
                )}
              </Card>
            )}
          </div>
        </Section>
      )}

      {/* 4. Quality of Earnings */}
      {qe && (
        <Section title="4. Quality of Earnings" icon={<ChartIcon />} color="amber">
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Revenue Recognition */}
              {qe.revenue_recognition && (
                <Card title="Revenue Recognition">
                  <MetricRow
                    label="Policy Assessment"
                    value={qe.revenue_recognition.policy_assessment || '-'}
                    notes={qe.revenue_recognition.policy_assessment}
                  />
                  {qe.revenue_recognition.accrued_unbilled_revenue_trend && (
                    <MetricRow
                      label="Accrued/Unbilled AR Trend"
                      value={qe.revenue_recognition.accrued_unbilled_revenue_trend}
                      notes={qe.revenue_recognition.accrued_unbilled_revenue_trend}
                    />
                  )}
                  {qe.revenue_recognition.deferred_revenue_trend && (
                    <MetricRow
                      label="Deferred Revenue Trend"
                      value={qe.revenue_recognition.deferred_revenue_trend}
                      notes={qe.revenue_recognition.deferred_revenue_trend}
                    />
                  )}
                  {qe.revenue_recognition.notes && (
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-3 pt-2 border-t border-gray-200 dark:border-gray-700">
                      {qe.revenue_recognition.notes}
                    </p>
                  )}
                </Card>
              )}

              {/* Expense Capitalisation */}
              {qe.expense_capitalisation && (
                <Card title="Expense Capitalisation">
                  <MetricRow
                    label="Capitalised Costs Concern"
                    value={qe.expense_capitalisation.capitalised_costs_concern ? 'Yes' : 'No'}
                    notes={qe.expense_capitalisation.capitalised_costs_concern ? 'concern' : ''}
                  />
                  <MetricRow
                    label="R&D Capitalisation Rate"
                    value={formatPercent(qe.expense_capitalisation.rd_capitalisation_rate)}
                  />
                  {qe.expense_capitalisation.depreciation_policy && (
                    <MetricRow
                      label="Depreciation Policy"
                      value={qe.expense_capitalisation.depreciation_policy}
                      notes={qe.expense_capitalisation.depreciation_policy}
                    />
                  )}
                  {qe.expense_capitalisation.notes && (
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-3 pt-2 border-t border-gray-200 dark:border-gray-700">
                      {qe.expense_capitalisation.notes}
                    </p>
                  )}
                </Card>
              )}
            </div>

            {/* EBITDA Adjustments */}
            {qe.ebitda_adjustments && qe.ebitda_adjustments.length > 0 && (
              <Card title="EBITDA Adjustments / Normalization">
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                    <thead>
                      <tr>
                        <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Adjustment</th>
                        <th className="px-3 py-2 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Amount</th>
                        <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Assessment</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                      {qe.ebitda_adjustments.map((adj, idx) => (
                        <tr key={idx}>
                          <td className="px-3 py-2 text-sm text-gray-900 dark:text-gray-100">{adj.adjustment_type}</td>
                          <td className="px-3 py-2 text-sm text-right text-gray-700 dark:text-gray-300">{formatCurrency(adj.amount)}</td>
                          <td className={`px-3 py-2 text-sm ${getFlagColor(adj.assessment)}`}>{adj.assessment}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>
            )}

            {/* Related Party Transactions */}
            {qe.related_party_transactions && qe.related_party_transactions.length > 0 && (
              <Card title="Related Party Transactions">
                <div className="space-y-2">
                  {qe.related_party_transactions.map((rpt, idx) => (
                    <div key={idx} className="p-2 bg-gray-50 dark:bg-gray-700/50 rounded">
                      <div className="flex justify-between items-start">
                        <span className="text-sm text-gray-900 dark:text-gray-100">{rpt.description}</span>
                        <span className="text-sm text-gray-600 dark:text-gray-400">{formatCurrency(rpt.amount)}</span>
                      </div>
                      {rpt.assessment && (
                        <p className={`text-xs mt-1 ${getFlagColor(rpt.assessment)}`}>{rpt.assessment}</p>
                      )}
                    </div>
                  ))}
                </div>
              </Card>
            )}

            {/* Owner Adjustments */}
            {qe.owner_adjustments && (qe.owner_adjustments.above_market_compensation || qe.owner_adjustments.personal_expenses_through_business) && (
              <Card title="Owner / Management Adjustments">
                <MetricRow label="Above-Market Compensation" value={formatCurrency(qe.owner_adjustments.above_market_compensation)} />
                <MetricRow label="Personal Expenses Through Business" value={formatCurrency(qe.owner_adjustments.personal_expenses_through_business)} />
                {qe.owner_adjustments.notes && (
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-3 pt-2 border-t border-gray-200 dark:border-gray-700">
                    {qe.owner_adjustments.notes}
                  </p>
                )}
              </Card>
            )}
          </div>
        </Section>
      )}

      {/* 5. Balance Sheet Integrity */}
      {bs && (
        <Section title="5. Balance Sheet Integrity" icon={<ChartIcon />} color="blue">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Asset Quality */}
            {bs.asset_quality && (
              <Card title="Asset Quality">
                <MetricRow label="Goodwill / Equity %" value={formatPercent(bs.asset_quality.goodwill_to_equity_pct)} />
                {bs.asset_quality.receivables_aging_concern && (
                  <MetricRow
                    label="Receivables Aging"
                    value={bs.asset_quality.receivables_aging_concern}
                    notes={bs.asset_quality.receivables_aging_concern}
                  />
                )}
                {bs.asset_quality.inventory_obsolescence_risk && (
                  <MetricRow
                    label="Inventory Obsolescence"
                    value={bs.asset_quality.inventory_obsolescence_risk}
                    notes={bs.asset_quality.inventory_obsolescence_risk}
                  />
                )}
                {bs.asset_quality.ppe_condition && (
                  <MetricRow
                    label="PPE Condition"
                    value={bs.asset_quality.ppe_condition}
                    notes={bs.asset_quality.ppe_condition}
                  />
                )}
                {bs.asset_quality.intercompany_balances_concern && (
                  <MetricRow
                    label="Intercompany Balances"
                    value={bs.asset_quality.intercompany_balances_concern}
                    notes={bs.asset_quality.intercompany_balances_concern}
                  />
                )}
                {bs.asset_quality.notes && (
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-3 pt-2 border-t border-gray-200 dark:border-gray-700">
                    {bs.asset_quality.notes}
                  </p>
                )}
              </Card>
            )}

            {/* Off-Balance Sheet */}
            {bs.off_balance_sheet && (
              <Card title="Off-Balance Sheet Items">
                <MetricRow label="Operating Lease Commitments" value={formatCurrency(bs.off_balance_sheet.operating_lease_commitments)} />
                <MetricRow label="Guarantees & Commitments" value={formatCurrency(bs.off_balance_sheet.guarantees_and_commitments)} />
                {bs.off_balance_sheet.factoring_securitisation && (
                  <MetricRow
                    label="Factoring/Securitisation"
                    value={bs.off_balance_sheet.factoring_securitisation}
                    notes={bs.off_balance_sheet.factoring_securitisation}
                  />
                )}
                {bs.off_balance_sheet.contingent_liabilities && bs.off_balance_sheet.contingent_liabilities.length > 0 && (
                  <div className="mt-3 pt-2 border-t border-gray-200 dark:border-gray-700">
                    <p className="text-xs font-medium text-gray-600 dark:text-gray-400 mb-2">Contingent Liabilities:</p>
                    {bs.off_balance_sheet.contingent_liabilities.map((cl, idx) => (
                      <div key={idx} className="text-xs p-2 bg-gray-50 dark:bg-gray-700/50 rounded mb-1">
                        <div className="flex justify-between">
                          <span className="text-gray-900 dark:text-gray-100">{cl.description}</span>
                          <span className="text-gray-600 dark:text-gray-400">{formatCurrency(cl.amount)}</span>
                        </div>
                        {cl.probability && (
                          <span className={`text-xs ${cl.probability === 'Probable' ? 'text-red-600' : cl.probability === 'Possible' ? 'text-amber-600' : 'text-gray-500'}`}>
                            {cl.probability}
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                )}
                {bs.off_balance_sheet.notes && (
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-3 pt-2 border-t border-gray-200 dark:border-gray-700">
                    {bs.off_balance_sheet.notes}
                  </p>
                )}
              </Card>
            )}
          </div>
        </Section>
      )}

      {/* 6. Trend Analysis */}
      {ta && (
        <Section title="6. Trend Analysis & Benchmarking" icon={<ChartIcon />} color="purple">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Historical Performance */}
            {ta.historical_performance && (
              <Card title="Historical Performance">
                <MetricRow label="Revenue 3yr CAGR" value={formatPercent(ta.historical_performance.revenue_3yr_cagr)} />
                <MetricRow label="EBITDA 3yr CAGR" value={formatPercent(ta.historical_performance.ebitda_3yr_cagr)} />
                {ta.historical_performance.inflection_points && ta.historical_performance.inflection_points.length > 0 && (
                  <div className="mt-2">
                    <p className="text-xs font-medium text-gray-600 dark:text-gray-400">Inflection Points:</p>
                    <ul className="text-xs text-gray-500 dark:text-gray-400 mt-1 list-disc list-inside">
                      {ta.historical_performance.inflection_points.map((point, idx) => (
                        <li key={idx}>{point}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {ta.historical_performance.notes && (
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-3 pt-2 border-t border-gray-200 dark:border-gray-700">
                    {ta.historical_performance.notes}
                  </p>
                )}
              </Card>
            )}

            {/* Seasonality */}
            {ta.seasonality_patterns && (
              <Card title="Seasonality Patterns">
                {ta.seasonality_patterns.quarterly_pattern && (
                  <MetricRow label="Quarterly Pattern" value={ta.seasonality_patterns.quarterly_pattern} />
                )}
                <MetricRow
                  label="Hockey-Stick Risk"
                  value={ta.seasonality_patterns.hockey_stick_risk ? 'Yes' : 'No'}
                  notes={ta.seasonality_patterns.hockey_stick_risk ? 'warning' : ''}
                />
                {ta.seasonality_patterns.notes && (
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-3 pt-2 border-t border-gray-200 dark:border-gray-700">
                    {ta.seasonality_patterns.notes}
                  </p>
                )}
              </Card>
            )}

            {/* Forecast Credibility */}
            {ta.forecast_credibility && (
              <Card title="Forecast Credibility">
                {ta.forecast_credibility.historical_accuracy && (
                  <MetricRow
                    label="Historical Accuracy"
                    value={ta.forecast_credibility.historical_accuracy}
                    notes={ta.forecast_credibility.historical_accuracy}
                  />
                )}
                {ta.forecast_credibility.budget_variance_pattern && (
                  <MetricRow
                    label="Budget Variance Pattern"
                    value={ta.forecast_credibility.budget_variance_pattern}
                    notes={ta.forecast_credibility.budget_variance_pattern}
                  />
                )}
                {ta.forecast_credibility.notes && (
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-3 pt-2 border-t border-gray-200 dark:border-gray-700">
                    {ta.forecast_credibility.notes}
                  </p>
                )}
              </Card>
            )}
          </div>
        </Section>
      )}

      {/* Red Flags Summary */}
      {analysis.red_flags_summary && analysis.red_flags_summary.length > 0 && (
        <Section title="Red Flags Summary" icon={<AlertIcon />} color="red" count={analysis.red_flags_summary.length}>
          <div className="space-y-3">
            {analysis.red_flags_summary.map((flag, idx) => (
              <div key={idx} className="p-4 bg-white dark:bg-gray-800 rounded-lg border border-red-200 dark:border-red-700">
                <div className="flex items-start gap-3">
                  {getSeverityBadge(flag.severity)}
                  {flag.category && (
                    <span className="px-2 py-0.5 text-xs bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300 rounded">
                      {flag.category}
                    </span>
                  )}
                </div>
                <p className="font-medium text-gray-900 dark:text-gray-100 mt-2">{flag.flag}</p>
                {flag.impact && (
                  <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                    <span className="font-medium">Impact:</span> {flag.impact}
                  </p>
                )}
                {flag.source && (
                  <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">Source: {flag.source}</p>
                )}
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* Data Gaps */}
      {analysis.data_gaps && analysis.data_gaps.length > 0 && (
        <Section title="Data Gaps & Missing Information" icon={<AlertIcon />} color="amber" count={analysis.data_gaps.length}>
          <div className="space-y-2">
            {analysis.data_gaps.map((gap, idx) => (
              <div key={idx} className="flex items-start gap-3 p-3 bg-white dark:bg-gray-800 rounded-lg border border-amber-200 dark:border-amber-700">
                {getSeverityBadge(gap.importance)}
                <div className="flex-1">
                  <p className="font-medium text-gray-900 dark:text-gray-100">{gap.missing_item}</p>
                  {gap.impact && (
                    <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">{gap.impact}</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </Section>
      )}
    </div>
  );
};

export default FinancialAnalysisView;
