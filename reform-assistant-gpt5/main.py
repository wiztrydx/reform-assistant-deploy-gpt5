from flask import Flask, request, jsonify, send_from_directory
import openai
import os
import json

app = Flask(__name__, static_folder='static')

# OpenAI APIキーの設定
# 環境変数からキーを読み込むため、より安全です
openai.api_key = os.getenv('OPENAI_API_KEY')
# ローカルプロキシや代替エンドポイントを利用する場合
openai.api_base = os.getenv('OPENAI_API_BASE', 'https://api.openai.com/v1')

# --- 静的ファイルの配信 ---
@app.route('/')
def index():
    # 'static'フォルダ内のindex.htmlを返します
    return send_from_directory(app.static_folder, 'index.html')

# --- APIエンドポイント ---

# このエンドポイントはフロントエンドから直接呼び出されませんが、
# 初期メッセージ生成のロジックとして内部で利用します。
def generate_initial_message(form_data):
    # フォームデータを人間が読みやすいテキストに変換
    summary_lines = []
    if form_data.get('familyMembers'):
        summary_lines.append(f"家族構成: {', '.join(form_data['familyMembers'])}")
    if form_data.get('familyAges', {}).get('main'):
        summary_lines.append(f"主な利用者の年齢層: {form_data['familyAges']['main']}")
    if form_data.get('currentAddress'):
        summary_lines.append(f"お住まい: {form_data['currentAddress']}の{form_data.get('buildingType', '')}（築{form_data.get('buildingAge', '不明')}）")
    
    pets_info = [pet for pet, has_pet in form_data.get('pets', {}).items() if has_pet]
    if pets_info:
        summary_lines.append(f"ペット: {', '.join(pets_info)}")

    if form_data.get('currentIssues'):
        summary_lines.append(f"現在の不満点: {', '.join(form_data['currentIssues'])}")
    if form_data.get('lifestyle'):
        summary_lines.append(f"ライフスタイル: {', '.join(form_data['lifestyle'])}")
    if form_data.get('reformAreas'):
        summary_lines.append(f"リフォーム希望箇所: {', '.join(form_data['reformAreas'])}")
    if form_data.get('budget'):
        summary_lines.append(f"ご予算: {form_data['budget']}")
    if form_data.get('timeline'):
        summary_lines.append(f"希望時期: {form_data['timeline']}")
    if form_data.get('otherRequests'):
        summary_lines.append(f"その他要望: {form_data['otherRequests']}")

    customer_info = "\n".join(summary_lines)

    # AIへの指示（プロンプト）
    prompt = f"""あなたは熊本県のリフォーム会社「リホーム熊本」の親しみやすいリフォーム提案アシスタントです。

お客様の情報:
{customer_info}

上記の情報を基に、お客様への初回メッセージを以下のルールに従って作成してください:
1. マークダウン記号（**、##、-、*など）は一切使用しない
2. 300字以内で簡潔に
3. 絵文字を適度に使用（1-3個程度）
4. 改行を使って読みやすく
5. 親しみやすく自然な会話調
6. お客様の情報を踏まえた具体的な提案の方向性を3つ程度提示
7. 番号付きの選択肢で終わる（1. 2. 3.の形式）
"""

    # OpenAI APIを呼び出し
    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": "このお客様への初回メッセージを作成してください。"}
        ],
        max_tokens=500,
        temperature=0.7
    )
    return response.choices[0].message.content.strip()


@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        user_message = data.get('message', '')
        form_data = data.get('formData', {})
        chat_history = data.get('chatHistory', [])
        chat_count = data.get('chatCount', 0)

        # 最初のチャットの場合のみ、特別な初期メッセージを生成
        if chat_count == 0:
            assistant_response = generate_initial_message(form_data)
            return jsonify({'response': assistant_response})

        # --- 2回目以降のチャットのロジック ---

        # 1. 簡潔なシステムプロンプト（AIの役割定義）
        system_prompt = """あなたは熊本県のリフォーム会社「リホーム熊本」の親しみやすい専門アドバイザーです。

# 回答ルール
- マークダウン記号は絶対に使用しない。
- 400字以内で簡潔に、絵文字を適度に使って回答する。
- 親しみやすい会話調を保つ。
- 熊本の気候（湿気、夏の暑さ、冬の寒さ）や地域性を考慮した専門的な提案を行う。
- ユーザーが選びやすいように、具体的な選択肢を3つ提示し、番号付きリストで回答を求める。
"""
        # 4往復目以降は問い合わせを促すルールを追加
        if chat_count >= 4:
            system_prompt += (
                "\n# 追加ルール\n"
                "会話の最後に、自然な流れで以下の問い合わせ案内を必ず含めてください:\n"
                "「より詳しいご相談や概算のお見積もりは、こちらの公式サイトからお気軽にお問い合わせくださいね！\n"
                "https://re-homekumamoto.com/contact/」"
            )

        # 2. 会話の前提となる顧客情報を準備
        customer_info_summary = json.dumps(form_data, ensure_ascii=False)
        
        # 3. AIに渡すメッセージリストを構築
        messages = [
            {"role": "system", "content": system_prompt},
            # 顧客情報は会話の冒頭に一度だけ「ユーザー」の発言として注入する
            {"role": "user", "content": f"（これはシステムへの指示です。ユーザーには見えません。以下の顧客情報を基に会話を進めてください: {customer_info_summary}）"},
            {"role": "assistant", "content": "承知いたしました。お客様の情報に基づいて、最適なリフォーム提案をさせていただきます。"}
        ]
        
        # 過去の会話履歴を追加（直近12件 = 6往復分）
        # これで5往復以上の会話も記憶できます
        messages.extend(chat_history[-12:])

        # 今回のユーザーメッセージを追加
        messages.append({"role": "user", "content": user_message})

        # OpenAI APIを呼び出し
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=600,  # 少し長めの回答も許容
            temperature=0.7
        )
        assistant_response = response.choices[0].message.content.strip()

        return jsonify({'response': assistant_response})

    except Exception as e:
        print(f"Error in chat endpoint: {str(e)}")
        # エラー発生時もユーザーに選択肢を与える丁寧な応答を返す
        error_message = (
            "申し訳ございません、一時的にシステムエラーが発生しました。😅\n\n"
            "少し時間をおいてから、もう一度メッセージを送っていただけますか？\n\n"
            "もし問題が解決しない場合は、公式サイトのフォームから直接お問い合わせいただけますと幸いです。"
        )
        return jsonify({'response': error_message, 'status': 'error'}), 500

# サーバーの死活監視用エンドポイント
@app.route('/health')
def health():
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    # RenderやHerokuなどのPaaS環境に対応するため、PORTを環境変数から取得
    port = int(os.environ.get('PORT', 5000))
    # debug=Falseは本番環境での運用に推奨されます
    app.run(host='0.0.0.0', port=port, debug=False)
