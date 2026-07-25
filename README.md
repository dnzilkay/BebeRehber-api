# BebeRehber API

BebeRehber web, Android ve iOS istemcilerinin kullandığı FastAPI backend'i.

[Ana proje](https://github.com/dnzilkay/BebeRehber) ·
[Canlı ürün vitrini](https://beberehber.dnzilkay.com) ·
[AI kullanım beyanı](AI_USAGE.md)

## Kapsam

API; kimlik doğrulama ve bebek profillerinin yanında aşağıdaki ürün
modüllerini sağlar:

- Uyku, beslenme ve bez bakım kayıtları
- Gelişim kilometre taşları ve hatırlatıcılar
- Albüm, günlük girdileri ve MinIO tabanlı medya yönetimi
- Birleşik timeline ve ZIP veri dışa aktarma
- Kişiselleştirilmiş öneriler ve rehber içerikleri
- Aile üyeliği ve davet bağlantıları
- Topluluk gönderileri, yorumlar ve moderasyon
- Admin ve sosyal medya yönetim uçları

Uygulamada 18 router grubu ve 57 HTTP endpoint'i bulunur. İnteraktif sözleşme
uygulama çalışırken `/docs` üzerinden incelenebilir.

## Teknolojiler

- Python 3.12 ve FastAPI
- PostgreSQL 16
- SQLAlchemy ve Alembic
- JWT tabanlı kimlik doğrulama
- MinIO nesne depolama
- pytest
- Docker ve Docker Compose

## Hızlı başlangıç

Gereksinimler: Docker ve Docker Compose.

```bash
git clone https://github.com/dnzilkay/BebeRehber-api.git
cd BebeRehber-api
cp .env.example .env
docker compose up --build
```

Compose başlangıçta migration'ları uygular ve yerel demo verisini oluşturur.

| Servis | Adres |
|---|---|
| API | `http://localhost:8000` |
| Sağlık kontrolü | `http://localhost:8000/health` |
| OpenAPI/Swagger | `http://localhost:8000/docs` |
| MinIO API | `http://localhost:9000` |
| MinIO Console | `http://localhost:9001` |

## Ortam değişkenleri

Örnek değerler `.env.example` içindedir. Başlıca ayarlar:

| Değişken | Amaç |
|---|---|
| `DATABASE_URL` | PostgreSQL bağlantısı |
| `JWT_SECRET` | Token imzalama anahtarı |
| `CORS_ORIGINS` | İzin verilen istemci adresleri |
| `MINIO_ENDPOINT` | Nesne deposu bağlantısı |
| `MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY` | MinIO kimlik bilgileri |
| `MINIO_BUCKET` / `MINIO_PUBLIC_URL` | Medya bucket'ı ve public taban adresi |

`.env.example` geliştirme içindir. Public veya üretim ortamında varsayılan
parolaları ve `JWT_SECRET` değerini kullanmayın.

## Migration ve test

```bash
# Çalışan api container'ında tüm testler
docker compose exec api pytest

# Migration durumunu uygulama
docker compose exec api alembic upgrade head
```

Mevcut test paketi 16 test dosyasında 147 testi kapsar.

## Proje yapısı

```text
app/
├── core/           # Ayarlar, veritabanı, güvenlik ve medya depolama
├── models/         # SQLAlchemy modelleri
├── routes/         # FastAPI router'ları
├── schemas/        # Pydantic istek/yanıt şemaları
├── cli.py          # Yerel seed komutları
└── main.py         # Uygulama girişi
alembic/            # Veritabanı migration'ları
tests/              # pytest paketi
docker-compose.yml
```

## Yayın notu

Bu repo portföy ve akademik değerlendirme için yayınlanan çalışır bir backend
uygulamasıdır. Sağlık veya gelişim önerileri tıbbi tavsiye olarak
değerlendirilmemelidir. Gerçek kullanıcı verisiyle üretim kullanımı öncesinde
secret yönetimi, rate limiting, gözlemlenebilirlik, yedekleme ve veri saklama
politikaları ayrıca yapılandırılmalıdır.
