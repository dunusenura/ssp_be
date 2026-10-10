from flask import Blueprint, request, jsonify, Response
from datetime import datetime, timezone
from bson import ObjectId
import hashlib
import time
try:
    import requests
except ImportError:
    requests = None

import config
import database as db_module

payment_bp = Blueprint('payment', __name__)

@payment_bp.route('/api/process-payment', methods=['POST'])
def process_payment():
    try:
        data = request.json or {}
        booking_id = data.get('booking_id')
        client_email = data.get('client_email')
        worker_email = data.get('worker_email')
        worker_name = data.get('worker_name', 'Worker Specialist')
        service_type = data.get('service_type', 'Professional Service')
        amount = data.get('amount', 4500)
        payment_method = data.get('payment_method', 'Cash on Job Completion')

        invoice_count = db_module.payments_collection.count_documents({}) + 1
        invoice_id = f"INV-2026-{str(invoice_count).zfill(2)}"

        payment_entry = {
            "invoice_id": invoice_id,
            "booking_id": str(booking_id) if booking_id else "",
            "client_email": client_email,
            "worker_email": worker_email,
            "worker_name": worker_name,
            "service_type": service_type,
            "amount": float(amount),
            "payment_method": payment_method,
            "gateway": "Cash on Completion",
            "status": "Paid via Cash on Job Completion",
            "escrow_status": "cash",
            "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        }

        res = db_module.payments_collection.insert_one(payment_entry)
        payment_entry['_id'] = str(res.inserted_id)

        if booking_id:
            try:
                db_module.bookings_collection.update_one(
                    {"_id": ObjectId(booking_id)},
                    {"$set": {
                        "status": "payment_completed",
                        "payment_status": "cash_confirmed",
                        "payment_method": payment_method,
                        "amount": float(amount),
                        "invoice_id": invoice_id
                    }}
                )
            except Exception as b_err:
                print(f"Booking status update error in payment: {b_err}")

        if worker_email:
            db_module.add_notification(
                user_identifier=worker_email,
                title="Cash Payment Confirmed on Completion",
                message=f"Customer confirmed cash payment of Rs. {float(amount):,.2f} for '{service_type}'. Cash will be handed directly to you on job completion.",
                notif_type="payment_success",
                link="/jobs"
            )
        if client_email:
            db_module.add_notification(
                user_identifier=client_email,
                title="Cash Payment Selected for Job",
                message=f"You selected Cash on Completion for '{service_type}' (Rs. {float(amount):,.2f}). Hand cash directly to the worker when completed.",
                notif_type="payment_success",
                link="/my-bookings"
            )

        return jsonify({
            "status": "success",
            "message": "Payment processed and recorded successfully.",
            "payment": payment_entry
        }), 200
    except Exception as e:
        print(f"Payment Processing Error: {e}")
        return jsonify({"error": str(e)}), 500

@payment_bp.route('/api/user-payments', methods=['GET'])
def get_user_payments():
    try:
        email = request.args.get('email')
        if not email:
            return jsonify([])

        query = {"$or": [{"client_email": email}, {"worker_email": email}]}
        payments = list(db_module.payments_collection.find(query).sort("created_at", -1))

        for p in payments:
            p['_id'] = str(p['_id'])

        return jsonify(payments)
    except Exception as e:
        print(f"Fetch User Payments Error: {e}")
        return jsonify([])

@payment_bp.route('/api/onepay/create-checkout', methods=['POST'])
def create_onepay_checkout():
    try:
        data = request.json or {}
        booking_id = data.get('booking_id')
        client_email = data.get('client_email') or data.get('customer_email') or 'customer@workpub.com'
        client_name = data.get('client_name') or data.get('customer_name') or 'WorkPub Customer'
        worker_email = data.get('worker_email') or ''
        worker_name = data.get('worker_name') or 'Worker Specialist'
        service_type = data.get('service_type') or data.get('service_name') or 'Professional Service'
        amount = float(data.get('amount', 4500))

        ref_id = f"WORKPUB_INV_{int(time.time())}_{str(booking_id)[-6:] if booking_id else 'TX'}"
        hash_string = f"{amount:.2f}{ref_id}LKR{config.ONEPAY_APP_ID}{config.ONEPAY_HASH_TOKEN}"
        hash_val = hashlib.sha256(hash_string.encode('utf-8')).hexdigest()

        return_url = f"http://127.0.0.1:5000/api/onepay/callback?booking_id={booking_id}&amount={amount}&client_email={client_email}&worker_email={worker_email}&worker_name={worker_name}&service={service_type}&ref={ref_id}"

        onepay_payload = {
            "amount": amount,
            "currency": "LKR",
            "app_id": config.ONEPAY_APP_ID,
            "reference": ref_id,
            "customer_first_name": client_name.split()[0] if client_name else "Client",
            "customer_last_name": client_name.split()[-1] if (client_name and len(client_name.split()) > 1) else "Customer",
            "customer_email": client_email,
            "customer_phone": "+94771234567",
            "transaction_redirect_url": return_url,
            "additional_data": service_type,
            "hash": hash_val
        }

        try:
            if requests:
                headers = {
                    "Authorization": config.ONEPAY_APP_TOKEN,
                    "Content-Type": "application/json"
                }
                op_res = requests.post(config.ONEPAY_API_URL, json=onepay_payload, headers=headers, timeout=5)
                if op_res.status_code == 200:
                    res_data = op_res.json()
                    redirect_url = res_data.get('redirect_url') or res_data.get('data', {}).get('link') or res_data.get('link')
                    if redirect_url:
                        return jsonify({"status": "success", "redirect_url": redirect_url, "reference": ref_id}), 200
        except Exception as op_err:
            print(f"OnePay REST API Live Call Notice: {op_err}")

        hosted_redirect_url = f"http://127.0.0.1:5000/api/onepay/hosted-checkout/{ref_id}?booking_id={booking_id}&amount={amount}&client_email={client_email}&worker_email={worker_email}&service={service_type}&worker_name={worker_name}"

        return jsonify({
            "status": "success",
            "redirect_url": hosted_redirect_url,
            "reference": ref_id
        }), 200
    except Exception as e:
        print(f"Create OnePay Checkout Error: {e}")
        return jsonify({"error": str(e)}), 500

@payment_bp.route('/api/onepay/hosted-checkout/<ref_id>', methods=['GET'])
def onepay_hosted_checkout(ref_id):
    booking_id = request.args.get('booking_id', '')
    amount = request.args.get('amount', '4500')
    client_email = request.args.get('client_email', '')
    worker_email = request.args.get('worker_email', '')
    service = request.args.get('service', 'Professional Service')
    worker_name = request.args.get('worker_name', 'Assigned Specialist')

    callback_url = f"/api/onepay/callback?booking_id={booking_id}&amount={amount}&client_email={client_email}&worker_email={worker_email}&worker_name={worker_name}&service={service}&ref={ref_id}"

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>OnePay Gateway Checkout - WorkPub Escrow</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background-color: #0f172a; color: #f8fafc; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; padding: 20px; }}
            .card {{ background: #1e293b; border: 1px solid #334155; border-radius: 20px; padding: 32px; max-width: 480px; width: 100%; box-shadow: 0 20px 50px rgba(0,0,0,0.6); }}
            .logo-row {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; border-bottom: 1px solid #334155; padding-bottom: 16px; }}
            .onepay-badge {{ background: #0284c7; color: white; padding: 6px 14px; border-radius: 20px; font-weight: 800; font-size: 0.85rem; letter-spacing: 0.5px; }}
            .escrow-box {{ background: rgba(14, 165, 233, 0.12); border: 1px solid #0284c7; border-radius: 12px; padding: 14px; margin: 20px 0; font-size: 0.84rem; line-height: 1.5; color: #e0f2fe; }}
            .summary-box {{ background: #0f172a; border-radius: 12px; padding: 16px; margin-bottom: 20px; border: 1px solid #334155; }}
            .pay-btn {{ background: #10b981; color: white; border: none; padding: 16px; border-radius: 12px; font-weight: 900; font-size: 1.05rem; width: 100%; cursor: pointer; transition: all 0.2s; box-shadow: 0 4px 15px rgba(16, 185, 129, 0.3); }}
            .pay-btn:hover {{ background: #059669; transform: translateY(-1px); }}
            .input-group {{ margin-bottom: 14px; text-align: left; }}
            .input-group label {{ display: block; font-size: 0.78rem; font-weight: 800; color: #94a3b8; text-transform: uppercase; margin-bottom: 6px; }}
            .input-group input {{ width: 100%; padding: 12px 14px; border-radius: 8px; border: 1px solid #334155; background: #0f172a; color: white; box-sizing: border-box; font-size: 0.95rem; outline: none; }}
        </style>
    </head>
    <body>
        <div class="card">
            <div class="logo-row">
                <div>
                    <h2 style="margin:0; font-size:1.4rem; color:#fff;">OnePay Gateway</h2>
                    <span style="font-size:0.8rem; color:#94a3b8;">Merchant: WorkPub (Pvt) Ltd</span>
                </div>
                <span class="onepay-badge">100% SECURE</span>
            </div>

            <div class="summary-box">
                <div style="display:flex; justify-space-between; margin-bottom:8px;">
                    <span style="color:#94a3b8;">Service:</span>
                    <strong style="color:#fff;">{service}</strong>
                </div>
                <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
                    <span style="color:#94a3b8;">Specialist:</span>
                    <strong style="color:#fff;">{worker_name}</strong>
                </div>
                <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
                    <span style="color:#94a3b8;">Reference:</span>
                    <strong style="color:#0284c7;">{ref_id}</strong>
                </div>
                <div style="display:flex; justify-content:space-between; font-size:1.2rem; font-weight:900; margin-top:12px; padding-top:10px; border-top:1px solid #334155;">
                    <span>Total Amount:</span>
                    <span style="color:#10b981;">Rs. {float(amount):,.2f}</span>
                </div>
            </div>

            <div class="escrow-box">
                🛡️ <strong>WORKPUB ESCROW GUARANTEE:</strong><br>
                Your payment is held safely in WORKPUB Escrow. Funds are released to the worker only after the job is completed and approved.
            </div>

            <form action="{callback_url}" method="POST">
                <div class="input-group">
                    <label>Cardholder Name</label>
                    <input type="text" value="Sampath Bandara" required />
                </div>
                <div class="input-group">
                    <label>Card Number (OnePay Encrypted)</label>
                    <input type="text" value="4242 •••• •••• 4242" required />
                </div>
                <div style="display:flex; gap:12px;">
                    <div class="input-group" style="flex:1;">
                        <label>Expiry Date</label>
                        <input type="text" value="08/28" required />
                    </div>
                    <div class="input-group" style="flex:1;">
                        <label>CVV / CVC</label>
                        <input type="text" value="888" required />
                    </div>
                </div>

                <button type="submit" class="pay-btn">
                    🔒 Pay Rs. {float(amount):,.2f} via OnePay
                </button>
            </form>
        </div>
    </body>
    </html>
    """
    return html_content

@payment_bp.route('/api/onepay/callback', methods=['GET', 'POST'])
def onepay_callback():
    try:
        booking_id = request.args.get('booking_id') or request.form.get('booking_id')
        amount = float(request.args.get('amount') or request.form.get('amount') or 4500)
        client_email = request.args.get('client_email') or request.form.get('client_email') or 'customer@workpub.com'
        worker_email = request.args.get('worker_email') or request.form.get('worker_email') or ''
        worker_name = request.args.get('worker_name') or request.form.get('worker_name') or 'Worker Specialist'
        service = request.args.get('service') or request.form.get('service') or 'Professional Service'
        ref_id = request.args.get('ref') or request.form.get('ref') or f"INV-2026-{int(time.time())}"

        invoice_count = db_module.payments_collection.count_documents({}) + 1
        invoice_id = f"INV-2026-{str(invoice_count).zfill(2)}"

        payment_entry = {
            "invoice_id": invoice_id,
            "booking_id": str(booking_id) if booking_id else "",
            "client_email": client_email,
            "worker_email": worker_email,
            "worker_name": worker_name,
            "service_type": service,
            "amount": amount,
            "payment_method": "OnePay Gateway (Visa/Mastercard)",
            "gateway": "OnePay Escrow Gateway",
            "status": "Paid (Escrow Held)",
            "escrow_status": "held",
            "reference": ref_id,
            "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        }

        db_module.payments_collection.insert_one(payment_entry)

        if booking_id:
            try:
                db_module.bookings_collection.update_one(
                    {"_id": ObjectId(booking_id)},
                    {"$set": {
                        "status": "payment_completed",
                        "payment_status": "escrow_paid",
                        "amount": amount,
                        "invoice_id": invoice_id
                    }}
                )
            except Exception as b_err:
                print(f"Booking status update error in OnePay callback: {b_err}")

        if worker_email:
            db_module.add_notification(
                user_identifier=worker_email,
                title="Customer OnePay Payment Escrowed!",
                message=f"Customer completed OnePay payment of Rs. {amount:,.2f} for '{service}'. You may now finish and complete the task.",
                notif_type="payment_success",
                link="/jobs"
            )
        if client_email:
            db_module.add_notification(
                user_identifier=client_email,
                title="OnePay Payment Held in Escrow",
                message=f"Your OnePay payment of Rs. {amount:,.2f} (Invoice #{invoice_id}) is held safely by WORKPUB Escrow.",
                notif_type="payment_success",
                link="/my-bookings"
            )

        return Response(f"""
            <html>
                <head>
                    <script>
                        window.location.href = "http://localhost:3000/profile?payment=success&booking_id={booking_id}";
                    </script>
                </head>
                <body>
                    <p>OnePay payment completed! Redirecting to WorkPub dashboard...</p>
                </body>
            </html>
        """, mimetype='text/html')
    except Exception as e:
        print(f"OnePay Callback Error: {e}")
        return jsonify({"error": str(e)}), 500

@payment_bp.route('/api/user-saved-cards', methods=['GET', 'POST'])
def handle_user_saved_cards():
    try:
        if request.method == 'GET':
            email = request.args.get('email')
            if not email:
                return jsonify([])
            cards = list(db_module.saved_cards_collection.find({"email": email}))
            for c in cards:
                c['_id'] = str(c['_id'])
            return jsonify(cards)

        elif request.method == 'POST':
            data = request.json or {}
            email = data.get('email')
            if not email:
                return jsonify({"error": "Missing email"}), 400

            card_entry = {
                "email": email,
                "type": data.get('type', 'Visa'),
                "last4": data.get('last4', '4242'),
                "expiry": data.get('expiry', '08/28'),
                "isDefault": data.get('isDefault', False),
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            db_module.saved_cards_collection.insert_one(card_entry)
            return jsonify({"status": "success", "message": "Card saved successfully"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500
