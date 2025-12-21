"""
Add Chain-of-Thought (CoT) questions to all blueprint YAML files.
Run this script once to update all blueprints with CoT reasoning questions.
"""
import os
import yaml

# CoT questions for each transaction type
COT_QUESTIONS = {
    "ma_corporate": {
        "corporate_governance": [
            "Is the company validly incorporated and are shares validly issued?",
            "What shareholder approvals are required per MOI and have they been obtained?",
            "Are there any restrictions on share transfers that affect the transaction?",
            "What pre-emption rights exist and have they been waived?",
            "Are there any shareholders agreements with tag/drag rights?",
        ],
        "change_of_control": [
            "What is the exact CoC definition in this document? Does 100% share sale meet it?",
            "Is termination automatic or discretionary upon CoC?",
            "What is the commercial value of this contract - what % of revenue depends on it?",
            "Can consent realistically be obtained pre-closing? What leverage does counterparty have?",
            "What are the financial consequences (liquidated damages, lost revenue)?",
            "What notice periods apply and what is the cure opportunity?",
        ],
        "material_contracts": [
            "What is this contract worth to the business (revenue/cost)?",
            "Does it contain assignment/CoC restrictions? Is consent required?",
            "What is the remaining term and renewal options?",
            "Are there any exclusivity or non-compete provisions?",
            "What termination rights exist and what are the consequences?",
            "Are there any minimum volume or take-or-pay obligations?",
        ],
        "financial_position": [
            "Are the financial statements fairly stated without qualification?",
            "What are the material off-balance sheet liabilities or arrangements?",
            "What is the working capital position and any trapped cash?",
            "Are there any contingent liabilities that could crystallize?",
            "What inter-company balances need to be settled on completion?",
        ],
        "debt_security": [
            "What is the total debt outstanding and who are the lenders?",
            "Does the facility contain CoC/event of default triggers?",
            "What is the acceleration exposure (principal + interest + fees)?",
            "What security has been granted and over which assets?",
            "Are there cross-default provisions that could cascade?",
            "Is lender consent required and likely to be obtained?",
        ],
        "employment": [
            "What are the CoC provisions in executive contracts?",
            "What is the total severance exposure on CoC?",
            "Are there key person dependencies? What retention arrangements exist?",
            "Are there any pending retrenchments, disputes, or strikes?",
            "What union/collective agreement obligations apply?",
        ],
        "regulatory": [
            "What regulatory licenses are required and are they in good standing?",
            "Does the transaction require Competition Commission approval?",
            "Are there any pending regulatory investigations?",
            "What happens if regulatory approval is refused or delayed?",
        ],
    },

    "real_estate": {
        "title_ownership": [
            "Is the seller the registered owner per the title deed?",
            "Are there any mortgage bonds, servitudes, or conditions registered?",
            "Are there any caveats, interdicts, or expropriation notices?",
            "What mineral rights apply to the property?",
            "Are there any boundary disputes or encroachments?",
        ],
        "zoning_land_use": [
            "What is the current zoning and is the use compliant?",
            "Are there valid building plans and occupation certificates for all structures?",
            "Are there any building contraventions or illegal structures?",
            "What development rights and bulk allowances apply?",
            "Are there any heritage or environmental restrictions?",
        ],
        "rates_taxes": [
            "Are all municipal rates and taxes paid up to date?",
            "Can a rates clearance certificate be obtained?",
            "What is the municipal valuation vs purchase price?",
            "Are there any special levies or rating area charges?",
        ],
        "leases_tenancies": [
            "What leases are in place and what is the total rental income?",
            "Do leases contain CoC or assignment provisions requiring consent?",
            "What is the lease expiry profile and renewal options?",
            "Are there any tenant arrears or disputes?",
            "What tenant deposits are held and how will they transfer?",
        ],
        "physical_condition": [
            "What is the age and condition of buildings?",
            "What capital expenditure is required (deferred maintenance)?",
            "Are there any asbestos, hazardous materials, or contamination issues?",
            "Are all services (water, electricity, sewer) connected and compliant?",
            "What is the fire and safety compliance status?",
        ],
        "environmental": [
            "Is there any soil or groundwater contamination?",
            "What environmental authorizations are required?",
            "What is the flood risk and stormwater management?",
            "Are there any protected species or ecosystems?",
        ],
    },

    "energy_power": {
        "generation_license": [
            "Is there a valid NERSA generation license and what are its conditions?",
            "What is the licensed capacity and when does it expire?",
            "Are there any pending license amendments or NERSA investigations?",
            "Is IRP allocation secured for the project?",
            "What grid code compliance requirements apply?",
        ],
        "power_purchase_agreement": [
            "What is the PPA term and tariff structure?",
            "Does the PPA contain CoC provisions? Is Eskom consent required?",
            "What are the termination rights and consequences?",
            "What minimum generation or availability requirements apply?",
            "What curtailment provisions exist and what is the compensation?",
            "Has COD been achieved? Any outstanding milestones?",
        ],
        "reipppp_compliance": [
            "Under which REIPPPP bid window was the project awarded?",
            "What economic development (ED) obligations apply and is compliance on track?",
            "What local content requirements exist?",
            "What community ownership requirements apply?",
            "What are the penalties for ED non-compliance?",
        ],
        "project_contracts": [
            "Is there an EPC contract and what is its status (warranties, defects)?",
            "What O&M agreement is in place and what are performance guarantees?",
            "Are there any disputes with contractors or suppliers?",
            "What equipment warranties remain in force?",
        ],
        "grid_connection": [
            "Is there a grid connection agreement and what is contracted capacity?",
            "What grid constraints or curtailment risks exist?",
            "What use-of-system charges and grid fees apply?",
            "Is wheeling available for private offtake?",
        ],
        "land_surface_rights": [
            "Is land owned or leased? Does lease term align with PPA?",
            "What rental/royalty arrangements apply?",
            "Are there any community land claims?",
            "What land rehabilitation obligations exist?",
        ],
        "environmental": [
            "Is there a valid Environmental Authorization and Water Use License?",
            "What conditions attach and is compliance on track?",
            "What decommissioning obligations and financial provision exist?",
        ],
    },

    "private_equity_vc": {
        "investment_structure": [
            "Is the investment structure appropriate and tax efficient?",
            "What instruments are being used (ordinary, preference, convertible)?",
            "What valuation methodology was used and are assumptions supportable?",
            "What anti-dilution and pre-emption rights will apply?",
            "What governance rights are appropriate for investment size?",
        ],
        "founder_management": [
            "What is the quality and track record of founders/management?",
            "Are management incentives appropriately structured and aligned?",
            "What restraint of trade and IP assignment provisions exist?",
            "What key person dependencies exist and is there succession planning?",
            "Are there any shareholder or management disputes?",
            "What are management intentions post-investment?",
        ],
        "business_commercial": [
            "Is the business model proven and unit economics sustainable?",
            "What is the market size, growth potential, and competitive dynamics?",
            "What are the key competitive advantages and barriers to entry?",
            "What is the customer concentration risk?",
            "What technology risks and technical debt exist?",
        ],
        "financial_dd": [
            "What is the quality of earnings and what normalization adjustments apply?",
            "Are financial projections achievable and assumptions reasonable?",
            "What is the working capital position and cash burn rate?",
            "Are there any debt-like items or off-balance sheet arrangements?",
            "Are there related party transactions requiring adjustment?",
        ],
        "legal_corporate": [
            "Is the corporate structure clean and cap table accurate?",
            "Are there existing shareholder arrangements affecting the investment?",
            "Is IP properly owned, registered, and protected?",
            "Are there any pending litigation matters?",
            "Is the company POPIA compliant?",
        ],
        "exit_liquidity": [
            "What are realistic exit routes and potential acquirers?",
            "What is expected investment horizon and target returns?",
            "Are drag-along and tag-along provisions appropriate?",
            "What are the liquidation preference and waterfall mechanics?",
            "Are there any contractual or regulatory restrictions on exit?",
        ],
        "regulatory": [
            "Is Competition Commission approval required?",
            "Are there any exchange control or SARB considerations?",
            "Are there any B-BBEE considerations affecting the investment?",
        ],
    },

    "financial_services": {
        "regulatory_licensing": [
            "What FSCA/PA licenses does the target hold and are they in good standing?",
            "What regulatory approvals are required for CoC and what is the timeline?",
            "Are there any pending regulatory investigations or enforcement actions?",
            "Are key individuals fit and proper as required?",
            "Have there been any regulatory sanctions or enforcement history?",
        ],
        "prudential_capital": [
            "Does the target meet capital adequacy / solvency requirements?",
            "What is the liquidity position (LCR, NSFR)?",
            "Are there any large exposure or concentration limit breaches?",
            "How will the transaction impact consolidated capital position?",
        ],
        "conduct_compliance": [
            "Is the target compliant with TCF outcomes?",
            "What is the customer complaints profile and resolution effectiveness?",
            "Are product governance processes compliant?",
            "Are conflicts of interest appropriately managed?",
        ],
        "aml_cft": [
            "Is the RMCP adequate and current?",
            "Are KYC/CDD processes compliant with FIC Act?",
            "Is transaction monitoring adequate and are STRs being filed?",
            "Are sanctions screening processes effective?",
            "Have there been any FIC findings or AML investigations?",
        ],
        "technology_cyber": [
            "What is the state of core systems and any material dependencies?",
            "Is cybersecurity posture adequate? Any material breaches?",
            "Are BCP/DR arrangements adequate and tested?",
            "Are third-party/outsourcing arrangements properly managed?",
        ],
        "insurance_specific": [
            "Are insurance reserves and technical provisions adequate?",
            "What is the reinsurance programme and counterparty exposure?",
            "What is the claims experience and loss ratio trend?",
        ],
        "banking_specific": [
            "What is the loan book quality and NPL/impairment coverage?",
            "Are credit risk management and underwriting standards adequate?",
            "What is the funding profile and depositor concentration?",
        ],
        "asset_management_specific": [
            "What are AUM trends, flows, and performance track record?",
            "Are mandate constraints being complied with?",
            "What is fee structure and revenue sustainability?",
            "Are there key person dependencies in investment team?",
        ],
    },

    "ip_technology": {
        "ip_ownership": [
            "What registered IP rights does the target own (patents, trademarks, copyright)?",
            "Is the chain of title complete - have all assignments been done?",
            "Has all IP been assigned from founders, employees, and contractors?",
            "Is there any IP held personally by founders that should be in the company?",
            "Are there any joint ownership or co-development arrangements?",
            "What trade secrets exist and how are they protected?",
        ],
        "ip_licensing_inbound": [
            "What IP licenses does the business rely on?",
            "Do licenses survive CoC or require consent?",
            "What open-source licenses are in use? Any GPL/copyleft obligations?",
            "Is third-party software properly licensed?",
            "Are there any minimum royalty or audit rights?",
        ],
        "ip_licensing_outbound": [
            "What IP has been licensed to third parties?",
            "Are any licenses exclusive? What restrictions apply?",
            "Do any licenses create obligations on sale?",
        ],
        "ip_disputes": [
            "Are there any pending IP infringement claims or cease and desist letters?",
            "Has freedom-to-operate analysis been conducted?",
            "What is the IP insurance position?",
        ],
        "technology_software": [
            "What is the core technology stack and any legacy issues?",
            "What is the technical debt position?",
            "Is source code held in escrow?",
            "What cloud or infrastructure dependencies exist?",
            "Are there any scalability limitations?",
        ],
        "data_privacy": [
            "Is the company POPIA compliant? Is Information Officer registered?",
            "What personal data is processed and on what legal basis?",
            "Have there been any data breaches?",
            "Are there adequate data processing agreements with third parties?",
            "Are there any cross-border data transfers or GDPR exposure?",
        ],
        "cybersecurity": [
            "Has cybersecurity assessment been conducted? Any certifications (ISO 27001, SOC2)?",
            "What security incidents have occurred?",
            "Is there adequate cyber insurance?",
        ],
    },

    "infrastructure_ppp": {
        "concession_agreement": [
            "What is the concession term and remaining duration?",
            "Does the concession contain CoC provisions? Is authority consent required?",
            "What step-in rights does the authority have?",
            "What termination rights exist and what is the compensation formula?",
            "What performance standards and penalty regimes apply?",
            "What extension or renewal options exist?",
        ],
        "revenue_tariffs": [
            "What is the revenue model (availability, usage, combination)?",
            "What tariff/unitary payment structure and indexation applies?",
            "What demand/volume risk exists? Any minimum revenue guarantees?",
            "What is the payment track record of the authority?",
            "Are there any tariff disputes or regulatory reviews pending?",
        ],
        "treasury_approvals": [
            "Have all required Treasury approvals been obtained?",
            "Does CoC require Treasury consent?",
            "Are there any PFMA/MFMA compliance issues?",
            "What conditions were attached to Treasury approval?",
        ],
        "construction_assets": [
            "What is the construction status? Any outstanding claims?",
            "What is the condition of infrastructure assets?",
            "What lifecycle replacement obligations exist?",
            "What handback condition requirements apply?",
        ],
        "bee_transformation": [
            "What BEE ownership requirements apply to the concession?",
            "What happens to BEE compliance on CoC?",
            "What local content and procurement obligations apply?",
        ],
        "project_finance": [
            "What project finance facilities are in place?",
            "Is lender consent required for CoC?",
            "What are the debt service coverage requirements?",
            "Are there any covenant breaches or waivers?",
        ],
    },

    "bee_transformation": {
        "ownership_structure": [
            "What is the current HDSA ownership percentage?",
            "How is ownership calculated (flow-through, modified flow-through)?",
            "Are there any deemed ownership provisions?",
            "What is the net value calculation for BEE ownership?",
        ],
        "transaction_impact": [
            "How will the transaction affect BEE ownership levels?",
            "Are there minimum BEE thresholds that must be maintained?",
            "Are there any lock-in periods or restrictions on BEE shareholder transfers?",
            "What are the consequences of falling below ownership thresholds?",
        ],
        "sector_requirements": [
            "What sector code or charter applies?",
            "What ownership targets apply under the applicable code?",
            "Are there any fronting concerns?",
            "What verification requirements apply?",
        ],
        "management_control": [
            "What are the management control requirements?",
            "Are there board representation requirements?",
            "What employment equity requirements apply?",
        ],
        "enterprise_supplier": [
            "What enterprise and supplier development obligations exist?",
            "What preferential procurement requirements apply?",
            "What socio-economic development commitments exist?",
        ],
    },

    "banking_finance": {
        "facility_terms": [
            "What is the total facility size and current utilization?",
            "What are the interest rate terms and margin structure?",
            "What fees apply (commitment, arrangement, prepayment)?",
            "What is the maturity profile and amortization schedule?",
        ],
        "covenants": [
            "What financial covenants apply (DSCR, interest cover, leverage)?",
            "What is the current covenant compliance and headroom?",
            "Are there any covenant breaches or existing waivers?",
            "What are the consequences of covenant breach?",
        ],
        "security": [
            "What security package has been provided?",
            "What assets are subject to security?",
            "Are there any inter-creditor arrangements?",
            "What is the security enforcement process?",
        ],
        "change_of_control": [
            "Does the facility contain CoC triggers?",
            "What is the consequence of CoC (mandatory prepayment, event of default)?",
            "Is lender consent required and likely to be obtained?",
            "What is the refinancing exposure if facility is called?",
        ],
        "representations_warranties": [
            "What representations and warranties apply?",
            "Are there any repeating representations?",
            "What disclosure obligations exist?",
        ],
    },

    "restructuring_insolvency": {
        "financial_distress": [
            "What is the current liquidity position and cash runway?",
            "Is the company commercially or factually insolvent?",
            "What are the directors' duties given the financial position?",
            "What is the debt maturity profile and refinancing exposure?",
        ],
        "stakeholder_position": [
            "Who are the key creditors and what are their claims?",
            "What is the inter-creditor position and priority of claims?",
            "Are there any secured vs unsecured creditor conflicts?",
            "What is the employee and trade creditor exposure?",
        ],
        "restructuring_options": [
            "What restructuring options are available (business rescue, compromise)?",
            "What are the prospects of a successful restructuring?",
            "What stakeholder support exists for restructuring?",
            "What is the timeline and cost of restructuring?",
        ],
        "business_rescue": [
            "Has business rescue been commenced or is it contemplated?",
            "Who is the business rescue practitioner?",
            "What is the status of the business rescue plan?",
            "What creditor voting thresholds apply?",
        ],
        "asset_disposal": [
            "What assets are available for disposal?",
            "What is the likely realization value vs book value?",
            "Are there any restrictions on asset disposals?",
            "What is the process for asset sales?",
        ],
    },

    "competition_regulatory": {
        "merger_control": [
            "Does the transaction meet merger notification thresholds?",
            "What is the appropriate filing (small, intermediate, large)?",
            "What is the expected timeline for approval?",
            "Are there any competition concerns (market definition, market share)?",
        ],
        "competition_assessment": [
            "What is the relevant market definition?",
            "What are the combined market shares post-merger?",
            "Are there any vertical or conglomerate concerns?",
            "What is the likelihood of conditions being imposed?",
        ],
        "public_interest": [
            "What public interest considerations apply?",
            "Are there any employment impact concerns?",
            "What is the impact on HDSA ownership?",
            "Are there any industrial policy considerations?",
        ],
        "remedies": [
            "What behavioral or structural remedies might be required?",
            "What is the process for negotiating conditions?",
            "What monitoring requirements might apply?",
        ],
    },

    "employment_labor": {
        "employment_contracts": [
            "What are the key terms of executive employment contracts?",
            "What CoC provisions exist (acceleration, golden parachute)?",
            "What notice periods and severance terms apply?",
            "What restraint of trade provisions exist and are they enforceable?",
        ],
        "collective_agreements": [
            "What recognition and collective agreements are in place?",
            "What wage agreements apply and when do they expire?",
            "Are there any pending wage negotiations?",
            "What union relationship issues exist?",
        ],
        "retrenchments": [
            "Are there any pending or contemplated retrenchments?",
            "What Section 189 consultation requirements apply?",
            "What is the severance exposure?",
            "Are there any transfer of business (Section 197) implications?",
        ],
        "disputes_litigation": [
            "Are there any pending CCMA referrals or Labour Court matters?",
            "What is the history of industrial action?",
            "Are there any discrimination or unfair dismissal claims?",
        ],
        "employee_benefits": [
            "What pension and provident fund arrangements exist?",
            "What medical aid and other benefits apply?",
            "Are there any defined benefit pension liabilities?",
            "What share incentive schemes exist and what is the impact of CoC?",
        ],
    },

    "capital_markets": {
        "listing_requirements": [
            "What stock exchange listing requirements apply?",
            "Is the transaction a Category 1, 2, or 3 transaction?",
            "What shareholder approval requirements apply?",
            "What circular and announcement requirements exist?",
        ],
        "takeover_regulation": [
            "Does the Takeover Regulation Panel have jurisdiction?",
            "What mandatory offer thresholds apply?",
            "Are there any frustrating action restrictions?",
            "What fair and reasonable opinion requirements apply?",
        ],
        "securities_disclosure": [
            "What ongoing disclosure obligations apply?",
            "Are there any price sensitive information considerations?",
            "What insider trading restrictions apply?",
            "What SENS announcement requirements exist?",
        ],
        "scheme_arrangement": [
            "Is a scheme of arrangement the appropriate mechanism?",
            "What voting thresholds apply for scheme approval?",
            "What court processes are required?",
            "What is the timeline for scheme implementation?",
        ],
    },

    "mining_resources": {
        "mining_rights": [
            "Is the mining right valid and in good standing?",
            "What conditions are attached and are they being complied with?",
            "What is the SLP commitment status (% complete, arrears)?",
            "Does share transfer require Section 11 consent?",
            "What is typical DMRE processing time for consents?",
            "Is the mining work programme being followed?",
        ],
        "environmental": [
            "What is the status of EMPr and Environmental Authorization?",
            "What is the rehabilitation liability vs financial provision?",
            "Is the Water Use License current and compliant?",
            "Are there any pending environmental actions or directives?",
        ],
        "change_of_control": [
            "What is the exact CoC definition? Does 100% share sale trigger it?",
            "Is termination automatic or discretionary?",
            "What is the commercial value and operational importance?",
            "Can consent realistically be obtained?",
            "What are the financial consequences?",
        ],
        "financial_banking": [
            "What is the total debt and covenant compliance position?",
            "Do facilities contain CoC triggers?",
            "What is the acceleration exposure?",
            "Is lender consent required and obtainable?",
        ],
        "offtake_contracts": [
            "What offtake/supply agreements are in place?",
            "Do they contain CoC provisions requiring consent?",
            "What is the revenue concentration risk?",
            "What take-or-pay or minimum volume obligations exist?",
        ],
        "bee_mining_charter": [
            "What is the current HDSA ownership and Mining Charter compliance?",
            "How will the transaction affect BEE ownership?",
            "Are there minimum ownership thresholds to maintain?",
        ],
    },
}


def add_cot_to_blueprint(filepath: str, cot_questions: dict) -> bool:
    """Add CoT questions to a blueprint file."""
    try:
        with open(filepath, 'r') as f:
            content = f.read()

        # Check if CoT questions already exist
        if 'cot_questions:' in content:
            print(f"  Skipping {filepath} - already has CoT questions")
            return False

        # Build the CoT questions YAML section
        cot_yaml = "\n# Chain-of-Thought (CoT) reasoning questions by category\n"
        cot_yaml += "# These guide the AI to reason through findings step-by-step\n"
        cot_yaml += "cot_questions:\n"

        for category, questions in cot_questions.items():
            cot_yaml += f"  {category}:\n"
            for q in questions:
                # Escape quotes in questions
                q_escaped = q.replace('"', '\\"')
                cot_yaml += f'    - "{q_escaped}"\n'

        # Append to file
        with open(filepath, 'a') as f:
            f.write(cot_yaml)

        print(f"  Added CoT questions to {filepath}")
        return True

    except Exception as e:
        print(f"  Error processing {filepath}: {e}")
        return False


def main():
    """Add CoT questions to all blueprint files."""
    blueprints_dir = os.path.dirname(os.path.abspath(__file__))

    # Map of blueprint files to their CoT question keys
    file_mapping = {
        "ma_corporate.yaml": "ma_corporate",
        "real_estate.yaml": "real_estate",
        "energy_power.yaml": "energy_power",
        "private_equity_vc.yaml": "private_equity_vc",
        "financial_services.yaml": "financial_services",
        "ip_technology.yaml": "ip_technology",
        "infrastructure_ppp.yaml": "infrastructure_ppp",
        "bee_transformation.yaml": "bee_transformation",
        "banking_finance.yaml": "banking_finance",
        "restructuring_insolvency.yaml": "restructuring_insolvency",
        "competition_regulatory.yaml": "competition_regulatory",
        "employment_labor.yaml": "employment_labor",
        "capital_markets.yaml": "capital_markets",
        "mining_resources.yaml": "mining_resources",
        # mining_acquisition.yaml already has CoT questions
    }

    print("Adding CoT questions to blueprint files...")
    print("=" * 50)

    updated = 0
    skipped = 0

    for filename, cot_key in file_mapping.items():
        filepath = os.path.join(blueprints_dir, filename)

        if not os.path.exists(filepath):
            print(f"  File not found: {filename}")
            continue

        if cot_key not in COT_QUESTIONS:
            print(f"  No CoT questions defined for: {cot_key}")
            continue

        if add_cot_to_blueprint(filepath, COT_QUESTIONS[cot_key]):
            updated += 1
        else:
            skipped += 1

    print("=" * 50)
    print(f"Updated: {updated} files")
    print(f"Skipped: {skipped} files")
    print("Done!")


if __name__ == "__main__":
    main()
