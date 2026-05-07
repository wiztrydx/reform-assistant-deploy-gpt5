"""リフォーム熊本 - リフォーム提案アシスタント (GPT-5.4 mini 版)."""

from __future__ import annotations

import logging
import os
import re
from typing import Any

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from openai import APIError, OpenAI, RateLimitError

# --- 設定値 ---
MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")
INITIAL_MAX_TOKENS = 400
CHAT_MAX_TOKENS = 500
TEMPERATURE = 0.8
PRESENCE_PENALTY = 0.3
FREQUENCY_PENALTY = 0.3
HISTORY_TURNS = 8  # 直近 8 往復 (=16 メッセージ) を保持
CONTACT_URL = "https://re-homekumamoto.com/contact/"

# --- ロギング ---
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("reform-assistant")

# --- OpenAI クライアント ---
# 起動時に APIキー が無くてもプロセスは落とさず、/chat 呼び出し時にエラー応答する。
# (Railway 等のデプロイで env 未注入時にワーカーが即死しないように)
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    logger.warning("OPENAI_API_KEY が未設定です。/chat はエラー応答を返します。")

client = OpenAI(
    api_key=api_key or "missing",
    base_url=os.getenv("OPENAI_API_BASE"),  # None なら公式エンドポイント
)

# --- Flask ---
app = Flask(__name__, static_folder="static")
CORS(app)


# --- 静的ファイル ---
@app.route("/")
def index() -> Any:
    return send_from_directory(app.static_folder, "index.html")


@app.route("/static/<path:filename>")
def static_files(filename: str) -> Any:
    return send_from_directory(app.static_folder, filename)


# --- ヘルパー ---
_MARKDOWN_PATTERNS = [
    (re.compile(r"\*\*([^*]+)\*\*"), r"\1"),
    (re.compile(r"\*([^*]+)\*"), r"\1"),
    (re.compile(r"__([^_]+)__"), r"\1"),
    (re.compile(r"_([^_]+)_"), r"\1"),
    (re.compile(r"`([^`]+)`"), r"\1"),
]
_NUMBER_LIST_NORMALIZER = re.compile(r"(\d+)\s*[.．。]\s*")


def remove_markdown(text: str) -> str:
    for pattern, repl in _MARKDOWN_PATTERNS:
        text = pattern.sub(repl, text)
    return text.strip()


def normalize_numbered_list(text: str) -> str:
    return _NUMBER_LIST_NORMALIZER.sub(r"\1. ", text)


def format_customer_info(form_data: dict) -> str:
    parts: list[str] = []

    if form_data.get("familyMembers"):
        parts.append(f"家族構成: {', '.join(form_data['familyMembers'])}")

    if form_data.get("currentAddress"):
        building = f"{form_data['currentAddress']}の{form_data.get('buildingType', '住宅')}"
        if form_data.get("buildingAge"):
            building += f"（築{form_data['buildingAge']}）"
        parts.append(f"お住まい: {building}")

    pets = [pet for pet, has in form_data.get("pets", {}).items() if has]
    if pets:
        parts.append(f"ペット: {', '.join(pets)}")

    if form_data.get("reformAreas"):
        parts.append(f"リフォーム希望: {', '.join(form_data['reformAreas'])}")

    if form_data.get("budget"):
        parts.append(f"予算: {form_data['budget']}")

    if form_data.get("timeline"):
        parts.append(f"希望時期: {form_data['timeline']}")

    if form_data.get("otherRequests"):
        parts.append(f"その他要望: {form_data['otherRequests']}")

    return " / ".join(parts)


def _build_initial_prompt(form_data: dict) -> str:
    customer_summary = format_customer_info(form_data)
    main_concerns: list[str] = []
    main_concerns.extend(form_data.get("currentIssues") or [])
    main_concerns.extend(form_data.get("lifestyle") or [])
    concern_text = ", ".join(main_concerns[:3]) if main_concerns else "快適な住まい"

    return f"""あなたは熊本県のリフォーム会社「リホーム熊本」の親しみやすいアドバイザーです。

お客様情報: {customer_summary}
主な関心事: {concern_text}

リホーム熊本の情報(聞かれたら答える)
所在地： 〒861-8038 熊本県熊本市東区長嶺東５丁目８−１０
電話番号： 0120-182-471

以下のルールで初回メッセージを作成:
1. 絶対にマークダウン記号（*、#、-、`など）を使わない
2. 250字以内で簡潔に
3. 絵文字を2-3個使用
4. 「〜ですね」「〜ませんか？」など親しみやすい語尾
5. 最後に「お客様が次に聞きたくなりそうな質問・要望」を3つ提示する
   - 必ず「1. 」「2. 」「3. 」の形式で改行して記載
   - お客様の一人称・話し言葉で短く（20字以内目安）
   - 「〜について教えて」「〜はいくら？」「〜はどれくらい？」のような追加質問にする
   - アシスタント側のアドバイス内容や提案項目を選択肢にしない（クリック=お客様の発言になるため）
6. 熊本の気候を考慮した提案を含める

例文の雰囲気:
「こんにちは！リホーム熊本です😊
キッチンのリフォームをご検討なんですね。熊本の暑い夏や湿気にも強いプランを一緒に考えていきましょう！

何から聞いてみますか？

1. 費用の目安を教えて
2. 工期はどれくらい？
3. おすすめの設備を知りたい」
"""


def _build_chat_prompt(customer_context: str, chat_count: int) -> str:
    base = f"""あなたは熊本県のリフォーム会社「リホーム熊本」の親しみやすい専門アドバイザーです。

【リホーム熊本の情報】(お客様から質問があった場合にのみ案内する)
所在地： 〒861-8038 熊本県熊本市東区長嶺東５丁目８−１０
電話番号： 0120-182-471

【お客様情報】
{customer_context}

【重要な応答ルール】
1. マークダウン記号（*、**、#、-、`、_、[]() など）は絶対に使用禁止
2. 強調したい部分は「」で囲む
3. 350字以内で簡潔に回答
4. 絵文字を1-3個自然に使用（😊 💡 🏠 ✨ 👍 など）
5. 「〜ですね」「〜ませんか？」など親しみやすい語尾を使用
6. 熊本の気候（湿気、夏の暑さ、台風）を考慮した実用的な提案

【会話の進め方】
- お客様の回答に共感を示してから提案する
- 専門用語は使わず、分かりやすい言葉で説明
- 回答の最後には必ず「お客様が次に聞きたくなりそうな質問・要望」を3つ提示する
  - 「1. 」「2. 」「3. 」の形式で改行して記載
  - お客様の一人称・話し言葉で短く（20字以内目安）
  - 「もう少し詳しく教えて」「費用はどれくらい？」「他の事例も見たい」のような追加質問にする
  - アシスタント側のアドバイス内容や提案項目を選択肢にしない
    （クリックされるとそのテキストがお客様の発言として送られるため）

【例文の口調と末尾選択肢】
「なるほど、外壁が気になるんですね！熊本は台風や雨が多いので、外壁と屋根を一緒に見直すと安心ですよ😊

次に気になることはありますか？

1. 費用の目安を教えて
2. 工期はどれくらい？
3. 雨漏りも一緒に相談できる？」"""

    if chat_count >= 4:
        base += f"""

【追加】会話の最後に自然に以下を追加:
「詳しいご相談やお見積もりは、お気軽にこちらからどうぞ！
{CONTACT_URL}」"""

    return base


def _call_openai(messages: list[dict], max_tokens: int) -> str:
    # GPT-5 系の新モデルは max_tokens を廃止し max_completion_tokens を要求する。
    # 旧モデル(gpt-4o 等)は max_completion_tokens でも受理されるので、これを既定で送る。
    kwargs: dict = {
        "model": MODEL_NAME,
        "messages": messages,
        "max_completion_tokens": max_tokens,
    }
    # GPT-5 系は temperature/penalty 系のチューニングパラメータを受け付けないことがあるため、
    # gpt-5 を含むモデル名では送らない。
    is_gpt5 = "gpt-5" in MODEL_NAME.lower()
    if not is_gpt5:
        kwargs["temperature"] = TEMPERATURE
        kwargs["presence_penalty"] = PRESENCE_PENALTY
        kwargs["frequency_penalty"] = FREQUENCY_PENALTY

    response = client.chat.completions.create(**kwargs)
    content = response.choices[0].message.content or ""
    cleaned = remove_markdown(content.strip())
    return normalize_numbered_list(cleaned)


def generate_initial_message(form_data: dict) -> str:
    prompt = _build_initial_prompt(form_data)
    return _call_openai(
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": "お客様への初回メッセージをお願いします。"},
        ],
        max_tokens=INITIAL_MAX_TOKENS,
    )


def _rate_limit_response() -> tuple:
    msg = (
        "申し訳ございません、現在多くのお問い合わせをいただいております😅\n\n"
        "少しお待ちいただくか、直接お問い合わせいただけますか？\n\n"
        f"お急ぎの場合はこちらから:\n{CONTACT_URL}"
    )
    return jsonify({"response": msg, "status": "rate_limit"}), 429


def _server_error_response() -> tuple:
    msg = (
        "申し訳ございません、一時的にエラーが発生しました😣\n\n"
        "お手数ですが、以下からお問い合わせいただけますか？\n\n"
        f"{CONTACT_URL}"
    )
    return jsonify({"response": msg, "status": "error"}), 500


# --- ルート ---
@app.route("/chat", methods=["POST"])
def chat() -> Any:
    try:
        data = request.get_json(silent=True) or {}
        user_message = (data.get("message") or "").strip()
        form_data = data.get("formData") or {}
        chat_history = data.get("chatHistory") or []
        chat_count = int(data.get("chatCount") or 0)

        # --- 初回メッセージ ---
        if chat_count == 0:
            assistant_response = generate_initial_message(form_data)
            return jsonify({"response": assistant_response})

        # --- 2 回目以降 ---
        if not user_message:
            return jsonify({"response": "メッセージが空でした。もう一度入力してください😊"}), 400

        customer_context = format_customer_info(form_data)
        system_prompt = _build_chat_prompt(customer_context, chat_count)

        # 履歴は直近 N 往復のみ送信
        recent_history = chat_history[-(HISTORY_TURNS * 2):]
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(recent_history)
        messages.append({"role": "user", "content": user_message})

        assistant_response = _call_openai(messages, max_tokens=CHAT_MAX_TOKENS)
        return jsonify({"response": assistant_response})

    except RateLimitError:
        logger.warning("OpenAI rate limit hit")
        return _rate_limit_response()
    except APIError as exc:
        logger.exception("OpenAI APIError: %s", exc)
        return _server_error_response()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected error in /chat: %s", exc)
        return _server_error_response()


@app.route("/health")
def health() -> Any:
    return jsonify({"status": "healthy", "model": MODEL_NAME})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG") == "1"
    logger.info("Starting on port %d (model=%s, debug=%s)", port, MODEL_NAME, debug)
    app.run(host="0.0.0.0", port=port, debug=debug)
