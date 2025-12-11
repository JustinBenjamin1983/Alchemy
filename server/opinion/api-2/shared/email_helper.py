import os
import logging
from azure.communication.email import EmailClient

def send_processing_complete_email(recipient_email: str, dd_name: str, dd_id: str, total_documents: int = None, processing_type: str = "document"):
    try:
        # Get connection string from environment variable
        connection_string = os.environ.get("AZURE_COMMUNICATION_SERVICES_CONNECTION_STRING")
        
        if not connection_string:
            logging.error("AZURE_COMMUNICATION_SERVICES_CONNECTION_STRING not found in environment variables")
            return False
            
        client = EmailClient.from_connection_string(connection_string)
        
        # Customize subject and content based on processing type
        if processing_type == "document":
            subject = f"Document Processing Complete - {dd_name}"
            plain_text = f"""
Hi,

Your document processing has been completed successfully.

Project Name: {dd_name}
{f"Documents Processed: {total_documents}" if total_documents else ""}

You can now access your processed documents in the application.

Best regards,
AI Legal Assistant Team
            """.strip()
            
            html_content = f"""
<html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #2c5aa0;">Document Processing Complete</h2>
            
            <p>Hello,</p>
            
            <p>Your document processing for <strong>"{dd_name}"</strong> has been completed successfully.</p>
            
            <div style="background-color: #f8f9fa; padding: 15px; border-left: 4px solid #2c5aa0; margin: 20px 0;">
                <p><strong>Project ID:</strong> {dd_id}</p>
                {f"<p><strong>Documents Processed:</strong> {total_documents}</p>" if total_documents else ""}
            </div>
            
            <p>You can now access your processed documents in the application.</p>
            
            <p style="margin-top: 30px;">
                Best regards,<br>
                <strong>AI Legal Assistant Team</strong>
            </p>
        </div>
    </body>
</html>
            """
        
        elif processing_type == "risk":
            subject = f"Risk Analysis Complete - {dd_name}"
            
            stats_text = f"\nRisks Analyzed: {total_documents}" if total_documents else ""
            
            plain_text = f"""
        Hello,
        Your risk analysis for "{dd_name}" has been completed successfully.
        Project ID: {dd_id}{stats_text}
        You can now review the risk findings and analysis results in the application.
        Best regards,
        AI Legal Assistant Team
            """.strip()
            
            stats_html = f"<p><strong>Risks Analyzed:</strong> {total_documents}</p>" if total_documents else ""
            
            html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #2c5aa0;">🔍 Risk Analysis Complete</h2>
                    
                    <p>Hello,</p>
                    
                    <p>Your risk analysis for <strong>"{dd_name}"</strong> has been completed successfully.</p>
                    
                    <div style="background-color: #f8f9fa; padding: 15px; border-left: 4px solid #2c5aa0; margin: 20px 0;">
                        <p><strong>Project ID:</strong> {dd_id}</p>
                        {stats_html}
                    </div>
                    
                    <p>You can now review the risk findings and analysis results in the application.</p>
                    
                    <p style="margin-top: 30px;">
                        Best regards,<br>
                        <strong>AI Legal Assistant Team</strong>
                    </p>
                </div>
            </body>
        </html>
            """
    
        # Get sender address from environment variable
        sender_address = os.environ.get("AZURE_COMMUNICATION_SERVICES_SENDER_ADDRESS", "DoNotReply@yourdomain.com")
        
        message = {
            "senderAddress": sender_address,
            "recipients": {
                "to": [{"address": recipient_email}]
            },
            "content": {
                "subject": subject,
                "plainText": plain_text,
                "html": html_content
            }
        }
        
        # Send the email
        poller = client.begin_send(message)
        result = poller.result()
        
        logging.info(f"Email sent successfully to {recipient_email}")
        return True
        
    except Exception as ex:
        logging.error(f"Failed to send email to {recipient_email}: {str(ex)}")
        return False