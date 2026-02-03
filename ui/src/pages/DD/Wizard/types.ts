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

export type ClientRole = string; // Dynamic based on transaction type

export interface ClientRoleOption {
  value: string;
  label: string;
}
export type DealStructure = string; // Dynamic based on transaction type

export interface DealStructureOption {
  value: string;
  label: string;
}

export interface OtherStakeholder {
  name: string;
  role: string;
}

export interface Shareholder {
  name: string;
  percentage: number | null;
  registrationNumber?: string;  // Company reg, trust IT number, or ID number
}

export interface LenderStakeholder {
  name: string;
  description: string;
  facilityAmount: string;
}

export interface CounterpartyStakeholder {
  name: string;
  description: string;
  exposure: string;
}

// Known Subsidiary for Entity Mapping
export interface KnownSubsidiary {
  name: string;
  relationship: 'subsidiary' | 'joint_venture' | 'associate' | 'related_party';
}

// Holding Company for Entity Mapping
export interface HoldingCompany {
  name: string;
  percentage: number;  // Percentage ownership
}

export interface DDProjectSetup {
  // Step 1: Transaction Basics
  transactionType: TransactionTypeCode | null;
  transactionName: string;
  clientName: string;
  targetEntityName: string;
  clientRole: ClientRole | null;
  dealStructure: DealStructure | null;
  estimatedValue: number | null;
  estimatedValueCurrency: string;
  targetClosingDate: Date | null;

  // Step 2: Deal Context
  dealRationale: string;
  knownConcerns: string[];

  // Step 3: Focus Areas
  criticalPriorities: string[];
  knownDealBreakers: string[];
  deprioritizedAreas: string[];

  // Step 4: Key Stakeholders
  targetCompanyName: string;
  keyIndividuals: string[];
  keySuppliers: string[];
  keyCustomers: CounterpartyStakeholder[];
  keyContractors: CounterpartyStakeholder[];  // Separate storage for contractors
  keyLenders: LenderStakeholder[];
  keyRegulators: string[];
  keyOther: OtherStakeholder[];

  // Step 4: Shareholders
  shareholderEntityName: string;
  shareholders: Shareholder[];

  // Step 5: Documents
  uploadedFile: File | null;

  // ===== PHASE 1 ENHANCEMENTS: Entity Mapping Context =====
  // These fields help the AI correctly identify entities across documents

  // Client registration number (company reg, trust IT number, or ID number)
  clientRegistrationNumber?: string;

  // Target entity registration number (helps match entity names across docs)
  targetRegistrationNumber?: string;

  // Known subsidiaries of the target (pre-populate entity map)
  knownSubsidiaries?: KnownSubsidiary[];

  // Holding company details (if target has a parent)
  holdingCompany?: HoldingCompany | null;

  // Expected counterparties (contract partners, customers, suppliers to watch for)
  expectedCounterparties?: string[];
}

export const DEFAULT_PROJECT_SETUP: DDProjectSetup = {
  transactionType: null,
  transactionName: "",
  clientName: "",
  targetEntityName: "",
  clientRole: null,
  dealStructure: null,
  estimatedValue: null,
  estimatedValueCurrency: "ZAR",
  targetClosingDate: null,
  dealRationale: "",
  knownConcerns: [],
  criticalPriorities: [],
  knownDealBreakers: [],
  deprioritizedAreas: [],
  targetCompanyName: "",
  keyIndividuals: [],
  keySuppliers: [],
  keyCustomers: [],
  keyContractors: [],
  keyLenders: [],
  keyRegulators: [],
  keyOther: [],
  shareholderEntityName: "",
  shareholders: [],
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
  mining_resources: ["DMRE", "Competition Commission", "DEA/DFFE", "DWS", "B-BBEE Commission"],
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

export const TARGET_ENTITY_LABELS: Record<TransactionTypeCode, { label: string; placeholder: string }> = {
  mining_resources: { label: "Target Entity", placeholder: "e.g., ABC Resources (Pty) Ltd" },
  ma_corporate: { label: "Target Company", placeholder: "e.g., Target Holdings (Pty) Ltd" },
  banking_finance: { label: "Borrower / Lender / Counterparty", placeholder: "e.g., Borrower Corp Ltd" },
  real_estate: { label: "Seller / Property Owner", placeholder: "e.g., Property Owner Trust" },
  competition_regulatory: { label: "Target Party", placeholder: "e.g., Merger Target Ltd" },
  employment_labor: { label: "Target Entity", placeholder: "e.g., Employer (Pty) Ltd" },
  ip_technology: { label: "Target / Licensor", placeholder: "e.g., Tech Innovations Ltd" },
  bee_transformation: { label: "Target Entity", placeholder: "e.g., BEE Partner (Pty) Ltd" },
  energy_power: { label: "Project Company", placeholder: "e.g., Solar Power SPV (Pty) Ltd" },
  infrastructure_ppp: { label: "Project Company / SPV", placeholder: "e.g., Infrastructure SPV Ltd" },
  capital_markets: { label: "Issuer", placeholder: "e.g., Listed Company Ltd" },
  restructuring_insolvency: { label: "Target Entity", placeholder: "e.g., Company in Business Rescue" },
  private_equity_vc: { label: "Target Company", placeholder: "e.g., Growth Co (Pty) Ltd" },
  financial_services: { label: "Target Entity", placeholder: "e.g., Financial Services Provider Ltd" },
};

export const CLIENT_ROLE_OPTIONS: Record<TransactionTypeCode, ClientRoleOption[]> = {
  mining_resources: [
    { value: "acquirer", label: "Acquirer / Purchaser" },
    { value: "seller", label: "Seller / Vendor" },
    { value: "target", label: "Target Company" },
    { value: "joint_venture_partner", label: "Joint Venture Partner" },
    { value: "advisor", label: "Independent Advisor" },
  ],
  ma_corporate: [
    { value: "buyer", label: "Buyer / Acquirer" },
    { value: "seller", label: "Seller / Vendor" },
    { value: "target", label: "Target Company" },
    { value: "advisor", label: "Independent Advisor" },
  ],
  banking_finance: [
    { value: "lender", label: "Lender / Financier" },
    { value: "borrower", label: "Borrower" },
    { value: "guarantor", label: "Guarantor / Security Provider" },
    { value: "arranger", label: "Arranger / Agent" },
    { value: "advisor", label: "Independent Advisor" },
  ],
  real_estate: [
    { value: "buyer", label: "Buyer / Purchaser" },
    { value: "seller", label: "Seller / Property Owner" },
    { value: "tenant", label: "Tenant / Lessee" },
    { value: "landlord", label: "Landlord / Lessor" },
    { value: "developer", label: "Developer" },
    { value: "advisor", label: "Independent Advisor" },
  ],
  competition_regulatory: [
    { value: "acquiring_firm", label: "Acquiring Firm" },
    { value: "target_firm", label: "Target Firm" },
    { value: "merging_party", label: "Merging Party" },
    { value: "advisor", label: "Independent Advisor" },
  ],
  employment_labor: [
    { value: "employer", label: "Employer" },
    { value: "acquiring_employer", label: "Acquiring Employer" },
    { value: "transferring_employer", label: "Transferring Employer" },
    { value: "advisor", label: "Independent Advisor" },
  ],
  ip_technology: [
    { value: "acquirer", label: "Acquirer / Licensee" },
    { value: "seller", label: "Seller / Licensor" },
    { value: "target", label: "Target Company" },
    { value: "advisor", label: "Independent Advisor" },
  ],
  bee_transformation: [
    { value: "bee_partner", label: "BEE Partner / Investor" },
    { value: "seller", label: "Seller / Existing Shareholder" },
    { value: "target", label: "Target Company" },
    { value: "advisor", label: "Independent Advisor" },
  ],
  energy_power: [
    { value: "developer", label: "Project Developer" },
    { value: "investor", label: "Investor / Financier" },
    { value: "offtaker", label: "Offtaker / PPA Counterparty" },
    { value: "epc_contractor", label: "EPC Contractor" },
    { value: "advisor", label: "Independent Advisor" },
  ],
  infrastructure_ppp: [
    { value: "concessionaire", label: "Concessionaire / SPV" },
    { value: "government", label: "Government / Public Authority" },
    { value: "investor", label: "Investor / Sponsor" },
    { value: "lender", label: "Lender / Financier" },
    { value: "advisor", label: "Independent Advisor" },
  ],
  capital_markets: [
    { value: "issuer", label: "Issuer" },
    { value: "underwriter", label: "Underwriter / Sponsor" },
    { value: "investor", label: "Investor" },
    { value: "selling_shareholder", label: "Selling Shareholder" },
    { value: "advisor", label: "Independent Advisor" },
  ],
  restructuring_insolvency: [
    { value: "debtor", label: "Debtor / Company in Distress" },
    { value: "creditor", label: "Creditor" },
    { value: "practitioner", label: "Business Rescue Practitioner" },
    { value: "investor", label: "Investor / Acquirer" },
    { value: "advisor", label: "Independent Advisor" },
  ],
  private_equity_vc: [
    { value: "investor", label: "Investor / Fund" },
    { value: "seller", label: "Seller / Existing Shareholder" },
    { value: "target", label: "Target Company" },
    { value: "management", label: "Management Team" },
    { value: "advisor", label: "Independent Advisor" },
  ],
  financial_services: [
    { value: "acquirer", label: "Acquirer / Purchaser" },
    { value: "seller", label: "Seller / Vendor" },
    { value: "target", label: "Target Institution" },
    { value: "regulator_liaison", label: "Regulatory Liaison" },
    { value: "advisor", label: "Independent Advisor" },
  ],
};

export const DEAL_STRUCTURE_OPTIONS: Record<TransactionTypeCode, DealStructureOption[]> = {
  mining_resources: [
    { value: "share_purchase", label: "Share Purchase" },
    { value: "asset_purchase", label: "Asset Purchase" },
    { value: "mining_right_transfer", label: "Mining Right Transfer" },
    { value: "section_11", label: "Section 11 Transfer" },
    { value: "joint_venture", label: "Joint Venture" },
    { value: "farm_in", label: "Farm-In Agreement" },
  ],
  ma_corporate: [
    { value: "share_purchase", label: "Share Purchase" },
    { value: "asset_purchase", label: "Asset Purchase" },
    { value: "merger", label: "Merger" },
    { value: "scheme", label: "Scheme of Arrangement" },
  ],
  banking_finance: [
    { value: "term_loan", label: "Term Loan Facility" },
    { value: "revolving_credit", label: "Revolving Credit Facility" },
    { value: "syndicated_loan", label: "Syndicated Loan" },
    { value: "project_finance", label: "Project Finance" },
    { value: "acquisition_finance", label: "Acquisition Finance" },
    { value: "debt_restructuring", label: "Debt Restructuring" },
    { value: "security_package", label: "Security Package" },
  ],
  real_estate: [
    { value: "sale_agreement", label: "Sale Agreement" },
    { value: "lease", label: "Lease Agreement" },
    { value: "development", label: "Development Agreement" },
    { value: "sectional_title", label: "Sectional Title Transfer" },
    { value: "share_block", label: "Share Block" },
  ],
  competition_regulatory: [
    { value: "merger_filing", label: "Merger Filing" },
    { value: "exemption_application", label: "Exemption Application" },
    { value: "compliance_review", label: "Compliance Review" },
  ],
  employment_labor: [
    { value: "section_197", label: "Section 197 Transfer" },
    { value: "retrenchment", label: "Retrenchment Process" },
    { value: "outsourcing", label: "Outsourcing Arrangement" },
    { value: "workforce_restructure", label: "Workforce Restructuring" },
  ],
  ip_technology: [
    { value: "ip_acquisition", label: "IP Acquisition" },
    { value: "license_agreement", label: "License Agreement" },
    { value: "technology_transfer", label: "Technology Transfer" },
    { value: "software_acquisition", label: "Software Acquisition" },
  ],
  bee_transformation: [
    { value: "bee_transaction", label: "BEE Ownership Transaction" },
    { value: "employee_scheme", label: "Employee Share Scheme" },
    { value: "community_trust", label: "Community Trust" },
    { value: "broad_based_scheme", label: "Broad-Based Scheme" },
  ],
  energy_power: [
    { value: "ppa", label: "Power Purchase Agreement" },
    { value: "epc", label: "EPC Contract" },
    { value: "project_acquisition", label: "Project Acquisition" },
    { value: "grid_connection", label: "Grid Connection Agreement" },
    { value: "offtake_agreement", label: "Offtake Agreement" },
  ],
  infrastructure_ppp: [
    { value: "concession", label: "Concession Agreement" },
    { value: "ppp", label: "PPP Agreement" },
    { value: "bot", label: "Build-Operate-Transfer" },
    { value: "design_build", label: "Design-Build" },
    { value: "availability_based", label: "Availability-Based" },
  ],
  capital_markets: [
    { value: "ipo", label: "Initial Public Offering" },
    { value: "rights_issue", label: "Rights Issue" },
    { value: "bond_issuance", label: "Bond Issuance" },
    { value: "secondary_listing", label: "Secondary Listing" },
    { value: "delisting", label: "Delisting" },
  ],
  restructuring_insolvency: [
    { value: "business_rescue", label: "Business Rescue" },
    { value: "liquidation", label: "Liquidation" },
    { value: "debt_restructure", label: "Debt Restructuring" },
    { value: "compromise", label: "Compromise with Creditors" },
    { value: "distressed_acquisition", label: "Distressed Asset Acquisition" },
  ],
  private_equity_vc: [
    { value: "buyout", label: "Buyout" },
    { value: "growth_equity", label: "Growth Equity Investment" },
    { value: "venture_capital", label: "Venture Capital Investment" },
    { value: "secondary", label: "Secondary Transaction" },
    { value: "mbo", label: "Management Buyout" },
  ],
  financial_services: [
    { value: "share_purchase", label: "Share Purchase" },
    { value: "asset_purchase", label: "Asset Purchase" },
    { value: "book_transfer", label: "Book Transfer" },
    { value: "bancassurance", label: "Bancassurance Partnership" },
    { value: "license_acquisition", label: "License Acquisition" },
  ],
};

export const VALUE_DATE_LABELS: Record<TransactionTypeCode, {
  valueLabel: string;
  valuePlaceholder: string;
  dateLabel: string;
}> = {
  mining_resources: {
    valueLabel: "Transaction Value (ZAR)",
    valuePlaceholder: "e.g., R500,000,000",
    dateLabel: "Target Completion Date",
  },
  ma_corporate: {
    valueLabel: "Estimated Purchase Price (ZAR)",
    valuePlaceholder: "e.g., R500,000,000",
    dateLabel: "Target Closing Date",
  },
  banking_finance: {
    valueLabel: "Facility Amount (ZAR)",
    valuePlaceholder: "e.g., R1,000,000,000",
    dateLabel: "Target Financial Close",
  },
  real_estate: {
    valueLabel: "Property Value (ZAR)",
    valuePlaceholder: "e.g., R50,000,000",
    dateLabel: "Transfer / Lease Start Date",
  },
  competition_regulatory: {
    valueLabel: "Transaction Value (ZAR)",
    valuePlaceholder: "e.g., R500,000,000",
    dateLabel: "Target Filing Date",
  },
  employment_labor: {
    valueLabel: "Workforce Value Impact (ZAR)",
    valuePlaceholder: "e.g., R10,000,000",
    dateLabel: "Effective Date",
  },
  ip_technology: {
    valueLabel: "IP / Technology Value (ZAR)",
    valuePlaceholder: "e.g., R25,000,000",
    dateLabel: "Target Completion Date",
  },
  bee_transformation: {
    valueLabel: "Transaction Value (ZAR)",
    valuePlaceholder: "e.g., R100,000,000",
    dateLabel: "Implementation Date",
  },
  energy_power: {
    valueLabel: "Project Value (ZAR)",
    valuePlaceholder: "e.g., R2,000,000,000",
    dateLabel: "Target Financial Close",
  },
  infrastructure_ppp: {
    valueLabel: "Project Value (ZAR)",
    valuePlaceholder: "e.g., R5,000,000,000",
    dateLabel: "Target Financial Close",
  },
  capital_markets: {
    valueLabel: "Issue Size (ZAR)",
    valuePlaceholder: "e.g., R1,000,000,000",
    dateLabel: "Target Listing / Issue Date",
  },
  restructuring_insolvency: {
    valueLabel: "Claim / Asset Value (ZAR)",
    valuePlaceholder: "e.g., R200,000,000",
    dateLabel: "Target Resolution Date",
  },
  private_equity_vc: {
    valueLabel: "Investment Amount (ZAR)",
    valuePlaceholder: "e.g., R300,000,000",
    dateLabel: "Target Closing Date",
  },
  financial_services: {
    valueLabel: "Transaction Value (ZAR)",
    valuePlaceholder: "e.g., R500,000,000",
    dateLabel: "Target Completion Date",
  },
};

export interface StakeholderFieldConfig {
  label: string;
  placeholder: string;
}

export interface StakeholderConfig {
  individuals: StakeholderFieldConfig;
  suppliers: StakeholderFieldConfig;
  customers: StakeholderFieldConfig;
  lenders: StakeholderFieldConfig;
  regulators: StakeholderFieldConfig;
  other: StakeholderFieldConfig;
}

// =============================================================================
// NEW: Flexible Step 4 Field Configuration System
// =============================================================================

/**
 * Field input types determine which component renders the field
 */
export type Step4FieldType =
  | "tags"           // Simple tag input (press Enter to add)
  | "counterparty"   // Name + Description + Exposure amount
  | "lender"         // Name + Description + Facility amount
  | "party_role"     // Name + Role/Description (no amount)
  | "bee_partner"    // Name + BEE Ownership % + BEE Level
  | "shareholder";   // Name + Percentage (used in shareholder section)

/**
 * Configuration for a single field in Step 4
 */
export interface Step4FieldDefinition {
  id: string;                    // Unique field identifier
  type: Step4FieldType;          // Determines input component
  label: string;                 // Display label
  placeholder: string;           // Input placeholder
  description?: string;          // Optional helper text
  suggestions?: string[];        // Optional quick-add suggestions
  required?: boolean;            // Whether field is required
  amountLabel?: string;          // Custom label for amount field (lender/counterparty)
  amountPlaceholder?: string;    // Custom placeholder for amount
}

/**
 * Configuration for the shareholder section
 */
export interface ShareholderSectionConfig {
  visible: boolean;
  title: string;
  description: string;
  entityLabel: string;
  entityPlaceholder: string;
  showBEECalculation?: boolean;  // Show BEE ownership % calculation
  showPrePost?: boolean;         // Show pre/post transaction columns
}

/**
 * Complete Step 4 configuration for a transaction type
 */
export interface Step4Config {
  title: string;                         // Section title (e.g., "Key Stakeholders")
  subtitle: string;                      // Section subtitle/description
  fields: Step4FieldDefinition[];        // Fields to display
  shareholderSection: ShareholderSectionConfig;
}

/**
 * Step 4 configurations for all transaction types
 */
export const STEP4_CONFIG: Record<TransactionTypeCode, Step4Config> = {
  // ===== BEE TRANSFORMATION =====
  bee_transformation: {
    title: "Transaction Parties",
    subtitle: "Identify the key parties to the BEE ownership transaction.",
    fields: [
      {
        id: "beePartners",
        type: "bee_partner",
        label: "BEE Partner(s) / Investor(s)",
        placeholder: "e.g., Empowerment Consortium (Pty) Ltd",
        description: "Black-owned entities acquiring ownership",
      },
      {
        id: "sellers",
        type: "party_role",
        label: "Seller(s) / Existing Shareholders",
        placeholder: "e.g., Founding Shareholder Trust",
        description: "Parties disposing of shares to BEE partners",
      },
      {
        id: "beeTrustSPV",
        type: "party_role",
        label: "BEE Trust / SPV (if applicable)",
        placeholder: "e.g., ABC Employee Share Trust",
        description: "Trust or SPV holding BEE shares",
      },
      {
        id: "funders",
        type: "lender",
        label: "Transaction Funders",
        placeholder: "e.g., Standard Bank, Vendor Finance",
        description: "Parties providing funding for the transaction",
        amountLabel: "Funding Amount",
        amountPlaceholder: "e.g., R50m",
      },
      {
        id: "verificationAgency",
        type: "tags",
        label: "Verification Agency",
        placeholder: "e.g., Empowerdex, AQRate",
        description: "Agency that will verify BEE credentials",
      },
      {
        id: "regulators",
        type: "tags",
        label: "Key Regulators",
        placeholder: "e.g., B-BBEE Commission",
        suggestions: ["B-BBEE Commission", "DTI/dtic", "DMRE", "Competition Commission"],
      },
      {
        id: "other",
        type: "party_role",
        label: "Other Parties",
        placeholder: "e.g., ESOP Trustees",
      },
    ],
    shareholderSection: {
      visible: true,
      title: "Ownership Structure",
      description: "Detail the pre and post-transaction ownership to calculate BEE ownership percentage.",
      entityLabel: "Target Entity",
      entityPlaceholder: "e.g., Target Company (Pty) Ltd",
      showBEECalculation: true,
      showPrePost: true,
    },
  },

  // ===== MINING & RESOURCES =====
  mining_resources: {
    title: "Key Stakeholders",
    subtitle: "Identify key parties involved in the mining transaction.",
    fields: [
      {
        id: "keyIndividuals",
        type: "tags",
        label: "Key Individuals",
        placeholder: "e.g., Mine Manager, CEO, Technical Director",
      },
      {
        id: "contractors",
        type: "counterparty",
        label: "Key Contractors",
        placeholder: "e.g., Mining contractor, equipment supplier",
        description: "Major contractors and service providers",
        amountLabel: "Contract Value",
        amountPlaceholder: "e.g., R100m",
      },
      {
        id: "offtakers",
        type: "counterparty",
        label: "Offtakers / Customers",
        placeholder: "e.g., Commodity traders, smelters",
        description: "Parties with offtake or sales agreements",
        amountLabel: "Annual Value",
        amountPlaceholder: "e.g., R500m",
      },
      {
        id: "financiers",
        type: "lender",
        label: "Project Financiers",
        placeholder: "e.g., DFI, commercial banks",
        amountLabel: "Facility Amount",
        amountPlaceholder: "e.g., R1bn",
      },
      {
        id: "regulators",
        type: "tags",
        label: "Key Regulators",
        placeholder: "e.g., DMRE, DEA",
        suggestions: ["DMRE", "Competition Commission", "DEA/DFFE", "DWS", "B-BBEE Commission"],
      },
      {
        id: "communities",
        type: "party_role",
        label: "Communities / Trusts",
        placeholder: "e.g., Local Community Trust",
        description: "Affected communities and their representatives",
      },
      {
        id: "other",
        type: "party_role",
        label: "Other Parties",
        placeholder: "e.g., JV partners, technical consultants",
      },
    ],
    shareholderSection: {
      visible: true,
      title: "Shareholders",
      description: "Add details of the shareholding structure for the target entity.",
      entityLabel: "Target Entity",
      entityPlaceholder: "e.g., Mining Co (Pty) Ltd",
      showBEECalculation: true,
      showPrePost: false,
    },
  },

  // ===== M&A CORPORATE =====
  ma_corporate: {
    title: "Key Stakeholders",
    subtitle: "Identify key parties to flag related findings and contracts.",
    fields: [
      {
        id: "keyIndividuals",
        type: "tags",
        label: "Key Individuals",
        placeholder: "e.g., CEO, CFO, Key executives",
      },
      {
        id: "suppliers",
        type: "counterparty",
        label: "Key Suppliers",
        placeholder: "e.g., Critical suppliers",
        description: "Suppliers with material contracts",
        amountLabel: "Annual Spend",
        amountPlaceholder: "e.g., R50m",
      },
      {
        id: "customers",
        type: "counterparty",
        label: "Key Customers",
        placeholder: "e.g., Major customers, key accounts",
        description: "Customers representing significant revenue",
        amountLabel: "Annual Revenue",
        amountPlaceholder: "e.g., R100m",
      },
      {
        id: "lenders",
        type: "lender",
        label: "Key Lenders",
        placeholder: "e.g., Banks, bondholders",
        amountLabel: "Facility Amount",
        amountPlaceholder: "e.g., R500m",
      },
      {
        id: "regulators",
        type: "tags",
        label: "Key Regulators",
        placeholder: "e.g., Competition Commission",
        suggestions: ["Competition Commission", "CIPC", "TRP", "Sector Regulator"],
      },
      {
        id: "other",
        type: "party_role",
        label: "Other Parties",
        placeholder: "e.g., JV partners, licensors",
      },
    ],
    shareholderSection: {
      visible: true,
      title: "Shareholders",
      description: "Add details of the shareholding structure for the target entity.",
      entityLabel: "Target Company",
      entityPlaceholder: "e.g., Target Holdings (Pty) Ltd",
      showBEECalculation: false,
      showPrePost: false,
    },
  },

  // ===== BANKING & FINANCE =====
  banking_finance: {
    title: "Transaction Parties",
    subtitle: "Identify key parties to the financing transaction.",
    fields: [
      {
        id: "keyExecutives",
        type: "tags",
        label: "Key Executives / Signatories",
        placeholder: "e.g., CFO, Treasury Head, Authorized signatories",
      },
      {
        id: "borrowerGroup",
        type: "party_role",
        label: "Borrower Group Members",
        placeholder: "e.g., Subsidiary Co (Pty) Ltd",
        description: "Borrower and related obligors",
      },
      {
        id: "guarantors",
        type: "lender",
        label: "Guarantors / Security Providers",
        placeholder: "e.g., Holding Company Ltd",
        description: "Parties providing guarantees or security",
        amountLabel: "Guarantee Amount",
        amountPlaceholder: "e.g., R500m",
      },
      {
        id: "existingLenders",
        type: "lender",
        label: "Existing Lenders / Syndicate",
        placeholder: "e.g., Standard Bank, RMB, Nedbank",
        description: "Current or proposed lenders",
        amountLabel: "Commitment",
        amountPlaceholder: "e.g., R250m",
      },
      {
        id: "advisors",
        type: "tags",
        label: "Advisors / Agents",
        placeholder: "e.g., Facility Agent, Security Agent",
      },
      {
        id: "regulators",
        type: "tags",
        label: "Key Regulators",
        placeholder: "e.g., SARB, FSCA",
        suggestions: ["SARB", "FSCA", "NCR", "Prudential Authority"],
      },
      {
        id: "other",
        type: "party_role",
        label: "Other Parties",
        placeholder: "e.g., Account bank, process agent",
      },
    ],
    shareholderSection: {
      visible: false,
      title: "Shareholders",
      description: "",
      entityLabel: "",
      entityPlaceholder: "",
    },
  },

  // ===== REAL ESTATE =====
  real_estate: {
    title: "Transaction Parties",
    subtitle: "Identify key parties to the property transaction.",
    fields: [
      {
        id: "keyIndividuals",
        type: "tags",
        label: "Key Individuals",
        placeholder: "e.g., Property manager, directors",
      },
      {
        id: "tenants",
        type: "counterparty",
        label: "Key Tenants",
        placeholder: "e.g., Anchor tenants, major lessees",
        description: "Significant tenants by rental value",
        amountLabel: "Monthly Rental",
        amountPlaceholder: "e.g., R500k",
      },
      {
        id: "serviceProviders",
        type: "party_role",
        label: "Service Providers",
        placeholder: "e.g., Managing agents, maintenance contractors",
      },
      {
        id: "financiers",
        type: "lender",
        label: "Financiers",
        placeholder: "e.g., Mortgage provider, development funder",
        amountLabel: "Facility Amount",
        amountPlaceholder: "e.g., R100m",
      },
      {
        id: "regulators",
        type: "tags",
        label: "Key Authorities",
        placeholder: "e.g., Municipality, Deeds Office",
        suggestions: ["Municipality", "Deeds Office", "NHBRC", "Body Corporate"],
      },
      {
        id: "other",
        type: "party_role",
        label: "Other Parties",
        placeholder: "e.g., Body corporate, neighbors",
      },
    ],
    shareholderSection: {
      visible: false,
      title: "Shareholders",
      description: "",
      entityLabel: "",
      entityPlaceholder: "",
    },
  },

  // ===== COMPETITION & REGULATORY =====
  competition_regulatory: {
    title: "Transaction Parties",
    subtitle: "Identify the merging parties and key stakeholders.",
    fields: [
      {
        id: "keyExecutives",
        type: "tags",
        label: "Key Executives",
        placeholder: "e.g., CEOs of merging parties",
      },
      {
        id: "mergingParties",
        type: "party_role",
        label: "Merging Parties",
        placeholder: "e.g., Acquiring Firm (Pty) Ltd",
        description: "Parties to the merger/acquisition",
      },
      {
        id: "competitors",
        type: "tags",
        label: "Key Competitors",
        placeholder: "e.g., Main competitors in the market",
      },
      {
        id: "suppliers",
        type: "tags",
        label: "Common Suppliers",
        placeholder: "e.g., Suppliers to both parties",
      },
      {
        id: "customers",
        type: "tags",
        label: "Common Customers",
        placeholder: "e.g., Overlapping customer base",
      },
      {
        id: "regulators",
        type: "tags",
        label: "Regulatory Bodies",
        placeholder: "e.g., Competition Commission",
        suggestions: ["Competition Commission", "Competition Tribunal", "CAC", "Sector Regulator"],
      },
      {
        id: "other",
        type: "party_role",
        label: "Other Parties",
        placeholder: "e.g., Industry associations",
      },
    ],
    shareholderSection: {
      visible: false,
      title: "Shareholders",
      description: "",
      entityLabel: "",
      entityPlaceholder: "",
    },
  },

  // ===== EMPLOYMENT & LABOR =====
  employment_labor: {
    title: "Key Parties",
    subtitle: "Identify key parties affected by the employment matter.",
    fields: [
      {
        id: "keyPersonnel",
        type: "tags",
        label: "Key Personnel",
        placeholder: "e.g., HR Director, affected executives",
      },
      {
        id: "unions",
        type: "party_role",
        label: "Trade Unions / Worker Representatives",
        placeholder: "e.g., NUM, NUMSA",
        description: "Recognized unions and workplace forums",
      },
      {
        id: "affectedEmployees",
        type: "party_role",
        label: "Employee Groups Affected",
        placeholder: "e.g., Production staff, Head office",
        description: "Categories of employees affected",
      },
      {
        id: "serviceProviders",
        type: "tags",
        label: "Service Providers",
        placeholder: "e.g., Payroll providers, benefits administrators",
      },
      {
        id: "regulators",
        type: "tags",
        label: "Labor Authorities",
        placeholder: "e.g., CCMA, Department of Labour",
        suggestions: ["CCMA", "Department of Labour", "Bargaining Council"],
      },
      {
        id: "other",
        type: "party_role",
        label: "Other Parties",
        placeholder: "e.g., Pension fund trustees",
      },
    ],
    shareholderSection: {
      visible: false,
      title: "Shareholders",
      description: "",
      entityLabel: "",
      entityPlaceholder: "",
    },
  },

  // ===== IP & TECHNOLOGY =====
  ip_technology: {
    title: "Key Stakeholders",
    subtitle: "Identify parties relevant to the IP/technology transaction.",
    fields: [
      {
        id: "keyPersonnel",
        type: "tags",
        label: "Key Personnel",
        placeholder: "e.g., CTO, key inventors, developers",
      },
      {
        id: "ipOwners",
        type: "party_role",
        label: "IP Owners / Licensors",
        placeholder: "e.g., Patent holder, software owner",
        description: "Current owners of the IP",
      },
      {
        id: "licensees",
        type: "counterparty",
        label: "Existing Licensees",
        placeholder: "e.g., Licensee Co Ltd",
        description: "Parties with existing license rights",
        amountLabel: "License Fee",
        amountPlaceholder: "e.g., R5m p.a.",
      },
      {
        id: "technologyProviders",
        type: "tags",
        label: "Technology Providers / Vendors",
        placeholder: "e.g., Software vendors, cloud providers",
      },
      {
        id: "regulators",
        type: "tags",
        label: "Key Authorities",
        placeholder: "e.g., CIPC, Information Regulator",
        suggestions: ["CIPC", "Information Regulator", "ICASA"],
      },
      {
        id: "other",
        type: "party_role",
        label: "Other Parties",
        placeholder: "e.g., R&D partners, universities",
      },
    ],
    shareholderSection: {
      visible: true,
      title: "Shareholders",
      description: "Add details of the shareholding structure for the target entity.",
      entityLabel: "Target Entity",
      entityPlaceholder: "e.g., Tech Innovations (Pty) Ltd",
      showBEECalculation: false,
      showPrePost: false,
    },
  },

  // ===== ENERGY & POWER =====
  energy_power: {
    title: "Project Parties",
    subtitle: "Identify key parties to the energy/power project.",
    fields: [
      {
        id: "keyPersonnel",
        type: "tags",
        label: "Key Personnel",
        placeholder: "e.g., Project director, plant manager",
      },
      {
        id: "offtakers",
        type: "counterparty",
        label: "Offtakers / PPA Counterparties",
        placeholder: "e.g., Eskom, private offtaker",
        description: "Parties purchasing power output",
        amountLabel: "PPA Value",
        amountPlaceholder: "e.g., R2bn over term",
      },
      {
        id: "epcContractor",
        type: "counterparty",
        label: "EPC Contractor",
        placeholder: "e.g., Construction JV",
        description: "Engineering, procurement, construction contractor",
        amountLabel: "EPC Price",
        amountPlaceholder: "e.g., R1.5bn",
      },
      {
        id: "omProvider",
        type: "counterparty",
        label: "O&M Provider",
        placeholder: "e.g., Operations company",
        description: "Operations and maintenance provider",
        amountLabel: "O&M Fee p.a.",
        amountPlaceholder: "e.g., R50m",
      },
      {
        id: "lenders",
        type: "lender",
        label: "Project Lenders",
        placeholder: "e.g., DFIs, commercial banks, ECAs",
        amountLabel: "Facility Amount",
        amountPlaceholder: "e.g., R1bn",
      },
      {
        id: "regulators",
        type: "tags",
        label: "Energy Regulators",
        placeholder: "e.g., NERSA, DMRE",
        suggestions: ["NERSA", "Eskom", "DMRE", "IPP Office", "Municipality"],
      },
      {
        id: "landowners",
        type: "party_role",
        label: "Landowners / Communities",
        placeholder: "e.g., Farm owner, local community",
      },
      {
        id: "other",
        type: "party_role",
        label: "Other Parties",
        placeholder: "e.g., Grid operator, equipment suppliers",
      },
    ],
    shareholderSection: {
      visible: true,
      title: "Project Company Shareholders",
      description: "Add details of the SPV shareholding structure.",
      entityLabel: "Project Company / SPV",
      entityPlaceholder: "e.g., Solar Power SPV (Pty) Ltd",
      showBEECalculation: true,
      showPrePost: false,
    },
  },

  // ===== INFRASTRUCTURE & PPP =====
  infrastructure_ppp: {
    title: "Project Parties",
    subtitle: "Identify key parties to the infrastructure/PPP project.",
    fields: [
      {
        id: "keyPersonnel",
        type: "tags",
        label: "Key Personnel",
        placeholder: "e.g., Project director, concession manager",
      },
      {
        id: "governmentAuthority",
        type: "party_role",
        label: "Government Authority / Contracting Party",
        placeholder: "e.g., National Department of X",
        description: "Public sector party to the PPP",
      },
      {
        id: "constructionContractor",
        type: "counterparty",
        label: "Construction Contractor",
        placeholder: "e.g., Construction JV",
        amountLabel: "Contract Value",
        amountPlaceholder: "e.g., R5bn",
      },
      {
        id: "facilitiesManager",
        type: "counterparty",
        label: "Facilities Manager / Operator",
        placeholder: "e.g., FM Company Ltd",
        amountLabel: "O&M Fee p.a.",
        amountPlaceholder: "e.g., R100m",
      },
      {
        id: "lenders",
        type: "lender",
        label: "Project Financiers",
        placeholder: "e.g., DFIs, infrastructure funds",
        amountLabel: "Facility Amount",
        amountPlaceholder: "e.g., R3bn",
      },
      {
        id: "regulators",
        type: "tags",
        label: "Government Bodies",
        placeholder: "e.g., National Treasury",
        suggestions: ["National Treasury", "PPP Unit", "GTAC", "Sector Department"],
      },
      {
        id: "other",
        type: "party_role",
        label: "Other Parties",
        placeholder: "e.g., Subcontractors, affected communities",
      },
    ],
    shareholderSection: {
      visible: true,
      title: "SPV / Concessionaire Shareholders",
      description: "Add details of the project company shareholding.",
      entityLabel: "SPV / Concessionaire",
      entityPlaceholder: "e.g., Infrastructure SPV Ltd",
      showBEECalculation: true,
      showPrePost: false,
    },
  },

  // ===== CAPITAL MARKETS =====
  capital_markets: {
    title: "Transaction Parties",
    subtitle: "Identify key parties to the capital markets transaction.",
    fields: [
      {
        id: "keyExecutives",
        type: "tags",
        label: "Key Executives",
        placeholder: "e.g., CEO, CFO, Company Secretary",
      },
      {
        id: "existingShareholders",
        type: "counterparty",
        label: "Existing / Selling Shareholders",
        placeholder: "e.g., Founding shareholder, PE fund",
        description: "Major shareholders or those selling",
        amountLabel: "Shareholding %",
        amountPlaceholder: "e.g., 25%",
      },
      {
        id: "cornerstoneInvestors",
        type: "counterparty",
        label: "Cornerstone / Anchor Investors",
        placeholder: "e.g., PIC, Allan Gray",
        description: "Committed investors",
        amountLabel: "Commitment",
        amountPlaceholder: "e.g., R500m",
      },
      {
        id: "underwriters",
        type: "lender",
        label: "Underwriters / Sponsors",
        placeholder: "e.g., RMB, Standard Bank",
        description: "Banks underwriting the issue",
        amountLabel: "Underwriting",
        amountPlaceholder: "e.g., R1bn",
      },
      {
        id: "advisors",
        type: "tags",
        label: "Transaction Advisors",
        placeholder: "e.g., Legal advisors, reporting accountants",
      },
      {
        id: "regulators",
        type: "tags",
        label: "Market Regulators",
        placeholder: "e.g., JSE, FSCA",
        suggestions: ["JSE", "FSCA", "CIPC", "TRP"],
      },
      {
        id: "other",
        type: "party_role",
        label: "Other Parties",
        placeholder: "e.g., Transfer secretaries, trustees",
      },
    ],
    shareholderSection: {
      visible: true,
      title: "Shareholding (Pre/Post Transaction)",
      description: "Add details of the shareholding structure pre and post transaction.",
      entityLabel: "Issuer",
      entityPlaceholder: "e.g., Listed Company Ltd",
      showBEECalculation: false,
      showPrePost: true,
    },
  },

  // ===== RESTRUCTURING & INSOLVENCY =====
  restructuring_insolvency: {
    title: "Key Parties",
    subtitle: "Identify key parties to the restructuring/insolvency matter.",
    fields: [
      {
        id: "keyPersonnel",
        type: "tags",
        label: "Key Personnel",
        placeholder: "e.g., BRP, liquidator, management",
      },
      {
        id: "securedCreditors",
        type: "lender",
        label: "Secured Creditors",
        placeholder: "e.g., Senior lenders, bondholders",
        description: "Creditors with security",
        amountLabel: "Claim Amount",
        amountPlaceholder: "e.g., R500m",
      },
      {
        id: "unsecuredCreditors",
        type: "lender",
        label: "Unsecured / Concurrent Creditors",
        placeholder: "e.g., Trade creditors, SARS",
        description: "Creditors without security",
        amountLabel: "Claim Amount",
        amountPlaceholder: "e.g., R100m",
      },
      {
        id: "potentialInvestors",
        type: "party_role",
        label: "Potential Investors / Acquirers",
        placeholder: "e.g., Distressed investor",
        description: "Parties interested in acquiring assets",
      },
      {
        id: "criticalSuppliers",
        type: "tags",
        label: "Critical Suppliers",
        placeholder: "e.g., Essential service providers",
      },
      {
        id: "regulators",
        type: "tags",
        label: "Key Authorities",
        placeholder: "e.g., Master, CIPC",
        suggestions: ["CIPC", "Master of the High Court", "Competition Commission", "SARS"],
      },
      {
        id: "other",
        type: "party_role",
        label: "Other Parties",
        placeholder: "e.g., Employees, creditor committees",
      },
    ],
    shareholderSection: {
      visible: false,
      title: "Shareholders",
      description: "",
      entityLabel: "",
      entityPlaceholder: "",
    },
  },

  // ===== PRIVATE EQUITY & VC =====
  private_equity_vc: {
    title: "Transaction Parties",
    subtitle: "Identify key parties to the PE/VC investment.",
    fields: [
      {
        id: "management",
        type: "tags",
        label: "Key Management",
        placeholder: "e.g., Founders, CEO, management team",
      },
      {
        id: "existingShareholders",
        type: "counterparty",
        label: "Existing Shareholders / Sellers",
        placeholder: "e.g., Founder, early investor",
        description: "Current shareholders",
        amountLabel: "Shareholding",
        amountPlaceholder: "e.g., 40%",
      },
      {
        id: "coInvestors",
        type: "counterparty",
        label: "Co-Investors",
        placeholder: "e.g., Co-investing fund",
        description: "Other investors in the round",
        amountLabel: "Investment",
        amountPlaceholder: "e.g., R50m",
      },
      {
        id: "lenders",
        type: "lender",
        label: "Debt Providers",
        placeholder: "e.g., Mezzanine provider, bank",
        description: "Providers of debt financing",
        amountLabel: "Facility",
        amountPlaceholder: "e.g., R100m",
      },
      {
        id: "suppliers",
        type: "tags",
        label: "Key Vendors / Suppliers",
        placeholder: "e.g., Critical service providers",
      },
      {
        id: "customers",
        type: "counterparty",
        label: "Key Customers",
        placeholder: "e.g., Enterprise clients, key accounts",
        amountLabel: "Revenue",
        amountPlaceholder: "e.g., R20m p.a.",
      },
      {
        id: "regulators",
        type: "tags",
        label: "Key Regulators",
        placeholder: "e.g., Competition Commission",
        suggestions: ["Competition Commission", "SARB", "FSCA", "Sector Regulator"],
      },
      {
        id: "other",
        type: "party_role",
        label: "Other Parties",
        placeholder: "e.g., Advisors, Board members",
      },
    ],
    shareholderSection: {
      visible: true,
      title: "Cap Table",
      description: "Add details of the pre and post-investment capitalization.",
      entityLabel: "Target Company",
      entityPlaceholder: "e.g., Growth Co (Pty) Ltd",
      showBEECalculation: false,
      showPrePost: true,
    },
  },

  // ===== FINANCIAL SERVICES =====
  financial_services: {
    title: "Transaction Parties",
    subtitle: "Identify key parties to the financial services transaction.",
    fields: [
      {
        id: "keyExecutives",
        type: "tags",
        label: "Key Executives",
        placeholder: "e.g., CEO, CFO, Chief Risk Officer",
      },
      {
        id: "targetInstitution",
        type: "party_role",
        label: "Target Institution / Counterparty",
        placeholder: "e.g., Insurance Company Ltd",
        description: "The financial institution involved",
      },
      {
        id: "keyClients",
        type: "counterparty",
        label: "Key Clients / Policyholders",
        placeholder: "e.g., Major depositors, corporate clients",
        description: "Significant clients by AUM or premium",
        amountLabel: "AUM / Premium",
        amountPlaceholder: "e.g., R1bn",
      },
      {
        id: "fundingProviders",
        type: "lender",
        label: "Funding Sources / Capital Providers",
        placeholder: "e.g., Interbank lenders, shareholders",
        amountLabel: "Facility",
        amountPlaceholder: "e.g., R500m",
      },
      {
        id: "serviceProviders",
        type: "tags",
        label: "Key Service Providers",
        placeholder: "e.g., IT providers, outsourced services",
      },
      {
        id: "regulators",
        type: "tags",
        label: "Financial Regulators",
        placeholder: "e.g., SARB, PA, FSCA",
        suggestions: ["SARB", "FSCA", "Prudential Authority", "NCR", "Information Regulator"],
      },
      {
        id: "other",
        type: "party_role",
        label: "Other Parties",
        placeholder: "e.g., Rating agencies, industry bodies",
      },
    ],
    shareholderSection: {
      visible: true,
      title: "Shareholders",
      description: "Add details of the shareholding structure.",
      entityLabel: "Target Entity",
      entityPlaceholder: "e.g., Financial Services Provider Ltd",
      showBEECalculation: false,
      showPrePost: false,
    },
  },

};

export const KEY_STAKEHOLDER_CONFIG: Record<TransactionTypeCode, StakeholderConfig> = {
  mining_resources: {
    individuals: { label: "Key Individuals", placeholder: "e.g., Mine Manager, CEO..." },
    suppliers: { label: "Key Contractors", placeholder: "e.g., Mining contractors, equipment suppliers..." },
    customers: { label: "Key Offtakers", placeholder: "e.g., Commodity traders, smelters..." },
    lenders: { label: "Key Financiers", placeholder: "e.g., Project finance lenders, DFIs..." },
    regulators: { label: "Key Regulators", placeholder: "e.g., DMRE, DEA..." },
    other: { label: "Other", placeholder: "e.g., Community trusts, JV partners..." },
  },
  ma_corporate: {
    individuals: { label: "Key Individuals", placeholder: "e.g., CEO, CFO, Key executives..." },
    suppliers: { label: "Key Suppliers", placeholder: "e.g., Critical suppliers..." },
    customers: { label: "Key Customers", placeholder: "e.g., Major customers, key accounts..." },
    lenders: { label: "Key Lenders", placeholder: "e.g., Banks, bondholders..." },
    regulators: { label: "Key Regulators", placeholder: "e.g., Competition Commission, CIPC..." },
    other: { label: "Other", placeholder: "e.g., JV partners, licensors..." },
  },
  banking_finance: {
    individuals: { label: "Key Executives / Signatories", placeholder: "e.g., CFO, Treasury Head, Authorized signatories..." },
    suppliers: { label: "Advisors / Service Providers", placeholder: "e.g., Legal advisors, valuers, auditors..." },
    customers: { label: "Security Providers / Guarantors", placeholder: "e.g., ABC Holdings (Pty) Ltd" },
    lenders: { label: "Existing Lenders / Syndicate", placeholder: "e.g., Standard Bank, RMB..." },
    regulators: { label: "Key Regulators", placeholder: "e.g., SARB, FSCA, NCR..." },
    other: { label: "Other", placeholder: "e.g., Account bank, process agent..." },
  },
  real_estate: {
    individuals: { label: "Key Individuals", placeholder: "e.g., Property manager, directors..." },
    suppliers: { label: "Key Service Providers", placeholder: "e.g., Managing agents, maintenance contractors..." },
    customers: { label: "Key Tenants", placeholder: "e.g., Anchor tenants, major lessees..." },
    lenders: { label: "Key Financiers", placeholder: "e.g., Mortgage providers, development funders..." },
    regulators: { label: "Key Authorities", placeholder: "e.g., Municipality, Deeds Office..." },
    other: { label: "Other", placeholder: "e.g., Body corporate, neighbors..." },
  },
  competition_regulatory: {
    individuals: { label: "Key Executives", placeholder: "e.g., CEOs of merging parties..." },
    suppliers: { label: "Key Suppliers", placeholder: "e.g., Common suppliers..." },
    customers: { label: "Key Customers", placeholder: "e.g., Overlapping customers..." },
    lenders: { label: "Key Financiers", placeholder: "e.g., Transaction funders..." },
    regulators: { label: "Regulatory Bodies", placeholder: "e.g., Competition Commission, Tribunal..." },
    other: { label: "Other", placeholder: "e.g., Competitors, industry bodies..." },
  },
  employment_labor: {
    individuals: { label: "Key Personnel", placeholder: "e.g., HR Director, affected executives..." },
    suppliers: { label: "Service Providers", placeholder: "e.g., Payroll providers, benefits administrators..." },
    customers: { label: "N/A", placeholder: "Not typically applicable..." },
    lenders: { label: "N/A", placeholder: "Not typically applicable..." },
    regulators: { label: "Labor Authorities", placeholder: "e.g., CCMA, Department of Labour..." },
    other: { label: "Other", placeholder: "e.g., Trade unions, workplace forums..." },
  },
  ip_technology: {
    individuals: { label: "Key Personnel", placeholder: "e.g., CTO, key inventors..." },
    suppliers: { label: "Technology Providers", placeholder: "e.g., Software vendors, licensors..." },
    customers: { label: "Key Licensees", placeholder: "e.g., Technology licensees, users..." },
    lenders: { label: "Key Financiers", placeholder: "e.g., VC investors, IP-backed lenders..." },
    regulators: { label: "Key Authorities", placeholder: "e.g., CIPC, Information Regulator..." },
    other: { label: "Other", placeholder: "e.g., R&D partners, universities..." },
  },
  bee_transformation: {
    individuals: { label: "Key Individuals", placeholder: "e.g., BEE partner principals..." },
    suppliers: { label: "Enterprise Development", placeholder: "e.g., ED beneficiaries, suppliers..." },
    customers: { label: "Key Clients", placeholder: "e.g., Preferential procurement sources..." },
    lenders: { label: "Transaction Funders", placeholder: "e.g., Vendor finance, banks..." },
    regulators: { label: "Verification Bodies", placeholder: "e.g., B-BBEE Commission, verification agencies..." },
    other: { label: "Other", placeholder: "e.g., Trusts, ESOP participants..." },
  },
  energy_power: {
    individuals: { label: "Key Personnel", placeholder: "e.g., Project director, plant manager..." },
    suppliers: { label: "EPC / O&M Contractors", placeholder: "e.g., EPC contractor, O&M provider..." },
    customers: { label: "Offtakers", placeholder: "e.g., Eskom, private offtakers..." },
    lenders: { label: "Project Lenders", placeholder: "e.g., DFIs, commercial banks, ECAs..." },
    regulators: { label: "Energy Regulators", placeholder: "e.g., NERSA, DMRE, IPP Office..." },
    other: { label: "Other", placeholder: "e.g., Grid operator, landowners, communities..." },
  },
  infrastructure_ppp: {
    individuals: { label: "Key Personnel", placeholder: "e.g., Project director, concession manager..." },
    suppliers: { label: "Construction / O&M", placeholder: "e.g., Construction JV, facilities manager..." },
    customers: { label: "End Users / Authority", placeholder: "e.g., Government department, end users..." },
    lenders: { label: "Project Financiers", placeholder: "e.g., DFIs, infrastructure funds..." },
    regulators: { label: "Government Bodies", placeholder: "e.g., National Treasury, PPP Unit..." },
    other: { label: "Other", placeholder: "e.g., Subcontractors, affected communities..." },
  },
  capital_markets: {
    individuals: { label: "Key Executives", placeholder: "e.g., CEO, CFO, Company Secretary..." },
    suppliers: { label: "Transaction Advisors", placeholder: "e.g., Sponsor, legal advisors, auditors..." },
    customers: { label: "Key Investors", placeholder: "e.g., Cornerstone investors, existing shareholders..." },
    lenders: { label: "Underwriters", placeholder: "e.g., Underwriting banks..." },
    regulators: { label: "Market Regulators", placeholder: "e.g., JSE, FSCA, TRP..." },
    other: { label: "Other", placeholder: "e.g., Transfer secretaries, trustees..." },
  },
  restructuring_insolvency: {
    individuals: { label: "Key Personnel", placeholder: "e.g., BRP, liquidator, management..." },
    suppliers: { label: "Critical Suppliers", placeholder: "e.g., Essential service providers..." },
    customers: { label: "Key Customers", placeholder: "e.g., Major debtors, key accounts..." },
    lenders: { label: "Creditors", placeholder: "e.g., Secured creditors, DIP lenders..." },
    regulators: { label: "Key Authorities", placeholder: "e.g., Master, CIPC..." },
    other: { label: "Other", placeholder: "e.g., Employees, creditor committees..." },
  },
  private_equity_vc: {
    individuals: { label: "Key Management", placeholder: "e.g., Founders, CEO, management team..." },
    suppliers: { label: "Key Vendors", placeholder: "e.g., Critical service providers..." },
    customers: { label: "Key Customers", placeholder: "e.g., Enterprise clients, key accounts..." },
    lenders: { label: "Co-Investors / Lenders", placeholder: "e.g., Co-investors, mezzanine providers..." },
    regulators: { label: "Key Regulators", placeholder: "e.g., Competition Commission, sector regulators..." },
    other: { label: "Other", placeholder: "e.g., Existing shareholders, advisors..." },
  },
  financial_services: {
    individuals: { label: "Key Executives", placeholder: "e.g., CEO, CFO, Chief Risk Officer..." },
    suppliers: { label: "Service Providers", placeholder: "e.g., IT providers, outsourced services..." },
    customers: { label: "Key Clients", placeholder: "e.g., Major depositors, policyholders..." },
    lenders: { label: "Funding Sources", placeholder: "e.g., Interbank lenders, capital providers..." },
    regulators: { label: "Financial Regulators", placeholder: "e.g., SARB, PA, FSCA..." },
    other: { label: "Other", placeholder: "e.g., Industry bodies, rating agencies..." },
  },
};
