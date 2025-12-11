# AlchemioChat/__init__.py - FIXED VERSION
import logging
import azure.functions as func
import json
import os
import re
from datetime import datetime, timezone
from shared.utils import auth_get_email
from shared.rag import call_llm_with
from shared.table_storage import get_user_info

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("✅ Enhanced AlchemioChat function triggered for legal opinion assistance.")
    
    if req.headers.get('function-key') != os.environ["FUNCTION_KEY"]:
        logging.info("❌ No matching function key in header")
        return func.HttpResponse("", status_code=401)
    
    try:
        email, err = auth_get_email(req)
        if err:
            logging.exception("❌ auth_get_email failed")
            return err
        
        data = req.get_json()
        
        # Validate required fields
        required_fields = ['opinion_id', 'message', 'opinion_text']
        for field in required_fields:
            if field not in data:
                return func.HttpResponse(f"Missing required field: {field}", status_code=400)
        
        opinion_id = data["opinion_id"]
        user_message = data["message"]
        opinion_text = data["opinion_text"]
        chat_history = data.get("chat_history", [])
        # Note: request_changes is always True from frontend, but we'll intelligently decide
        
        logging.info(f"AlchemioChat request for opinion {opinion_id}: {user_message[:100]}...")
        
        # Get user and opinion data for context
        entity = get_user_info(email)
        entity_data = json.loads(entity.get("payload", "{}"))
        opinions = entity_data.get("opinions", [])
        matched_opinion = next((item for item in opinions if item.get("id") == opinion_id), None)
        
        if not matched_opinion:
            return func.HttpResponse("Opinion not found", status_code=404)
        
        # INTELLIGENT CHANGE DETECTION: Let LLM decide if changes are needed
        logging.info("Analyzing message intent with AI...")
        change_intent = analyze_change_intent(
            user_message=user_message,
            opinion_context=matched_opinion,
            chat_history=chat_history
        )
        
        logging.info(f"Change intent analysis: needs_changes={change_intent['needs_changes']}, confidence={change_intent['confidence']}")
        
        # Generate response based on intent
        if change_intent["needs_changes"] and change_intent["confidence"] > 0.3:
            logging.info("Generating Alchemio response with change suggestions...")
            response_data = generate_enhanced_alchemio_response(
                user_message=user_message,
                opinion_text=opinion_text,
                opinion_context=matched_opinion,
                chat_history=chat_history,
                change_intent=change_intent
            )
        else:
            logging.info("Generating conversational response without changes...")
            # Generate conversational response only
            chat_response = generate_alchemio_response(
                user_message=user_message,
                opinion_text=opinion_text,
                opinion_context=matched_opinion,
                chat_history=chat_history
            )
            response_data = {
                "response": chat_response,
                "changes": None
            }
        
        logging.info("Enhanced Alchemio response generated successfully")
        
        return func.HttpResponse(json.dumps({
            "response": response_data["response"],
            "changes": response_data.get("changes"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "success"
        }), mimetype="application/json", status_code=200)
        
    except Exception as e:
        logging.error(f"❌ Enhanced AlchemioChat error: {str(e)}")
        logging.exception("Full exception details")
        return func.HttpResponse("Server error", status_code=500)

def analyze_change_intent(user_message: str, opinion_context: dict, chat_history: list) -> dict:
    """
    Use AI to intelligently determine if the user is requesting changes to their opinion
    """
    
    # Format recent chat history for context
    formatted_history = ""
    if chat_history:
        history_messages = []
        for msg in chat_history[-3:]:  # Last 3 messages for context
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            history_messages.append(f"{role.title()}: {content}")
        formatted_history = "\n".join(history_messages)
    
    # FIXED: Escaped curly braces in the JSON example
    system_prompt = f"""You are an expert at analyzing user intent for legal opinion editing requests.

CONTEXT:
- Opinion Title: {opinion_context.get('title', 'Unknown')}
- Client: {opinion_context.get('client_name', 'Unknown')}

RECENT CHAT HISTORY:
{formatted_history if formatted_history else "No previous conversation"}

USER MESSAGE: "{user_message}"

Your task is to determine if the user is requesting modifications, changes, or updates to their legal opinion.

EXAMPLES OF CHANGE REQUESTS:
- "So there has been some changes in the situation an MOI was signed that prevents the director from voting, please rewrite the opinion" → YES (new facts require rewrite)
- "The client wants us to add a risk assessment section" → YES (explicit addition request)
- "Make this more concise" → YES (explicit editing request)  
- "Can we update this based on the new case law?" → YES (update request)
- "There's been a development in the matter, we need to revise our advice" → YES (revision needed)
- "Please incorporate these new facts into the opinion" → YES (incorporation request)

EXAMPLES OF NON-CHANGE REQUESTS:
- "What do you think of this opinion?" → NO (seeking feedback)
- "Can you explain section 3 to me?" → NO (seeking clarification)
- "Is this legally sound?" → NO (seeking validation)
- "What are the risks here?" → NO (seeking analysis)
- "How strong is our position?" → NO (seeking assessment)

ANALYSIS FACTORS:
1. New information provided (facts, law changes, client instructions)
2. Explicit requests for modifications (rewrite, add, remove, change)
3. Implied need for updates (new developments, changed circumstances)
4. Context suggesting content modifications vs. just discussion

Return ONLY a JSON object:
{{
    "needs_changes": true/false,
    "confidence": 0.0-1.0,
    "reasoning": "brief explanation of your decision",
    "change_type": "rewrite|addition|modification|clarification|none"
}}"""

    try:
        response = call_llm_with(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Analyze this message for change intent: {user_message}"}
            ],
            temperature=0.1,  # Low temperature for consistent analysis
            max_tokens=300,
            model_deployment_env_var='OPINION_MODEL_DEPLOYMENT',
            model_version_env_var='OPINION_MODEL_VERSION'
        )
        
        # Clean and parse JSON response
        response_clean = response.strip()
        if response_clean.startswith("```json"):
            response_clean = response_clean[7:]
        if response_clean.endswith("```"):
            response_clean = response_clean[:-3]
        response_clean = response_clean.strip()
        
        try:
            intent_data = json.loads(response_clean)
            
            # Validate response structure
            if "needs_changes" not in intent_data:
                intent_data["needs_changes"] = False
            if "confidence" not in intent_data:
                intent_data["confidence"] = 0.0
            if "reasoning" not in intent_data:
                intent_data["reasoning"] = "Failed to analyze intent"
            if "change_type" not in intent_data:
                intent_data["change_type"] = "none"
                
            logging.info(f"Intent analysis result: {intent_data}")
            return intent_data
            
        except json.JSONDecodeError:
            logging.error(f"Failed to parse intent JSON: {response_clean[:200]}")
            return {
                "needs_changes": False,
                "confidence": 0.0,
                "reasoning": "Failed to parse intent analysis",
                "change_type": "none"
            }
            
    except Exception as e:
        logging.error(f"❌ Error analyzing change intent: {str(e)}")
        return {
            "needs_changes": False,
            "confidence": 0.0,
            "reasoning": f"Error in intent analysis: {str(e)}",
            "change_type": "none"
        }

def generate_enhanced_alchemio_response(user_message: str, opinion_text: str, opinion_context: dict, chat_history: list, change_intent: dict) -> dict:
    """
    Generate an enhanced AI response with both chat content and structured change suggestions
    """
    
    # First, generate the conversational response
    chat_response = generate_alchemio_response(
        user_message, opinion_text, opinion_context, chat_history
    )
    
    # Then, generate specific changes based on the intent analysis
    change_suggestions = analyze_and_generate_changes(
        user_message=user_message,
        opinion_text=opinion_text,
        opinion_context=opinion_context,
        chat_response=chat_response,
        change_intent=change_intent
    )
    
    return {
        "response": chat_response,
        "changes": change_suggestions if change_suggestions["changes"] else None
    }

def analyze_and_generate_changes(user_message: str, opinion_text: str, opinion_context: dict, chat_response: str, change_intent: dict) -> dict:
    """
    Generate specific, actionable changes based on the user request and intent analysis
    """
    
    # FIXED: Escaped curly braces in the JSON example
    system_prompt = f"""You are a legal text analysis system that generates specific changes to legal opinions.

CHANGE INTENT ANALYSIS:
- Change Type: {change_intent.get('change_type', 'modification')}
- Confidence: {change_intent.get('confidence', 0.5)}
- Reasoning: {change_intent.get('reasoning', 'General modification')}

CURRENT LEGAL OPINION:
{opinion_text}

USER REQUEST: "{user_message}"

Based on the change intent analysis, generate specific changes to address the user's request.

For REWRITE requests: Focus on substantial text replacements
For ADDITION requests: Focus on inserting new sections/content  
For MODIFICATION requests: Focus on improving existing text
For CLARIFICATION requests: Focus on making text clearer

Return a JSON object in this exact format:
{{
    "changes": [
        {{
            "id": "unique_identifier",
            "type": "replace|insert|delete|restructure",
            "originalText": "exact text to be replaced/deleted",
            "newText": "new text to insert/replace with",
            "startIndex": number,
            "endIndex": number,
            "reasoning": "brief explanation of why this change addresses the user's request",
            "section": "section name if applicable",
            "priority": "high|medium|low"
        }}
    ],
    "summary": "brief summary of all changes",
    "confidence": 0.85
}}

ENHANCED RULES:
1. Consider the change intent type when generating modifications
2. For new factual information (like MOI signing), focus on substantial rewrites
3. For structural requests, focus on reorganization
4. For content additions, find appropriate insertion points
5. Maximum 5 changes per request to avoid overwhelming the user
6. If the request is too vague, return fewer but higher-confidence changes
7. Maintain South African legal opinion structure and terminology

IMPORTANT: Return ONLY the JSON object, no other text."""

    try:
        # Generate the structured changes using the enhanced prompt
        response = call_llm_with(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Generate specific changes for this {change_intent.get('change_type', 'modification')} request: {user_message}"}
            ],
            temperature=0.2,  # Low temperature for consistent output
            max_tokens=1500,
            model_deployment_env_var='OPINION_MODEL_DEPLOYMENT',
            model_version_env_var='OPINION_MODEL_VERSION'
        )
        
        # Clean the response to extract JSON
        response_clean = response.strip()
        if response_clean.startswith("```json"):
            response_clean = response_clean[7:]
        if response_clean.endswith("```"):
            response_clean = response_clean[:-3]
        response_clean = response_clean.strip()
        
        # Parse the JSON response
        try:
            changes_data = json.loads(response_clean)
        except json.JSONDecodeError:
            logging.error(f"Failed to parse changes JSON: {response_clean[:500]}")
            return {"changes": [], "summary": "Failed to parse changes", "confidence": 0.0}
        
        # Validate and process the changes
        if "changes" in changes_data and isinstance(changes_data["changes"], list):
            # Process each change to ensure accuracy
            processed_changes = []
            for change in changes_data["changes"]:
                if validate_and_process_change(change, opinion_text):
                    processed_changes.append(change)
            
            changes_data["changes"] = processed_changes
            
            # If we have valid changes, ensure they have proper indices
            if processed_changes:
                changes_data = refine_change_indices(changes_data, opinion_text)
            
            # Add metadata about the intent analysis
            changes_data["intent_type"] = change_intent.get("change_type", "modification")
            changes_data["intent_confidence"] = change_intent.get("confidence", 0.5)
        
        return changes_data
        
    except Exception as e:
        logging.error(f"❌ Error generating change analysis: {str(e)}")
        return {
            "changes": [],
            "summary": "Error analyzing changes",
            "confidence": 0.0,
            "intent_type": change_intent.get("change_type", "none"),
            "intent_confidence": change_intent.get("confidence", 0.0)
        }

def validate_and_process_change(change: dict, opinion_text: str) -> bool:
    """
    Validate and process a single change suggestion
    """
    required_fields = ["id", "type", "reasoning", "priority"]
    
    # Check required fields
    for field in required_fields:
        if field not in change:
            logging.warning(f"Change missing required field: {field}")
            return False
    
    # Validate change type
    valid_types = ["replace", "insert", "delete", "restructure"]
    if change["type"] not in valid_types:
        logging.warning(f"Invalid change type: {change['type']}")
        return False
    
    # For replace and delete operations, we need originalText
    if change["type"] in ["replace", "delete"]:
        if "originalText" not in change or not change["originalText"]:
            logging.warning("Replace/delete change missing originalText")
            return False
    
    # For replace and insert operations, we need newText
    if change["type"] in ["replace", "insert"]:
        if "newText" not in change or not change["newText"]:
            logging.warning("Replace/insert change missing newText")
            return False
    
    # Generate a unique ID if not provided
    if not change.get("id"):
        change["id"] = f"change_{hash(str(change))}"
    
    return True

def refine_change_indices(changes_data: dict, opinion_text: str) -> dict:
    """
    Refine and calculate accurate indices for text changes
    """
    for change in changes_data["changes"]:
        if "originalText" in change and change["originalText"]:
            # Find the text in the opinion
            original_text = change["originalText"]
            
            # Try exact match first
            start_index = opinion_text.find(original_text)
            
            if start_index != -1:
                change["startIndex"] = start_index
                change["endIndex"] = start_index + len(original_text)
            else:
                # Try fuzzy matching for partial text
                words = original_text.split()[:10]  # First 10 words
                if words:
                    search_text = " ".join(words)
                    start_index = opinion_text.find(search_text)
                    
                    if start_index != -1:
                        change["startIndex"] = start_index
                        change["endIndex"] = start_index + len(search_text)
                        change["originalText"] = search_text  # Update to match what we found
                    else:
                        # Use intelligent section matching
                        section_start = find_section_start(opinion_text, change.get("section", ""))
                        change["startIndex"] = section_start
                        change["endIndex"] = section_start
                        change["type"] = "insert"  # Change to insert if we can't find the text
        
        elif change["type"] == "insert":
            # For insertions, try to find a good insertion point
            section_start = find_section_start(opinion_text, change.get("section", ""))
            change["startIndex"] = section_start
            change["endIndex"] = section_start
    
    return changes_data

def find_section_start(opinion_text: str, section_name: str) -> int:
    """
    Find the start index of a section in the opinion text
    """
    if not section_name:
        return 0
    
    # Common legal opinion section patterns
    section_patterns = [
        rf"#{1,4}\s*{re.escape(section_name)}",  # Markdown headers
        rf"^{re.escape(section_name)}:?\s*$",    # Section headers
        rf"\b{re.escape(section_name)}\b",       # Section name mention
    ]
    
    for pattern in section_patterns:
        match = re.search(pattern, opinion_text, re.MULTILINE | re.IGNORECASE)
        if match:
            return match.start()
    
    # If no section found, return position based on section type
    section_positions = {
        "executive summary": 0,
        "background": int(len(opinion_text) * 0.1),
        "issues": int(len(opinion_text) * 0.3),
        "analysis": int(len(opinion_text) * 0.4),
        "opinion": int(len(opinion_text) * 0.5),
        "conclusion": int(len(opinion_text) * 0.8),
        "recommendations": int(len(opinion_text) * 0.9),
    }
    
    for section_key, position in section_positions.items():
        if section_key in section_name.lower():
            return position
    
    return 0

def generate_alchemio_response(user_message: str, opinion_text: str, opinion_context: dict, chat_history: list) -> str:
    """
    Generate the conversational AI response
    """
    
    # Format chat history for context
    formatted_history = ""
    if chat_history:
        history_messages = []
        for msg in chat_history[-6:]:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            history_messages.append(f"{role.title()}: {content}")
        formatted_history = "\n".join(history_messages)
    
    # Create system prompt for Alchemio
    system_prompt = f"""You are Alchemio, an expert South African legal opinion improvement assistant. You help lawyers refine and enhance their legal opinions with specific, actionable suggestions.

CURRENT LEGAL OPINION CONTEXT:
- Title: {opinion_context.get('title', 'Unknown')}
- Client: {opinion_context.get('client_name', 'Unknown')}
- Facts: {opinion_context.get('facts', 'Not provided')[:500]}...
- Questions: {opinion_context.get('questions', 'Not provided')[:500]}...
- Assumptions: {opinion_context.get('assumptions', 'Not provided')[:300]}...

RECENT CHAT HISTORY:
{formatted_history if formatted_history else "No previous conversation"}

CURRENT OPINION TEXT (First 2000 characters):
{opinion_text[:2000]}...

YOUR ROLE:
- Provide specific, actionable suggestions for improving the legal opinion
- Focus on legal accuracy, clarity, structure, and professional presentation
- Suggest specific text changes, additions, or reorganizations when requested
- Explain the reasoning behind your suggestions
- Be concise but comprehensive in your advice
- Always maintain a professional, helpful tone

RESPONSE GUIDELINES:
- Give practical, implementable advice
- Reference specific sections of the opinion when making suggestions
- Explain why each suggestion would improve the opinion
- If asked about legal precedents, suggest specific South African cases when relevant
- Keep responses focused and not overly lengthy (aim for 200-400 words)
- Always be constructive and supportive
- When users ask for specific changes, let them know you're analyzing their opinion and will provide detailed suggestions they can review

Remember: You are an AI assistant helping to improve legal opinions. Always encourage the lawyer to verify any legal references and use their professional judgment."""

    user_prompt = f"""The user is asking: "{user_message}"

Please provide specific, helpful suggestions to improve their legal opinion based on this request. Focus on actionable recommendations they can implement. If they're asking for specific changes to be made, let them know you're analyzing their opinion and will provide detailed suggestions they can review."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    try:
        response = call_llm_with(
            messages=messages,
            temperature=0.3,
            max_tokens=800,
            model_deployment_env_var='OPINION_MODEL_DEPLOYMENT',
            model_version_env_var='OPINION_MODEL_VERSION'
        )
        
        return response.strip()
        
    except Exception as e:
        logging.error(f"❌ Error generating Alchemio response: {str(e)}")
        return "I apologize, but I'm having trouble processing your request right now. Please try again, or feel free to ask a different question about improving your legal opinion."