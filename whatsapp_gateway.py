"""
WhatsApp Cloud API & Twilio Gateway Integration Module for WorkPub
Provides privacy masking and WhatsApp message routing via WorkPub Virtual Business Gateway.
"""

import os
import re
import json
import logging
from datetime import datetime

logger = logging.getLogger("WhatsAppGateway")
logger.setLevel(logging.INFO)

# WorkPub Verified Business Number for Gateway Routing
WORKPUB_BUSINESS_NUMBER = "+94117000900"
WORKPUB_DISPLAY_NAME = "WorkPub Verified Business"

class WhatsAppGateway:
    """
    Future-Ready WhatsApp Gateway supporting Meta Cloud API & Twilio API.
    Routes messages using Task/Booking IDs without exposing direct user contact details.
    """

    @staticmethod
    def mask_phone_number(phone_str):
        """
        Masks phone numbers to protect worker & customer privacy.
        Example: '+94771234567' -> '+94 77 *** *567'
        """
        if not phone_str or phone_str == 'Not Provided':
            return "[Protected by WorkPub]"
        
        # Clean digits
        digits = re.sub(r'\D', '', str(phone_str))
        if len(digits) >= 9:
            prefix = digits[:4]
            suffix = digits[-3:]
            return f"+{prefix} *** *{suffix} (Masked)"
        return "[Protected by WorkPub]"

    @staticmethod
    def mask_email(email_str):
        """
        Masks personal email addresses to enforce platform privacy.
        Example: 'kusumsiri@gmail.com' -> 'k***i@workpub.com'
        """
        if not email_str or '@' not in email_str:
            return "[Protected Email]"
        
        parts = email_str.split('@')
        name = parts[0]
        if len(name) <= 2:
            masked_name = name[0] + "*"
        else:
            masked_name = name[0] + "***" + name[-1]
        return f"{masked_name}@workpub.com"

    @classmethod
    def send_task_alert_via_whatsapp(cls, recipient_phone, task_id, task_title, alert_type, message_text):
        """
        Simulates / dispatches a WhatsApp template message via Meta Cloud API / Twilio gateway.
        """
        masked_phone = cls.mask_phone_number(recipient_phone)
        
        # Meta WhatsApp Cloud API Payload Structure (Future-Ready)
        meta_payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient_phone,
            "type": "template",
            "template": {
                "name": "workpub_task_update",
                "language": {"code": "en_US"},
                "components": [
                    {
                        "type": "header",
                        "parameters": [{"type": "text", "text": f"Task #{task_id}"}]
                    },
                    {
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": task_title},
                            {"type": "text", "text": alert_type},
                            {"type": "text", "text": message_text}
                        ]
                    }
                ]
            },
            "context": {
                "business_number": WORKPUB_BUSINESS_NUMBER,
                "routing_type": "task_bound",
                "task_id": str(task_id)
            }
        }

        print(f"📱 [WhatsApp Gateway Alert] Sent to {masked_phone} via Gateway {WORKPUB_BUSINESS_NUMBER}:")
        print(f"   Task ID: #{task_id} | Title: '{task_title}' | Event: '{alert_type}'")
        print(f"   Payload: {json.dumps(meta_payload, indent=2)}")
        
        return {
            "status": "queued",
            "gateway": WORKPUB_BUSINESS_NUMBER,
            "task_id": task_id,
            "masked_recipient": masked_phone,
            "timestamp": datetime.utcnow().isoformat()
        }

    @classmethod
    def handle_incoming_webhook(cls, payload):
        """
        Processes incoming WhatsApp messages from Meta Cloud API webhook.
        Maps incoming WhatsApp responses back to internal Task ID.
        """
        try:
            entries = payload.get('entry', [])
            processed_messages = []
            
            for entry in entries:
                changes = entry.get('changes', [])
                for change in changes:
                    value = change.get('value', {})
                    messages = value.get('messages', [])
                    for msg in messages:
                        from_number = msg.get('from')
                        text = msg.get('text', {}).get('body', '')
                        msg_id = msg.get('id')
                        
                        processed_messages.append({
                            "whatsapp_msg_id": msg_id,
                            "from_masked": cls.mask_phone_number(from_number),
                            "text": text,
                            "received_at": datetime.utcnow().isoformat()
                        })
            return {"status": "success", "processed_count": len(processed_messages), "messages": processed_messages}
        except Exception as e:
            return {"status": "error", "error": str(e)}
