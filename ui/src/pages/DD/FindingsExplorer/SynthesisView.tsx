/**
 * SynthesisView - Display synthesis data from Pass 4
 *
 * Renders different views based on the selected tab:
 * - Executive Summary
 * - Deal Assessment
 * - Financial Exposures
 * - Deal Blockers
 * - Conditions Precedent
 * - Recommendations
 */

import React from 'react';
import { SynthesisData } from '@/hooks/useAnalysisRuns';

// Icons
const CheckCircleIcon = () => (
  <svg className="w-5 h-5 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

const XCircleIcon = () => (
  <svg className="w-5 h-5 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

const AlertTriangleIcon = () => (
  <svg className="w-5 h-5 text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
  </svg>
);

const CurrencyIcon = () => (
  <svg className="w-5 h-5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

const ClipboardListIcon = () => (
  <svg className="w-5 h-5 text-purple-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
  </svg>
);

const LightBulbIcon = () => (
  <svg className="w-5 h-5 text-yellow-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
  </svg>
);

type SynthesisTab =
  | 'executive_summary'
  | 'deal_assessment'
  | 'financial_exposures'
  | 'deal_blockers'
  | 'conditions_precedent'
  | 'warranties'
  | 'indemnities'
  | 'recommendations';

// Shield icon for warranties
const ShieldCheckIcon = () => (
  <svg className="w-5 h-5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
  </svg>
);

// Document warning icon for indemnities
const DocumentShieldIcon = () => (
  <svg className="w-5 h-5 text-orange-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
  </svg>
);

interface SynthesisViewProps {
  activeTab: SynthesisTab | string;
  synthesisData: SynthesisData;
}

export const SynthesisView: React.FC<SynthesisViewProps> = ({
  activeTab,
  synthesisData
}) => {
  // Format currency
  const formatCurrency = (amount: number, currency = 'ZAR') => {
    return new Intl.NumberFormat('en-ZA', {
      style: 'currency',
      currency: currency,
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(amount);
  };

  // Risk rating badge
  const getRiskBadge = (rating?: string) => {
    const colors = {
      high: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
      medium: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400',
      low: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400'
    };
    return colors[rating as keyof typeof colors] || colors.medium;
  };

  // Executive Summary View
  if (activeTab === 'executive_summary') {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="mb-6">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-slate-800 mb-2">
            Executive Summary
          </h2>
          <p className="text-sm text-gray-500 dark:text-slate-600">
            AI-generated summary of the due diligence analysis
          </p>
        </div>
        <div className="bg-white dark:bg-slate-300 rounded-lg border border-gray-300 dark:border-slate-400 p-6">
          <div className="prose dark:prose-invert max-w-none">
            {synthesisData.executive_summary ? (
              <p className="text-gray-700 dark:text-slate-700 whitespace-pre-wrap leading-relaxed">
                {synthesisData.executive_summary}
              </p>
            ) : (
              <p className="text-gray-400 italic">No executive summary available</p>
            )}
          </div>
        </div>
      </div>
    );
  }

  // Deal Assessment View
  if (activeTab === 'deal_assessment') {
    const assessment = synthesisData.deal_assessment || {};
    return (
      <div className="max-w-4xl mx-auto">
        <div className="mb-6">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-slate-800 mb-2">
            Deal Assessment
          </h2>
          <p className="text-sm text-gray-500 dark:text-slate-600">
            Overall assessment of the transaction viability
          </p>
        </div>

        {/* Can Proceed Card */}
        <div className={`mb-6 p-6 rounded-lg border-2 ${
          assessment.can_proceed
            ? 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800'
            : 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800'
        }`}>
          <div className="flex items-center gap-3 mb-2">
            {assessment.can_proceed ? <CheckCircleIcon /> : <XCircleIcon />}
            <span className="text-lg font-semibold">
              {assessment.can_proceed ? 'Transaction Can Proceed' : 'Transaction Cannot Proceed'}
            </span>
          </div>
          {assessment.overall_risk_rating && (
            <span className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${getRiskBadge(assessment.overall_risk_rating)}`}>
              {assessment.overall_risk_rating.toUpperCase()} RISK
            </span>
          )}
        </div>

        {/* Blocking Issues */}
        {assessment.blocking_issues && assessment.blocking_issues.length > 0 && (
          <div className="mb-6 bg-white dark:bg-slate-300 rounded-lg border border-gray-300 dark:border-slate-400 p-6">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-slate-800 mb-4 flex items-center gap-2">
              <AlertTriangleIcon />
              Blocking Issues
            </h3>
            <ul className="space-y-3">
              {assessment.blocking_issues.map((issue, index) => (
                <li key={index} className="flex items-start gap-3 p-3 bg-red-50 dark:bg-red-900/20 rounded-lg">
                  <span className="flex-shrink-0 w-6 h-6 flex items-center justify-center bg-red-100 dark:bg-red-800 text-red-700 dark:text-red-300 rounded-full text-sm font-medium">
                    {index + 1}
                  </span>
                  <span className="text-gray-700 dark:text-slate-700">{issue}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Key Risks */}
        {assessment.key_risks && assessment.key_risks.length > 0 && (
          <div className="bg-white dark:bg-slate-300 rounded-lg border border-gray-300 dark:border-slate-400 p-6">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-slate-800 mb-4">
              Key Risks
            </h3>
            <ul className="space-y-2">
              {assessment.key_risks.map((risk, index) => (
                <li key={index} className="flex items-start gap-3 text-gray-700 dark:text-slate-700">
                  <span className="flex-shrink-0 w-2 h-2 mt-2 bg-amber-500 rounded-full" />
                  {risk}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    );
  }

  // Financial Exposures View
  if (activeTab === 'financial_exposures') {
    const exposures = synthesisData.financial_exposures || {};
    return (
      <div className="max-w-4xl mx-auto">
        <div className="mb-6">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-slate-800 mb-2">
            Financial Exposures
          </h2>
          <p className="text-sm text-gray-500 dark:text-slate-600">
            Quantified financial risks and exposures
          </p>
        </div>

        {/* Total Exposure Card */}
        <div className="mb-6 p-6 bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
          <div className="flex items-center gap-3 mb-2">
            <CurrencyIcon />
            <span className="text-sm text-gray-600 dark:text-slate-600">Total Exposure</span>
          </div>
          <span className="text-3xl font-bold text-gray-900 dark:text-slate-800">
            {formatCurrency(exposures.total || 0, exposures.currency)}
          </span>
        </div>

        {/* Exposure Items */}
        {exposures.items && exposures.items.length > 0 && (
          <div className="bg-white dark:bg-slate-300 rounded-lg border border-gray-300 dark:border-slate-400 overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead className="bg-gray-100 dark:bg-slate-400/50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-slate-600 uppercase tracking-wider">Source</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-slate-600 uppercase tracking-wider">Type</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-slate-600 uppercase tracking-wider">Amount</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-slate-600 uppercase tracking-wider">Risk Level</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {exposures.items.map((item, index) => (
                  <tr key={index} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                    <td className="px-6 py-4 text-sm text-gray-900 dark:text-slate-800">{item.source}</td>
                    <td className="px-6 py-4 text-sm text-gray-600 dark:text-slate-600">{item.type}</td>
                    <td className="px-6 py-4 text-sm text-right font-medium text-gray-900 dark:text-slate-800">
                      {formatCurrency(item.amount, exposures.currency)}
                    </td>
                    <td className="px-6 py-4">
                      <span className={`inline-block px-2 py-1 rounded text-xs font-medium ${getRiskBadge(item.risk_level)}`}>
                        {item.risk_level}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Calculation Notes */}
        {exposures.calculation_notes && exposures.calculation_notes.length > 0 && (
          <div className="mt-6 p-4 bg-gray-50 dark:bg-slate-300/50 rounded-lg">
            <h4 className="text-sm font-medium text-gray-700 dark:text-slate-700 mb-2">Calculation Notes</h4>
            <ul className="text-sm text-gray-600 dark:text-slate-600 space-y-1">
              {exposures.calculation_notes.map((note, index) => (
                <li key={index}>• {note}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    );
  }

  // Deal Blockers View
  if (activeTab === 'deal_blockers') {
    const blockers = synthesisData.deal_blockers || [];
    return (
      <div className="max-w-4xl mx-auto">
        <div className="mb-6">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-slate-800 mb-2">
            Deal Blockers
          </h2>
          <p className="text-sm text-gray-500 dark:text-slate-600">
            Issues that must be resolved before the transaction can proceed
          </p>
        </div>

        {blockers.length === 0 ? (
          <div className="p-6 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-800 text-center">
            <CheckCircleIcon />
            <p className="mt-2 text-green-700 dark:text-green-400 font-medium">No deal blockers identified</p>
          </div>
        ) : (
          <div className="space-y-4">
            {blockers.map((blocker, index) => (
              <div key={index} className="bg-white dark:bg-slate-300 rounded-lg border border-red-200 dark:border-red-800 overflow-hidden">
                <div className="px-6 py-4 bg-red-50 dark:bg-red-900/20 border-b border-red-200 dark:border-red-800">
                  <div className="flex items-center gap-2">
                    <AlertTriangleIcon />
                    <h3 className="font-semibold text-gray-900 dark:text-slate-800">
                      {blocker.issue || blocker.description || `Blocker ${index + 1}`}
                    </h3>
                  </div>
                </div>
                <div className="px-6 py-4 space-y-3">
                  {blocker.source && (
                    <div>
                      <span className="text-xs text-gray-500 dark:text-slate-600 uppercase tracking-wider">Source</span>
                      <p className="text-sm text-gray-700 dark:text-slate-700">{blocker.source}</p>
                    </div>
                  )}
                  {blocker.why_blocking && (
                    <div>
                      <span className="text-xs text-gray-500 dark:text-slate-600 uppercase tracking-wider">Why Blocking</span>
                      <p className="text-sm text-gray-700 dark:text-slate-700">{blocker.why_blocking}</p>
                    </div>
                  )}
                  {blocker.resolution_path && (
                    <div>
                      <span className="text-xs text-gray-500 dark:text-slate-600 uppercase tracking-wider">Resolution Path</span>
                      <p className="text-sm text-gray-700 dark:text-slate-700">{blocker.resolution_path}</p>
                    </div>
                  )}
                  <div className="flex gap-4 text-sm">
                    {blocker.resolution_timeline && (
                      <span className="text-gray-600 dark:text-slate-600">
                        Timeline: <span className="font-medium">{blocker.resolution_timeline}</span>
                      </span>
                    )}
                    {blocker.owner && (
                      <span className="text-gray-600 dark:text-slate-600">
                        Owner: <span className="font-medium">{blocker.owner}</span>
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  // Conditions Precedent View
  if (activeTab === 'conditions_precedent') {
    const cps = synthesisData.conditions_precedent || [];
    return (
      <div className="max-w-4xl mx-auto">
        <div className="mb-6">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-slate-800 mb-2">
            Conditions Precedent Register
          </h2>
          <p className="text-sm text-gray-500 dark:text-slate-600">
            Actions and conditions that must be satisfied before closing
          </p>
        </div>

        {cps.length === 0 ? (
          <div className="p-6 bg-gray-50 dark:bg-slate-300 rounded-lg border border-gray-300 dark:border-slate-400 text-center">
            <ClipboardListIcon />
            <p className="mt-2 text-gray-600 dark:text-slate-600">No conditions precedent identified</p>
          </div>
        ) : (
          <div className="bg-white dark:bg-slate-300 rounded-lg border border-gray-300 dark:border-slate-400 overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead className="bg-gray-100 dark:bg-slate-400/50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-slate-600 uppercase tracking-wider w-12">#</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-slate-600 uppercase tracking-wider">Description</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-slate-600 uppercase tracking-wider">Category</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-slate-600 uppercase tracking-wider">Responsible</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-slate-600 uppercase tracking-wider">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {cps.map((cp, index) => (
                  <tr key={index} className={`hover:bg-gray-50 dark:hover:bg-gray-700/50 ${cp.is_deal_blocker ? 'bg-red-50/50 dark:bg-red-900/10' : ''}`}>
                    <td className="px-4 py-4 text-sm font-medium text-gray-900 dark:text-slate-800">
                      {cp.cp_number || index + 1}
                    </td>
                    <td className="px-4 py-4 text-sm text-gray-700 dark:text-slate-700">
                      {cp.description}
                      {cp.is_deal_blocker && (
                        <span className="ml-2 inline-block px-2 py-0.5 text-xs bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 rounded">
                          Deal Blocker
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-4 text-sm text-gray-600 dark:text-slate-600">{cp.category}</td>
                    <td className="px-4 py-4 text-sm text-gray-600 dark:text-slate-600">{cp.responsible_party}</td>
                    <td className="px-4 py-4">
                      <span className={`inline-block px-2 py-1 rounded text-xs font-medium ${
                        cp.status === 'complete' ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400' :
                        cp.status === 'in_progress' ? 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400' :
                        'bg-gray-100 text-gray-800 dark:bg-slate-400 dark:text-slate-600'
                      }`}>
                        {cp.status || 'not_started'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    );
  }

  // Warranties Register View
  if (activeTab === 'warranties') {
    const warranties = synthesisData.warranties_register || [];

    // Priority badge helper
    const getPriorityBadge = (priority?: string) => {
      const colors = {
        critical: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
        high: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400',
        medium: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400'
      };
      return colors[priority as keyof typeof colors] || colors.medium;
    };

    return (
      <div className="max-w-5xl mx-auto">
        <div className="mb-6">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-slate-800 mb-2 flex items-center gap-2">
            <ShieldCheckIcon />
            Warranties Register
          </h2>
          <p className="text-sm text-gray-500 dark:text-slate-600">
            Recommended warranties to protect the client based on DD findings
          </p>
        </div>

        {warranties.length === 0 ? (
          <div className="p-6 bg-gray-50 dark:bg-slate-300 rounded-lg border border-gray-300 dark:border-slate-400 text-center">
            <ShieldCheckIcon />
            <p className="mt-2 text-gray-600 dark:text-slate-600">No warranties identified yet</p>
            <p className="mt-1 text-sm text-gray-400 dark:text-gray-500">
              Warranties will be generated based on the DD analysis findings
            </p>
          </div>
        ) : (
          <div className="bg-white dark:bg-slate-300 rounded-lg border border-gray-300 dark:border-slate-400 overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead className="bg-gray-100 dark:bg-slate-400/50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-slate-600 uppercase tracking-wider w-12">#</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-slate-600 uppercase tracking-wider">Category</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-slate-600 uppercase tracking-wider">Description</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-slate-600 uppercase tracking-wider">Cap / Survival</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-slate-600 uppercase tracking-wider">Priority</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {warranties.map((warranty, index) => (
                  <tr key={index} className={`hover:bg-gray-50 dark:hover:bg-gray-700/50 ${warranty.is_fundamental ? 'bg-blue-50/50 dark:bg-blue-900/10' : ''}`}>
                    <td className="px-4 py-4 text-sm font-medium text-gray-900 dark:text-slate-800">
                      {warranty.warranty_number || index + 1}
                    </td>
                    <td className="px-4 py-4 text-sm text-gray-700 dark:text-slate-700">
                      <span className="font-medium">{warranty.category}</span>
                      {warranty.is_fundamental && (
                        <span className="ml-2 inline-block px-2 py-0.5 text-xs bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 rounded">
                          Fundamental
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-4 text-sm text-gray-600 dark:text-slate-600">
                      <p>{warranty.description}</p>
                      {warranty.source_finding && (
                        <p className="mt-1 text-xs text-gray-400">Source: {warranty.source_finding}</p>
                      )}
                    </td>
                    <td className="px-4 py-4 text-sm text-gray-600 dark:text-slate-600">
                      <div>{warranty.typical_cap || '-'}</div>
                      <div className="text-xs text-gray-400">{warranty.survival_period || '-'}</div>
                    </td>
                    <td className="px-4 py-4">
                      <span className={`inline-block px-2 py-1 rounded text-xs font-medium ${getPriorityBadge(warranty.priority)}`}>
                        {warranty.priority || 'medium'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Summary Stats */}
        {warranties.length > 0 && (
          <div className="mt-6 grid grid-cols-3 gap-4">
            <div className="p-4 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800">
              <div className="text-2xl font-bold text-red-700 dark:text-red-400">
                {warranties.filter(w => w.priority === 'critical').length}
              </div>
              <div className="text-sm text-red-600 dark:text-red-400">Critical Priority</div>
            </div>
            <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
              <div className="text-2xl font-bold text-blue-700 dark:text-blue-400">
                {warranties.filter(w => w.is_fundamental).length}
              </div>
              <div className="text-sm text-blue-600 dark:text-blue-400">Fundamental Warranties</div>
            </div>
            <div className="p-4 bg-gray-50 dark:bg-slate-300 rounded-lg border border-gray-300 dark:border-slate-400">
              <div className="text-2xl font-bold text-gray-700 dark:text-slate-700">
                {warranties.length}
              </div>
              <div className="text-sm text-gray-600 dark:text-slate-600">Total Warranties</div>
            </div>
          </div>
        )}
      </div>
    );
  }

  // Indemnities Register View
  if (activeTab === 'indemnities') {
    const indemnities = synthesisData.indemnities_register || [];

    // Priority badge helper
    const getPriorityBadge = (priority?: string) => {
      const colors = {
        critical: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
        high: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400',
        medium: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400'
      };
      return colors[priority as keyof typeof colors] || colors.medium;
    };

    return (
      <div className="max-w-5xl mx-auto">
        <div className="mb-6">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-slate-800 mb-2 flex items-center gap-2">
            <DocumentShieldIcon />
            Indemnities Register
          </h2>
          <p className="text-sm text-gray-500 dark:text-slate-600">
            Recommended indemnities to protect the client based on DD risk findings
          </p>
        </div>

        {indemnities.length === 0 ? (
          <div className="p-6 bg-gray-50 dark:bg-slate-300 rounded-lg border border-gray-300 dark:border-slate-400 text-center">
            <DocumentShieldIcon />
            <p className="mt-2 text-gray-600 dark:text-slate-600">No indemnities identified yet</p>
            <p className="mt-1 text-sm text-gray-400 dark:text-gray-500">
              Indemnities will be generated based on specific risks identified in DD
            </p>
          </div>
        ) : (
          <div className="bg-white dark:bg-slate-300 rounded-lg border border-gray-300 dark:border-slate-400 overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead className="bg-gray-100 dark:bg-slate-400/50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-slate-600 uppercase tracking-wider w-12">#</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-slate-600 uppercase tracking-wider">Category</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-slate-600 uppercase tracking-wider">Description</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-slate-600 uppercase tracking-wider">Trigger / Exposure</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-slate-600 uppercase tracking-wider">Cap / Survival</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-slate-600 uppercase tracking-wider">Priority</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {indemnities.map((indemnity, index) => (
                  <tr key={index} className={`hover:bg-gray-50 dark:hover:bg-gray-700/50 ${indemnity.escrow_recommendation ? 'bg-orange-50/50 dark:bg-orange-900/10' : ''}`}>
                    <td className="px-4 py-4 text-sm font-medium text-gray-900 dark:text-slate-800">
                      {indemnity.indemnity_number || index + 1}
                    </td>
                    <td className="px-4 py-4 text-sm text-gray-700 dark:text-slate-700">
                      <span className="font-medium">{indemnity.category}</span>
                      {indemnity.escrow_recommendation && (
                        <span className="ml-2 inline-block px-2 py-0.5 text-xs bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-400 rounded">
                          Escrow
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-4 text-sm text-gray-600 dark:text-slate-600">
                      <p>{indemnity.description}</p>
                      {indemnity.source_finding && (
                        <p className="mt-1 text-xs text-gray-400">Source: {indemnity.source_finding}</p>
                      )}
                    </td>
                    <td className="px-4 py-4 text-sm text-gray-600 dark:text-slate-600">
                      {indemnity.trigger_event && (
                        <div className="text-xs text-gray-500 mb-1">Trigger: {indemnity.trigger_event}</div>
                      )}
                      {indemnity.quantified_exposure && (
                        <div className="font-medium text-amber-600 dark:text-amber-400">{indemnity.quantified_exposure}</div>
                      )}
                    </td>
                    <td className="px-4 py-4 text-sm text-gray-600 dark:text-slate-600">
                      <div>{indemnity.typical_cap || '-'}</div>
                      <div className="text-xs text-gray-400">{indemnity.survival_period || '-'}</div>
                    </td>
                    <td className="px-4 py-4">
                      <span className={`inline-block px-2 py-1 rounded text-xs font-medium ${getPriorityBadge(indemnity.priority)}`}>
                        {indemnity.priority || 'medium'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Summary Stats */}
        {indemnities.length > 0 && (
          <div className="mt-6 grid grid-cols-3 gap-4">
            <div className="p-4 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800">
              <div className="text-2xl font-bold text-red-700 dark:text-red-400">
                {indemnities.filter(i => i.priority === 'critical').length}
              </div>
              <div className="text-sm text-red-600 dark:text-red-400">Critical Priority</div>
            </div>
            <div className="p-4 bg-orange-50 dark:bg-orange-900/20 rounded-lg border border-orange-200 dark:border-orange-800">
              <div className="text-2xl font-bold text-orange-700 dark:text-orange-400">
                {indemnities.filter(i => i.escrow_recommendation).length}
              </div>
              <div className="text-sm text-orange-600 dark:text-orange-400">Escrow Recommended</div>
            </div>
            <div className="p-4 bg-gray-50 dark:bg-slate-300 rounded-lg border border-gray-300 dark:border-slate-400">
              <div className="text-2xl font-bold text-gray-700 dark:text-slate-700">
                {indemnities.length}
              </div>
              <div className="text-sm text-gray-600 dark:text-slate-600">Total Indemnities</div>
            </div>
          </div>
        )}
      </div>
    );
  }

  // Recommendations View
  if (activeTab === 'recommendations') {
    const recommendations = synthesisData.recommendations || [];
    return (
      <div className="max-w-4xl mx-auto">
        <div className="mb-6">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-slate-800 mb-2">
            Key Recommendations
          </h2>
          <p className="text-sm text-gray-500 dark:text-slate-600">
            Recommended actions for the transaction team
          </p>
        </div>

        {recommendations.length === 0 ? (
          <div className="p-6 bg-gray-50 dark:bg-slate-300 rounded-lg border border-gray-300 dark:border-slate-400 text-center">
            <LightBulbIcon />
            <p className="mt-2 text-gray-600 dark:text-slate-600">No recommendations available</p>
          </div>
        ) : (
          <div className="space-y-4">
            {recommendations.map((rec, index) => (
              <div key={index} className="flex items-start gap-4 p-4 bg-white dark:bg-slate-300 rounded-lg border border-gray-300 dark:border-slate-400">
                <div className="flex-shrink-0 w-8 h-8 flex items-center justify-center bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400 rounded-full font-semibold">
                  {index + 1}
                </div>
                <p className="text-gray-700 dark:text-slate-700 pt-1">{rec}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  // Fallback
  return (
    <div className="text-center text-gray-500 dark:text-slate-600 py-12">
      Select a view from the dropdown
    </div>
  );
};
