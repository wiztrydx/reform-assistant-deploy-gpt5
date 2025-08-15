import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import openai

app = Flask(__name__, static_folder='static')
CORS(app)

# OpenAI APIキーの設定
openai.api_key = os.environ.get('OPENAI_API_KEY')

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        messages = data.get('messages', [])
        
        # GPT-5 APIに送信
        response = openai.ChatCompletion.create(
            model="gpt-5",  # 最新のGPT-5モデル
            messages=messages,
            max_tokens=1500,
            temperature=0.7
        )
        
        return jsonify({
            'response': response.choices[0].message.content
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/initial-message', methods=['POST'])
def initial_message():
    try:
        data = request.get_json()
        form_data = data.get('formData', {})
        
        # フォームデータを基にプロンプトを作成
        prompt = f"""
あなたはリフォーム熊本の最先端AIアドバイザーです。GPT-5の高度な推論能力を活用して、以下のお客様情報を基に、4つの革新的で魅力的なリフォームプランを提案してください。

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

GPT-5の高度な推論能力を活用して、お客様のライフスタイルと要望を深く分析し、4つの創造的で実用的なリフォームプランを提案してください。
各プランには以下を含めてください：
1. 絵文字とキャッチーなタイトル
2. 具体的な設計アイデア（2-3行）
3. 予想される効果やメリット
4. 概算予算の目安（可能であれば）

最後に「どのプランが気になりますか？番号で教えてください！😊 GPT-5の詳細分析で、さらに具体的な提案も可能です！」と質問してください。
"""
        
        response = openai.ChatCompletion.create(
            model="gpt-5",  # 最新のGPT-5モデル
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1500,
            temperature=0.7
        )
        
        return jsonify({
            'response': response.choices[0].message.content
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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
            'model': 'GPT-5',
            'version': '2025.08.15'
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
    print(f"🚀 Starting GPT-5 powered Reform Assistant on port {port}")
    print(f"🔑 API Key status: {'Set' if os.environ.get('OPENAI_API_KEY') else 'Not set'}")
    app.run(host='0.0.0.0', port=port, debug=False)

