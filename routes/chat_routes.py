from flask import Blueprint, request, jsonify, Response
from datetime import datetime, timezone
import re
from whatsapp_gateway import WhatsAppGateway
import database as db_module

chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/api/messages', methods=['POST'])
@chat_bp.route('/api/send-message', methods=['POST'])
@chat_bp.route('/api/chat/send', methods=['POST'])
def send_message():
    try:
        data = request.json or {}
        text = data.get('message') or data.get('text') or data.get('content') or ''
        sender = data.get('sender_email') or data.get('sender') or data.get('sender_id') or ''
        receiver = data.get('receiver_email') or data.get('receiver') or data.get('receiver_id') or ''
        task_id = data.get('task_id') or data.get('booking_id') or data.get('job_id') or 'general'
        msg_type = data.get('type', 'text')
        voice_url = data.get('voice_url', '')
        attachment = data.get('attachment', None)

        if not text and msg_type == 'text':
            return jsonify({"error": "Missing required message content or sender"}), 400
        if not sender:
            return jsonify({"error": "Missing sender identification"}), 400

        # Anti-fraud check: Strictly block actual phone numbers
        phone_match = re.search(r'(\+?94|0)[\s\-\.]?7[0-9][\s\-\.]?[0-9]{3}[\s\-\.]?[0-9]{4}', text)
        if phone_match and msg_type != 'voice':
            return jsonify({
                "error": "PHONE_SHARING_BLOCKED",
                "message": "Sharing phone numbers or contacting outside WorkPub is strictly prohibited to protect payments and platform terms."
            }), 400

        new_msg = {
            "task_id": str(task_id),
            "sender": sender,
            "sender_email": sender,
            "receiver": receiver,
            "receiver_email": receiver,
            "sender_id": sender,
            "receiver_id": receiver,
            "message": text,
            "text": text,
            "content": text,
            "type": msg_type,
            "voice_url": voice_url,
            "attachment": attachment,
            "status": "sent",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        res = db_module.messages_collection.insert_one(new_msg)
        new_msg['_id'] = str(res.inserted_id)

        try:
            receiver_user = db_module.users_collection.find_one({"email": receiver})
            if receiver_user and receiver_user.get('phone'):
                WhatsAppGateway.send_task_alert_via_whatsapp(
                    recipient_phone=receiver_user.get('phone'),
                    task_id=task_id,
                    task_title=f"Task #{task_id}",
                    alert_type="New Message",
                    message_text=text[:60] if text else "Sent an attachment"
                )
        except Exception as wa_err:
            print(f"WhatsApp Alert Dispatch Warning: {wa_err}")

        return jsonify({"status": "sent", "message": "Sent successfully", "data": new_msg}), 201
    except Exception as e:
        print(f"Send Message Error: {e}")
        return jsonify({"error": str(e)}), 500

@chat_bp.route('/api/messages', methods=['GET'])
@chat_bp.route('/api/get-messages', methods=['GET'])
@chat_bp.route('/api/chat/messages/<task_id>', methods=['GET'])
def get_messages(task_id=None):
    try:
        req_task_id = task_id or request.args.get('task_id') or request.args.get('booking_id')
        u1 = request.args.get('user1') or request.args.get('sender') or request.args.get('user_id') or request.args.get('sender_email')
        u2 = request.args.get('user2') or request.args.get('receiver') or request.args.get('contact') or request.args.get('receiver_email')

        query_conditions = []
        if req_task_id and str(req_task_id) not in ['general', 'undefined', 'null', '']:
            query_conditions.append({"task_id": str(req_task_id)})

        if u1 and u2:
            query_conditions.append({
                "$or": [
                    {"sender": u1, "receiver": u2},
                    {"sender": u2, "receiver": u1},
                    {"sender_id": u1, "receiver_id": u2},
                    {"sender_id": u2, "receiver_id": u1},
                    {"sender_email": u1, "receiver_email": u2},
                    {"sender_email": u2, "receiver_email": u1}
                ]
            })

        if query_conditions:
            if len(query_conditions) > 1:
                query = {"$or": query_conditions}
            else:
                query = query_conditions[0]
        else:
            query = {}

        msgs = list(db_module.messages_collection.find(query).sort("timestamp", 1))

        for m in msgs:
            m['_id'] = str(m['_id'])
            if 'text' not in m and 'content' in m:
                m['text'] = m['content']
            if 'message' not in m:
                m['message'] = m.get('text') or m.get('content') or ''
            if 'sender' not in m and 'sender_id' in m:
                m['sender'] = m['sender_id']
            if 'sender_email' not in m:
                m['sender_email'] = m.get('sender') or m.get('sender_id') or ''
            if 'receiver' not in m and 'receiver_id' in m:
                m['receiver'] = m['receiver_id']
            if 'receiver_email' not in m:
                m['receiver_email'] = m.get('receiver') or m.get('receiver_id') or ''
            if 'status' not in m:
                m['status'] = 'delivered'

        return jsonify(msgs), 200
    except Exception as e:
        print(f"Get Messages Error: {e}")
        return jsonify([]), 500

@chat_bp.route('/api/mark-chats-read', methods=['POST'])
def mark_chats_read():
    try:
        data = request.json or {}
        receiver_email = data.get('receiver_email') or data.get('user_email')
        sender_email = data.get('sender_email')
        task_id = data.get('task_id')

        query = {}
        if task_id:
            query["task_id"] = str(task_id)
        if receiver_email and sender_email:
            query["receiver"] = receiver_email
            query["sender"] = sender_email

        if query:
            db_module.messages_collection.update_many(
                query,
                {"$set": {"status": "read"}}
            )
        return jsonify({"status": "success", "message": "Chats marked as read"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@chat_bp.route('/api/book', methods=['POST'])
def handle_booking():
    data = request.json or {}
    seeker_id = data.get('seeker_id')
    worker_id = data.get('worker_id')
    booking_date = data.get('date')

    new_booking = {
        "seeker_id": seeker_id,
        "worker_id": worker_id,
        "date": booking_date,
        "status": "pending"
    }
    b_res = db_module.bookings_collection.insert_one(new_booking)
    booking_id = str(b_res.inserted_id)

    ack_message = {
        "task_id": booking_id,
        "sender_id": seeker_id,
        "receiver_id": worker_id,
        "sender": seeker_id,
        "receiver": worker_id,
        "message": f"📅 SYSTEM: New booking request for {booking_date}. Click here to acknowledge.",
        "text": f"📅 SYSTEM: New booking request for {booking_date}. Click here to acknowledge.",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "type": "booking_alert",
        "status": "sent"
    }
    db_module.messages_collection.insert_one(ack_message)

    return jsonify({"message": "Booking successful and worker acknowledged via chat!", "booking_id": booking_id})

@chat_bp.route('/api/chat/inbox/<worker_id>', methods=['GET'])
def get_worker_inbox(worker_id):
    messages = list(db_module.messages_collection.find({"receiver_id": worker_id}).sort("timestamp", -1))
    for m in messages:
        m['_id'] = str(m['_id'])
    return jsonify(messages)

@chat_bp.route('/api/user-conversations', methods=['GET'])
def get_user_conversations():
    try:
        user_email = request.args.get('email')
        if not user_email:
            return jsonify([])

        msgs = list(db_module.messages_collection.find({
            "$or": [{"sender": user_email}, {"receiver": user_email}, {"sender_id": user_email}, {"receiver_id": user_email}]
        }).sort("timestamp", -1))

        conversations = {}
        for m in msgs:
            sender = m.get('sender') or m.get('sender_id') or ''
            receiver = m.get('receiver') or m.get('receiver_id') or ''
            other = receiver if sender == user_email else sender
            task_id = m.get('task_id', 'general')

            if not other or other == user_email:
                continue

            conv_key = f"{other}_{task_id}" if task_id != 'general' else other

            if conv_key not in conversations:
                other_user = db_module.users_collection.find_one({"email": other})
                raw_name = other_user.get('name') if (other_user and other_user.get('name')) else other.split('@')[0].capitalize()
                other_role = other_user.get('role', 'worker') if other_user else 'worker'
                other_cat = other_user.get('category', 'General Specialist') if other_user else 'General Specialist'
                other_location = other_user.get('location', 'Gampaha') if other_user else 'Gampaha'

                masked_email = WhatsAppGateway.mask_email(other)
                masked_phone = WhatsAppGateway.mask_phone_number(other_user.get('phone') if other_user else None)

                unread_cnt = db_module.messages_collection.count_documents({
                    "sender": other,
                    "receiver": user_email,
                    "status": {"$ne": "read"}
                })

                conversations[conv_key] = {
                    "key": conv_key,
                    "email": other,
                    "masked_email": masked_email,
                    "masked_phone": masked_phone,
                    "task_id": task_id,
                    "name": raw_name,
                    "role": other_role,
                    "category": other_cat,
                    "location": other_location,
                    "last_message": m.get('text') or m.get('content') or 'Message',
                    "msg_type": m.get('type', 'text'),
                    "timestamp": m.get('timestamp', ''),
                    "status": m.get('status', 'sent'),
                    "unread": unread_cnt
                }

        return jsonify(list(conversations.values()))
    except Exception as e:
        print(f"User Conversations Fetch Error: {e}")
        return jsonify([])

@chat_bp.route('/api/whatsapp/webhook', methods=['GET'])
def verify_whatsapp_webhook():
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')

    VERIFY_TOKEN = 'workpub_whatsapp_secret_token'

    if mode and token:
        if mode == 'subscribe' and token == VERIFY_TOKEN:
            return Response(challenge, status=200, mimetype='text/plain')
        return jsonify({"error": "Forbidden - Invalid Verify Token"}), 403
    return jsonify({"status": "WorkPub WhatsApp Gateway Active"}), 200

@chat_bp.route('/api/whatsapp/webhook', methods=['POST'])
def handle_whatsapp_webhook():
    payload = request.json or {}
    res = WhatsAppGateway.handle_incoming_webhook(payload)
    return jsonify(res), 200

@chat_bp.route('/api/whatsapp/send-alert', methods=['POST'])
def send_whatsapp_alert():
    data = request.json or {}
    phone = data.get('phone')
    task_id = data.get('task_id', 'general')
    title = data.get('title', 'WorkPub Notification')
    alert_type = data.get('alert_type', 'Status Update')
    msg = data.get('message', '')

    res = WhatsAppGateway.send_task_alert_via_whatsapp(
        recipient_phone=phone,
        task_id=task_id,
        task_title=title,
        alert_type=alert_type,
        message_text=msg
    )
    return jsonify(res), 200
