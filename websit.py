import os
import re
import requests
from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "nova_ultimate_premium_engine_2026")

# 🔑 كيقرا من .env تلقائياً
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# 💳 PayPal من .env
PAYPAL_CLIENT_ID = os.environ.get("PAYPAL_CLIENT_ID", "")
PAYPAL_SECRET = os.environ.get("PAYPAL_SECRET", "")
PAYPAL_BASE_URL = "https://api-m.paypal.com"
DOMAIN = os.environ.get("DOMAIN", "http://127.0.0.1:5000")
SITE_PRICE = "5.00"

# 👑 Admin
ADMIN_EMAILS = ["abdelhakimelgrich@gmail.com"]


def call_gemini(prompt, system_instruction):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "system_instruction": {"parts": [{"text": system_instruction}]},
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.4}
    }
    response = requests.post(url, json=payload)
    data = response.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]


def get_paypal_token():
    response = requests.post(
        f"{PAYPAL_BASE_URL}/v1/oauth2/token",
        headers={"Accept": "application/json", "Accept-Language": "en_US"},
        data={"grant_type": "client_credentials"},
        auth=(PAYPAL_CLIENT_ID, PAYPAL_SECRET)
    )
    return response.json().get("access_token")


@app.route('/')
def login_page():
    error = request.args.get('error', '')
    return render_template('login.html', error=error)


@app.route('/login', methods=['POST'])
def do_login():
    username = request.form.get('username', '').strip().lower()
    password = request.form.get('password', '').strip()

    if username and password and "@" in username:
        session['user'] = username
        session['is_admin'] = username in ADMIN_EMAILS
        return redirect(url_for('dashboard_page'))

    return redirect(url_for('login_page', error="invalid"))


@app.route('/logout')
def do_logout():
    session.clear()
    return redirect(url_for('login_page'))


@app.route('/dashboard')
def dashboard_page():
    if 'user' not in session:
        return redirect(url_for('login_page'))
    return render_template('index.html')


@app.route('/ask-nova', methods=['POST'])
def ask_nova():
    if 'user' not in session:
        return jsonify({"generated_html": "<h1>🔒 خاصك تسجل الدخول أولا</h1>"})

    data = request.json
    style_context = data.get('context', '')
    site_prompt = data.get('prompt', '')

    if not GEMINI_API_KEY:
        return jsonify({
            "generated_html": "<h1 style='color:#ef4444;text-align:center;padding:20px;'>⚠️ Nova Engine Missing API Key</h1>"
        })

    system_instruction = (
        "You are the Core Production Engine of Nova AI Website Builder. You generate REAL, FULLY FUNCTIONAL, and professional single-page websites.\n"
        "CRITICAL REQUIREMENTS:\n"
        "1. Output ONLY valid, clean HTML5 code.\n"
        "2. ALWAYS include Tailwind CSS CDN (<script src='https://cdn.tailwindcss.com'></script>) in the <head>.\n"
        "3. Include interactive features using clean, embedded vanilla JavaScript.\n"
        "4. Ensure it is 100% responsive with realistic placeholder content.\n"
        f"5. Implement these aesthetic choices perfectly: {style_context}.\n"
        "6. Do NOT wrap the code in markdown blocks like ```html. Start directly with <!DOCTYPE html>."
    )

    try:
        raw_code = call_gemini(
            f"Build a production-ready complete website for: {site_prompt}",
            system_instruction
        )
        clean_html = re.sub(r'^```html\s*', '', raw_code, flags=re.IGNORECASE)
        clean_html = re.sub(r'^```\s*', '', clean_html)
        clean_html = re.sub(r'\s*```$', '', clean_html)
        clean_html = clean_html.strip()
        session['last_generated_html'] = clean_html
    except Exception as e:
        clean_html = f"<h1>❌ Engine Compile Error</h1><p>{str(e)}</p>"

    return jsonify({"generated_html": clean_html})


@app.route('/build-live-site', methods=['POST'])
def build_live_site():
    if 'user' not in session:
        return redirect(url_for('login_page'))

    if session.get('is_admin', False):
        session['can_download'] = True
        return jsonify({"redirect_url": "/download-site"})

    try:
        token = get_paypal_token()
        if not token:
            return jsonify({"error": "تعذر الاتصال بـ PayPal"}), 400

        response = requests.post(
            f"{PAYPAL_BASE_URL}/v2/checkout/orders",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}"
            },
            json={
                "intent": "CAPTURE",
                "purchase_units": [{
                    "amount": {"currency_code": "USD", "value": SITE_PRICE},
                    "description": "Nova Website - Build & Download"
                }],
                "application_context": {
                    "return_url": DOMAIN + "/payment-success",
                    "cancel_url": DOMAIN + "/payment-cancel"
                }
            }
        )
        data = response.json()
        approve_url = next(
            (link["href"] for link in data.get("links", []) if link["rel"] == "approve"),
            None
        )
        if not approve_url:
            return jsonify({"error": "تعذر صاوب جلسة الدفع"}), 400

        session['pending_order_id'] = data.get("id")
        return jsonify({"redirect_url": approve_url})

    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route('/payment-success')
def payment_success():
    token_param = request.args.get('token')
    try:
        token = get_paypal_token()
        capture = requests.post(
            f"{PAYPAL_BASE_URL}/v2/checkout/orders/{token_param}/capture",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}"
            }
        )
        if capture.status_code == 201:
            session['can_download'] = True
    except Exception:
        pass
    return redirect(url_for('dashboard_page'))


@app.route('/payment-cancel')
def payment_cancel():
    return redirect(url_for('dashboard_page'))


@app.route('/download-site')
def download_site():
    if not (session.get('can_download') or session.get('is_admin')):
        return "🔒 خاصك تدفع أولا", 403

    html = session.get('last_generated_html', '<h1>ماكاين حتى موقع</h1>')
    session['can_download'] = False
    return html, 200, {
        'Content-Type': 'text/html',
        'Content-Disposition': 'attachment; filename=index.html'
    }


if __name__ == '__main__':
    app.run(debug=False)
