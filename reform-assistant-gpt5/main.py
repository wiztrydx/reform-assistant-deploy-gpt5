import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import openai

app = Flask(__name__, static_folder='static')
CORS(app, origins="*", methods=["GET", "POST", "OPTIONS"], allow_headers=["Content-Type"])

# OpenAI APIキーの設定
openai.api_key = os.environ.get('OPENAI_API_KEY')

@app.route('/api/chat', methods=['POST', 'OPTIONS'])
def chat():
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        print("📨 Chat request received")
        
        if not openai.api_key:
            print("❌ OPENAI_API_KEY not found")
            return jsonify({'error': 'OpenAI API key not available'}), 500
            
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data received'}), 400
            
        messages = data.get('messages', [])
        print(f"💬 Processing {len(messages)} messages")
        
        # OpenAI API v0.28.x の構文
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=messages,
            max_tokens=1500,
            temperature=0.7
        )
        
        result = response.choices[0].message.content
        print("✅ Chat response generated successfully")
        
        return jsonify({
            'response': result
        })
    except Exception as e:
        print(f"❌ Error in chat endpoint: {e}")
        return jsonify({'error': f'Chat error: {str(e)}'}), 500

@app.route('/api/initial-message', methods=['POST', 'OPTIONS'])
def initial_message():
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        print("📨 Initial message request received")
        
        if not openai.api_key:
            print("❌ OPENAI_API_KEY not found")
            return jsonify({'error': 'OpenAI API key not available'}), 500
            
        data = request.get_json()
        if not data:
            print("❌ No JSON data received")
            return jsonify({'error': 'No JSON data received'}), 400
            
        form_data = data.get('formData', {})
        print(f"📋 Processing form data: {form_data}")
        
        # 安全にデータを取得（Noneの場合は空のリストや文字列を返す）
        family_members = form_data.get('familyMembers', []) or []
        pets = form_data.get('pets', {}) or {}
        address = form_data.get('address', '') or ''
        lifestyle = form_data.get('lifestyle', []) or []
        hobbies = form_data.get('hobbies', []) or []
        interior_style = form_data.get('interiorStyle', []) or []
        reform_areas = form_data.get('reformAreas', []) or []
        reform_reasons = form_data.get('reformReasons', []) or []
        other_requests = form_data.get('otherRequests', '') or ''
        
        # フォームデータを基にプロンプトを作成
        prompt = f"""
あなたはリフォーム熊本の親しみやすいAIアドバイザーです。以下のお客様情報を基に、4つの魅力的なリフォームプランを提案してください。

お客様情報:
- 家族構成: {family_members}
- ペット: {pets}
- 住所: {address}
- ライフスタイル: {lifestyle}
- 趣味: {hobbies}
- インテリアスタイル: {interior_style}
- リフォーム箇所: {reform_areas}
- リフォーム理由: {reform_reasons}
- その他の要望: {other_requests}

4つのプランを番号付きで提案し、それぞれに絵文字とキャッチーなタイトルをつけてください。
各プランは2-3行で簡潔に説明してください。
最後に「どのプランが気になりますか？番号で教えてください！😊」と質問してください。
"""
        
        print("🤖 Sending request to OpenAI...")
        
        # OpenAI API v0.28.x の構文
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1500,
            temperature=0.7
        )
        
        result = response.choices[0].message.content
        print("✅ Initial message generated successfully")
        
        return jsonify({
            'response': result
        })
    except Exception as e:
        print(f"❌ Error in initial_message endpoint: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Initial message error: {str(e)}'}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """ヘルスチェック用エンドポイント"""
    try:
        api_key = os.environ.get('OPENAI_API_KEY')
        api_key_status = "Set" if api_key else "Not set"
        api_key_format = "Valid" if api_key and api_key.startswith('sk-') else "Invalid"
        
        return jsonify({
            'status': 'healthy',
            'api_key_status': api_key_status,
            'api_key_format': api_key_format,
            'api_provider': 'OpenAI',
            'model': 'GPT-4',
            'version': '2025.08.15-compatibility-fix'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Starting Reform Assistant on port {port}")
    print(f"🔑 API Key status: {'Set' if os.environ.get('OPENAI_API_KEY') else 'Not set'}")
    app.run(host='0.0.0.0', port=port, debug=True)
