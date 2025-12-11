import logging
import azure.functions as func
import os
from shared.utils import auth_get_email, save, get

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("✅ SaveOpinion function triggered.")
    
    if req.headers.get('function-key') != os.environ["FUNCTION_KEY"]:
        logging.info("no matching value in header")
        return func.HttpResponse("", status_code=401)
    
    try:
        email, err = auth_get_email(req)
        if err:
            logging.exception("❌ auth_get_email", err)
            return err
        logging.info(f"email {email}")

        data = req.get_json()
        id = data["id"]
        
        # Get existing user data
        existing = get(email)
        if not existing:
            return func.HttpResponse(f"No existing data for user", status_code=404)
        
        logging.info(f"existing = {existing}")
        
        # Find the specific opinion to update
        existing_opinion = next((doc for doc in existing["clean_payload"]["opinions"] if doc["id"] == id), None)
        if not existing_opinion:
            return func.HttpResponse(f"No existing opinion for id {id}", status_code=404)
        
        logging.info(f"existing_opinion = {existing_opinion}")
        
        # Update the specific opinion
        updated = False
        for i, opinion in enumerate(existing["clean_payload"]["opinions"]):
            if opinion["id"] == id:
                # Update only the fields that are provided
                opinion["title"] = data.get("title", opinion.get("title", ""))
                opinion["facts"] = data.get("facts", opinion.get("facts", ""))
                opinion["questions"] = data.get("questions", opinion.get("questions", ""))
                opinion["assumptions"] = data.get("assumptions", opinion.get("assumptions", ""))
                opinion["client_name"] = data.get("client_name", opinion.get("client_name", ""))
                opinion["client_address"] = data.get("client_address", opinion.get("client_address", ""))
                
                # Keep existing data like documents, drafts, etc.
                # Don't overwrite the entire opinion object
                
                updated = True
                logging.info(f"Updated opinion: {opinion}")
                break
        
        if not updated:
            return func.HttpResponse(f"Failed to update opinion for id {id}", status_code=404)
        
        # Save the complete payload back (this will use the fixed save function without add_to_item)
        logging.info(f"Saving updated payload with {len(existing['clean_payload']['opinions'])} opinions")
        save(email, existing["clean_payload"], ["id", "title", "facts", "questions", "assumptions", "client_name", "client_address"])
        
        return func.HttpResponse(f"Opinion saved successfully", status_code=200)
        
    except Exception as e:
        logging.error(f"SaveOpinion failed: {str(e)}")
        logging.exception("❌ Error occurred")
        return func.HttpResponse("Server error", status_code=500)