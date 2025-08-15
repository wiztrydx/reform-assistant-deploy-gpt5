from flask import Flask, request, jsonify, send_from_directory
import openai
import os
import json

app = Flask(__name__, static_folder='static')

# OpenAI APIキーの設定
openai.api_key = os.getenv('OPENAI_API_KEY')
openai.api_base = os.getenv('OPENAI_API_BASE', 'https://api.openai.com/v1')

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/api/initial-message', methods=['POST'])
def initial_message():
    try:
        data = request.get_json()
        form_data = data.get('formData', {})
        
        # フォームデータを整理
        family_info = []
        if form_data.get('familyMembers'):
            family_info.append(f"家族構成: {', '.join(form_data['familyMembers'])}")
        if form_data.get('familyAges', {}).get('main'):
            family_info.append(f"年齢層: {form_data['familyAges']['main']}")
        
        building_info = []
        if form_data.get('currentAddress'):
            building_info.append(f"住所: {form_data['currentAddress']}")
        if form_data.get('buildingType'):
            building_info.append(f"建物: {form_data['buildingType']}")
        if form_data.get('buildingAge'):
            building_info.append(f"築年数: {form_data['buildingAge']}")
        
        pets_info = []
        if form_data.get('pets'):
            for pet, has_pet in form_data['pets'].items():
                if has_pet:
                    pets_info.append(pet)
        
        issues_info = form_data.get('currentIssues', [])
        lifestyle_info = form_data.get('lifestyle', [])
        reform_areas = form_data.get('reformAreas', [])
        
        budget_info = []
        if form_data.get('budget'):
            budget_info.append(f"予算: {form_data['budget']}")
        if form_data.get('timeline'):
            budget_info.append(f"時期: {form_data['timeline']}")
        
        other_requests = form_data.get('otherRequests', '')
        
        # プロンプトを作成
        prompt = f"""あなたは熊本県のリフォーム会社「リホーム熊本」の親しみやすいリフォーム提案アシスタントです。

お客様の情報:
{chr(10).join(family_info) if family_info else ''}
{chr(10).join(building_info) if building_info else ''}
{'ペット: ' + ', '.join(pets_info) if pets_info else 'ペット: なし'}
{'現在の不満: ' + ', '.join(issues_info) if issues_info else ''}
{'ライフスタイル: ' + ', '.join(lifestyle_info) if lifestyle_info else ''}
{'リフォーム希望箇所: ' + ', '.join(reform_areas) if reform_areas else ''}
{chr(10).join(budget_info) if budget_info else ''}
{'その他要望: ' + other_requests if other_requests else ''}

以下のルールに従って初回メッセージを作成してください:

1. マークダウン記号（**、##、-、*など）は一切使用しない
2. 300字以内で簡潔に
3. 絵文字を適度に使用（1-3個程度）
4. 改行を使って読みやすく
5. 親しみやすく自然な会話調
6. お客様の情報を踏まえた具体的な提案の方向性を3つ程度提示
7. 番号付きの選択肢で終わる（1. 2. 3.の形式）

例:
こんにちは！😊
ヒアリングありがとうございました。

○○様のご家族構成とご希望を拝見させていただき、
いくつかの素敵なプランが思い浮かびました！

特におすすめしたいのは以下の3つです：

1. △△を重視した機能的なリフォーム
2. □□を活かしたデザイン重視のリフォーム  
3. ◇◇に配慮したバリアフリーリフォーム

どちらに一番興味がおありでしょうか？🏠
"""
        
        # OpenAI APIを呼び出し
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": "初回メッセージをお願いします"}
            ],
            max_tokens=500,
            temperature=0.7
        )
        
        assistant_message = response.choices[0].message.content.strip()
        
        return jsonify({
            'response': assistant_message
        })
        
    except Exception as e:
        print(f"Error in initial_message: {str(e)}")
        return jsonify({
            'error': 'エラーが発生しました',
            'response': 'こんにちは！😊\nリフォーム提案アシスタントです。\n\nヒアリング内容を確認させていただき、\nあなたにぴったりのリフォームプランを\nご提案させていただきますね！\n\nまずは、どのような点を\n一番重視されたいでしょうか？\n\n1. 機能性・使いやすさ\n2. デザイン・見た目\n3. コストパフォーマンス\n\n番号でお答えください！🏠'
        }), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        messages = data.get('messages', [])
        chat_count = data.get('chatCount', 0)
        
        # システムプロンプト
        system_prompt = """あなたは熊本県のリフォーム会社「リホーム熊本」の親しみやすいリフォーム提案アシスタントです。

以下のルールに従って回答してください:

1. マークダウン記号（**、##、-、*など）は一切使用しない
2. 400字以内で簡潔に
3. 絵文字を適度に使用
4. 改行を使って読みやすく
5. 親しみやすく自然な会話調
6. リフォームの専門知識を活かした具体的なアドバイス
7. 熊本の気候や住環境を考慮した提案
8. 能動的に理想の具体的なリフォームプランを提案する
9. できるだけ番号付きの選択肢で回答を求める（1. 2. 3.の形式）
10. ユーザーが選択しやすいよう、具体的な選択肢を提示する

回答例:
そうですね！😊
キッチンのリフォームでしたら、
熊本の湿気対策も大切ですね。

あなたのご希望に合わせて、
こんなプランはいかがでしょうか？

1. 対面キッチンで家族との会話を重視
2. アイランドキッチンで開放感を演出
3. 壁付けキッチンで収納力をアップ

どのスタイルがお気に入りでしょうか？🏠"""

        # 4往復目の場合は、URL案内を含める
        if chat_count >= 4:
            system_prompt += """

重要: 4往復目以降は、回答の最後に自然な流れで以下のURL案内を含めてください:
「より詳しいご相談は、こちらからお気軽にお問い合わせください
https://re-homekumamoto.com/contact/」

この案内は自然な会話の流れの中で、押し付けがましくなく案内してください。"""
        
        # メッセージリストを準備
        api_messages = [{"role": "system", "content": system_prompt}]
        api_messages.extend(messages)
        
        # OpenAI APIを呼び出し
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=api_messages,
            max_tokens=500,
            temperature=0.7
        )
        
        assistant_message = response.choices[0].message.content.strip()
        
        return jsonify({
            'response': assistant_message
        })
        
    except Exception as e:
        print(f"Error in chat: {str(e)}")
        return jsonify({
            'error': 'エラーが発生しました',
            'response': '申し訳ございません。😅\n一時的にエラーが発生しました。\n\nしばらくしてから再度お試しいただくか、\n以下からお選びください：\n\n1. もう一度質問する\n2. 別の話題に変える\n3. 直接お電話で相談する\n\nどちらがよろしいでしょうか？🏠'
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

