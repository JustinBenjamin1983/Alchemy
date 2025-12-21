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

export interface DDProjectSetup {
  // Step 1: Transaction Basics
  transactionType: TransactionTypeCode | null;
  transactionName: string;
  clientName: string;
  targetEntityName: string;
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

  // Step 4: Key Stakeholders
  targetCompanyName: string;
  keyIndividuals: string[];
  keySuppliers: string[];
  keyCustomers: CounterpartyStakeholder[];
  keyLenders: LenderStakeholder[];
  keyRegulators: string[];
  keyOther: OtherStakeholder[];

  // Step 4: Shareholders
  shareholderEntityName: string;
  shareholders: Shareholder[];

  // Step 5: Documents
  uploadedFile: File | null;
}

export const DEFAULT_PROJECT_SETUP: DDProjectSetup = {
  transactionType: null,
  transactionName: "",
  clientName: "",
  targetEntityName: "",
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
  keyIndividuals: [],
  keySuppliers: [],
  keyCustomers: [],
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
