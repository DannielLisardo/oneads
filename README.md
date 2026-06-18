# OneAds

Plataforma para agências de tráfego pago conectarem contas de anúncios de seus **clientes** e sincronizarem dados no **Google Drive do próprio cliente**.

## Estrutura

```
OneAds/
├── backend/          ← API FastAPI (Python)
│   ├── main.py
│   ├── config.py
│   ├── requirements.txt
│   ├── .env.example
│   ├── routers/      ← OAuth + endpoints de sync
│   ├── services/     ← Lógica de cada plataforma
│   └── models/
├── frontend/         ← Interface HTML/JS
│   ├── index.html
│   ├── css/style.css
│   └── js/app.js
└── start.bat         ← Inicia tudo no Windows
```

## Setup Rápido

### 1. Copie o .env
```bash
cd backend
copy .env.example .env
```

### 2. Preencha as credenciais no `.env`
Cada plataforma precisa de um app criado em seu portal de desenvolvedores:
- **Google**: https://console.cloud.google.com/apis/credentials
- **Meta**: https://developers.facebook.com/apps/
- **TikTok**: https://ads.tiktok.com/marketing_api/apps/
- **Hotmart**: https://developers.hotmart.com/

### 3. Configure os Redirect URIs
Em cada app de desenvolvedor, adicione:
- `http://localhost:8000/auth/google/callback`
- `http://localhost:8000/auth/meta/callback`
- `http://localhost:8000/auth/tiktok/callback`
- `http://localhost:8000/auth/hotmart/callback`

### 4. Inicie o backend
```bash
# Windows
start.bat

# Manual
cd backend
pip install -r requirements.txt
python main.py
```

### 5. Abra o frontend
Acesse: **http://localhost:8000**

## Fluxo do cliente

1. Clica em **Conectar Google Drive** → autoriza com a conta própria
2. Clica em **Conectar Meta Ads** / **Google Ads** / etc.
3. Clica em **Sincronizar** → dados vão para planilhas no Drive do cliente
4. Acessa as planilhas direto pelo link na interface

## APIs utilizadas

| Plataforma | API | Docs |
|---|---|---|
| Google Drive | Drive API v3 | https://developers.google.com/drive |
| Google Sheets | Sheets API v4 | https://developers.google.com/sheets |
| Google Ads | Google Ads API v16 | https://developers.google.com/google-ads/api |
| Meta Ads | Graph API v19 | https://developers.facebook.com/docs/graph-api |
| TikTok Ads | Business API v1.3 | https://ads.tiktok.com/marketing_api/docs |
| Hotmart | Payments API v1 | https://developers.hotmart.com |

## Evoluindo para SaaS

Quando quiser hospedar para múltiplos clientes:
1. Substitua `token_store.py` por banco de dados (PostgreSQL/Supabase)
2. Adicione autenticação de usuário (JWT)
3. Hospede o backend (Railway, Render, AWS)
4. Configure domínio e SSL
