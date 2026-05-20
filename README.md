# MotoKZ — Auto Marketplace Prototype

Python/FastAPI backend-пен жасалған авто сатып алу/сату прототипі.

## Features

- Register / Login / Logout
- Авто объявление қосу, өңдеу, өшіру
- Фото upload
- Каталог, search, filters, sorting
- Detail page + seller phone reveal
- Favorites
- Seller dashboard
- Kaspi Pay link + QR payment flow
- Demo card fallback
- REST API: `/api/listings`
- Premium animated UI: glass navbar, hero car SVG, hover tilt, magnetic buttons, reveal animations

## Run

```bash
cd moto-kz-prototype
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Windows:

```bat
run_windows.bat
```

Open:

```text
http://127.0.0.1:8000
```

## Demo account

```text
Email: demo@motokz.kz
Password: demo12345
```

## Kaspi payment link

```text
https://kaspi.kz/pay/DUMKUniversla?subservice_id=10840&region_id=19&started_from=share
```

Prototype mode: external Kaspi payment status is not automatically verified. After paying, user returns to the site and clicks “Төледім — объявлениені жариялау”. Production requires Kaspi merchant API/webhook/status validation.
