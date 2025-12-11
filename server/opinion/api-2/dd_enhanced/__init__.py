"""
DD Enhanced - Multi-Pass Due Diligence Analysis POC

This module demonstrates architectural improvements to the Alchemy DD system:
1. Pass 1: Extract & Index - Pull structured data from all documents
2. Pass 2: Per-Document Analysis - Analyze each document with reference context
3. Pass 3: Cross-Document Synthesis - Find conflicts and cascades (KEY IMPROVEMENT)
4. Pass 4: Deal Synthesis - Calculate exposures and classify deal-blockers

Usage:
    python run_poc.py
"""

__version__ = "0.1.0"
__author__ = "Alchemy Law Africa"
