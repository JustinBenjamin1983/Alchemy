"""
Question Loader for Folder-Aware Processing (Phase 3)

Loads folder-specific questions from blueprint YAML files, mapping folder
categories (01_Corporate, 02_Commercial, etc.) to analysis questions.

Architecture:
- Each folder category has its own set of analysis questions
- Questions are loaded from the blueprint's `folder_questions` section
- Falls back to existing doc_type-based questions when folder_questions unavailable
- FOLDER_TO_CLUSTER_MAP preserves existing Pass 3 cluster logic

Usage:
    loader = QuestionLoader(blueprint)
    questions = loader.get_questions_for_folder("01_Corporate")
    cross_doc_checks = loader.get_cross_doc_checks_for_folder("01_Corporate")
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


# Maps folder categories to Pass 3 clusters for cross-document analysis
# This preserves the existing clustering logic while integrating folder structure
FOLDER_TO_CLUSTER_MAP: Dict[str, str] = {
    "01_Corporate": "corporate_governance",
    "02_Commercial": "commercial_contracts",
    "03_Financial": "financial",
    "04_Regulatory": "operational_regulatory",
    "05_Employment": "employment",
    "06_Property": "operational_regulatory",  # Property is operational
    "07_Insurance": "financial",  # Insurance relates to financial
    "08_Litigation": "commercial_contracts",  # Litigation affects commercial
    "09_Tax": "financial",  # Tax relates to financial
    "99_Needs_Review": None,  # Skip - documents need manual classification
}

# Reverse mapping: cluster -> folders (for grouping in Pass 3)
CLUSTER_TO_FOLDERS_MAP: Dict[str, List[str]] = {
    "corporate_governance": ["01_Corporate"],
    "commercial_contracts": ["02_Commercial", "08_Litigation"],
    "financial": ["03_Financial", "07_Insurance", "09_Tax"],
    "operational_regulatory": ["04_Regulatory", "06_Property"],
    "employment": ["05_Employment"],
}


@dataclass
class FolderQuestionSet:
    """Questions for a specific folder category."""
    folder_category: str
    display_name: str
    relevance: str  # critical, high, medium, low
    questions: List[Dict[str, Any]]  # List of {question, priority, cot_hint}
    cross_doc_checks: List[Dict[str, Any]]  # Cross-document validation checks

    @property
    def critical_questions(self) -> List[Dict[str, Any]]:
        """Return only critical priority questions."""
        return [q for q in self.questions if q.get("priority") == "critical"]

    @property
    def high_questions(self) -> List[Dict[str, Any]]:
        """Return high priority questions."""
        return [q for q in self.questions if q.get("priority") == "high"]


class QuestionLoader:
    """
    Loads and manages folder-specific questions from blueprint YAML.

    The loader:
    1. Checks for folder_questions in blueprint (Phase 3)
    2. Falls back to risk_categories questions mapped by doc_type
    3. Provides cluster-based cross-doc questions for Pass 3
    """

    def __init__(self, blueprint: Optional[Dict] = None):
        """
        Initialize loader with optional blueprint.

        Args:
            blueprint: Loaded blueprint dict from YAML
        """
        self.blueprint = blueprint or {}
        self._folder_questions_cache: Dict[str, FolderQuestionSet] = {}
        self._load_folder_questions()

    def _load_folder_questions(self) -> None:
        """Load folder_questions from blueprint into cache."""
        folder_questions = self.blueprint.get("folder_questions", {})

        for folder_cat, config in folder_questions.items():
            questions = []
            for q in config.get("questions", []):
                questions.append({
                    "question": q.get("question", ""),
                    "priority": q.get("priority", "medium"),
                    "detail": q.get("detail", ""),
                    "cot_hint": q.get("cot_hint", ""),
                })

            cross_doc = []
            for check in config.get("cross_doc_checks", []):
                cross_doc.append({
                    "check": check.get("check", ""),
                    "related_folders": check.get("related_folders", []),
                    "description": check.get("description", ""),
                })

            self._folder_questions_cache[folder_cat] = FolderQuestionSet(
                folder_category=folder_cat,
                display_name=config.get("display_name", folder_cat),
                relevance=config.get("relevance", "medium"),
                questions=questions,
                cross_doc_checks=cross_doc,
            )

    def has_folder_questions(self) -> bool:
        """Check if blueprint has folder_questions section."""
        return bool(self._folder_questions_cache)

    def get_questions_for_folder(
        self,
        folder_category: str,
        priority_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get questions for a specific folder category.

        Args:
            folder_category: e.g., "01_Corporate", "02_Commercial"
            priority_filter: Optional filter - "critical", "high", etc.

        Returns:
            List of question dicts with question, priority, detail, cot_hint
        """
        # Try folder_questions first (Phase 3)
        if folder_category in self._folder_questions_cache:
            q_set = self._folder_questions_cache[folder_category]
            if priority_filter:
                return [q for q in q_set.questions if q.get("priority") == priority_filter]
            return q_set.questions

        # Fall back to existing doc_type-based questions from risk_categories
        return self._get_fallback_questions_for_folder(folder_category, priority_filter)

    def _get_fallback_questions_for_folder(
        self,
        folder_category: str,
        priority_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get questions from risk_categories for folders without folder_questions.

        Maps folder category to relevant risk categories based on naming.
        """
        # Map folder to likely risk categories
        folder_to_risk_category = {
            "01_Corporate": ["Change of Control", "Corporate Governance"],
            "02_Commercial": ["Offtake & Commercial Contracts", "Change of Control"],
            "03_Financial": ["Banking & Finance", "Financial"],
            "04_Regulatory": ["Mining Rights & Title", "Environmental Compliance", "Health & Safety"],
            "05_Employment": ["Employment & Key Persons"],
            "06_Property": ["Surface Rights & Property"],
            "07_Insurance": ["Insurance"],
            "08_Litigation": ["Litigation", "Disputes"],
            "09_Tax": ["Tax"],
        }

        target_categories = folder_to_risk_category.get(folder_category, [])
        questions = []

        for risk_cat in self.blueprint.get("risk_categories", []):
            cat_name = risk_cat.get("name", "")
            if any(target.lower() in cat_name.lower() for target in target_categories):
                for q in risk_cat.get("standard_questions", []):
                    question_dict = {
                        "question": q.get("question", ""),
                        "priority": q.get("priority", "medium"),
                        "detail": q.get("detail", ""),
                        "cot_hint": "",  # risk_categories don't have cot_hints
                    }
                    if priority_filter is None or question_dict["priority"] == priority_filter:
                        questions.append(question_dict)

        return questions

    def get_cross_doc_checks_for_folder(
        self,
        folder_category: str
    ) -> List[Dict[str, Any]]:
        """
        Get cross-document validation checks for a folder.

        Args:
            folder_category: e.g., "01_Corporate"

        Returns:
            List of cross-doc check dicts
        """
        if folder_category in self._folder_questions_cache:
            return self._folder_questions_cache[folder_category].cross_doc_checks

        # Fall back to cluster-based cross-doc checks
        return self._get_fallback_cross_doc_checks(folder_category)

    def _get_fallback_cross_doc_checks(
        self,
        folder_category: str
    ) -> List[Dict[str, Any]]:
        """Get cross-doc checks from risk_categories for folders without folder_questions."""
        folder_to_risk_category = {
            "01_Corporate": ["Change of Control"],
            "02_Commercial": ["Offtake & Commercial Contracts"],
            "03_Financial": ["Banking & Finance"],
            "04_Regulatory": ["Mining Rights & Title", "Environmental Compliance"],
            "05_Employment": ["Employment & Key Persons"],
            "06_Property": ["Surface Rights & Property"],
        }

        target_categories = folder_to_risk_category.get(folder_category, [])
        checks = []

        for risk_cat in self.blueprint.get("risk_categories", []):
            cat_name = risk_cat.get("name", "")
            if any(target.lower() in cat_name.lower() for target in target_categories):
                for validation in risk_cat.get("cross_doc_validations", []):
                    checks.append({
                        "check": validation.get("check", ""),
                        "description": validation.get("description", ""),
                        "related_folders": [],  # Not specified in risk_categories
                    })

        return checks

    def get_questions_for_cluster(
        self,
        cluster_name: str,
        priority_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all questions for a Pass 3 cluster by aggregating folder questions.

        Args:
            cluster_name: e.g., "corporate_governance", "financial"
            priority_filter: Optional filter - "critical", "high", etc.

        Returns:
            Combined questions from all folders mapped to this cluster
        """
        folders = CLUSTER_TO_FOLDERS_MAP.get(cluster_name, [])
        all_questions = []
        seen_questions = set()  # Deduplicate

        for folder in folders:
            folder_qs = self.get_questions_for_folder(folder, priority_filter)
            for q in folder_qs:
                q_text = q.get("question", "")
                if q_text and q_text not in seen_questions:
                    seen_questions.add(q_text)
                    all_questions.append(q)

        return all_questions

    def get_cross_doc_checks_for_cluster(
        self,
        cluster_name: str
    ) -> List[Dict[str, Any]]:
        """
        Get all cross-doc checks for a Pass 3 cluster.

        Args:
            cluster_name: e.g., "corporate_governance", "financial"

        Returns:
            Combined cross-doc checks from all folders mapped to this cluster
        """
        folders = CLUSTER_TO_FOLDERS_MAP.get(cluster_name, [])
        all_checks = []
        seen_checks = set()

        for folder in folders:
            folder_checks = self.get_cross_doc_checks_for_folder(folder)
            for check in folder_checks:
                check_text = check.get("check", "")
                if check_text and check_text not in seen_checks:
                    seen_checks.add(check_text)
                    all_checks.append(check)

        return all_checks

    def get_folder_relevance(self, folder_category: str) -> str:
        """
        Get relevance level for a folder category.

        Returns: "critical", "high", "medium", "low", or "n/a"
        """
        if folder_category in self._folder_questions_cache:
            return self._folder_questions_cache[folder_category].relevance

        # Fall back to folder_structure in blueprint
        folder_structure = self.blueprint.get("folder_structure", {})
        if folder_category in folder_structure:
            return folder_structure[folder_category].get("relevance", "medium")

        return "medium"

    def get_all_folder_categories(self) -> List[str]:
        """Get list of all folder categories with questions."""
        if self._folder_questions_cache:
            return list(self._folder_questions_cache.keys())

        # Fall back to folder_structure
        return list(self.blueprint.get("folder_structure", {}).keys())

    def get_folder_question_set(self, folder_category: str) -> Optional[FolderQuestionSet]:
        """Get the full FolderQuestionSet for a folder category."""
        return self._folder_questions_cache.get(folder_category)


def get_cluster_for_folder(folder_category: str) -> Optional[str]:
    """
    Get the Pass 3 cluster for a folder category.

    Args:
        folder_category: e.g., "01_Corporate"

    Returns:
        Cluster name or None if folder should be skipped (99_Needs_Review)
    """
    return FOLDER_TO_CLUSTER_MAP.get(folder_category)


def get_folders_for_cluster(cluster_name: str) -> List[str]:
    """
    Get all folder categories mapped to a cluster.

    Args:
        cluster_name: e.g., "corporate_governance"

    Returns:
        List of folder categories
    """
    return CLUSTER_TO_FOLDERS_MAP.get(cluster_name, [])


def should_skip_folder(folder_category: str) -> bool:
    """
    Check if folder should be skipped in processing.

    99_Needs_Review documents are skipped - they need manual classification.
    """
    return folder_category == "99_Needs_Review" or FOLDER_TO_CLUSTER_MAP.get(folder_category) is None
