import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from openai import OpenAI

app = Flask(__name__, static_folder='static')
CORS(app, origins="*", methods=["GET", "POST", "OPTIONS"], allow_headers=["Content-Type"])

# OpenAI クライアントの初期化
client = None

def get_openai_client():
    global client
    if client is None:
        try:
            api_key = os.environ.get('OPENAI_API_KEY')
            if not api_key:
                print("❌ OPENAI_API_KEY not found")
                return None
            client = OpenAI(api_key=api_key)
            print("✅ OpenAI client initialized successfully")
        except Exception as e:
            print(f"❌ Error initializing OpenAI client: {e}")
            return None
    return client

@app.route('/api/chat', methods=['POST', 'OPTIONS'])
def chat():
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        print("📨 Chat request received")
        openai_client = get_openai_client()
        if not openai_client:
            return jsonify({'error': 'OpenAI client not available'}), 500
            
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data received'}), 400
            
        messages = data.get('messages', [])
        print(f"💬 Processing {len(messages)} messages")
        
        # OpenAI API v1.x の新しい構文
        response = openai_client.chat.completions.create(
            model="gpt-4",  # GPT-5が利用できない場合はGPT-4を使用
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
        openai_client = get_openai_client()
        if not openai_client:
            return jsonify({'error': 'OpenAI client not available'}), 500
            
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data received'}), 400
            
        form_data = data.get('formData', {})
        print("📋 Processing form data for initial message")
        
        # フォームデータを基にプロンプトを作成
        prompt = f"""
あなたはリフォーム熊本の親しみやすいAIアドバイザーです。以下のお客様情報を基に、4つの魅力的なリフォームプランを提案してください。

お客様情報:
- 家族構成: {form_data.get('familyMembers', [])}
- ペット: {form_data.get('pets', {})}
- 住所: {form_data.get('address', '')}
- ライフスタイル: {form_data.get('lifestyle', [])}
- 趣味: {form_data.get('hobbies', [])}
- インテリアスタイル: {form_data.get('interiorStyle', [])}
- リフォーム箇所: {form_data.get('reformAreas', [])}
- リフォーム理由: {form_data.get('reformReasons', [])}
- その他の要望: {form_data.get('otherRequests', '')}

4つのプランを番号付きで提案し、それぞれに絵文字とキャッチーなタイトルをつけてください。
各プランは2-3行で簡潔に説明してください。
最後に「どのプランが気になりますか？番号で教えてください！😊」と質問してください。
"""
        
        # OpenAI API v1.x の新しい構文
        response = openai_client.chat.completions.create(
            model="gpt-4",  # GPT-5が利用できない場合はGPT-4を使用
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
        return jsonify({'error': f'Initial message error: {str(e)}'}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """ヘルスチェック用エンドポイント"""
    try:
        api_key = os.environ.get('OPENAI_API_KEY')
        api_key_status = "Set" if api_key else "Not set"
        api_key_format = "Valid" if api_key and api_key.startswith('sk-') else "Invalid"
        
        # OpenAI クライアントのテスト
        openai_client = get_openai_client()
        client_status = "OK" if openai_client else "Failed"
        
        return jsonify({
            'status': 'healthy',
            'api_key_status': api_key_status,
            'api_key_format': api_key_format,
            'client_status': client_status,
            'api_provider': 'OpenAI',
            'model': 'GPT-4',
            'version': '2025.08.15-fixed'
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

