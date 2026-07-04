import os
from flask import Flask, request, jsonify, render_template
import google.generativeai as genai
from dotenv import load_dotenv

# تحميل ملف .env إذا كان موجوداً محلياً (عند التطوير على جهازك)
load_dotenv()

app = Flask(__name__)

# قراءة الـ API Key من إعدادات البيئة تلقائياً
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

if not GEMINI_API_KEY:
    print("⚠️ تحذير: لم يتم العثور على GEMINI_API_KEY في إعدادات البيئة!")

# إعداد مكتبة Gemini بالمفتاح المقروء
genai.configure(api_key=GEMINI_API_KEY)

@app.route('/')
def index():
    # تأكد أن ملف index.html موجود داخل مجلد اسمه templates
    return render_template('index.html')

@app.route('/ask-nova', methods=['POST'])
def ask_nova():
    data = request.get_json()
    prompt = data.get('prompt', '')
    context = data.get('context', '')
    
    if not prompt:
        return jsonify({'error': 'الوصف فارغ'}), 400

    try:
        # تجهيز الطلب لـ Gemini ليعطي كود HTML نقي
        full_prompt = (
            f"صاوب موقع إلكتروني كامل بـ HTML و Tailwind CSS بناءً على هاد الوصف: {prompt}. "
            f"الستايل المطلوب: {context}. "
            f"عطيني كود HTML فقط وبدون أي كتابة أخرى خارج الكود."
        )
        
        # استخدام النموذج المستقر والسريع
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(full_prompt)
        
        generated_html = response.text
        
        # تنظيف الكود إذا قام جيمني بوضعه داخل علامات التنسيق Markdown (```html)
        if "```html" in generated_html:
            generated_html = generated_html.split("```html")[1].split("```")[0]
        elif "```" in generated_html:
            generated_html = generated_html.split("```")[1].split("```")[0]
            
        return jsonify({'generated_html': generated_html.strip()})
        
    except Exception as e:
        print(f"Error calling Gemini API: {str(e)}")
        return jsonify({'error': 'Engine Compile Error', 'details': str(e)}), 500

@app.route('/build-live-site', methods=['POST'])
def build_live_site():
    # هنا الكود الخاص بالدفع أو البناء المباشر لموقعك
    return jsonify({'redirect_url': '[https://www.paypal.com](https://www.paypal.com)'})

if __name__ == '__main__':
    # تشغيل محلي للتطوير على جهازك
    app.run(debug=True, port=5000)
