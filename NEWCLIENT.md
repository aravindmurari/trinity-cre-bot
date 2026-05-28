# New Client Onboarding Checklist

This repo is a template. Each client gets their own copy. Steps below take roughly 30–60 minutes end-to-end.

---

## 1. Create the new repo

```bash
gh repo create <client-name>-bot --template aravindmurari/trinity-cre-bot --private --clone
cd <client-name>-bot
```

---

## 2. Update the knowledge base

Replace all files in `/knowledge/` with the client's content:

| File | What goes in it |
|------|----------------|
| `overview.md` | Broker bio, credentials, contact info |
| `services.md` | Service areas (industrial, office, investment, etc.) |
| `listings.md` | Current property listings |
| `insights.md` | Blog posts / market articles with URLs |
| `faq.md` | Common Q&A |
| `market.md` | Local market data and context |

---

## 3. Update backend config

Edit **`backend/config.py`** — this is the only backend file you touch per client:

```python
MODEL = "claude-sonnet-4-6"          # AI model (leave as-is unless upgrading)
TOP_K = 5                             # Pinecone chunks retrieved per query

SYSTEM_PROMPT = """You are the <ClientName> assistant..."""
# Update: broker name, firm name, geography, services, phone, email, CTA URL
```

---

## 4. Update frontend config

Edit **`frontend/config.js`** — the only frontend file you touch per client:

```js
const CLIENT_CONFIG = {
  apiUrl:           'https://<new-railway-url>.up.railway.app',
  tagline:          '<Specialty> — <City/Region>',
  openingMessage:   `Hi, I'm the <ClientName> assistant...`,
  avatarLetter:     '<First letter of firm name>',
  inputPlaceholder: 'Ask about <service> in <region>...',
  pageTitle:        '<ClientName> Assistant',
};
```

---

## 5. Set up Pinecone

1. Log in to [pinecone.io](https://www.pinecone.io)
2. Create a new index:
   - Name: `<client-name>-knowledge`
   - Dimensions: `512`
   - Metric: `cosine`
   - Cloud: AWS / us-east-1 (free tier)
3. Copy the index name — you'll need it for Railway env vars

---

## 6. Set up Railway

1. Create a new Railway project at [railway.app](https://railway.app)
2. Connect it to the new GitHub repo
3. Set these environment variables:

| Variable | Value |
|----------|-------|
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `VOYAGE_API_KEY` | Voyage AI API key |
| `PINECONE_API_KEY` | Pinecone API key |
| `PINECONE_INDEX_NAME` | `<client-name>-knowledge` |
| `SUPABASE_URL` | Supabase project URL (optional) |
| `SUPABASE_KEY` | Supabase anon/service key (optional) |

4. Deploy — Railway auto-builds from the Dockerfile
5. Copy the Railway public URL (e.g. `https://web-production-xxxx.up.railway.app`)

---

## 7. Run ingest

After Railway is up and Pinecone index is created:

```bash
cd backend
cp ../.env.example .env      # fill in your keys
venv/bin/python3 ingest.py
```

This chunks all knowledge files, embeds them via Voyage AI, and loads them into Pinecone. Re-run any time knowledge files change.

---

## 8. Update frontend API URL

Paste the Railway URL into `frontend/config.js`:

```js
apiUrl: 'https://web-production-xxxx.up.railway.app',
```

---

## 9. Set up GitHub Pages

1. Go to repo Settings > Pages
2. Source: GitHub Actions
3. Push to `main` — the workflow in `.github/workflows/deploy-pages.yml` deploys `frontend/` automatically

---

## 10. Replace the logo

Drop the client's logo into `frontend/` as `logo-tcre-white.png` (or update the `src` in `index.html`).

---

## 11. Smoke test

- Open the GitHub Pages URL
- Ask 3–4 questions covering each service area
- Verify the CTA appears with correct phone, email, and consultation link
- Check Railway logs for errors
- Check Supabase for logged messages (if configured)

---

## Files changed per client (summary)

| File | What changes |
|------|-------------|
| `backend/config.py` | System prompt, model, TOP_K |
| `frontend/config.js` | API URL, tagline, opening message, avatar, placeholder |
| `knowledge/*.md` | All knowledge content |
| `frontend/logo-tcre-white.png` | Client logo |

Everything else (backend logic, RAG pipeline, streaming, logging, Dockerfile, GitHub Actions) is identical across all clients and stays untouched.
