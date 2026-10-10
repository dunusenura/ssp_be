import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://workpub:xGHDf7NDGDTKv2f0workpub@workpub.a3d5qu8.mongodb.net/?appName=WORKPUB")
SECRET_KEY = os.getenv("SECRET_KEY", "workpub_secret_key_2026")
PORT = int(os.getenv("PORT", 5000))
DEBUG = os.getenv("DEBUG", "True").lower() == "true"

# OnePay Gateway Credentials
ONEPAY_APP_ID = os.getenv('ONEPAY_APP_ID', 'WORKPUB_MERCHANT_APP_ID')
ONEPAY_APP_TOKEN = os.getenv('ONEPAY_APP_TOKEN', 'WORKPUB_MERCHANT_APP_TOKEN')
ONEPAY_HASH_TOKEN = os.getenv('ONEPAY_HASH_TOKEN', 'WORKPUB_SECRET_HASH')
ONEPAY_API_URL = os.getenv('ONEPAY_API_URL', 'https://api.onepay.lk/v3/checkout/link/')

# WhatsApp Gateway Credentials
WHATSAPP_VERIFY_TOKEN = os.getenv('WHATSAPP_VERIFY_TOKEN', 'workpub_whatsapp_secret_token')
