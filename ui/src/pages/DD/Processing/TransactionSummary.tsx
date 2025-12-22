/**
 * Transaction Summary Component
 *
 * Displays the transaction context configured in the wizard.
 * Shows how this context influences the DD analysis.
 */
import React, { useState } from "react";
import {
  Building2,
  Users,
  Target,
  Calendar,
  DollarSign,
  FileText,
  Info,
  ChevronDown,
  ChevronRight,
  AlertTriangle,
  UserCheck,
  Truck,
  ShoppingCart,
  Landmark,
  Scale,
  MoreHorizontal,
  PieChart,
} from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { TRANSACTION_TYPE_INFO, TransactionTypeCode } from "../Wizard/types";

interface ProjectSetup {
  transactionType: string | null;
  transactionName: string;
  clientName: string;
  targetEntityName: string;
  clientRole: string | null;
  dealStructure: string | null;
  estimatedValue: number | null;
  targetClosingDate: string | null;
  dealRationale: string;
  knownConcerns: string[];
  criticalPriorities: string[];
  knownDealBreakers: string[];
  deprioritizedAreas: string[];
  targetCompanyName: string;
  keyIndividuals: string[];
  keySuppliers: string[];
  keyCustomers: Array<{ name: string; description: string; exposure: string }>;
  keyLenders: Array<{ name: string; description: string; facilityAmount: string }>;
  keyRegulators: string[];
  keyOther: Array<{ name: string; role: string }>;
  shareholderEntityName: string;
  shareholders: Array<{ name: string; percentage: number | null }>;
}

interface TransactionSummaryProps {
  briefing: string | null;
  name: string;
  isCollapsed?: boolean;
  onToggleCollapse?: () => void;
  className?: string;
  transactionTypeCode?: string | null;
  projectSetup?: ProjectSetup | null;
}

interface ParsedBriefing {
  transactionType: string;
  clientName: string;
  targetEntity: string;
  clientRole: string;
  dealStructure: string;
  estimatedValue: string;
  targetClosing: string;
  dealRationale: string;
  knownConcerns: string;
  criticalPriorities: string;
  knownDealBreakers: string;
  deprioritizedAreas: string;
  keyIndividuals: string;
  keySuppliers: string;
  keyCustomers: string;
  keyLenders: string;
  keyRegulators: string;
  keyOther: string;
  shareholderEntity: string;
  shareholders: string;
}

function parseBriefing(briefing: string | null): ParsedBriefing {
  const defaults: ParsedBriefing = {
    transactionType: "Not specified",
    clientName: "Not specified",
    targetEntity: "Not specified",
    clientRole: "Not specified",
    dealStructure: "Not specified",
    estimatedValue: "Not specified",
    targetClosing: "Not specified",
    dealRationale: "Not provided",
    knownConcerns: "None specified",
    criticalPriorities: "None specified",
    knownDealBreakers: "None specified",
    deprioritizedAreas: "None specified",
    keyIndividuals: "None specified",
    keySuppliers: "None specified",
    keyCustomers: "None specified",
    keyLenders: "None specified",
    keyRegulators: "None specified",
    keyOther: "None specified",
    shareholderEntity: "None specified",
    shareholders: "None specified",
  };

  if (!briefing) return defaults;

  const extract = (label: string): string => {
    const regex = new RegExp(`${label}:\\s*(.+?)(?=\\n|$)`, "i");
    const match = briefing.match(regex);
    return match?.[1]?.trim() || defaults[label as keyof ParsedBriefing] || "Not specified";
  };

  return {
    transactionType: extract("Transaction Type"),
    clientName: extract("Client Name"),
    targetEntity: extract("Target Entity"),
    clientRole: extract("Client Role"),
    dealStructure: extract("Deal Structure"),
    estimatedValue: extract("Estimated Value"),
    targetClosing: extract("Target Closing"),
    dealRationale: extract("Deal Rationale"),
    knownConcerns: extract("Known Concerns"),
    criticalPriorities: extract("Critical Priorities"),
    knownDealBreakers: extract("Known Deal Breakers"),
    deprioritizedAreas: extract("Deprioritized Areas"),
    keyIndividuals: extract("Key Individuals"),
    keySuppliers: extract("Key Suppliers"),
    keyCustomers: extract("Key Customers"),
    keyLenders: extract("Key Lenders"),
    keyRegulators: extract("Key Regulators"),
    keyOther: extract("Other Stakeholders"),
    shareholderEntity: extract("Shareholder Entity"),
    shareholders: extract("Shareholders"),
  };
}

// Convert projectSetup to ParsedBriefing format (more reliable than parsing briefing string)
function projectSetupToParsed(setup: ProjectSetup): ParsedBriefing {
  const formatValue = (val: number | null) => val ? `R${val.toLocaleString("en-ZA")}` : "Not specified";
  const formatDate = (date: string | null) => {
    if (!date) return "Not specified";
    try {
      return new Date(date).toLocaleDateString("en-ZA", { timeZone: "Africa/Johannesburg" });
    } catch {
      return date;
    }
  };

  return {
    transactionType: setup.transactionType || "Not specified",
    clientName: setup.clientName || "Not specified",
    targetEntity: setup.targetEntityName || "Not specified",
    clientRole: setup.clientRole || "Not specified",
    dealStructure: setup.dealStructure || "Not specified",
    estimatedValue: formatValue(setup.estimatedValue),
    targetClosing: formatDate(setup.targetClosingDate),
    dealRationale: setup.dealRationale || "Not provided",
    knownConcerns: setup.knownConcerns?.length > 0 ? setup.knownConcerns.join(", ") : "None specified",
    criticalPriorities: setup.criticalPriorities?.length > 0 ? setup.criticalPriorities.join(", ") : "None specified",
    knownDealBreakers: setup.knownDealBreakers?.length > 0 ? setup.knownDealBreakers.join(", ") : "None specified",
    deprioritizedAreas: setup.deprioritizedAreas?.length > 0 ? setup.deprioritizedAreas.join(", ") : "None specified",
    keyIndividuals: setup.keyIndividuals?.length > 0 ? setup.keyIndividuals.join(", ") : "None specified",
    keySuppliers: setup.keySuppliers?.length > 0 ? setup.keySuppliers.join(", ") : "None specified",
    keyCustomers: setup.keyCustomers?.length > 0
      ? setup.keyCustomers.map(c => c.name + (c.description ? ` (${c.description})` : "") + (c.exposure ? ` - ${c.exposure}` : "")).join("; ")
      : "None specified",
    keyLenders: setup.keyLenders?.length > 0
      ? setup.keyLenders.map(l => l.name + (l.description ? ` (${l.description})` : "") + (l.facilityAmount ? ` - ${l.facilityAmount}` : "")).join("; ")
      : "None specified",
    keyRegulators: setup.keyRegulators?.length > 0 ? setup.keyRegulators.join(", ") : "None specified",
    keyOther: setup.keyOther?.length > 0
      ? setup.keyOther.map(o => o.name + (o.role ? ` (${o.role})` : "")).join("; ")
      : "None specified",
    shareholderEntity: setup.shareholderEntityName || "None specified",
    shareholders: setup.shareholders?.filter(s => s.name)?.length > 0
      ? setup.shareholders.filter(s => s.name).map(s => s.name + (s.percentage ? ` (${s.percentage}%)` : "")).join(", ")
      : "None specified",
  };
}

// Helper to render a list of items as badges (for short items)
function renderBadgeList(items: string, emptyText: string = "None", delimiter: string = ",") {
  if (!items || items === "None specified" || items === "Not specified") {
    return <span className="text-xs text-gray-400 italic">{emptyText}</span>;
  }
  const itemList = items.split(delimiter).map((s) => s.trim()).filter(Boolean);
  if (itemList.length === 0) {
    return <span className="text-xs text-gray-400 italic">{emptyText}</span>;
  }
  return (
    <div className="flex flex-wrap gap-1">
      {itemList.map((item, idx) => (
        <Badge key={idx} variant="secondary" className="text-xs py-0 px-1.5">
          {item}
        </Badge>
      ))}
    </div>
  );
}

// Helper to render stakeholders with detailed info (name, description, amount) as a clean list
function renderStakeholderList(items: string, delimiter: string = ";") {
  if (!items || items === "None specified" || items === "Not specified") {
    return <span className="text-xs text-gray-400 italic">None</span>;
  }
  const itemList = items.split(delimiter).map((s) => s.trim()).filter(Boolean);
  if (itemList.length === 0) {
    return <span className="text-xs text-gray-400 italic">None</span>;
  }
  return (
    <div className="space-y-1.5">
      {itemList.map((item, idx) => {
        // Parse item: "Name (Description) - Amount" format
        const amountMatch = item.match(/^(.+?)\s*-\s*([R$][\d,\s]+(?:\d{3})*)$/);
        const descMatch = item.match(/^([^(]+)\s*\(([^)]+)\)/);

        let name = item;
        let description = "";
        let amount = "";

        if (amountMatch) {
          const beforeAmount = amountMatch[1].trim();
          amount = amountMatch[2].trim();
          // Check if there's a description in the name part
          const innerDescMatch = beforeAmount.match(/^([^(]+)\s*\(([^)]+)\)/);
          if (innerDescMatch) {
            name = innerDescMatch[1].trim();
            description = innerDescMatch[2].trim();
          } else {
            name = beforeAmount;
          }
        } else if (descMatch) {
          name = descMatch[1].trim();
          description = descMatch[2].trim();
        }

        return (
          <div
            key={idx}
            className="bg-gray-50 dark:bg-gray-700/50 rounded-lg px-2.5 py-1.5 text-xs"
          >
            <div className="font-medium text-gray-800 dark:text-gray-200">{name}</div>
            {description && (
              <div className="text-gray-500 dark:text-gray-400 text-[11px]">{description}</div>
            )}
            {amount && (
              <div className="text-blue-600 dark:text-blue-400 font-medium mt-0.5">{amount}</div>
            )}
          </div>
        );
      })}
    </div>
  );
}

const CONTEXT_TOOLTIP = `This transaction context shapes the DD analysis in several ways:

• Transaction Type selects the appropriate legal blueprint with transaction-specific risk categories, legislation, and deal blocker definitions

• Client Name & Target Entity help the AI identify relevant parties across all documents

• Critical Priorities elevate certain questions to Tier 1, ensuring they're analysed first and in depth

• Known Deal Breakers are flagged with higher severity when found in documents

• Deprioritized Areas reduce focus on less relevant questions, optimising analysis time

• Key Stakeholders help identify individuals, suppliers, customers, lenders, and regulators mentioned in documents`;

export const TransactionSummary: React.FC<TransactionSummaryProps> = ({
  briefing,
  name,
  isCollapsed = false,
  onToggleCollapse,
  className = "",
  transactionTypeCode,
  projectSetup,
}) => {
  // State to control expanded/collapsed details sections
  const [isDetailsExpanded, setIsDetailsExpanded] = useState(false);

  // Use projectSetup if available (more reliable), otherwise fall back to parsing briefing
  const parsed = projectSetup ? projectSetupToParsed(projectSetup) : parseBriefing(briefing);

  // Check if there are any details to show in the expandable section
  const hasExpandableDetails =
    parsed.dealRationale !== "Not provided" ||
    parsed.criticalPriorities !== "None specified" ||
    parsed.knownDealBreakers !== "None specified" ||
    parsed.knownConcerns !== "None specified" ||
    parsed.deprioritizedAreas !== "None specified" ||
    parsed.keyIndividuals !== "None specified" ||
    parsed.keySuppliers !== "None specified" ||
    parsed.keyCustomers !== "None specified" ||
    parsed.keyLenders !== "None specified" ||
    parsed.keyRegulators !== "None specified" ||
    parsed.keyOther !== "None specified" ||
    parsed.shareholderEntity !== "None specified" ||
    parsed.shareholders !== "None specified";

  // Get transaction type info from the code (if provided) or fall back to parsed briefing
  const typeCode = transactionTypeCode as TransactionTypeCode | undefined;
  const typeInfo = typeCode ? TRANSACTION_TYPE_INFO[typeCode] : null;

  const formatTransactionType = (type: string): string => {
    return type
      .replace(/_/g, " ")
      .replace(/\b\w/g, (c) => c.toUpperCase());
  };

  const formatClientRole = (role: string): string => {
    const roleMap: Record<string, string> = {
      // M&A / Corporate
      buyer: "Buyer / Acquirer",
      seller: "Seller / Vendor",
      target: "Target Company",
      advisor: "Independent Advisor",
      // Mining
      acquirer: "Acquirer / Purchaser",
      joint_venture_partner: "Joint Venture Partner",
      // Banking & Finance
      lender: "Lender / Financier",
      borrower: "Borrower",
      guarantor: "Guarantor / Security Provider",
      arranger: "Arranger / Agent",
      // Real Estate
      tenant: "Tenant / Lessee",
      landlord: "Landlord / Lessor",
      developer: "Developer",
      // Competition
      acquiring_firm: "Acquiring Firm",
      target_firm: "Target Firm",
      merging_party: "Merging Party",
      // Employment
      employer: "Employer",
      acquiring_employer: "Acquiring Employer",
      transferring_employer: "Transferring Employer",
      // BEE
      bee_partner: "BEE Partner / Investor",
      // Energy & Infrastructure
      investor: "Investor / Financier",
      offtaker: "Offtaker / PPA Counterparty",
      epc_contractor: "EPC Contractor",
      concessionaire: "Concessionaire / SPV",
      government: "Government / Public Authority",
      // Capital Markets
      issuer: "Issuer",
      underwriter: "Underwriter / Sponsor",
      selling_shareholder: "Selling Shareholder",
      // Restructuring
      debtor: "Debtor / Company in Distress",
      creditor: "Creditor",
      practitioner: "Business Rescue Practitioner",
      // Private Equity
      management: "Management Team",
      // Financial Services
      regulator_liaison: "Regulatory Liaison",
    };
    return roleMap[role?.toLowerCase()] || role;
  };

  const formatDealStructure = (structure: string): string => {
    const structureMap: Record<string, string> = {
      // M&A / Corporate
      share_purchase: "Share Purchase",
      asset_purchase: "Asset Purchase",
      merger: "Merger",
      scheme: "Scheme of Arrangement",
      // Mining
      mining_right_transfer: "Mining Right Transfer",
      joint_venture: "Joint Venture",
      farm_in: "Farm-In Agreement",
      // Banking & Finance
      term_loan: "Term Loan Facility",
      revolving_credit: "Revolving Credit Facility",
      syndicated_loan: "Syndicated Loan",
      project_finance: "Project Finance",
      acquisition_finance: "Acquisition Finance",
      debt_restructuring: "Debt Restructuring",
      security_package: "Security Package",
      // Real Estate
      sale_agreement: "Sale Agreement",
      lease: "Lease Agreement",
      development: "Development Agreement",
      sectional_title: "Sectional Title Transfer",
      share_block: "Share Block",
      // Competition
      merger_filing: "Merger Filing",
      exemption_application: "Exemption Application",
      compliance_review: "Compliance Review",
      // Employment
      section_197: "Section 197 Transfer",
      retrenchment: "Retrenchment Process",
      outsourcing: "Outsourcing Arrangement",
      workforce_restructure: "Workforce Restructuring",
      // IP & Technology
      ip_acquisition: "IP Acquisition",
      license_agreement: "License Agreement",
      technology_transfer: "Technology Transfer",
      software_acquisition: "Software Acquisition",
      // BEE
      bee_transaction: "BEE Ownership Transaction",
      employee_scheme: "Employee Share Scheme",
      community_trust: "Community Trust",
      broad_based_scheme: "Broad-Based Scheme",
      // Energy
      ppa: "Power Purchase Agreement",
      epc: "EPC Contract",
      project_acquisition: "Project Acquisition",
      grid_connection: "Grid Connection Agreement",
      offtake_agreement: "Offtake Agreement",
      // Infrastructure
      concession: "Concession Agreement",
      ppp: "PPP Agreement",
      bot: "Build-Operate-Transfer",
      design_build: "Design-Build",
      availability_based: "Availability-Based",
      // Capital Markets
      ipo: "Initial Public Offering",
      rights_issue: "Rights Issue",
      bond_issuance: "Bond Issuance",
      secondary_listing: "Secondary Listing",
      delisting: "Delisting",
      // Restructuring
      business_rescue: "Business Rescue",
      liquidation: "Liquidation",
      debt_restructure: "Debt Restructuring",
      compromise: "Compromise with Creditors",
      distressed_acquisition: "Distressed Asset Acquisition",
      // Private Equity
      buyout: "Buyout",
      growth_equity: "Growth Equity Investment",
      venture_capital: "Venture Capital Investment",
      secondary: "Secondary Transaction",
      mbo: "Management Buyout",
      // Financial Services
      book_transfer: "Book Transfer",
      bancassurance: "Bancassurance Partnership",
      license_acquisition: "License Acquisition",
    };
    return structureMap[structure?.toLowerCase()] || structure;
  };

  return (
    <div
      className={cn(
        "bg-white dark:bg-gray-800 rounded-xl border border-gray-300 dark:border-gray-600 shadow-lg overflow-hidden transition-shadow hover:shadow-xl",
        className
      )}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-3 bg-alchemyPrimaryNavyBlue border-b border-gray-700 cursor-pointer"
        onClick={onToggleCollapse}
      >
        <div className="flex items-center gap-2">
          {isCollapsed ? (
            <ChevronRight className="w-4 h-4 text-white/70" />
          ) : (
            <ChevronDown className="w-4 h-4 text-white/70" />
          )}
          <FileText className="w-4 h-4 text-white" />
          <h3 className="font-medium text-white">
            {name}
          </h3>
          {typeInfo && (
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <span onClick={(e) => e.stopPropagation()}>
                    <Badge
                      variant="outline"
                      className="ml-1 text-xs py-0.5 px-2 bg-white/20 border-white/30 text-white cursor-help"
                    >
                      <span className="mr-1">{typeInfo.icon}</span>
                      {typeInfo.name}
                    </Badge>
                  </span>
                </TooltipTrigger>
                <TooltipContent side="bottom" className="max-w-xs">
                  <p className="text-xs font-medium">{typeInfo.name}</p>
                  <p className="text-xs text-gray-500 mt-0.5">{typeInfo.description}</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          )}
        </div>
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <button
                className="p-1 rounded-full hover:bg-white/20 transition-colors"
                onClick={(e) => e.stopPropagation()}
              >
                <Info className="w-4 h-4 text-white/70" />
              </button>
            </TooltipTrigger>
            <TooltipContent
              side="left"
              className="max-w-sm p-3 text-xs whitespace-pre-line"
            >
              {CONTEXT_TOOLTIP}
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>

      {/* Content */}
      {!isCollapsed && (
        <div className="p-5 bg-white dark:bg-gray-800">
          {/* Primary Details Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
            <div className="space-y-1">
              <div className="flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400">
                <Building2 className="w-3 h-3" />
                Client
              </div>
              <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                {parsed.clientName}
              </p>
            </div>

            <div className="space-y-1">
              <div className="flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400">
                <Target className="w-3 h-3" />
                Target Entity
              </div>
              <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                {parsed.targetEntity}
              </p>
            </div>

            <div className="space-y-1">
              <div className="flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400">
                <Users className="w-3 h-3" />
                Client Role
              </div>
              <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
                {formatClientRole(parsed.clientRole)}
              </p>
            </div>

            <div className="space-y-1">
              <div className="flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400">
                <FileText className="w-3 h-3" />
                Deal Structure
              </div>
              <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
                {formatDealStructure(parsed.dealStructure)}
              </p>
            </div>
          </div>

          {/* Secondary Details */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-3 border-t border-gray-100 dark:border-gray-700">
            <div className="space-y-1">
              <div className="flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400">
                <FileText className="w-3 h-3" />
                Transaction Type
              </div>
              <p className="text-sm text-gray-700 dark:text-gray-300">
                {typeInfo?.name || formatTransactionType(parsed.transactionType)}
              </p>
            </div>

            <div className="space-y-1">
              <div className="flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400">
                <DollarSign className="w-3 h-3" />
                Estimated Value
              </div>
              <p className="text-sm text-gray-700 dark:text-gray-300">
                {parsed.estimatedValue}
              </p>
            </div>

            <div className="space-y-1">
              <div className="flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400">
                <Calendar className="w-3 h-3" />
                Target Closing
              </div>
              <p className="text-sm text-gray-700 dark:text-gray-300">
                {parsed.targetClosing}
              </p>
            </div>
          </div>

          {/* Expand/Collapse Toggle for Details */}
          {hasExpandableDetails && (
            <button
              onClick={() => setIsDetailsExpanded(!isDetailsExpanded)}
              className="w-full mt-3 pt-3 border-t border-gray-100 dark:border-gray-700 flex items-center justify-center gap-2 text-xs text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 transition-colors"
            >
              {isDetailsExpanded ? (
                <>
                  <ChevronDown className="w-4 h-4 rotate-180 transition-transform" />
                  Hide Details
                </>
              ) : (
                <>
                  <ChevronDown className="w-4 h-4 transition-transform" />
                  Show Deal Rationale, Stakeholders & More
                </>
              )}
            </button>
          )}

          {/* Expandable Details Section */}
          {isDetailsExpanded && (
            <>
              {/* Deal Rationale (if provided) */}
              {parsed.dealRationale !== "Not provided" && (
                <div className="mt-3 pt-3 border-t border-gray-100 dark:border-gray-700">
                  <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">
                    Deal Rationale
                  </div>
                  <p className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
                    {parsed.dealRationale}
                  </p>
                </div>
              )}

          {/* Focus Areas Section */}
          {(parsed.criticalPriorities !== "None specified" ||
            parsed.knownDealBreakers !== "None specified" ||
            parsed.knownConcerns !== "None specified" ||
            parsed.deprioritizedAreas !== "None specified") && (
            <div className="mt-3 pt-3 border-t border-gray-100 dark:border-gray-700">
              <div className="text-xs font-medium text-gray-600 dark:text-gray-300 mb-2 flex items-center gap-1.5">
                <AlertTriangle className="w-3 h-3" />
                Focus Areas
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
                {parsed.criticalPriorities !== "None specified" && (
                  <div className="space-y-1">
                    <div className="text-xs text-gray-500 dark:text-gray-400">
                      Critical Priorities
                    </div>
                    {renderBadgeList(parsed.criticalPriorities)}
                  </div>
                )}
                {parsed.knownDealBreakers !== "None specified" && (
                  <div className="space-y-1">
                    <div className="text-xs text-gray-500 dark:text-gray-400">
                      Known Deal Breakers
                    </div>
                    {renderBadgeList(parsed.knownDealBreakers)}
                  </div>
                )}
                {parsed.knownConcerns !== "None specified" && (
                  <div className="space-y-1">
                    <div className="text-xs text-gray-500 dark:text-gray-400">
                      Known Concerns
                    </div>
                    {renderBadgeList(parsed.knownConcerns)}
                  </div>
                )}
                {parsed.deprioritizedAreas !== "None specified" && (
                  <div className="space-y-1">
                    <div className="text-xs text-gray-500 dark:text-gray-400">
                      Deprioritized Areas
                    </div>
                    {renderBadgeList(parsed.deprioritizedAreas)}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Key Stakeholders Section */}
          {(parsed.keyIndividuals !== "None specified" ||
            parsed.keySuppliers !== "None specified" ||
            parsed.keyCustomers !== "None specified" ||
            parsed.keyLenders !== "None specified" ||
            parsed.keyRegulators !== "None specified" ||
            parsed.keyOther !== "None specified" ||
            parsed.shareholders !== "None specified") && (
            <div className="mt-3 pt-3 border-t border-gray-100 dark:border-gray-700">
              <div className="text-xs font-medium text-gray-600 dark:text-gray-300 mb-3 flex items-center gap-1.5">
                <Users className="w-3 h-3" />
                Key Stakeholders
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {parsed.keyCustomers !== "None specified" && (
                  <div className="space-y-2">
                    <div className="text-xs text-gray-500 dark:text-gray-400 flex items-center gap-1 font-medium">
                      <ShoppingCart className="w-3 h-3" />
                      Security Providers / Guarantors
                    </div>
                    {renderStakeholderList(parsed.keyCustomers, ";")}
                  </div>
                )}
                {parsed.keyLenders !== "None specified" && (
                  <div className="space-y-2">
                    <div className="text-xs text-gray-500 dark:text-gray-400 flex items-center gap-1 font-medium">
                      <Landmark className="w-3 h-3" />
                      Lenders
                    </div>
                    {renderStakeholderList(parsed.keyLenders, ";")}
                  </div>
                )}
                {parsed.keyIndividuals !== "None specified" && (
                  <div className="space-y-2">
                    <div className="text-xs text-gray-500 dark:text-gray-400 flex items-center gap-1 font-medium">
                      <UserCheck className="w-3 h-3" />
                      Key Individuals
                    </div>
                    {renderBadgeList(parsed.keyIndividuals)}
                  </div>
                )}
                {parsed.keySuppliers !== "None specified" && (
                  <div className="space-y-2">
                    <div className="text-xs text-gray-500 dark:text-gray-400 flex items-center gap-1 font-medium">
                      <Truck className="w-3 h-3" />
                      Advisors / Service Providers
                    </div>
                    {renderBadgeList(parsed.keySuppliers)}
                  </div>
                )}
                {parsed.keyRegulators !== "None specified" && (
                  <div className="space-y-2">
                    <div className="text-xs text-gray-500 dark:text-gray-400 flex items-center gap-1 font-medium">
                      <Scale className="w-3 h-3" />
                      Regulators
                    </div>
                    {renderBadgeList(parsed.keyRegulators)}
                  </div>
                )}
                {parsed.keyOther !== "None specified" && (
                  <div className="space-y-2">
                    <div className="text-xs text-gray-500 dark:text-gray-400 flex items-center gap-1 font-medium">
                      <MoreHorizontal className="w-3 h-3" />
                      Other
                    </div>
                    {renderStakeholderList(parsed.keyOther, ";")}
                  </div>
                )}
              </div>
            </div>
          )}

              {/* Shareholders Section */}
              {(parsed.shareholderEntity !== "None specified" ||
                parsed.shareholders !== "None specified") && (
                <div className="mt-3 pt-3 border-t border-gray-100 dark:border-gray-700">
                  <div className="text-xs font-medium text-gray-600 dark:text-gray-300 mb-2 flex items-center gap-1.5">
                    <PieChart className="w-3 h-3" />
                    Shareholders
                    {parsed.shareholderEntity !== "None specified" && (
                      <span className="font-normal text-gray-500">
                        ({parsed.shareholderEntity})
                      </span>
                    )}
                  </div>
                  {parsed.shareholders !== "None specified" && (
                    <div className="space-y-1">
                      {renderBadgeList(parsed.shareholders)}
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
};

export default TransactionSummary;
