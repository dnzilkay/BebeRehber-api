# BebeRehber API

BebeRehber ebeveyn rehberi uygulamasının backend servisi.

**Ana proje:** [BebeRehber](https://github.com/dnzilkay/BebeRehber)

## Teknolojiler

- Python 3.12
- FastAPI
- PostgreSQL 16
- SQLAlchemy + Alembic
- JWT (kimlik doğrulama)
- Docker + Docker Compose

## Çalıştırma

```bash
git clone https://github.com/dnzilkay/BebeRehber-api.git
cd BebeRehber-api
cp .env.example .env
docker-compose up --build
```

API sağlık kontrolü: <http://localhost:8000/health>
OpenAPI dokümanı: <http://localhost:8000/docs>

## Klasör Yapısı

```
app/
├── main.py           # FastAPI uygulama girişi
├── core/config.py    # Ayarlar (env)
├── models/           # SQLAlchemy modelleri
├── routes/           # API endpoint'leri
└── schemas/          # Pydantic şemaları
tests/                # pytest
```

## Test

```bash
docker-compose exec api pytest
```
