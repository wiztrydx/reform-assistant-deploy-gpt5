from flask import Flask, request, jsonify, send_from_directory
import openai
import os
import json
import re

app = Flask(__name__, static_folder='static')

# OpenAI APIキーの設定
openai.api_key = os.getenv('OPENAI_API_KEY')
openai.api_base = os.getenv('OPENAI_API_BASE', 'https://api.openai.com/v1')

# --- 静的ファイルの配信 ---
@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

# --- ヘルパー関数 ---
def remove_markdown(text):
    """マークダウン記号を確実に除去する関数"""
    # 太字、イタリック、コードブロック等を除去
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # **太字**
    text = re.sub(r'\*([^*]+)\*', r'\1', text)      # *イタリック*
    text = re.sub(r'__([^_]+)__', r'\1', text)      # __太字__
    text = re.sub(r'_([^_]+)_', r'\1', text)        # _イタリック_

    
    return text.strip()

def format_customer_info(form_data):
    """顧客情報を簡潔な文字列に整形"""
    info_parts = []
    
    if form_data.get('familyMembers'):
        info_parts.append(f"家族構成: {', '.join(form_data['familyMembers'])}")
    
    if form_data.get('currentAddress'):
        building_info = f"{form_data['currentAddress']}の{form_data.get('buildingType', '住宅')}"
        if form_data.get('buildingAge'):
            building_info += f"（築{form_data['buildingAge']}）"
        info_parts.append(f"お住まい: {building_info}")
    
    pets_info = [pet for pet, has_pet in form_data.get('pets', {}).items() if has_pet]
    if pets_info:
        info_parts.append(f"ペット: {', '.join(pets_info)}")
    
    if form_data.get('reformAreas'):
        info_parts.append(f"リフォーム希望: {', '.join(form_data['reformAreas'])}")
    
    if form_data.get('budget'):
        info_parts.append(f"予算: {form_data['budget']}")
    
    return " / ".join(info_parts)

def generate_initial_message(form_data):
    """初回メッセージ生成"""
    customer_summary = format_customer_info(form_data)
    
    # 具体的な要望を抽出
    main_concerns = []
    if form_data.get('currentIssues'):
        main_concerns.extend(form_data['currentIssues'])
    if form_data.get('lifestyle'):
        main_concerns.extend(form_data['lifestyle'])
    
    prompt = f"""あなたは熊本県のリフォーム会社「リホーム熊本」の親しみやすいアドバイザーです。

お客様情報: {customer_summary}
主な関心事: {', '.join(main_concerns[:3]) if main_concerns else '快適な住まい'}

リホーム熊本の情報(聞かれたら答える)
所在地： 〒861-8038 熊本県熊本市東区長嶺東５丁目８−１０
電話番号： 0120-182-471


以下のルールで初回メッセージを作成:
1. 絶対にマークダウン記号（*、#、-、`など）を使わない
2. 250字以内で簡潔に
3. 絵文字を2-3個使用
4. 「〜ですね」「〜ませんか？」など親しみやすい語尾
5. 最後に番号付き選択肢を3つ（必ず「1. 」「2. 」「3. 」の形式で記載）
6. 熊本の気候を考慮した提案を含める

例文の雰囲気:
「こんにちは！リホーム熊本です😊
〇〇のリフォームをご検討なんですね。熊本の暑い夏も快適に過ごせるよう、一緒に理想の住まいを考えていきましょう！

まずはどちらから詳しくお聞きしましょうか？

1. 〇〇について
2. △△について  
3. □□について」
"""

    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": "お客様への初回メッセージをお願いします。"}
        ],
        max_tokens=400,
        temperature=0.8
    )
    
    return remove_markdown(response.choices[0].message.content.strip())

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        user_message = data.get('message', '')
        form_data = data.get('formData', {})
        chat_history = data.get('chatHistory', [])
        chat_count = data.get('chatCount', 0)

        # 初回メッセージ
        if chat_count == 0:
            assistant_response = generate_initial_message(form_data)
            return jsonify({'response': assistant_response})

        # 2回目以降のチャット
        customer_context = format_customer_info(form_data)
        
        # より具体的で親しみやすいシステムプロンプト
        system_prompt = f"""あなたは熊本県のリフォーム会社「リホーム熊本」の親しみやすい専門アドバイザーです。

【お客様情報】
{customer_context}

【重要な応答ルール】
1. マークダウン記号（*、**、#、-、`、_、[]()など）は絶対に使用禁止
2. 強調したい部分は「」で囲む
3. 350字以内で簡潔に回答
4. 絵文字を1-3個自然に使用（😊 💡 🏠 ✨ 👍 など）
5. 「〜ですね」「〜ませんか？」など親しみやすい語尾を使用
6. 熊本の気候（湿気、夏の暑さ、台風）を考慮した実用的な提案

【会話の進め方】
- お客様の回答に共感を示してから提案する
- 専門用語は使わず、分かりやすい言葉で説明
- 常に3つの選択肢を数字で提示（1. 2. 3.の形式のみ）
- 選択肢は具体的で選びやすいものにする

【例文の口調】
「なるほど、〇〇が気になるんですね！熊本の夏は特に暑いので、その点も考慮した提案をさせていただきますね😊」"""

        # 4往復目以降は問い合わせを促す
        if chat_count >= 4:
            system_prompt += """

【追加】会話の最後に自然に以下を追加:
「詳しいご相談やお見積もりは、お気軽にこちらからどうぞ！
https://re-homekumamoto.com/contact/」"""

        # メッセージリストの構築（よりシンプルに）
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        # 会話履歴を追加（最大16件 = 8往復分）
        if len(chat_history) > 0:
            messages.extend(chat_history[-16:])
        
        # 現在のユーザーメッセージを追加
        messages.append({"role": "user", "content": user_message})

        # OpenAI API呼び出し
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=500,
            temperature=0.8,  # より自然な会話のため少し上げる
            presence_penalty=0.3,  # 繰り返しを避ける
            frequency_penalty=0.3  # 同じフレーズの使用を抑制
        )
        
        # レスポンスからマークダウンを除去
        assistant_response = remove_markdown(response.choices[0].message.content.strip())
        
        # 番号付きリストの形式を統一（念のため）
        assistant_response = re.sub(r'(\d+)\s*[.．。]\s*', r'\1. ', assistant_response)
        
        return jsonify({'response': assistant_response})

    except openai.error.RateLimitError:
        error_message = (
            "申し訳ございません、現在多くのお問い合わせをいただいております😅\n\n"
            "少しお待ちいただくか、直接お問い合わせいただけますか？\n\n"
            "お急ぎの場合はこちらから:\n"
            "https://re-homekumamoto.com/contact/"
        )
        return jsonify({'response': error_message, 'status': 'rate_limit'}), 429
        
    except Exception as e:
        print(f"Error in chat endpoint: {str(e)}")
        error_message = (
            "申し訳ございません、一時的にエラーが発生しました😣\n\n"
            "お手数ですが、以下からお問い合わせいただけますか？\n\n"
            "https://re-homekumamoto.com/contact/"
        )
        return jsonify({'response': error_message, 'status': 'error'}), 500

@app.route('/health')
def health():
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
