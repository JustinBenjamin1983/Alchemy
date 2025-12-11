# File: server/opinion/api-2/OpinionGenerate/__init__.py
import logging
import azure.functions as func
import json
import os
from shared.utils import auth_get_email
from shared.search import search_similar_documents
from shared.table_storage import get_user_info
import re

from shared.rag import (
    create_chunks_and_embeddings_from_text, call_llm_with, call_llm_with_search,
    verify_draft_with_local_and_web, rewrite_opinion_with_verified_sources_hardtrace,
    filter_saflii_cases, build_saflii_case_provenance, llm_filter_saflii_cases
)

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("✅ Generate opinion function triggered with comprehensive source integration.")
    
    if req.headers.get('function-key') != os.environ["FUNCTION_KEY"]:
        logging.info("no matching value in header")
        return func.HttpResponse("", status_code=401)
    
    try:
        email, err = auth_get_email(req)
        if err:
            logging.exception("❌ auth_get_email", err)
            return err
        
        data = req.get_json()
        id = data["id"]
        
        if not id:
            return func.HttpResponse("Id not supplied", status_code=404)
        
        entity = get_user_info(email)
        entity_data = json.loads(entity.get("payload", "{}"))
        opinions = entity_data.get("opinions", [])
        matched_opinion = next((item for item in opinions if item.get("id") == id), None)
        
        if not matched_opinion:
            return func.HttpResponse("Opinion not found", status_code=404)
        
        documents = matched_opinion.get("documents", [])
        enabled_docs = [
            {"doc_id": doc["doc_id"], "doc_name": doc["doc_name"]}
            for doc in documents if doc.get("enabled")
        ]
        
        logging.info(f"opinion {id=} {enabled_docs=}")
        
        # Step 1: Get relevant documents from client's uploaded documents using embeddings search
        doc_results = find_in_opinion_docs([doc["doc_id"] for doc in enabled_docs], matched_opinion["questions"])
        logging.info(f"Document search results: {doc_results}")
        logging.info(f"Found {len(doc_results.get('value', []))} relevant document chunks")
        
        # Step 2: Search SAFLII via GPT web search (no internal KB) and filter strictly to saflii.org
        logging.info("Starting SAFLII case law search...")
        case_law_data_raw = search_saflii_case_law_structured(
            facts=matched_opinion["facts"],
            questions=matched_opinion["questions"],
            assumptions=matched_opinion["assumptions"]
        )
        case_law_data = filter_saflii_cases(case_law_data_raw)
        logging.info(f"SAFLII case law search completed. Kept {len(case_law_data.get('cases', []))} SAFLII cases")

        # Step 2a: Download each SAFLII case and build provenance (paragraph map + hashed excerpts)
        logging.info("Downloading SAFLII cases and building provenance...")
        saflii_dl = build_saflii_case_provenance(case_law_data.get("cases", []))
        logging.info(f"Built provenance for {len(saflii_dl.get('cases', []))} cases; "
                     f"{len(saflii_dl.get('provenance', []))} paragraph snippets")

        # Step 2b: Run an LLM-based SAFLII filter using full-text provenance + your structured search insights
        logging.info("Filtering SAFLII cases with LLM using provenance + structured insights...")
        case_law_filtered = llm_filter_saflii_cases(
            cases=saflii_dl.get("cases", []),
            facts=matched_opinion["facts"],
            questions=matched_opinion["questions"],
            assumptions=matched_opinion["assumptions"],
            provenance=saflii_dl.get("provenance", [])
        )
        logging.info(f"SAFLII filtering complete. Kept {len(case_law_filtered.get('cases', []))} cases")

        # Step 3: Generate the draft using ONLY client docs + filtered SAFLII cases
        logging.info("start create_comprehensive_opinion")
        draft = create_comprehensive_opinion(
            facts=matched_opinion["facts"],
            questions=matched_opinion["questions"],
            assumptions=matched_opinion["assumptions"],
            doc_results=doc_results['value'],
            case_law_data=case_law_filtered,  # ← use filtered cases
            client_name=matched_opinion.get("client_name"),
            client_address=matched_opinion.get("client_address"),
            title=matched_opinion.get("title")
        )
        logging.info("end create_comprehensive_opinion")

                # Step 4: Verify draft (prefer local SAFLII index; fall back to web) → then rewrite
        logging.info("start verify_draft_with_local_and_web")
        verification_report = verify_draft_with_local_and_web(
            draft_text=draft,
            facts=matched_opinion["facts"],
            questions=matched_opinion["questions"],
            assumptions=matched_opinion["assumptions"],
            saflii_index=saflii_dl  # ← includes cases, provenance, and paragraph index
        )
        logging.info("end verify_draft_with_local_and_web")

        logging.info("start rewrite_opinion_with_verified_sources_hardtrace")
        final_draft = rewrite_opinion_with_verified_sources_hardtrace(
            draft_text=draft,
            verification_report=verification_report,
            doc_results=doc_results['value'],
            facts=matched_opinion["facts"],
            questions=matched_opinion["questions"],
            assumptions=matched_opinion["assumptions"]
        )
        logging.info("end rewrite_opinion_with_verified_sources_hardtrace")


        
        return func.HttpResponse(json.dumps({
            "draft": draft,
            "final_draft": final_draft,  # ← rewritten using verified sources only
            "verification_report": verification_report,  # ← structured verification JSON
            "docs": doc_results['value'],
            "case_law_found": case_law_data.get('cases', []),
            "case_law_narrative": case_law_data_raw.get('narrative', ''),
            "case_law_searched": True,
            "facts": matched_opinion["facts"],
            "questions": matched_opinion["questions"],
            "assumptions": matched_opinion["assumptions"],
            "client_name": matched_opinion.get("client_name"),
            "client_address": matched_opinion.get("client_address"),
            "title": matched_opinion.get("title")
        }), mimetype="application/json", status_code=200)

        
    except Exception as e:
        logging.info(f"failed")
        logging.info(e)
        logging.exception("❌ Error occurred", e)
        return func.HttpResponse("Server error", status_code=500)

def find_in_opinion_docs(doc_ids, prompt):
    """Find relevant documents using embeddings search - restored from original implementation"""
    if not doc_ids:
        logging.info("No document IDs provided for search")
        return {"value": []}
    
    logging.info(f"Searching documents with IDs: {doc_ids}")
    logging.info(f"Search prompt: {prompt}")
    
    try:
        # Create embeddings from the search prompt (questions)
        chunks_and_embeddings = create_chunks_and_embeddings_from_text(prompt)
        embeddings = [value for item in chunks_and_embeddings for value in item["embedding"]]
        
        logging.info(f"Created {len(embeddings)} embeddings for search")
        
        # Search for similar documents using Azure AI Search
        found_results = search_similar_documents(embeddings, doc_ids, prompt, os.environ["AISearch_K"])
        
        logging.info(f"Document search returned: {found_results}")
        
        return found_results
        
    except Exception as e:
        logging.exception(f"❌ Error in find_in_opinion_docs: {e}")
        return {"value": []}

def search_saflii_case_law_structured(facts, questions, assumptions):
    """
    Search for South African case law from SAFLII and return structured data with URLs
    Generic version that adapts to any legal domain based on facts, questions, and assumptions
    """
    try:
        # Create adaptive search query that extracts key legal concepts from the case
        search_instructions = f"""You are a South African legal research specialist with access to web search capabilities.

CRITICAL REQUIREMENTS:
1. Return ONLY case law from SAFLII (domain must contain "saflii.org").
2. Return your findings in the EXACT JSON format specified below
3. Include the full SAFLII URL for each case found

LEGAL MATTER TO RESEARCH:
FACTS: {facts}
QUESTIONS: {questions}
ASSUMPTIONS: {assumptions}

SEARCH STRATEGY:
1. Analyze the facts, questions, and assumptions to identify key legal concepts and areas of law
2. Use targeted SAFLII searches like "site:saflii.org [key legal terms from the case]"
3. Search for relevant South African case law in the applicable legal domains
4. Look for High Court, Supreme Court of Appeal, and Constitutional Court decisions
5. Focus on cases that address similar legal questions or factual scenarios

REQUIRED JSON OUTPUT FORMAT:
{{
  "search_summary": "Brief summary of searches performed and legal areas explored",
  "cases": [
    {{
      "case_name": "Full Case Name v Respondent Name",
      "citation": "YEAR (Citation) Court",
      "year": "YYYY",
      "court": "Court abbreviation",
      "url": "https://www.saflii.org/full-url-if-found",
      "legal_principle": "Key legal principle or ratio decidendi from the judgment",
      "relevance": "Specific relevance to the current legal questions",
      "quote": "Key quote from judgment if available"
    }}
  ],
  "total_cases_found": 0,
  "search_queries_used": ["list of actual search queries performed"]
}}

EXAMPLE OF VALID JSON RESPONSE:
{{
  "search_summary": "Searched SAFLII for contract law cases involving breach of warranty and damages",
  "cases": [
    {{
      "case_name": "Smith v Jones Construction",
      "citation": "2020 (1) SA 123 (SCA)",
      "year": "2020",
      "court": "SCA",
      "url": "https://www.saflii.org/za/cases/ZASCA/2020/123.html",
      "legal_principle": "Damages for breach of warranty must be foreseeable and directly causally linked",
      "relevance": "Establishes principles for calculating damages in breach of warranty claims",
      "quote": "The test for remoteness of damages requires both foreseeability and direct causation"
    }}
  ],
  "total_cases_found": 1,
  "search_queries_used": ["site:saflii.org contract breach warranty damages"]
}}

CRITICAL INSTRUCTIONS:
- Extract key legal concepts from the provided facts and questions
- Search broadly across relevant areas of South African law
- Return ONLY valid JSON with no additional text
- If no relevant cases found, return empty cases array with explanation in search_summary"""

        # Get the raw search results
        logging.info("Calling OpenAI with generic case law search instructions...")
        raw_search_result = call_llm_with_search(
            messages=[
                {"role": "system", "content": search_instructions},
                {"role": "user", "content": f"Search SAFLII comprehensively for case law relevant to these legal questions and return structured JSON: {questions}"}
            ],
            max_tokens=12000,
            model="o4-mini",
            enable_web_search=True
        )
        
        logging.info(f"Raw SAFLII search result length: {len(raw_search_result)}")
        logging.info(f"Raw SAFLII search result content: {raw_search_result[:500]}...")  # Log first 500 chars
        
        # Extract and parse JSON from the search result with enhanced debugging
        case_law_data = extract_json_from_search_result_enhanced(raw_search_result)
        
        # Add the original narrative for reference
        case_law_data['narrative'] = raw_search_result
        
        logging.info(f"Structured case law extraction completed. Found {len(case_law_data.get('cases', []))} cases")
        logging.info(f"Case law data structure: {json.dumps(case_law_data, indent=2)}")
        
        return case_law_data
        
    except Exception as e:
        logging.exception(f"❌ Error in SAFLII case law search: {e}")
        return {
            "search_summary": f"Error occurred during search: {str(e)}",
            "cases": [],
            "total_cases_found": 0,
            "search_queries_used": [],
            "narrative": f"Search error: {str(e)}"
        }

def extract_json_from_search_result_enhanced(search_result):
    """
    Enhanced JSON extraction with better debugging and multiple strategies
    """
    logging.info(f"Starting JSON extraction from {len(search_result)} character response")
    
    # Strategy 1: Try to extract JSON block with brace matching
    try:
        logging.info("Trying Strategy 0: Direct JSON parsing")
        json_data = json.loads(search_result.strip())
        if validate_case_law_json(json_data):
            logging.info(f"Strategy 0 SUCCESS! Found {len(json_data.get('cases', []))} cases")
            return json_data
    except json.JSONDecodeError as e:
        logging.info(f"Strategy 0 failed - not pure JSON")
    except Exception as e:
        logging.warning(f"Strategy 0 failed: {e}")
    
    # Strategy 2: Look for JSON in code blocks or markdown
    try:
        logging.info("Trying Strategy 2: Code block JSON extraction")
        json_data = extract_json_from_markdown(search_result)
        if json_data and validate_case_law_json(json_data):
            logging.info("Strategy 2 successful - found valid JSON in markdown")
            return json_data
    except Exception as e:
        logging.warning(f"Strategy 2 failed: {e}")
    
    # Strategy 3: Try to fix common JSON issues and parse
    try:
        logging.info("Trying Strategy 3: Fix and parse JSON")
        json_data = fix_and_parse_json(search_result)
        if json_data and validate_case_law_json(json_data):
            logging.info("Strategy 3 successful - fixed and parsed JSON")
            return json_data
    except Exception as e:
        logging.warning(f"Strategy 3 failed: {e}")
    
    # Strategy 4: Extract case information using regex patterns from free text
    try:
        logging.info("Trying Strategy 4: Regex case extraction from free text")
        json_data = extract_cases_from_freetext(search_result)
        if json_data and validate_case_law_json(json_data):
            logging.info("Strategy 4 successful - extracted cases using regex")
            return json_data
    except Exception as e:
        logging.warning(f"Strategy 4 failed: {e}")
    
    # If all strategies fail, create a summary from the narrative
    logging.warning("All JSON extraction strategies failed, creating summary from narrative")
    return create_fallback_case_structure(search_result)

def extract_complete_json_block(text):
    """
    Extract complete JSON block using proper brace matching
    """
    # Find all potential JSON start positions
    start_positions = []
    for i, char in enumerate(text):
        if char == '{':
            start_positions.append(i)
    
    # Try each start position
    for start_idx in start_positions:
        brace_count = 0
        in_string = False
        escaped = False
        
        for i in range(start_idx, len(text)):
            char = text[i]
            
            if escaped:
                escaped = False
                continue
                
            if char == '\\':
                escaped = True
                continue
                
            if char == '"' and not escaped:
                in_string = not in_string
                continue
                
            if not in_string:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        json_str = text[start_idx:i + 1]
                        try:
                            return json.loads(json_str)
                        except json.JSONDecodeError:
                            continue
    
    return None

def extract_json_from_markdown(text):
    """
    Extract JSON from markdown code blocks
    """
    patterns = [
        r'```json\s*(\{.*?\})\s*```',  # ```json
        r'```\s*(\{.*?\})\s*```',      # ```
        r'`(\{.*?\})`',                # Single backticks
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
        for match in matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue
    
    return None

def fix_and_parse_json(text):
    """
    Try to fix common JSON formatting issues
    """
    # Common fixes
    fixes = [
        (r'(\w+)(?=\s*:)', r'"\1"'),  # Quote unquoted keys
        (r':\s*([^",\[\]{}]+)(?=\s*[,}])', r': "\1"'),  # Quote unquoted string values
        (r',\s*}', '}'),  # Remove trailing commas before }
        (r',\s*]', ']'),  # Remove trailing commas before ]
        (r'}\s*{', '}, {'),  # Add comma between objects
    ]
    
    # Try to find JSON-like structures
    json_patterns = [
        r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}',  # Simple nested objects
        r'\{.*?\}',  # Any content between braces
    ]
    
    for pattern in json_patterns:
        matches = re.findall(pattern, text, re.DOTALL)
        for match in matches:
            fixed_json = match
            for fix_pattern, replacement in fixes:
                fixed_json = re.sub(fix_pattern, replacement, fixed_json)
            
            try:
                return json.loads(fixed_json)
            except json.JSONDecodeError:
                continue
    
    return None

def extract_cases_from_freetext(text):
    """
    Extract case information from free text when JSON parsing fails completely
    """
    cases = []
    
    # Common South African case citation patterns
    case_patterns = [
        # Pattern 1: Standard SA citation
        r'([A-Z][^v\n]*?)\s+v\s+([A-Z][^\n]*?)\s+(\d{4})\s*\(\s*(\d+)\s*\)\s*SA\s+(\d+)\s*\(([A-Z]+)\)',
        # Pattern 2: General citation pattern
        r'([A-Z][^v\n]*?)\s+v\s+([A-Z][^\n]*?)\s+(\d{4})\s*\(([^)]+)\)\s*([A-Z]+)',
        # Pattern 3: Case name without full citation
        r'([A-Z][^v\n]*?)\s+v\s+([A-Z][^\n]*?)(?:\s+case|\s+matter|\s+judgment)',
    ]
    
    url_pattern = r'https?://[^\s<>"]*saflii\.org[^\s<>"]*'
    
    # Look for SAFLII URLs in the text
    urls_found = re.findall(url_pattern, text)
    logging.info(f"Found {len(urls_found)} SAFLII URLs in text")
    
    for pattern in case_patterns:
        matches = re.finditer(pattern, text, re.MULTILINE | re.IGNORECASE)
        
        for match in matches:
            try:
                case_name = f"{match.group(1).strip()} v {match.group(2).strip()}"
                year = match.group(3)
                
                if len(match.groups()) >= 6:  # Full SA citation
                    citation = f"{year} ({match.group(4)}) SA {match.group(5)} ({match.group(6)})"
                    court = match.group(6)
                elif len(match.groups()) >= 5:  # General citation
                    citation = f"{year} ({match.group(4)}) {match.group(5)}"
                    court = match.group(5)
                else:  # Minimal citation
                    citation = f"{year} (Citation) Court"
                    court = "Unknown"
                
                # Try to find URL for this case
                url = ""
                if urls_found:
                    # Use the first URL found (simple approach)
                    url = urls_found[0] if urls_found else ""
                
                # Extract context around the case for principle and relevance
                case_start = match.start()
                case_end = match.end()
                context = text[max(0, case_start - 200):case_end + 200]
                
                principle = extract_legal_principle(context) or "Legal principle not extracted from text"
                relevance = extract_relevance(context) or "Relevance to current matter not specified"
                
                case_data = {
                    "case_name": case_name[:100],  # Limit length
                    "citation": citation,
                    "year": year,
                    "court": court,
                    "url": url,
                    "legal_principle": principle[:200],  # Limit length
                    "relevance": relevance[:200],  # Limit length
                }
                
                cases.append(case_data)
                
            except (IndexError, AttributeError) as e:
                logging.warning(f"Error processing case match: {e}")
                continue
    
    if cases:
        return {
            "search_summary": f"Extracted {len(cases)} cases from free text using regex patterns",
            "cases": cases,
            "total_cases_found": len(cases),
            "search_queries_used": ["freetext_extraction"],
            "extraction_method": "regex_freetext"
        }
    
    return None

def extract_legal_principle(context):
    """Extract legal principle from context text"""
    principle_indicators = [
        r'held?\s+that\s+([^.]+)',
        r'principle\s+(?:is|was)\s+([^.]+)',
        r'established\s+(?:that|the)\s+([^.]+)',
        r'decided\s+(?:that|the)\s+([^.]+)',
        r'ruled?\s+(?:that|the)\s+([^.]+)'
    ]
    
    for pattern in principle_indicators:
        match = re.search(pattern, context, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    
    return ""

def extract_relevance(context):
    """Extract relevance information from context text"""
    relevance_indicators = [
        r'relevant\s+(?:to|for)\s+([^.]+)',
        r'applies?\s+(?:to|in)\s+([^.]+)',
        r'concerning\s+([^.]+)',
        r'regarding\s+([^.]+)',
        r'in\s+relation\s+to\s+([^.]+)'
    ]
    
    for pattern in relevance_indicators:
        match = re.search(pattern, context, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    
    return ""

def validate_case_law_json(data):
    """Validate that JSON has the expected case law structure"""
    if not isinstance(data, dict):
        return False
    
    # Check required top-level keys
    if 'cases' not in data:
        return False
    
    if not isinstance(data['cases'], list):
        return False
    
    # If there are cases, validate their structure
    for case in data['cases']:
        if not isinstance(case, dict):
            return False
        
        required_fields = ['case_name', 'legal_principle', 'relevance']
        if not all(field in case for field in required_fields):
            return False
        
        # Check that required fields aren't empty
        if not all(case.get(field) for field in required_fields):
            return False
    
    return True

def create_fallback_case_structure(search_result):
    """Create a fallback structure when all extraction methods fail"""
    return {
        "search_summary": "Case law search completed but no structured data could be extracted",
        "cases": [],
        "total_cases_found": 0,
        "search_queries_used": ["search_performed"],
        "narrative": search_result,
        "extraction_status": "failed_all_strategies",
        "note": "Raw search results available in narrative field"
    }

# Replace your existing extract_json_from_search_result function with this call:
def extract_json_from_search_result(search_result):
    """
    Main function - calls the enhanced extraction
    """
    return extract_json_from_search_result_enhanced(search_result)


def validate_case_structure(case):
    """
    Validate that a case has the required structure
    """
    required_fields = ['case_name', 'citation', 'court', 'legal_principle', 'relevance']
    optional_fields = ['year', 'url', 'quote']
    
    if not isinstance(case, dict):
        return False
    
    # Check required fields
    for field in required_fields:
        if field not in case or not case[field]:
            return False
    
    # Ensure URL is a valid SAFLII URL if provided
    if 'url' in case and case['url']:
        if not case['url'].startswith('http') or 'saflii.org' not in case['url']:
            logging.warning(f"Invalid SAFLII URL: {case['url']}")
    
    return True

def create_empty_case_law_structure():
    """
    Create empty case law structure for error cases
    """
    return {
        "search_summary": "No cases found or error occurred",
        "cases": [],
        "total_cases_found": 0,
        "search_queries_used": [],
    }

def create_comprehensive_opinion(facts, questions, assumptions, doc_results, case_law_data, client_name=None, client_address=None, title=None):
    """
    Create a comprehensive legal opinion with enhanced structure following ChatGPT feedback
    Enhanced to use structured case law data with URLs and proper legal opinion formatting
    """
    
    # Format client documents
    formatted_doc_results = ""
    if doc_results and len(doc_results) > 0:
        logging.info(f"Formatting {len(doc_results)} client document chunks")
        formatted_doc_results = "\n\n".join(
            f"Document: {doc_result.get('filename', 'Unknown file')}\nPage: {doc_result.get('page_number', 'N/A')}\nContent: {doc_result.get('content', '').strip()}"
            for doc_result in doc_results
        )
        logging.info(f"Formatted client documents: {len(formatted_doc_results)} characters")
    else:
        logging.info("No client documents provided for this opinion")
        formatted_doc_results = "No client documents were provided or found relevant to this opinion."
    
    # Format structured case law data
    formatted_case_law = ""
    cases_found = case_law_data.get('cases', [])
    if cases_found:
        logging.info(f"Formatting {len(cases_found)} SAFLII cases")
        case_law_entries = []
        for i, case in enumerate(cases_found, 1):
            case_entry = f"""Case {i}: {case['case_name']} {case['citation']}
Court: {case['court']}
Legal Principle: {case['legal_principle']}
Relevance: {case['relevance']}
URL: {case.get('url', 'URL not available')}"""
            if case.get('quote'):
                case_entry += f"\nKey Quote: {case['quote']}"
            case_law_entries.append(case_entry)
        
        formatted_case_law = "\n\n".join(case_law_entries)
        logging.info(f"Formatted case law: {len(formatted_case_law)} characters")
    else:
        formatted_case_law = "No relevant SAFLII cases found for this opinion."
    
    # Enhanced system prompt with proper legal opinion structure
    system_content = f"""You are a Senior Partner specializing in South African corporate law with 30+ years of experience drafting legal opinions for major law firms.

CRITICAL FORMATTING REQUIREMENTS:
1. Use NUMBERED CITATIONS [1], [2], [3] etc. throughout the opinion
2. Structure with Roman numeral headings (I., II., III., etc.)
3. Include ALL mandatory sections as specified below
4. Provide complete SOURCES section at the end with full citations

MANDATORY OPINION STRUCTURE:

**CLIENT INFORMATION**
{f"Client: {client_name}" if client_name else "Client: [Client Name]"}
{f"Address: {client_address}" if client_address else "Address: [Client Address]"}
{f"Matter: {title}" if title else "Matter: [Opinion Title]"}
Date: [Current Date]

**SCOPE AND ASSUMPTIONS**
This opinion is given on the assumptions stated below and addresses only the specific questions posed. It does not consider tax, regulatory, or other non-corporate law issues unless specifically mentioned.

**DEFINITIONS AND ABBREVIATIONS**
- "the Act" = Companies Act, No. 71 of 2008
- "PAIA" = Promotion of Access to Information Act
- [Define other key terms and abbreviations as they appear]

## I. EXECUTIVE SUMMARY
[2-3 sentences directly answering the key questions with numbered citations where appropriate]

## II. BACKGROUND AND FACTS
[Clearly state the relevant facts from the client matter, with numbered citations to source documents where appropriate]

## III. ISSUES
The following questions have been posed for our consideration:
[List each question exactly as provided, numbered 1, 2, 3, etc.]

## IV. OPINION AND LEGAL POSITION

[For each Issue below, use CREAC micro-structure.]

### Issue 1: [First Question]
#### 4.1 Conclusion (short answer)
#### 4.2 Rule (Statutes & binding authority)
#### 4.3 Explanation (Principle, policy, distinctions)
#### 4.4 Application (Apply facts with cites to client docs and SAFLII)
#### 4.5 Counter-arguments & Distinctions (address opposing cases; explain why not followed)
#### 4.6 Mini-Conclusion

[Repeat for each subsequent issue]

## V. STANDARD OF REVIEW / ONUS
[Identify applicable standard (e.g., interim interdict factors, Setlogelo test; burden of proof), with SAFLII pinpoints where available.]

## VI. REMEDIES & RELIEF SOUGHT
[List practical orders, interim vs final, alternative relief (variation, suspension), timing, forum, and key evidentiary showings; tie each to sources.]


## VII. RECOMMENDATIONS
[Specific actionable advice with numbered citations where appropriate, organized by priority]

## VIII Next Steps & Open Items
- [List missing documents or facts required to firm up unsupported points]
- [Filing/appeal deadlines if any are apparent from the case timeline]


## VIIII. CONCLUSION
[Concise summary of findings with key numbered citations]

## X. SOURCES

### Legislation and Regulations
[1] Companies Act, No. 71 of 2008, section [X] - [brief description]
[2] JSE Listings Requirements, [specific provision] - [brief description]
[etc.]

### Client Documents  
[X] [Document Name], Page [Y] - [brief description of content]
[etc.]

### Case Law
[X] *Case Name v Case Name* [Year] Citation Court - [brief description of principle]  
URL: [Full SAFLII URL]
[etc.]

SOURCE CATEGORIES:
1. **GENERAL LEGAL PRINCIPLES** (Legislation & Governance Frameworks)
   - Companies Act, No. 71 of 2008 (various sections)
   - JSE Listings Requirements
   - King IV Report on Corporate Governance for South Africa
   - Other established SA legislation

2. **CLIENT DOCUMENTS** (Supporting Documents)
CLIENT DOCUMENTS PROVIDED:
{formatted_doc_results}

3. **CASE LAW** (SAFLII Sources with URLs)
VERIFIED SAFLII CASES FOUND:
{formatted_case_law}

FACTUAL ASSUMPTIONS TO INCLUDE:
{assumptions}

HARD RULES:
- Include client information at the top.
- Include Scope and Assumptions section.
- Include Definitions section with key abbreviations.
- List all client questions exactly as posed in the Issues section.
- Do NOT cite any source other than ALLOWED SOURCES.
- Where a legal proposition relies on case law, use ONLY items from VERIFIED SAFLII CASES.
- The first time you cite a case for a proposition, include the SAFLII URL; if a paragraph is known, append '#para-<n>' and say 'at para <n>'. Include a ≤35-word verbatim quotation if available.
- Subsequent citations to the same case may omit the quote but MUST keep the pinpoint if known.
- If no verified support exists, replace the proposition with [UNSUPPORTED] (do not paraphrase unsupported law).
- **Do NOT show “[UNSUPPORTED]” in the Executive Summary.** If any conclusion depends on unsupported points, present it as conditional (“subject to contract review”) and move the unsupported detail to the body.
- Add a short **Limitations** sub-section at the end of the opinion explaining any unsupported gaps.



The opinion should read like a premium law firm work product with impeccable citation standards, proper structure, and verifiable sources suitable for client presentation."""

    user_content = f"""LEGAL OPINION REQUEST:

CLIENT QUESTIONS:
{questions}

RELEVANT FACTS:
{facts}

ASSUMPTIONS:
{assumptions}

Please draft a comprehensive legal opinion following the exact structure specified in your instructions, addressing each question systematically with proper Roman numeral headings, numbered citations throughout, and a complete SOURCES section at the end with URLs for all SAFLII cases."""

    messages = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content}
    ]
    
    # Generate opinion using your Azure OpenAI model
    return call_llm_with(
        messages=messages, 
        temperature=0.0, 
        max_tokens=12000,  # Increased for comprehensive opinions with all sections
        model_deployment_env_var='OPINION_MODEL_DEPLOYMENT', 
        model_version_env_var='OPINION_MODEL_VERSION'
    )