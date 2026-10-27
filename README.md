# PolyStack Taste Gate (Qloo Agentic Hackathon 2026)

Agent that **refuses to ship cultural / product references without Qloo taste-graph evidence**.

Locate (`/search`) → Diagnose (`/v2/insights`) → Apply with entity receipts **or** Refuse when signals are weak.

## Why Qloo (not a generic LLM)

Without the taste graph the agent has no cultural grounding — it must **refuse**. That is the product, not a bolted-on recommender.

## Run (local / fixture)

```bash
cd submissions/qloo-agentic-2026
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env.local   # add QLOO_API_KEY when issued
python app.py
```

Open `http://127.0.0.1:8787`. Without a key the server runs **fixture mode** so the UI stays demoable.

## Env

| Var | Required | Notes |
|-----|----------|-------|
| `QLOO_API_KEY` | for live | header `X-Api-Key` only |
| `QLOO_BASE_URL` | no | default `https://hackathon.api.qloo.com` |
| `PORT` | no | default `8787` |

Never commit `.env.local` or Qloo response dumps.

## License

MIT — see `LICENSE`.
