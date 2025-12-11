# File: server/opinion/api_2/shared/rag.py

import json, logging, os, requests, textwrap, time, re
from langchain_text_splitters import RecursiveCharacterTextSplitter
from shared.utils import sleep_random_time
from shared.models import DueDiligence, Document, Folder
import hashlib
from bs4 import BeautifulSoup
from typing import List, Dict

# Check for dev mode
def _is_dev_mode():
    return os.environ.get("DEV_MODE", "").lower() in ("true", "1", "yes", "local")

# Conditionally import Claude adapter for dev mode
if _is_dev_mode():
    logging.info("🔧 [rag] DEV MODE - Using Claude LLM adapter")
    from shared.dev_adapters.claude_llm import (
        call_llm_with as _dev_call_llm_with,
        call_llm_with_search as _dev_call_llm_with_search,
        create_chunks_and_embeddings_from_pages as _dev_create_embeddings
    )

def _sha256(text: str) -> str:
    return hashlib.sha256((text or "").lower().encode("utf-8")).hexdigest()

def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())

def _excerpt(text: str, min_words=8, max_words=24) -> str:
    words = _norm(text).split()
    if len(words) <= max_words:
        return " ".join(words)
    return " ".join(words[:max_words])


def _fetch_saflii_paragraphs(url: str) -> dict:
    """
    Returns {"title": str, "paragraphs": {"1": "...", "2":"..."}, "full_text": "..."}
    Very defensive to accommodate different SAFLII layouts.
    """
    out = {"title": None, "paragraphs": {}, "full_text": ""}
    try:
        r = requests.get(url, timeout=25)
        r.raise_for_status()
        html = r.text
        soup = BeautifulSoup(html, "html.parser")
        # title
        if soup.title and soup.title.string:
            out["title"] = _norm(soup.title.string)

        # collect paragraphs
        para_map = {}
        num_re = re.compile(r"^\s*\(?\s*(\d{1,4})\s*\)?\s*[.\)]?\s+")
        candidates = soup.find_all(["p", "div", "span"], string=True)
        for tag in candidates:
            txt = _norm(tag.get_text(" "))
            m = num_re.match(txt)
            if m:
                pno = m.group(1)
                body = _norm(num_re.sub("", txt, count=1))
                if body:
                    para_map[pno] = body

        # fallback: sequential <p> tags if no numbered paras found
        if not para_map:
            i = 1
            for p in soup.find_all("p"):
                t = _norm(p.get_text(" "))
                if t:
                    para_map[str(i)] = t
                    i += 1

        out["paragraphs"] = para_map
        out["full_text"] = _norm(" ".join(para_map.get(str(i), "") for i in range(1, len(para_map)+1)))
        return out
    except Exception as e:
        logging.warning(f"_fetch_saflii_paragraphs failed for {url}: {e}")
        return out

def build_saflii_case_provenance(cases: list) -> dict:
    """
    Input: list of cases from search/filter.
    Output:
      {
        "cases": [ original cases augmented: {"download_ok": bool, "title": str, "para_count": int} ],
        "provenance": [ {case_url, case_name, citation, court, year, para, excerpt, hash} ],
        "index": { url: { "title": str, "paragraphs": { "1": "text...", "2": "text..." } } }
      }
    """
    prov, augmented, index = [], [], {}
    for c in (cases or []):
        url = (c.get("url") or "").strip()
        if not url or "saflii.org" not in url:
            continue
        parsed = _fetch_saflii_paragraphs(url)
        para_map = parsed.get("paragraphs") or {}
        title = parsed.get("title")
        # keep a compact index (trim paragraphs to keep memory bounded)
        trimmed_map = {k: _norm(v)[:1200] for k, v in list(para_map.items())[:900]}  # soft cap
        index[url] = {"title": title, "paragraphs": trimmed_map}

        keys = list(trimmed_map.keys())
        picks = []
        if keys:
            picks.append(keys[0])
            if len(keys) >= 3:
                picks.append(keys[len(keys)//2])
                picks.append(keys[-1])
            elif len(keys) == 2:
                picks.append(keys[-1])

        for p in picks:
            ex = _excerpt(trimmed_map.get(p, ""))
            if ex:
                prov.append({
                    "case_url": url,
                    "case_name": c.get("case_name") or title or "",
                    "citation": c.get("citation") or "",
                    "court": c.get("court") or "",
                    "year": c.get("year") or "",
                    "para": str(p),
                    "excerpt": ex,
                    "hash": _sha256(ex)
                })

        augmented.append({
            **c,
            "download_ok": bool(trimmed_map),
            "title": title,
            "para_count": len(trimmed_map)
        })

    return {"cases": augmented, "provenance": prov, "index": index}


def llm_filter_saflii_cases(*, cases: list, facts: str, questions: str, assumptions: str, provenance: list) -> dict:
    """
    Takes the 'cases' from structured search and the provenance snippets, and filters/ranks cases.
    Returns { "search_summary": "...", "cases": [...], "total_cases_found": N, "search_queries_used": [] }
    Shape mirrors your earlier structures so callers don't change.
    """
    try:
        # Make a compact JSON for the model (keep within token budget)
        compact_cases = [
            {
                "case_name": c.get("case_name"), "citation": c.get("citation"),
                "year": c.get("year"), "court": c.get("court"), "url": c.get("url"),
                "legal_principle": c.get("legal_principle"), "relevance": c.get("relevance"),
                "download_ok": c.get("download_ok"), "para_count": c.get("para_count")
            } for c in (cases or [])
        ]
        # Short provenance list grouped by case
        prov_by_url = {}
        for p in provenance or []:
            prov_by_url.setdefault(p["case_url"], []).append(
                {"para": p["para"], "excerpt": p["excerpt"]}
            )

        system = f"""
You are a South African legal research editor. Using *only* the inputs provided, rate and select SAFLII cases
that most directly answer the client's QUESTIONS given the FACTS and ASSUMPTIONS.

Decision rules (apply strictly):
- Prefer Constitutional Court/SCA over High Court where otherwise similar.
- Prefer cases with strong substantive alignment in the provenance excerpts.
- Drop cases with no downloadable paragraphs (download_ok == false).
- Avoid duplicates (same URL) and near-duplicates.
- Keep 3–8 best cases where possible.

Return STRICT JSON with the same item shape as input 'cases', but only the selected ones.
Also include a short 'search_summary' string explaining choices.
"""
        user = json.dumps({
            "facts": facts, "questions": questions, "assumptions": assumptions,
            "candidates": compact_cases,
            "provenance": prov_by_url
        }, ensure_ascii=False)

        res = call_llm_with(
            messages=[{"role":"system","content":system},{"role":"user","content":user}],
            temperature=0.0,
            max_tokens=2500,
            model_deployment_env_var='OPINION_MODEL_DEPLOYMENT',
            model_version_env_var='OPINION_MODEL_VERSION'
        )

        # Parse/normalize JSON from response
        # Accept either a full dict or just an array and wrap it
        try:
            start = res.find("{")
            end = res.rfind("}")
            obj = json.loads(res[start:end+1]) if start != -1 and end != -1 else json.loads(res)
        except Exception:
            # If assistant returned array only, wrap it
            try:
                arr = json.loads(res)
                obj = {"cases": arr}
            except Exception:
                logging.warning("llm_filter_saflii_cases: could not parse JSON; falling back to original cases")
                return {
                    "search_summary": "LLM filter failed to parse; using pre-filtered cases",
                    "cases": [c for c in cases if c.get("download_ok")],
                    "total_cases_found": len([c for c in cases if c.get("download_ok")]),
                    "search_queries_used": []
                }

        selected = obj.get("cases", [])
        # Ensure URL still points to saflii, and keep the original fields we had
        cleaned = []
        urls_seen = set()
        for c in selected:
            url = (c.get("url") or "").strip()
            if not url or "saflii.org" not in url:
                continue
            if url in urls_seen:
                continue
            urls_seen.add(url)
            # Merge back any structured fields that might have been omitted by the LLM
            original = next((x for x in cases if (x.get("url") or "").strip() == url), {})
            merged = {**original, **c}
            cleaned.append(merged)

        return {
            "search_summary": obj.get("search_summary", "LLM-selected SAFLII cases"),
            "cases": cleaned,
            "total_cases_found": len(cleaned),
            "search_queries_used": []
        }

    except Exception as e:
        logging.exception("llm_filter_saflii_cases error")
        # Safe fallback: keep downloadable-only
        only_dl = [c for c in (cases or []) if c.get("download_ok")]
        return {
            "search_summary": f"Error during LLM filter: {e}. Returned downloadable-only.",
            "cases": only_dl,
            "total_cases_found": len(only_dl),
            "search_queries_used": []
        }


def filter_saflii_cases(case_law_data: dict) -> dict:
    """Keep only cases with saflii.org URLs and plausible citation; drop everything else."""
    try:
        cases = case_law_data.get("cases", []) or []
        filtered = []
        for c in cases:
            url = (c.get("url") or "").strip()
            if not url or "saflii.org" not in url.lower():
                continue
            # simple neutral/report pattern check (soft gate to avoid over-filtering)
            cit = (c.get("citation") or "") + " " + (c.get("year") or "")
            plausible = bool(re.search(r"\[\d{4}\]\s*ZA[A-Z]{2,}\s*\d+|\d{4}\s*\(\d+\)\s*SA\s*\d+\s*\([A-Z]+\)", cit))
            if not plausible:
                # still allow if URL is saflii; we'll rely on verification pass to catch dubious summaries
                plausible = True
            c["url"] = url
            filtered.append(c)
        return {**case_law_data, "cases": filtered, "total_cases_found": len(filtered)}
    except Exception as e:
        logging.warning(f"filter_saflii_cases error: {e}")
        return {**case_law_data, "cases": [], "total_cases_found": 0}

def verify_draft_with_local_and_web(
    draft_text: str,
    facts: str,
    questions: str,
    assumptions: str,
    saflii_index: dict
) -> dict:
    """
    Parse the draft for case citations (names, neutral/report cites, URLs, pinpoints).
    Try to confirm each proposition using the local SAFLII paragraph index first (exact or near-exact match).
    For misses, fall back to site:saflii.org via web search.
    Return STRICT JSON with:
      - citations[] (each with status, match_source=local|web|none, pinpoints_found, exact_quote, trace_url_with_anchor)
      - verified_cases[] (normalized set for rewriting)
      - matrix[] (per-claim traceability table for audit)
    """
    # Compact local index for the model
    index_payload = {}
    try:
        for url, item in (saflii_index.get("index") or {}).items():
            paras = item.get("paragraphs") or {}
            # keep only first 80 paragraphs (configurable) to stay under token limits
            keep_keys = sorted(paras.keys(), key=lambda x: int(re.sub(r"\D","",x) or 0))[:80]
            index_payload[url] = {
                "title": item.get("title"),
                "paragraphs": {k: paras[k] for k in keep_keys}
            }
    except Exception as e:
        logging.warning(f"verify_draft_with_local_and_web: index compaction error {e}")
        index_payload = {}

    SYSTEM = """
You are a verification auditor for South African legal opinions.
You will receive:
  (1) The Draft,
  (2) A LOCAL SAFLII INDEX (url → {title, paragraphs{para_no:text}}),
  (3) FACTS/QUESTIONS/ASSUMPTIONS.

Task:
A) Extract every case citation in the DRAFT (case name, year, neutral/report citation, any URL, any para pinpoints).
B) For each, attempt LOCAL verification:
   - Find the best matching SAFLII URL from the local index (by URL, citation, or name).
   - If a specific paragraph number is present, check that paragraph for support of the proposition.
   - If no pinpoint, scan up to ±3 paragraphs around likely matches.
   - When support is found, capture an EXACT VERBATIM QUOTE (max 35 words) and record para number(s).
C) For items not verified locally, do a web search strictly on site:saflii.org and repeat B.
D) Classify each item: "verified" | "dubious" | "unverified".
   - verified: content exists and supports the proposition (pinpoint found or a tight match)
   - dubious: case exists but quote/ratio or pinpoint is misaligned
   - unverified: cannot locate on SAFLII
E) Output STRICT JSON ONLY with this schema (no extra keys, no prose):

{
  "summary": "short status",
  "citations": [
    {
      "case_name": "string",
      "year": "string",
      "citation": "string",
      "url_in_draft": "string",
      "url_verified": "string",
      "status": "verified|dubious|unverified",
      "match_source": "local|web|none",
      "pinpoints_in_draft": ["..."],
      "pinpoints_verified": ["..."],
      "support_quote": "verbatim ≤35 words from SAFLII paragraph(s)",
      "support_para_text": "optional slightly longer snippet ≤80 words",
      "reason": "short reason for status"
    }
  ],
  "verified_cases": [
    {
      "case_name": "string",
      "citation": "string",
      "year": "string",
      "court": "string",
      "url": "https://www.saflii.org/....html#para-23",
      "pinpoints": ["..."],
      "support_quote": "verbatim ≤35 words"
    }
  ],
  "matrix": [
    {
      "proposition": "short paraphrase of the proposition from draft",
      "case_name": "string",
      "status": "verified|dubious|unverified",
      "trace": "url#para",
      "quote": "verbatim ≤35 words"
    }
  ]
}
RULES:
- Quote SAFLII text verbatim (≤35 words).
- Prefer the LOCAL index. Only use web search for misses.
- Add an anchor to url_verified if a paragraph is known (format: url + '#para-<n>').
- Return ONLY JSON.
"""
    USER = json.dumps({
        "draft": draft_text,
        "facts": facts,
        "questions": questions,
        "assumptions": assumptions,
        "local_index": index_payload
    }, ensure_ascii=False)

    try:
        res = call_llm_with_search(
            messages=[{"role":"system","content":SYSTEM},{"role":"user","content":USER}],
            max_tokens=7000,
            model="o4-mini",
            enable_web_search=True,
            include_search_results=False
        )
        # Strict JSON extraction
        try:
            start, end = res.find("{"), res.rfind("}")
            obj = json.loads(res[start:end+1]) if start != -1 and end != -1 else json.loads(res)
        except Exception as e:
            logging.warning(f"verify_draft_with_local_and_web parse error: {e}")
            return {"summary":"parse_error","citations":[],"verified_cases":[],"matrix":[],"raw":res}

        # normalize arrays
        obj["citations"] = obj.get("citations", []) or []
        obj["verified_cases"] = obj.get("verified_cases", []) or []
        obj["matrix"] = obj.get("matrix", []) or []
        return obj

    except Exception as e:
        logging.exception("verify_draft_with_local_and_web error")
        return {"summary": f"error: {e}", "citations": [], "verified_cases": [], "matrix": []}


def rewrite_opinion_with_verified_sources_hardtrace(
    draft_text: str,
    verification_report: dict,
    doc_results: list,
    facts: str,
    questions: str,
    assumptions: str
) -> str:
    """
    Rewrites the draft:
      - ONLY allows verified SAFLII cases from verification_report['verified_cases'].
      - Inserts explicit para pinpoints and a ≤35-word verbatim quote the first time a case is used.
      - Removes or marks [UNSUPPORTED] wherever a proposition lacks verified support.
      - Preserves overall structure, tightens language, and appends an 'Audit Appendix' summarizing changes.
    """
    verified_cases = verification_report.get("verified_cases", []) or []
    citations = verification_report.get("citations", []) or []
    matrix = verification_report.get("matrix", []) or []

    # Build compact verified index
    verified_index_lines = []
    for c in verified_cases:
        pin = ", ".join(c.get("pinpoints", []) or [])
        line = f"- {c.get('case_name','Unknown')} | {c.get('citation','')} | {c.get('url','')} | paras: {pin}"
        if c.get("support_quote"):
            line += f"\n  quote: \"{c['support_quote']}\""
        verified_index_lines.append(line)
    verified_block = "\n".join(verified_index_lines) or "None"

    # Build document snippets
    docs_for_prompt = []
    for d in (doc_results or [])[:20]:
        fn = d.get("filename","Unknown file")
        pg = d.get("page_number","N/A")
        ct = (d.get("content","") or "").strip()
        if ct:
            docs_for_prompt.append(f"Filename: {fn} (Page {pg})\nExcerpt: {ct}")
    doc_block = "\n---\n".join(docs_for_prompt) or "No client documents."

    SYSTEM = f"""
You are a senior legal writer. Rewrite the opinion with *hard traceability*.

ALLOWED SOURCES:
1) CLIENT DOCUMENTS (below)
2) VERIFIED SAFLII CASES (below)

HARD RULES:
- Do NOT cite any source other than ALLOWED SOURCES.
- Where a legal proposition relies on case law, use ONLY items from VERIFIED SAFLII CASES.
- The first time you cite a case for a proposition, include:
    • the SAFLII URL with a '#para-<n>' anchor,
    • 'at para <n>',
    • a ≤35-word verbatim quotation from that paragraph enclosed in double quotes.
- Subsequent citations to the same case may omit the quote but MUST keep the pinpoint.
- If no verified support exists, replace the proposition with [UNSUPPORTED] (do not paraphrase unsupported law).
- Maintain the existing high-level section structure but remove fluff; keep it concise and exact.
- Use numbered citations [1], [2], ... consistently.
- Keep all client-document cites in the format (Source: [Filename], Page [X]).
- If the verification snapshot shows any “dubious” items relevant to an issue, include a short **Counter-arguments & Distinctions** sub-section for that issue, explaining why those authorities are not followed (without citing them if not SAFLII-verified).
- At the end, append an "Audit Appendix" listing:
    • Removed/changed citations,
    • Replacements made,
    • Unsupported propositions left as [UNSUPPORTED].

VERIFIED SAFLII CASES (normalized):
{verified_block}

CLIENT DOCUMENTS (snippets):
{doc_block}
    """.strip()

    USER = f"""
DRAFT TO REWRITE:
{draft_text}

FACTS:
{facts}

QUESTIONS:
{questions}

ASSUMPTIONS:
{assumptions}

VERIFICATION SNAPSHOT (for audit awareness only; do not cite this directly):
{json.dumps({
    "citations": [
        {k: v for k, v in c.items() if k in ["case_name","url_in_draft","url_verified","status","pinpoints_in_draft","pinpoints_verified","reason","support_quote"]}
        for c in citations
    ],
    "matrix": matrix[:30]
}, ensure_ascii=False)}
    """.strip()

    return call_llm_with(
        messages=[{"role":"system","content":SYSTEM},{"role":"user","content":USER}],
        temperature=0.0,
        max_tokens=12000,
        model_deployment_env_var='OPINION_MODEL_DEPLOYMENT',
        model_version_env_var='OPINION_MODEL_VERSION'
    )



def call_llm_with(*, messages, temperature=0, max_tokens=4000,
                  end_point_env_var='AZURE_OPENAI_ENDPOINT',
                  key_env_var='AZURE_OPENAI_KEY',
                  model_deployment_env_var='AZURE_MODEL_DEPLOYMENT',
                  model_version_env_var='AZURE_MODEL_VERSION'):
    """
    Enhanced LLM call with exponential backoff and polling for o3-mini
    """
    # Use Claude adapter in dev mode
    if _is_dev_mode():
        return _dev_call_llm_with(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            end_point_env_var=end_point_env_var,
            key_env_var=key_env_var,
            model_deployment_env_var=model_deployment_env_var,
            model_version_env_var=model_version_env_var
        )

    endpoint = os.environ[end_point_env_var]
    api_key = os.environ[key_env_var]
    deployment_name = os.environ[model_deployment_env_var]
    api_version = os.environ[model_version_env_var]
    
    url = f"{endpoint}/openai/deployments/{deployment_name}/chat/completions?api-version={api_version}"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    json_data = {
        "messages": messages, 
        "max_completion_tokens": max_tokens, 
        "model": deployment_name,
    }
    
    # Retry configuration
    max_retries = 5
    base_delay = 2
    max_delay = 60
    
    for attempt in range(max_retries):
        try:
            logging.info(f"LLM call attempt {attempt + 1}/{max_retries}")
            
            response = requests.post(url, headers=headers, json=json_data, timeout=120)
            
            # Handle rate limiting (429)
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', base_delay * (2 ** attempt)))
                retry_after = min(retry_after, max_delay)
                
                logging.warning(
                    f"Rate limited (429) on attempt {attempt + 1}. "
                    f"Waiting {retry_after}s before retry..."
                )
                
                if attempt < max_retries - 1:
                    time.sleep(retry_after)
                    continue
                else:
                    response.raise_for_status()
            
            # Handle server errors (5xx)
            if 500 <= response.status_code < 600:
                wait_time = min(base_delay * (2 ** attempt), max_delay)
                logging.warning(
                    f"Server error ({response.status_code}) on attempt {attempt + 1}. "
                    f"Waiting {wait_time}s before retry..."
                )
                
                if attempt < max_retries - 1:
                    time.sleep(wait_time)
                    continue
                else:
                    response.raise_for_status()
            
            # Success
            response.raise_for_status()
            response_json = response.json()
            
            # Log token usage
            usage = response_json.get("usage", {})
            logging.info(
                f"LLM call successful. Tokens - "
                f"Prompt: {usage.get('prompt_tokens', 0)}, "
                f"Completion: {usage.get('completion_tokens', 0)}, "
                f"Total: {usage.get('total_tokens', 0)}"
            )
            
            reply = response_json["choices"][0]["message"]["content"]
            return reply
            
        except requests.exceptions.Timeout:
            wait_time = min(base_delay * (2 ** attempt), max_delay)
            logging.warning(
                f"Request timeout on attempt {attempt + 1}. "
                f"Waiting {wait_time}s before retry..."
            )
            
            if attempt < max_retries - 1:
                time.sleep(wait_time)
                continue
            else:
                logging.error("Max retries reached after timeout")
                raise
                
        except requests.exceptions.RequestException as e:
            wait_time = min(base_delay * (2 ** attempt), max_delay)
            logging.error(f"Request error on attempt {attempt + 1}: {str(e)}")
            
            if attempt < max_retries - 1:
                time.sleep(wait_time)
                continue
            else:
                logging.error("Max retries reached after request exception")
                raise
                
        except Exception as e:
            logging.exception(f"Unexpected error on attempt {attempt + 1}")
            
            if attempt < max_retries - 1:
                wait_time = min(base_delay * (2 ** attempt), max_delay)
                time.sleep(wait_time)
                continue
            else:
                raise
    
    # Should never reach here, but just in case
    raise Exception("Max retries exceeded without successful response")

def validate_and_enhance_opinion(draft_opinion, facts, questions, assumptions):
    """
    Validate and enhance the opinion to ensure proper legal formatting and citation compliance
    """
    
    validation_instructions = f"""You are a senior legal editor reviewing a draft legal opinion for final quality control.

ORIGINAL DRAFT TO REVIEW:
{draft_opinion}

VALIDATION CHECKLIST:
1. **Citation Compliance**: Ensure all citations follow one of these approved formats:
   - Legislation: (Companies Act, No. 71 of 2008, section X)
   - Client Documents: (Source: [Document Name], Page [X])
   - Case Law: (Case Name v Case Name YEAR (Citation) Court)

2. **Structure Verification**: Confirm the opinion includes:
   - Executive Summary
   - Opinion and Legal Position (with numbered points for each question)
   - Practical Recommendations
   - Conclusion

3. **Legal Accuracy**: Verify that:
   - Each client question is directly addressed
   - Legal reasoning is logical and well-supported
   - Facts from the case are properly integrated
   - Assumptions are appropriately referenced

4. **Professional Standards**: Ensure:
   - Language is appropriate for a senior partner-level opinion
   - Recommendations are specific and actionable
   - Potential risks or limitations are noted where appropriate

CLIENT CONTEXT:
Questions: {questions}
Facts: {facts}
Assumptions: {assumptions}

TASK: Review the draft and provide the final, polished version. Make minimal changes - only fix citation formats, structural issues, or clarity problems. Do not change the substantive legal analysis."""

    messages = [
        {"role": "system", "content": validation_instructions},
        {"role": "user", "content": "Please review and provide the final polished opinion, ensuring all citations and formatting meet professional standards."}
    ]
    
    return call_llm_with(
        messages=messages,
        temperature=0.0,
        max_tokens=6000,
        model_deployment_env_var='OPINION_MODEL_DEPLOYMENT', 
        model_version_env_var='OPINION_MODEL_VERSION'
    )
        
def call_llm_with_search(*, messages, max_tokens=4000,
                         model="o4-mini", enable_web_search=True,  # Changed from o3-mini to gpt-4o
                         max_tool_calls=10, include_search_results=True):
    # Use Claude adapter in dev mode
    if _is_dev_mode():
        return _dev_call_llm_with_search(
            messages=messages,
            max_tokens=max_tokens,
            model=model,
            enable_web_search=enable_web_search,
            max_tool_calls=max_tool_calls,
            include_search_results=include_search_results
        )

    try:
        api_key = os.environ.get("OPENAI_API_KEY", "")
        url = "https://api.openai.com/v1/responses"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        # Convert messages format to Responses API format
        system_instructions = None
        user_input = ""
        
        for message in messages:
            if message["role"] == "system":
                system_instructions = message["content"]
            elif message["role"] == "user":
                if user_input:
                    user_input += "\n\n" + message["content"]
                else:
                    user_input = message["content"]
            elif message["role"] == "assistant":
                logging.warning("Assistant messages found - consider using previous_response_id for multi-turn")
        
        # Build the request payload
        json_data = {
            "model": model,
            "input": user_input,
            "max_output_tokens": max_tokens,
            "parallel_tool_calls": True,
            "max_tool_calls": max_tool_calls,
        }
        
        # Add system instructions if present
        if system_instructions:
            json_data["instructions"] = system_instructions
        
        # Enable web search tool - use the correct tool type
        if enable_web_search:
            json_data["tools"] = [
                {
                    "type": "web_search_preview"  # This is the correct tool type name
                }
            ]
            json_data["tool_choice"] = "auto"
        
        # Include search results in response if requested
        if include_search_results and enable_web_search:
            json_data["include"] = ["web_search_call.results"]
        
        logging.info(f"OpenAI Responses API request: model={model}, web_search={enable_web_search}")
        logging.info(f"Request payload: {json.dumps(json_data, indent=2)}")  # Enhanced logging
        
        # Make the API call
        response = requests.post(url, headers=headers, json=json_data)
        
        logging.info(f"OpenAI Responses API status: {response.status_code}")
        
        if response.status_code != 200:
            logging.error(f"API Error: {response.text}")
            response.raise_for_status()
        
        response_data = response.json()
        
        logging.info(f"Response status: {response_data.get('status')}")
        logging.info(f"Response ID: {response_data.get('id')}")
        
        # Parse the response
        if response_data.get("status") == "completed":
            output = response_data.get("output", [])
            
            if not output:
                raise ValueError("No output in completed response")
            
            # Extract the main text response and web search info
            main_text = ""
            web_search_details = []
            
            for output_item in output:
                if output_item.get("type") == "message":
                    content = output_item.get("content", [])
                    for content_item in content:
                        if content_item.get("type") == "output_text":
                            main_text = content_item.get("text", "")
                
                elif output_item.get("type") == "tool_call" and output_item.get("tool_type") == "web_search_preview":
                    # Enhanced web search logging
                    search_input = output_item.get("input", {})
                    search_query = search_input.get("query", "Unknown query")
                    
                    logging.info(f"Web search performed for: {search_query}")
                    
                    # Extract search results if included
                    if "results" in output_item:
                        search_results = output_item["results"]
                        logging.info(f"Web search found {len(search_results)} results")
                        
                        # Log first few results for debugging
                        for i, result in enumerate(search_results[:3]):  # Log first 3 results
                            logging.info(f"Result {i+1}: {result.get('title', 'No title')} - {result.get('url', 'No URL')}")
                        
                        web_search_details.append({
                            "query": search_query,
                            "results_count": len(search_results),
                            "results": search_results[:5]  # Keep top 5 for response
                        })
            
            if not main_text:
                raise ValueError("No text content found in response")
            
            # Append web search summary if requested
            if web_search_details and include_search_results:
                search_summary = "\n\n=== WEB SEARCH PERFORMED ===\n"
                for search in web_search_details:
                    search_summary += f"Query: '{search['query']}' - {search['results_count']} results found\n"
                    for result in search['results']:
                        search_summary += f"- {result.get('title', 'No title')}: {result.get('url', 'No URL')}\n"
                search_summary += "=========================="
                final_response = main_text + search_summary
            else:
                final_response = main_text
            
            # Log usage information
            usage = response_data.get("usage", {})
            logging.info(f"Token usage - Input: {usage.get('input_tokens', 0)}, Output: {usage.get('output_tokens', 0)}, Total: {usage.get('total_tokens', 0)}")
            
            return final_response
            
        elif response_data.get("status") == "failed":
            error = response_data.get("error", {})
            error_message = error.get("message", "Unknown error")
            logging.error(f"OpenAI Responses API failed: {error_message}")
            raise Exception(f"API request failed: {error_message}")
            
        else:
            raise ValueError(f"Unexpected response status: {response_data.get('status')}")
        
    except Exception as e:
        logging.exception("❌ Error in call_llm_with_search")
        logging.error(f"Error details: {str(e)}")
        raise e
    
def parse_completed_response(response_data, include_search_results):
    """
    Parse a completed response from the OpenAI Responses API
    """
    output = response_data.get("output", [])
    
    if not output:
        raise ValueError("No output in completed response")
    
    # Extract the main text response and web search info
    main_text = ""
    web_search_details = []
    
    for output_item in output:
        if output_item.get("type") == "message":
            content = output_item.get("content", [])
            for content_item in content:
                if content_item.get("type") == "output_text":
                    main_text = content_item.get("text", "")
        
        elif output_item.get("type") == "tool_call" and output_item.get("tool_type") == "web_search_preview":
            # Enhanced web search logging
            search_input = output_item.get("input", {})
            search_query = search_input.get("query", "Unknown query")
            
            logging.info(f"Web search performed for: {search_query}")
            
            # Extract search results if included
            if "results" in output_item:
                search_results = output_item["results"]
                logging.info(f"Web search found {len(search_results)} results")
                
                # Log first few results for debugging
                for i, result in enumerate(search_results[:3]):
                    logging.info(f"Result {i+1}: {result.get('title', 'No title')} - {result.get('url', 'No URL')}")
                
                web_search_details.append({
                    "query": search_query,
                    "results_count": len(search_results),
                    "results": search_results[:5]
                })
    
    if not main_text:
        raise ValueError("No text content found in response")
    
    # Append web search summary if requested
    if web_search_details and include_search_results:
        search_summary = "\n\n=== WEB SEARCH PERFORMED ===\n"
        for search in web_search_details:
            search_summary += f"Query: '{search['query']}' - {search['results_count']} results found\n"
            for result in search['results']:
                search_summary += f"- {result.get('title', 'No title')}: {result.get('url', 'No URL')}\n"
        search_summary += "=========================="
        final_response = main_text + search_summary
    else:
        final_response = main_text
    
    # Log usage information
    usage = response_data.get("usage", {})
    logging.info(f"Token usage - Input: {usage.get('input_tokens', 0)}, Output: {usage.get('output_tokens', 0)}, Total: {usage.get('total_tokens', 0)}")
    
    return final_response
        
def get_llm_summaryChat(doc_results, prompt):
    formatted_doc_results = "\n\n".join(
        f"Document ID: {doc_result.get('doc_id', 'Unknown')}\nFilename: {doc_result.get('filename', 'Unknown file')}\nPage Number: {doc_result.get('page_number', 'N/A')}\nContent: {doc_result.get('content', '').strip()}"
        for doc_result in doc_results
    )
    
    messages = [
        {"role": "system", "content": textwrap.dedent(f"""
            {prompt}
            
            Here are the source documents provided by the client. Use ONLY this information as your source:
            {formatted_doc_results}
            
            CRITICAL INSTRUCTIONS FOR YOUR RESPONSE:
            
            1. STRUCTURE your response using this EXACT format:
            
            ## Executive Summary
            [Provide a concise 1-2 sentence direct answer to the question]
            
            ## Detailed Analysis
            [Provide thorough analysis with specific references]
            
            ## Key Findings
            [Use bullet points for main discoveries, each with confidence scores and citations]
            
            ## Source References
            [List all documents referenced with page numbers]
            
            2. CONFIDENCE SCORING: For every factual claim, include a confidence score using this format:
            - **High Confidence (90-100%)**: Information explicitly stated in multiple sources or clearly documented
            - **Medium Confidence (70-89%)**: Information clearly stated in one reliable source
            - **Low Confidence (50-69%)**: Information inferred or partially documented
            - **Uncertain (<50%)**: Information unclear or contradictory
            
            3. CITATIONS: Use this exact format for every claim:
            - For direct quotes: "exact text" (Source: [Filename], Page [X])
            - For paraphrased information: [Information] (Source: [Filename], Page [X])
            - For cross-referenced information: [Information] (Sources: [Filename1], Page [X]; [Filename2], Page [Y])
            
            4. FORMATTING REQUIREMENTS:
            - Use markdown formatting with proper headers (##)
            - Use bullet points for lists
            - Use **bold** for confidence levels
            - Use *italics* for document names
            - Include direct quotes in quotation marks when relevant
            
            5. LEGAL PRECISION:
            - Be specific about dates, amounts, and legal terms
            - Distinguish between different types of shares/instruments
            - Note any discrepancies between documents
            - Highlight any missing information that would be relevant
            
            If the provided information is insufficient to answer the question meaningfully, respond with "NONE".
            """)},
        {"role": "user", "content": "Extract the relevant information as requested, following the structured format and citation requirements exactly."}
    ]
    
    temperature = 0.0
    max_tokens = 4_000
    
    return call_llm_with(messages=messages, temperature=temperature, max_tokens=max_tokens)

def get_llm_summary(doc_results, prompt):

    formatted_doc_results = "\n\n".join(
        f"Filename: {doc_result.get('filename', 'Unknown file')}\nPage Number: {doc_result.get('page_number', 'N/A')}\nContent: {doc_result.get('content', '').strip()}"
        for doc_result in doc_results
    )

    messages = [
        {"role": "system", "content": textwrap.dedent(f"""
            {prompt}

            Here is additional files and content provided by the client. Use it as your only source of information. If this information is not helpful just reply with "NONE":
            {formatted_doc_results}

            
            """)},
            {"role" : "user", "content" : f"""
Extract the relevant information as requested.
            """}
        ]
    # TODO make this more reusable - prompt wise
    temperature = 0.0
    max_tokens = 4_000
    
    return call_llm_with(messages=messages, temperature=temperature, max_tokens=max_tokens)


def clean_text(text: str) -> str: # TODO
    text = re.sub(r"\s+", " ", text)  # normalize whitespace
    text = re.sub(r"\n{2,}", "\n", text)  # remove extra line breaks
    text = re.sub(r"Page \d+ of \d+", "", text)  # remove common footers
    text = text.strip()
    return text

def split_text(text, chunk_size=500, chunk_overlap=50): # TODO check consistency between APIs
    logging.info("split_text 2")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,  # 50 tokens overlap
        separators=["\n\n", "\n", ".", " ", ""]
    )

    chunks = text_splitter.split_text(text)
    return chunks

def split_text_by_page(pages, chunk_size=500, chunk_overlap=50): # TODO check consistency between APIs
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ".", " ", ""]
    )

    split_chunks = []

    for page in pages:
        page_number = page["page_number"]
        text = page["text"]

        chunks = text_splitter.split_text(text)

        for idx, chunk in enumerate(chunks):
            split_chunks.append({
                "page_number": page_number,
                "chunk_index": idx,
                "text": chunk
            })

    return split_chunks


def create_chunks_and_embeddings_from_text(text: str) -> List[Dict]:
    """
    Optimized version for single text input.
    """
    text_chunks = split_text(text)
    
    pages_format = [
        {
            "text": chunk,
            "page_number": 1,
            "chunk_index": idx
        }
        for idx, chunk in enumerate(text_chunks)
    ]
    
    embeddings_with_metadata = create_chunks_and_embeddings_from_pages(pages_format, batch_size=500)
    return [
        {
            "chunk": item["chunk"],
            "embedding": item["embedding"]
        }
        for item in embeddings_with_metadata
    ]

def create_chunks_and_embeddings_from_pages(pages: List[Dict], batch_size: int = 500) -> List[Dict]:
    """
    Optimized embedding generation. Rate Lims -> 150,000 TPM, 900 RPM

    Args:
        pages: List of page chunks with text, page_number, chunk_index
        batch_size: Number of chunks to process per call

    Returns:
        List of dicts with chunk, page_number, chunk_index, and embedding
    """
    # Use Claude adapter (mock embeddings) in dev mode
    if _is_dev_mode():
        return _dev_create_embeddings(pages, batch_size)

    embeddings = []

    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
    api_key = os.environ.get("AZURE_OPENAI_KEY")
    #TODO -> Def as ENV var, but easier to change on the fly
    deployment_name = "text-embedding-3-large"
    api_version = "2024-02-01"
    
    url = f"{endpoint}/openai/deployments/{deployment_name}/embeddings?api-version={api_version}"
    
    headers = {
        "Content-Type": "application/json",
        "api-key": api_key
    }
    
    total_pages = len(pages)
    logging.info(f"Starting embedding generation for {total_pages} chunks")
    
    start_time = time.time()
    successful_batches = 0
    total_tokens_processed = 0
    
    for i in range(0, total_pages, batch_size):
        batch = pages[i:i + batch_size]
        texts = [item["text"] for item in batch]
        
        data = {
            "input": texts,
            "encoding_format": "float",
            "dimensions": 1536 #Compatible with current index
        }
        
        # Retry logic with exponential backoff
        max_retries = 4
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                response = requests.post(url, headers=headers, json=data, timeout=60)
                
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', retry_delay))
                    logging.warning(
                        f"Rate limited on batch {i//batch_size + 1}/{(total_pages + batch_size - 1)//batch_size} "
                        f"(attempt {attempt + 1}/{max_retries}). Waiting {retry_after}s..."
                    )
                    if attempt < max_retries - 1:
                        time.sleep(retry_after)
                        retry_delay *= 2
                        continue
                    else:
                        response.raise_for_status()
                
                response.raise_for_status()

                response_data = response.json()
                batch_embeddings = response_data["data"]

                usage = response_data.get("usage", {})
                tokens_used = usage.get("total_tokens", 0)
                total_tokens_processed += tokens_used

                for j, emb in enumerate(batch_embeddings):
                    item = batch[j]
                    embeddings.append({
                        "chunk": item["text"],
                        "page_number": item["page_number"],
                        "chunk_index": item["chunk_index"],
                        "embedding": emb["embedding"]
                    })
                
                successful_batches += 1
                

                if successful_batches % 5 == 0:
                    elapsed = time.time() - start_time
                    rate = successful_batches / elapsed if elapsed > 0 else 0
                    logging.info(
                        f"Batch {successful_batches}/{(total_pages + batch_size - 1)//batch_size} complete | "
                        f"Rate: {rate:.2f} batches/sec | Tokens: {total_tokens_processed:,}"
                    )
                break
                
            except requests.exceptions.Timeout:
                logging.warning(
                    f"Timeout on batch {i//batch_size + 1} (attempt {attempt + 1}/{max_retries})"
                )
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                else:
                    logging.error(f"Failed after {max_retries} timeout attempts")
                    raise
                    
            except requests.exceptions.HTTPError as e:
                logging.error(
                    f"HTTP error on batch {i//batch_size + 1}: {e.response.status_code} - {e.response.text}"
                )
                
                if 500 <= e.response.status_code < 600 and attempt < max_retries - 1:
                    logging.info(f"🔄 Retrying due to server error (attempt {attempt + 2}/{max_retries})...")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                else:
                    raise
                    
            except Exception as e:
                logging.error(f"❌ Unexpected error on batch {i//batch_size + 1}: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                else:
                    raise
    
    elapsed = time.time() - start_time
    chunks_per_sec = len(embeddings) / elapsed if elapsed > 0 else 0
    
    logging.info(
        f"Embedding generation complete! "
        f"{len(embeddings)} chunks in {elapsed:.1f}s "
        f"({chunks_per_sec:.1f} chunks/sec, {total_tokens_processed:,} tokens)"
    )
    
    return embeddings

def assess_legal_risks(answer_text, document_results, dd_briefing):
    """
    Assess legal risks in the provided answer and documents with yellow/amber/red classification
    """
    try:
        # Prepare document context
        doc_context = "\n\n".join([
            f"Document: {doc.get('filename', 'Unknown')}\nPage: {doc.get('page_number', 'N/A')}\nContent: {doc.get('content', '')[:500]}..."
            for doc in document_results[:5]  # Limit to avoid token limits
        ])
        
        risk_assessment_prompt = textwrap.dedent(f"""
            You are a senior legal risk analyst specializing in South African corporate law and due diligence.
            
            Your task is to identify and classify potential legal risks based on the analysis and supporting documents.
            
            DUE DILIGENCE CONTEXT:
            {dd_briefing}
            
            ANALYSIS TO REVIEW:
            {answer_text}
            
            SUPPORTING DOCUMENTS:
            {doc_context}
            
            RISK CLASSIFICATION GUIDELINES:
            
            🔴 RED RISKS (High/Critical):
            - Regulatory non-compliance or violations
            - Material contract breaches or defaults
            - Litigation risks with significant financial exposure
            - Corporate governance failures
            - Insolvency or financial distress indicators
            - Missing critical regulatory approvals or licenses
            - Tax compliance issues with material exposure
            
            🟠 AMBER RISKS (Medium/Moderate):
            - Potential compliance gaps requiring attention
            - Contract terms that may be disadvantageous
            - Operational risks that could impact business
            - Incomplete documentation or missing records
            - Related party transactions requiring scrutiny
            - Environmental or social compliance concerns
            - Intellectual property vulnerabilities
            
            🟡 YELLOW RISKS (Low/Administrative):
            - Minor documentation inconsistencies
            - Administrative compliance matters
            - Process improvements needed
            - Information gaps that should be filled
            - Best practice recommendations
            - Minor contractual clarifications needed
            
            REQUIRED OUTPUT FORMAT:
            Provide a JSON array of risks. Each risk must include:
            - "level": "red", "amber", or "yellow"
            - "category": (e.g., "Regulatory Compliance", "Contract Risk", "Financial Risk", etc.)
            - "description": Brief description of the specific risk
            - "impact": Potential business impact
            - "recommendation": Specific action recommended
            - "confidence": "high", "medium", or "low" based on evidence quality
            - "supporting_docs": Array of relevant document filenames
            
            If no significant risks are identified, return an empty array [].
            
            Focus on actionable, specific risks rather than generic concerns.
        """)
        
        messages = [
            {"role": "system", "content": risk_assessment_prompt},
            {"role": "user", "content": "Analyze the provided information and identify specific legal risks with appropriate classifications."}
        ]
        
        risk_response = call_llm_with(
            messages=messages,
            temperature=0.1,
            max_tokens=2000
        )
        
        # Parse JSON response
        try:
            # Extract JSON from response if it's wrapped in text
            import re
            json_match = re.search(r'\[.*\]', risk_response, re.DOTALL)
            if json_match:
                risks_data = json.loads(json_match.group())
            else:
                # Try to parse the whole response
                risks_data = json.loads(risk_response)
            
            # Validate and clean the risks data
            validated_risks = []
            for risk in risks_data:
                if isinstance(risk, dict) and 'level' in risk and 'description' in risk:
                    # Ensure required fields
                    validated_risk = {
                        "level": risk.get("level", "yellow").lower(),
                        "category": risk.get("category", "General"),
                        "description": risk.get("description", ""),
                        "impact": risk.get("impact", ""),
                        "recommendation": risk.get("recommendation", ""),
                        "confidence": risk.get("confidence", "medium").lower(),
                        "supporting_docs": risk.get("supporting_docs", [])
                    }
                    
                    # Validate level
                    if validated_risk["level"] not in ["red", "amber", "yellow"]:
                        validated_risk["level"] = "yellow"
                    
                    validated_risks.append(validated_risk)
            
            return validated_risks
            
        except json.JSONDecodeError as e:
            logging.warning(f"Could not parse risk assessment JSON: {e}")
            # Return a fallback risk assessment
            return [
                {
                    "level": "yellow",
                    "category": "Analysis Required",
                    "description": "Manual risk assessment required - automated analysis inconclusive",
                    "impact": "Unknown",
                    "recommendation": "Review documents manually for potential risks",
                    "confidence": "low",
                    "supporting_docs": []
                }
            ]
    
    except Exception as e:
        logging.error(f"Error in risk assessment: {str(e)}")
        return []


def combine_multiple_responses(question, individual_responses, dd_briefing, perspective_lens):
    """
    Combine multiple individual responses into a cohesive, comprehensive answer
    """
    try:
        # Prepare individual responses for the prompt
        responses_text = ""
        for i, response in enumerate(individual_responses, 1):
            source_info = f"{response['source_type'].title()} {response['source_id']}"
            responses_text += f"\n\n=== RESPONSE {i} - {source_info} ===\n{response['answer']}\n"
        
        combination_prompt = textwrap.dedent(f"""
            You are a senior South African corporate lawyer synthesizing multiple analyses for a comprehensive due diligence opinion.
            
            ORIGINAL QUESTION:
            {question}
            
            DUE DILIGENCE CONTEXT:
            {dd_briefing}
            
            YOUR PERSPECTIVE:
            {perspective_lens}
            
            INDIVIDUAL ANALYSES TO SYNTHESIZE:
            {responses_text}
            
            CRITICAL FORMATTING REQUIREMENTS:
            You MUST maintain the EXACT same formatting structure as the individual responses. This is essential for proper display:
            
            1. STRUCTURE your response using this EXACT format:
            
            ## Executive Summary
            [Provide a concise 1-2 sentence direct answer to the question]
            
            ## Detailed Analysis
            [Provide thorough synthesized analysis with specific references]
            
            ## Key Findings
            [Use bullet points for main discoveries, each with confidence scores and citations]
            
            ## Source References
            [List all documents referenced with page numbers]
            
            2. CONFIDENCE SCORING: Use this EXACT format for every factual claim:
            - **High Confidence (90-100%)**: Information explicitly stated in multiple sources or clearly documented
            - **Medium Confidence (70-89%)**: Information clearly stated in one reliable source
            - **Low Confidence (50-69%)**: Information inferred or partially documented
            - **Uncertain (<50%)**: Information unclear or contradictory
            
            3. CITATIONS: Use this exact format for every claim:
            - For direct quotes: "exact text" (Source: [Filename], Page [X])
            - For paraphrased information: [Information] (Source: [Filename], Page [X])
            - For cross-referenced information: [Information] (Sources: [Filename1], Page [X]; [Filename2], Page [Y])
            
            4. FORMATTING REQUIREMENTS:
            - Use markdown formatting with proper headers (##)
            - Use bullet points for lists
            - Use **bold** for confidence levels exactly as shown above
            - Use *italics* for document names
            - Include direct quotes in quotation marks when relevant
            
            5. SYNTHESIS REQUIREMENTS:
            - Identify common themes across sources
            - Highlight contradictions or inconsistencies between sources
            - Provide a unified view while noting source-specific insights
            - Maintain all confidence indicators from individual responses using the EXACT format above
            - Preserve all citation information
            - Do not simply concatenate responses - synthesize them intelligently
            - Eliminate redundancy while preserving important details
            - Connect insights across sources
            - Flag any gaps or areas needing additional investigation
            
            6. LEGAL PRECISION:
            - Be specific about dates, amounts, and legal terms
            - Distinguish between different types of shares/instruments
            - Note any discrepancies between documents
            - Highlight any missing information that would be relevant
            
            IMPORTANT: The formatting MUST match exactly what individual responses use. Pay special attention to confidence scoring format.
        """)
        
        messages = [
            {"role": "system", "content": combination_prompt},
            {"role": "user", "content": "Please synthesize these individual analyses into a comprehensive, unified response following the exact formatting requirements."}
        ]
        
        combined_response = call_llm_with(
            messages=messages,
            temperature=0.1,  # Lower temperature for more consistent formatting
            max_tokens=4000
        )
        
        return combined_response
        
    except Exception as e:
        logging.error(f"Error combining responses: {str(e)}")
        # Fallback: return a simple concatenation with proper formatting
        fallback_response = textwrap.dedent(f"""
        ## Executive Summary
        
        Based on review of multiple sources, analysis has been provided across {len(individual_responses)} different references.
        
        ## Detailed Analysis
        
        The following analysis synthesizes findings from multiple sources:
        
        """)
        
        for i, response in enumerate(individual_responses, 1):
            fallback_response += f"**Source {i} ({response['source_type']}):**\n{response['answer']}\n\n"
        
        fallback_response += """
        ## Key Findings
        
        - **High Confidence (90-100%)**: Multiple sources reviewed across different document sets
        - **Medium Confidence (70-89%)**: Individual source analyses completed successfully
        
        ## Source References
        
        Multiple documents referenced across all analyzed sources.
        """
        
        return fallback_response


def get_llm_summaryChat_enhanced(doc_results, prompt, include_risk_assessment=True):
    """
    Enhanced version of get_llm_summaryChat with improved risk awareness
    """
    formatted_doc_results = "\n\n".join(
        f"Document ID: {doc_result.get('doc_id', 'Unknown')}\nFilename: {doc_result.get('filename', 'Unknown file')}\nPage Number: {doc_result.get('page_number', 'N/A')}\nContent: {doc_result.get('content', '').strip()}"
        for doc_result in doc_results
    )
    
    enhanced_prompt = f"""
    {prompt}
    
    Here are the source documents provided by the client. Use ONLY this information as your source:
    {formatted_doc_results}
    
    CRITICAL INSTRUCTIONS FOR YOUR RESPONSE:
    
    1. STRUCTURE your response using this EXACT format:
    
    ## Executive Summary
    [Provide a concise 1-2 sentence direct answer to the question]
    
    ## Detailed Analysis
    [Provide thorough analysis with specific references]
    
    ## Key Findings
    [Use bullet points for main discoveries, each with confidence scores and citations]
    
    ## Risk Indicators
    [Highlight any potential legal, regulatory, or business risks identified]
    
    ## Source References
    [List all documents referenced with page numbers]
    
    2. CONFIDENCE SCORING: For every factual claim, include a confidence score using this format:
    - **High Confidence (90-100%)**: Information explicitly stated in multiple sources or clearly documented
    - **Medium Confidence (70-89%)**: Information clearly stated in one reliable source
    - **Low Confidence (50-69%)**: Information inferred or partially documented
    - **Uncertain (<50%)**: Information unclear or contradictory
    
    3. CITATIONS: Use this exact format for every claim:
    - For direct quotes: "exact text" (Source: [Filename], Page [X])
    - For paraphrased information: [Information] (Source: [Filename], Page [X])
    - For cross-referenced information: [Information] (Sources: [Filename1], Page [X]; [Filename2], Page [Y])
    
    4. RISK AWARENESS: Pay special attention to:
    - Regulatory compliance issues
    - Contract terms that may be problematic
    - Missing documentation or approvals
    - Financial irregularities or concerns
    - Governance or operational issues
    - Potential liabilities or exposures
    
    5. LEGAL PRECISION:
    - Be specific about dates, amounts, and legal terms
    - Distinguish between different types of shares/instruments
    - Note any discrepancies between documents
    - Highlight any missing information that would be relevant
    - Flag any time-sensitive matters or deadlines
    
    If the provided information is insufficient to answer the question meaningfully, respond with "NONE".
    """
    
    messages = [
        {"role": "system", "content": enhanced_prompt},
        {"role": "user", "content": "Extract the relevant information as requested, following the structured format and citation requirements exactly, with particular attention to potential risks."}
    ]
    
    temperature = 0.0
    max_tokens = 4_000
    
    return call_llm_with(messages=messages, temperature=temperature, max_tokens=max_tokens)

def generate_document_description(filename: str, file_content: str, file_type: str, 
                                 folder_path: str = None, max_content_chars: int = 1000) -> str:
    """
    Generate a concise AI description of a document for legal due diligence.
    
    Args:
        filename: The name of the file
        file_content: The extracted text content (first 1000 chars will be used)
        file_type: The file extension/type
        folder_path: The folder path where the document is located
        max_content_chars: Maximum characters of content to analyze
    
    Returns:
        A concise description of the document
    """
    try:
        # Truncate content to avoid token limits
        truncated_content = file_content[:max_content_chars] if file_content else "No content extracted"
        
        # Add ellipsis if content was truncated
        if len(file_content) > max_content_chars:
            truncated_content += "..."
        
        system_prompt = textwrap.dedent("""
            You are a legal AI assistant specializing in due diligence document analysis.
            Your task is to generate a concise, informative description of a document based on its filename and initial content.
            
            The description should:
            1. Be 2-3 sentences maximum
            2. Identify the document type and purpose
            3. Highlight key legal or business relevance
            4. Note any critical dates, parties, or amounts if visible
            5. Use clear, professional language suitable for lawyers
            
            Focus on what would be most useful for a lawyer searching through documents later.
            If the content is unclear or insufficient, make reasonable inferences from the filename.
        """)
        
        user_prompt = f"""
        Generate a concise description for this document:
        
        Filename: {filename}
        File Type: {file_type}
        Folder Location: {folder_path if folder_path else 'Root folder'}
        
        Initial Content:
        {truncated_content}
        
        Provide only the description, no additional commentary.
        """
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        description = call_llm_with(
            messages=messages,
            temperature=0.1,  # Low temperature for consistency
            max_tokens=200,
            model_deployment_env_var='OPINION_MODEL_DEPLOYMENT',
            model_version_env_var='OPINION_MODEL_VERSION'
        )
        
        return description.strip()
        
    except Exception as e:
        logging.error(f"Failed to generate description for {filename}: {str(e)}")
        # Fallback to basic description
        return f"{file_type.upper()} document: {filename}"


def generate_folder_description(folder_name: str, folder_path: str, 
                               document_descriptions: list, dd_briefing: str = None) -> str:
    """
    Generate a concise AI description of a folder based on its contents.
    
    Args:
        folder_name: The name of the folder
        folder_path: The full path of the folder
        document_descriptions: List of document descriptions in this folder
        dd_briefing: The due diligence briefing context
    
    Returns:
        A concise description of the folder's contents and purpose
    """
    try:
        # Prepare document summary
        if document_descriptions:
            doc_summary = "\n".join([f"- {desc[:100]}..." if len(desc) > 100 else f"- {desc}" 
                                    for desc in document_descriptions[:10]])  # Limit to first 10 docs
            doc_count = len(document_descriptions)
        else:
            doc_summary = "No documents in this folder"
            doc_count = 0
        
        system_prompt = textwrap.dedent("""
            You are a legal AI assistant specializing in due diligence document organization.
            Your task is to generate a concise description of a folder based on its name and contents.
            
            The description should:
            1. Be 2-3 sentences maximum
            2. Summarize the type and purpose of documents in the folder
            3. Identify the folder's role in the due diligence process
            4. Note any patterns or themes in the documentation
            5. Use clear, professional language suitable for lawyers
            
            Focus on helping lawyers quickly understand what's in this folder.
        """)
        
        user_prompt = f"""
        Generate a concise description for this folder:
        
        Folder Name: {folder_name}
        Folder Path: {folder_path}
        Number of Documents: {doc_count}
        
        {"Due Diligence Context: " + dd_briefing if dd_briefing else ""}
        
        Document Summaries in this folder:
        {doc_summary}
        
        Provide only the folder description, no additional commentary.
        """
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        description = call_llm_with(
            messages=messages,
            temperature=0.3,
            max_tokens=200
        )
        
        return description.strip()
        
    except Exception as e:
        logging.error(f"Failed to generate description for folder {folder_name}: {str(e)}")
        # Fallback to basic description
        return f"Folder containing {doc_count} documents related to {folder_name}"


def generate_all_folder_descriptions(dd_id: str, session):
    """
    Generate descriptions for all folders in a due diligence after documents are processed.
    This should be called after all documents have been processed.
    """
    try:
        from datetime import datetime
        
        # Get the due diligence briefing
        dd = session.query(DueDiligence).filter(DueDiligence.id == dd_id).first()
        dd_briefing = dd.briefing if dd else None
        
        # Get all folders for this DD
        folders = session.query(Folder).filter(
            Folder.dd_id == dd_id
        ).all()
        
        for folder in folders:
            # Skip if description already exists and is recent (less than 24 hours old)
            if folder.description and folder.description_generated_at:
                time_since_generation = datetime.utcnow() - folder.description_generated_at
                if time_since_generation.total_seconds() < 86400:  # 24 hours
                    logging.info(f"Skipping folder {folder.folder_name} - recent description exists")
                    continue
            
            # Get all document descriptions in this folder
            documents = session.query(Document).filter(
                Document.folder_id == folder.id,
                Document.is_original == False,
                Document.processing_status == "Complete"
            ).all()
            
            document_descriptions = [doc.description for doc in documents if doc.description]
            
            # Generate folder description
            folder.description = generate_folder_description(
                folder_name=folder.folder_name,
                folder_path=folder.path,
                document_descriptions=document_descriptions,
                dd_briefing=dd_briefing
            )
            folder.description_generated_at = datetime.utcnow()
            
            logging.info(f"Generated description for folder: {folder.folder_name}")
            
            # Commit periodically to avoid losing progress
            session.commit()
            
            # Add a small delay to avoid rate limiting
            sleep_random_time(1, 3)
            
    except Exception as e:
        logging.error(f"Failed to generate folder descriptions: {str(e)}")
        session.rollback()
        raise