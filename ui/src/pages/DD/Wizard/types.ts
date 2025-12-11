export type TransactionTypeCode =
  | "mining_resources"
  | "ma_corporate"
  | "banking_finance"
  | "real_estate"
  | "competition_regulatory"
  | "employment_labor"
  | "ip_technology"
  | "bee_transformation"
  | "energy_power"
  | "infrastructure_ppp"
  | "capital_markets"
  | "restructuring_insolvency"
  | "private_equity_vc"
  | "financial_services";

export type ClientRole = "buyer" | "seller" | "target" | "advisor";
export type DealStructure = "share_purchase" | "asset_purchase" | "merger" | "scheme";

export interface DDProjectSetup {
  // Step 1: Transaction Basics
  transactionType: TransactionTypeCode | null;
  transactionName: string;
  clientRole: ClientRole | null;
  dealStructure: DealStructure | null;
  estimatedValue: number | null;
  targetClosingDate: Date | null;

  // Step 2: Deal Context
  dealRationale: string;
  knownConcerns: string[];

  // Step 3: Focus Areas
  criticalPriorities: string[];
  knownDealBreakers: string[];
  deprioritizedAreas: string[];

  // Step 4: Key Parties
  targetCompanyName: string;
  keyPersons: string[];
  counterparties: string[];
  keyLenders: string[];
  keyRegulators: string[];

  // Step 5: Documents
  uploadedFile: File | null;
}

export const DEFAULT_PROJECT_SETUP: DDProjectSetup = {
  transactionType: null,
  transactionName: "",
  clientRole: null,
  dealStructure: null,
  estimatedValue: null,
  targetClosingDate: null,
  dealRationale: "",
  knownConcerns: [],
  criticalPriorities: [],
  knownDealBreakers: [],
  deprioritizedAreas: [],
  targetCompanyName: "",
  keyPersons: [],
  counterparties: [],
  keyLenders: [],
  keyRegulators: [],
  uploadedFile: null,
};

export const TRANSACTION_TYPE_INFO: Record<
  TransactionTypeCode,
  { name: string; icon: string; description: string }
> = {
  mining_resources: {
    name: "Mining & Resources",
    icon: "⛏️",
    description: "Mining rights, mineral resources, environmental compliance",
  },
  ma_corporate: {
    name: "M&A / Corporate",
    icon: "🏢",
    description: "Share purchases, mergers, corporate acquisitions",
  },
  banking_finance: {
    name: "Banking & Finance",
    icon: "🏦",
    description: "Lending, debt restructuring, security packages",
  },
  real_estate: {
    name: "Real Estate & Property",
    icon: "🏠",
    description: "Property transactions, leases, development",
  },
  competition_regulatory: {
    name: "Competition & Regulatory",
    icon: "⚖️",
    description: "Merger control, competition filings, regulatory approvals",
  },
  employment_labor: {
    name: "Employment & Labor",
    icon: "👥",
    description: "Workforce transfers, Section 197, union matters",
  },
  ip_technology: {
    name: "IP & Technology",
    icon: "💡",
    description: "Patents, software, data privacy, cyber security",
  },
  bee_transformation: {
    name: "BEE & Transformation",
    icon: "🤝",
    description: "BEE ownership, Mining Charter, transformation",
  },
  energy_power: {
    name: "Energy & Power",
    icon: "⚡",
    description: "IPP projects, PPAs, renewable energy, grid connection",
  },
  infrastructure_ppp: {
    name: "Infrastructure & PPP",
    icon: "🌉",
    description: "Concessions, PPP projects, treasury approvals",
  },
  capital_markets: {
    name: "Capital Markets",
    icon: "📈",
    description: "IPOs, listings, rights issues, bond issuances",
  },
  restructuring_insolvency: {
    name: "Restructuring & Insolvency",
    icon: "🔄",
    description: "Business rescue, liquidations, debt restructuring",
  },
  private_equity_vc: {
    name: "Private Equity & VC",
    icon: "💰",
    description: "Buyouts, VC investments, growth equity, fund investments",
  },
  financial_services: {
    name: "Financial Services",
    icon: "🏛️",
    description: "Banking, insurance, asset management, fintech acquisitions",
  },
};

export const REGULATOR_SUGGESTIONS: Record<TransactionTypeCode, string[]> = {
  mining_resources: ["DMRE", "Competition Commission", "DEA/DFFE", "DWS"],
  ma_corporate: ["Competition Commission", "CIPC", "TRP"],
  banking_finance: ["SARB", "FSCA", "NCR"],
  real_estate: ["Municipality", "Deeds Office", "NHBRC"],
  competition_regulatory: ["Competition Commission", "Competition Tribunal", "CAC"],
  employment_labor: ["CCMA", "DoL", "Bargaining Council"],
  ip_technology: ["CIPC", "Information Regulator"],
  bee_transformation: ["B-BBEE Commission", "DMRE", "DTI"],
  energy_power: ["NERSA", "Eskom", "DMRE", "IPP Office"],
  infrastructure_ppp: ["National Treasury", "PPP Unit", "GTAC"],
  capital_markets: ["JSE", "FSCA", "CIPC", "TRP"],
  restructuring_insolvency: ["CIPC", "Master of the High Court", "Competition Commission"],
  private_equity_vc: ["Competition Commission", "SARB", "FSCA"],
  financial_services: ["SARB", "FSCA", "Prudential Authority", "NCR", "Information Regulator"],
};
