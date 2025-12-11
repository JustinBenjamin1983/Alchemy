#!/usr/bin/env python3
"""
Verify Document Registry

Tests that all document registries load correctly and provides summary statistics.
"""

import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config.documents.registry import (
    load_document_registry,
    list_available_registries,
    classify_document,
    generate_document_request_list,
    DocumentPriority,
)


def verify_all_registries():
    """Verify all document registries load correctly."""
    print("=" * 60)
    print("DOCUMENT REGISTRY VERIFICATION")
    print("=" * 60)

    # Get available registries
    registries = list_available_registries()
    print(f"\nFound {len(registries)} transaction-specific registries:")
    for reg in registries:
        print(f"  - {reg}")

    print("\n" + "-" * 60)

    # Load and verify each registry
    total_docs = 0
    total_folders = 0
    all_passed = True

    for registry_name in registries:
        try:
            registry = load_document_registry(registry_name)

            doc_count = len(registry.get("documents", []))
            folder_count = len(registry.get("folder_structure", []))
            category_count = len(registry.get("categories", []))

            # Count documents by priority
            priority_counts = {p.value: 0 for p in DocumentPriority}
            for doc in registry.get("documents", []):
                priority = doc.get("priority", "required")
                if priority in priority_counts:
                    priority_counts[priority] += 1

            total_docs += doc_count
            total_folders += folder_count

            print(f"\n✓ {registry_name}")
            print(f"  Transaction Type: {registry.get('transaction_type', 'Unknown')}")
            print(f"  Documents: {doc_count} | Folders: {folder_count} | Categories: {category_count}")
            print(f"  Priority breakdown: Critical={priority_counts['critical']}, "
                  f"Required={priority_counts['required']}, "
                  f"Recommended={priority_counts['recommended']}, "
                  f"Optional={priority_counts['optional']}")

        except Exception as e:
            print(f"\n✗ {registry_name}: FAILED")
            print(f"  Error: {e}")
            all_passed = False

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total Registries: {len(registries)}")
    print(f"Total Documents: {total_docs}")
    print(f"Total Folder Templates: {total_folders}")

    # Test classification with sample filenames
    print("\n" + "-" * 60)
    print("CLASSIFICATION TESTS")
    print("-" * 60)

    test_files = [
        ("Mining_Right_12345.pdf", "mining_resources", "Mining rights certificate"),
        ("MOI - Target Company.pdf", "ma_corporate", "Memorandum of Incorporation"),
        ("Environmental_Authorization_2023.pdf", "mining_resources", "Environmental authorization"),
        ("PPA_Eskom_Solar_Project.pdf", "energy_power", "Power purchase agreement"),
        ("B-BBEE_Certificate_Level1.pdf", "bee_transformation", "BBBEE certificate verification"),
        ("Senior_Facility_Agreement.pdf", "banking_finance", "Senior facility agreement"),
        ("Title_Deed_Erf123.pdf", "real_estate", "Title deed property"),
        ("Competition_Commission_Approval.pdf", "competition_regulatory", "Competition Commission approval"),
        ("Employee_List_2024.xlsx", "employment_labor", "Employee list headcount"),
        ("Patent_Portfolio.pdf", "ip_technology", "Patent portfolio schedule"),
        ("Concession_Agreement_Road.pdf", "infrastructure_ppp", "Concession agreement PPP"),
    ]

    for filename, registry_name, content_preview in test_files:
        try:
            category, folder, confidence = classify_document(filename, content_preview, registry_name)
            print(f"  ✓ '{filename}' → {folder} (confidence: {confidence:.2f})")
        except Exception as e:
            print(f"  ✗ '{filename}' → Error: {e}")

    # Test document request list generation
    print("\n" + "-" * 60)
    print("REQUEST LIST GENERATION TEST (Mining)")
    print("-" * 60)

    try:
        request_list = generate_document_request_list("mining_resources", DocumentPriority.CRITICAL)
        lines = request_list.strip().split('\n')
        print(f"  Generated request list with {len(lines)} lines")
        # Show first few lines
        for line in lines[:10]:
            print(f"  {line}")
        if len(lines) > 10:
            print(f"  ... and {len(lines) - 10} more lines")
    except Exception as e:
        print(f"  ✗ Request list generation failed: {e}")
        all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("✓ ALL VERIFICATIONS PASSED")
    else:
        print("✗ SOME VERIFICATIONS FAILED")
    print("=" * 60)

    return all_passed


if __name__ == "__main__":
    success = verify_all_registries()
    sys.exit(0 if success else 1)
