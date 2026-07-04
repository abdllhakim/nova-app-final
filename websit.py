import os
from flask import Flask, request, jsonify, render_template
import google.generativeai as genai
from dotenv import load_dotenv

# تحميل ملف .env للمحيط المحلي
load_dotenv()

app = Flask(__name__)

# قراءة الـ API Key من الـ Environment Variables
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# إعداد مكتبة جوجل بالمفتاح الجديد
genai.configure(api_key=GEMINI_API_KEY)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/ask-nova', methods=['POST'])
def ask_nova():
    data = request.get_json()
    prompt = data.get('prompt', '')
    context = data.get('context', '')
    
    if not prompt:
        return jsonify({'error': 'الوصف فارغ'}), 400

    try:
        full_prompt = (
            f"صاوب موقع إلكتروني كامل بـ HTML و Tailwind CSS بناءً على هاد الوصف: {prompt}. "
            f"الستايل المطلوب: {context}. "
            f"عطيني كود HTML فقط وبدون أي كتابة أخرى خارج الكود."
        )
        
        # استخدام نسخة البرو المستقرة والممتازة للأكواد
        model = genai.GenerativeModel('gemini-1.5-pro')
        response = model.generate_content(full_prompt)
        
        generated_html = response.text
        
        if not generated_html:
            return jsonify({'generated_html': "<body style='color:red;background:#0e101f;text-align:center;padding:40px;'>❌ السيرفر رجع استجابة فارغة، حاول مرة أخرى.</body>"})

        # تنظيف آمن للكود لتفادي مشاكل الـ Markdown والـ undefined
        if "```html" in generated_html:
            try:
                generated_html = generated_html.split("```html")[1].split("```")[0]
            except IndexError:
                pass
        elif "```" in generated_html:
            try:
                generated_html = generated_html.split("```")[1].split("```")[0]
            except IndexError:
                pass
            
        return jsonify({'generated_html': generated_html.strip()})
        
    except Exception as e:
        print(f"Error calling Gemini API: {str(e)}")
        # إظهار الخطأ بوضوح في الـ Preview في حالة وجود مشكل في الـ API Key
        error_message = f"<body style='color:#ef4444;background:#0e101f;text-align:center;padding:40px;direction:rtl;'>❌ خطأ فالمحرك: {str(e)}</body>"
        return jsonify({'generated_html': error_message}), 500

@app.route('/build-live-site', methods=['POST'])
def build_live_site():
    return jsonify({'redirect_url': 'https://www.paypal.com'})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
