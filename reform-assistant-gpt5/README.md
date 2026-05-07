# リフォーム提案アシスタント - GPT-5.4 mini 版

熊本県のリフォーム会社「リホーム熊本」向け、GPT-5.4 mini を活用したリフォーム提案チャットアシスタント。

## 構成

- **Backend**: Flask 3.x + OpenAI SDK 1.x (Chat Completions API)
- **Model**: `gpt-5.4-mini`(2026-03-17 リリース、400k コンテキスト)
- **Frontend**: 静的 HTML/CSS/JavaScript(SPA)
- **Deploy**: Railway / Render / Fly.io 等の Python ランタイムに対応

## 機能

- 7 ステップのヒアリングフォーム(家族構成・建物・ライフスタイル・予算 等)
- ヒアリング内容を踏まえた AI チャット
- 番号付き選択肢を**タップ可能なクイックリプライ・チップ**として自動表示
- IME 安全な Enter 送信(Shift+Enter で改行、変換中は誤送信なし)
- ヒアリング内容を `localStorage` に自動保存(誤リロード対策)
- 一定回数の往復後、問い合わせフォームへ自然に誘導

## ローカル実行

```bash
cd reform-assistant-gpt5
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

export OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx
python main.py
# → http://localhost:5000
```

### 環境変数

| 変数 | 必須 | 既定値 | 用途 |
|---|---|---|---|
| `OPENAI_API_KEY` | ✅ | — | OpenAI API キー |
| `OPENAI_MODEL` | | `gpt-5.4-mini` | 使用モデル ID |
| `OPENAI_API_BASE` | | OpenAI 公式 | プロキシや互換 API を使う場合 |
| `PORT` | | `5000` | 起動ポート |
| `LOG_LEVEL` | | `INFO` | ログレベル |
| `FLASK_DEBUG` | | — | `1` でデバッグモード |

## デプロイ(Railway)

1. GitHub リポジトリを Railway に接続
2. ルートディレクトリに `reform-assistant-gpt5` を指定(または該当フォルダで再構成)
3. 環境変数 `OPENAI_API_KEY` を設定
4. ビルド: `pip install -r requirements.txt`
5. 起動: `Procfile` の `web: gunicorn -b 0.0.0.0:$PORT main:app` が使われます

## モデル料金(2026-05 時点)

GPT-5.4 mini:
- 入力: **$0.75 / 1M tokens**(キャッシュヒット時 $0.075)
- 出力: **$4.50 / 1M tokens**

## ファイル構成

```
reform-assistant-gpt5/
├── main.py            Flask アプリ本体
├── requirements.txt   依存パッケージ
├── Procfile           Railway/Heroku 起動コマンド
├── runtime.txt        Python バージョン指定
├── README.md          このファイル
└── static/
    ├── index.html     SPA(ヒアリング + チャット)
    ├── favicon.ico
    ├── logo-rehome.png
    └── logo-rinozent.png
```

## ライセンス

社内向け非公開プロダクト。再配布禁止。
