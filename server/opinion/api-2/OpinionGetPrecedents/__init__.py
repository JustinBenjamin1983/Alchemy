import logging
import azure.functions as func
import json
import os
import re

from shared.utils import auth_get_email
from shared.table_storage import get_user_info
from shared.rag import call_llm_with_search

def _strip_code_fences(s: str) -> str:
    if not isinstance(s, str):
        return s
    s = s.strip()
    # remove ```json ... ``` or ``` ... ```
    s = re.sub(r"^```(?:json)?\s*", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\s*```$", "", s)
    return s.strip()

def _parse_json_maybe(text: str):
    """Try to parse JSON from raw model output, tolerating code fences."""
    if not text:
        return None
    text = _strip_code_fences(text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to pull a JSON object from inside markdown/text
        m = re.search(r"(\{(?:.|\n)*\})", text)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                pass
    return None

def _build_messages(facts: str, questions: str, assumptions: str):
    system = f"""You are a South African legal research specialist.

REQUIREMENTS:
- Search ONLY SAFLII (enforce 'site:saflii.org').
- Return STRICT JSON (no commentary/text) with keys:
{{
  "search_summary": "short string",
  "cases": [
    {{
      "case_name": "Full case title",
      "citation": "standard SA citation if available",
      "url": "https://www.saflii.org/…",
      "legal_principle": "one-sentence principle",
      "relevance": "one-sentence why it matters"
    }}
  ],
  "total_cases_found": 0,
  "search_queries_used": ["..."]
}}

MATTER:
FACTS: {facts}
QUESTIONS: {questions}
ASSUMPTIONS: {assumptions}

Only include cases with a valid SAFLII URL. If unsure, omit."""
    user = (
        "Perform a SAFLII-only search (site:saflii.org) relevant to the matter, "
        "then return the JSON exactly as specified."
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("✅ Find Case Law function triggered.")

    # auth
    if req.headers.get("function-key") != os.environ.get("FUNCTION_KEY"):
        logging.info("❌ Invalid function key")
        return func.HttpResponse("", status_code=401)

    try:
        email, err = auth_get_email(req)
        if err:
            logging.exception("❌ auth_get_email failed")
            return err

        data = req.get_json()
        opinion_id = data.get("opinion_id")
        if not opinion_id:
            return func.HttpResponse("opinion_id not supplied", status_code=400)

        # load opinion from table storage
        user_info = get_user_info(email) or {}
        payload = user_info.get("clean_payload") or user_info.get("payload") or {}
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except Exception:
                payload = {}

        found = None
        for op in payload.get("opinions", []):
            if op.get("id") == opinion_id:
                found = op
                break
        if not found:
            return func.HttpResponse("Opinion not found", status_code=404)

        facts = found.get("facts", "")
        questions = found.get("questions", "")  # ← fixed (was facts)
        assumptions = found.get("assumptions", "")

        # run SAFLII search via GPT web
        messages = _build_messages(facts, questions, assumptions)
        raw = call_llm_with_search(
            messages=messages,
            enable_web_search=True,
            # The tiny, fast model is fine for search orchestration; tune as needed
            model=os.environ.get("GPT_SEARCH_MODEL", "o4-mini"),
            max_tokens=8000,
        )

        parsed = _parse_json_maybe(raw) or {}
        cases_in = parsed.get("cases", [])
        summary = parsed.get("search_summary", "")
        # strictly keep only SAFLII URLs
        cleaned = []
        for c in cases_in:
            if not isinstance(c, dict):
                continue
            url = c.get("url") or ""
            if "saflii.org" not in url:
                continue
            name = c.get("case_name") or c.get("title") or c.get("name")
            if not name:
                continue
            description = (
                c.get("legal_principle")
                or c.get("summary")
                or c.get("quote")
                or ""
            )
            cleaned.append(
                {
                    "name": name,
                    "url": url,
                    "description": description,
                    "relevance": c.get("relevance", ""),
                    # keep citation if you want to show it later
                    "citation": c.get("citation", ""),
                }
            )

        result = {
            "cases": cleaned,
            "total": len(cleaned),
            "search_summary": summary,
        }
        return func.HttpResponse(
            json.dumps(result), mimetype="application/json", status_code=200
        )

    except Exception as e:
        logging.exception("❌ Error occurred in Find Case Law")
        return func.HttpResponse("Server error", status_code=500)
