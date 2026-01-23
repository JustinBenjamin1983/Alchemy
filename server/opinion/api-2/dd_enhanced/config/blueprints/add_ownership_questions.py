"""
Script to add universal ownership/regulatory questions to all blueprint YAML files.

Run this script to add the ownership_regulatory CoT questions to all blueprints.
This addresses the gap identified in the DD tool evaluation where BEE/ownership
analysis was missing.

Usage:
    python add_ownership_questions.py
"""

import yaml
from pathlib import Path

# Universal ownership questions that apply to ALL transaction types
UNIVERSAL_OWNERSHIP_QUESTIONS = [
    "What is the current ownership structure of the target, including all shareholders and their percentage holdings?",
    "How does this transaction change the ownership structure? What is the post-transaction ownership?",
    "What regulatory approvals or notifications are triggered by ownership changes (e.g., >15%, >25%, >49% thresholds)?",
    "Are there any ownership restrictions in constitutional documents, shareholder agreements, or regulatory conditions?",
    "What licenses, permits, or authorizations are dependent on the current ownership structure?",
    "What are the consequences of non-compliance with ownership-based regulatory requirements?",
]

# Industry-specific ownership questions
INDUSTRY_OWNERSHIP_QUESTIONS = {
    "mining_resources": [  # Also covers mining_acquisition
        "What is the current HDSA/BEE ownership percentage and how is it verified?",
        "How does the acquisition affect Mining Charter III compliance (minimum 30% HDSA)?",
        "If acquirer is non-HDSA, what mechanisms exist to restore BEE compliance (trusts, partners)?",
        "What is the current Mining Charter scorecard status and how will it be affected?",
        "Are there any BEE shareholding lock-in periods that affect the transaction?",
    ],
    "financial_services": [
        "What FSP licenses does the target hold and do they require ownership change notification?",
        "Does the transaction trigger Prudential Authority approval (>15%/25%/49% thresholds)?",
        "Are there any fit and proper requirements for new significant shareholders?",
        "What FAIS Section 20 notification requirements apply to this transaction?",
    ],
    "banking_finance": [
        "Does the transaction trigger Prudential Authority approval for significant ownership changes?",
        "What fit and proper assessments are required for the acquirer?",
        "Are there any regulatory capital implications of the ownership change?",
        "What banking license conditions relate to ownership structure?",
    ],
    "capital_markets": [
        "What JSE or exchange requirements apply to the change in ownership?",
        "Are there any mandatory offer thresholds triggered by the transaction?",
        "What shareholder disclosure requirements apply post-transaction?",
        "Does the transaction trigger any takeover regulation requirements?",
    ],
    "energy_power": [
        "What NERSA or energy regulator approvals are required for ownership changes?",
        "Are there any IPP or generation license conditions tied to ownership?",
        "What BEE requirements apply to energy sector ownership?",
        "Do any power purchase agreements require consent for ownership changes?",
    ],
    "infrastructure_ppp": [
        "What Treasury or government approvals are required for ownership changes in PPP structures?",
        "Are there any empowerment requirements in the concession agreement?",
        "Does the change of control affect the PPP security package?",
        "What step-in rights do government parties have on ownership change?",
    ],
    "real_estate": [
        "Are there any property ownership restrictions (e.g., agricultural land, foreign ownership)?",
        "Do any property-related licenses require ownership change approval?",
        "Are there any sectoral BEE requirements for property holding companies?",
        "What landlord consents are required for change of ownership?",
    ],
    "bee_transformation": [
        "What is the target's current B-BBEE contributor level and how will it be affected?",
        "Are there any BEE shareholding lock-in periods or clawback provisions?",
        "How do the various B-BBEE scorecard elements score currently?",
        "What ownership element requirements apply to this sector?",
        "Are there any empowerment financing arrangements that survive the transaction?",
    ],
    "competition_regulatory": [
        "What competition authority merger thresholds are triggered?",
        "Are there any sector-specific regulatory approvals required?",
        "What public interest considerations apply to this transaction?",
        "Are there any conditions or undertakings from prior transactions that apply?",
    ],
}


def load_yaml(filepath: Path) -> dict:
    """Load YAML file with safe parsing."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f) or {}


def save_yaml(filepath: Path, data: dict):
    """Save YAML file with proper formatting."""
    with open(filepath, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False, width=120)


def add_ownership_questions_to_blueprint(filepath: Path) -> bool:
    """
    Add ownership/regulatory questions to a blueprint file.

    Returns True if changes were made, False if questions already existed.
    """
    blueprint = load_yaml(filepath)

    if not blueprint:
        print(f"  Skipping {filepath.name} - empty or invalid")
        return False

    # Get the blueprint code for industry-specific questions
    code = blueprint.get('code', filepath.stem)

    # Ensure cot_questions section exists
    if 'cot_questions' not in blueprint:
        blueprint['cot_questions'] = {}

    # Check if ownership_regulatory already exists
    if 'ownership_regulatory' in blueprint['cot_questions']:
        print(f"  {filepath.name} - ownership_regulatory already exists, skipping")
        return False

    # Add universal ownership questions
    all_questions = UNIVERSAL_OWNERSHIP_QUESTIONS.copy()

    # Add industry-specific questions if available
    if code in INDUSTRY_OWNERSHIP_QUESTIONS:
        all_questions.extend(INDUSTRY_OWNERSHIP_QUESTIONS[code])

    # Add to cot_questions at the beginning (before other categories)
    new_cot = {'ownership_regulatory': all_questions}
    new_cot.update(blueprint['cot_questions'])
    blueprint['cot_questions'] = new_cot

    # Save the updated blueprint
    save_yaml(filepath, blueprint)
    print(f"  {filepath.name} - added {len(all_questions)} ownership questions")

    return True


def main():
    """Add ownership questions to all blueprint YAML files."""
    blueprint_dir = Path(__file__).parent
    yaml_files = list(blueprint_dir.glob("*.yaml"))

    # Filter out non-blueprint files
    yaml_files = [f for f in yaml_files if not f.name.startswith('_')]

    print(f"Found {len(yaml_files)} blueprint files")
    print()

    updated_count = 0
    for yaml_file in sorted(yaml_files):
        if add_ownership_questions_to_blueprint(yaml_file):
            updated_count += 1

    print()
    print(f"Updated {updated_count} of {len(yaml_files)} blueprints")
    print("Done!")


if __name__ == "__main__":
    main()
