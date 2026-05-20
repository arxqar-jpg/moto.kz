from __future__ import annotations

import os
import secrets
import shutil
from datetime import datetime
from hashlib import pbkdf2_hmac
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, Response, UploadFile, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import and_, desc, func, select
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from .database import Base, SessionLocal, engine, get_db
from .models import Favorite, Listing, Payment, User

APP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = APP_DIR.parent
UPLOAD_DIR = PROJECT_ROOT / "static" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

LISTING_FEE_KZT = 990
KASPI_PAY_URL = "https://kaspi.kz/pay/DUMKUniversla?subservice_id=10840&region_id=19&started_from=share"
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")

app = FastAPI(title="Moto KZ Prototype")
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)
app.mount("/static", StaticFiles(directory=str(PROJECT_ROOT / "static")), name="static")
templates = Jinja2Templates(directory=str(PROJECT_ROOT / "templates"))


# ---------- helpers ----------

def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000)
    return f"pbkdf2_sha256${salt}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, salt, _digest = stored_hash.split("$", 2)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    return secrets.compare_digest(hash_password(password, salt), stored_hash)


def current_user(request: Request, db: Session) -> Optional[User]:
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return db.get(User, int(user_id))


def require_user(request: Request, db: Session = Depends(get_db)) -> User:
    user = current_user(request, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/login"})
    return user


def flash(request: Request, message: str, kind: str = "success") -> None:
    request.session["flash"] = {"message": message, "kind": kind}


def pop_flash(request: Request) -> dict | None:
    value = request.session.get("flash")
    if value:
        del request.session["flash"]
    return value


def render(request: Request, name: str, context: dict, db: Session) -> HTMLResponse:
    context.update({
        "request": request,
        "user": current_user(request, db),
        "flash": pop_flash(request),
        "listing_fee": LISTING_FEE_KZT,
        "kaspi_pay_url": KASPI_PAY_URL,
    })
    return templates.TemplateResponse(name, context)


def redirect(path: str) -> RedirectResponse:
    return RedirectResponse(path, status_code=status.HTTP_303_SEE_OTHER)


def save_upload(file: UploadFile | None) -> str | None:
    if not file or not file.filename:
        return None
    suffix = Path(file.filename).suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        raise HTTPException(status_code=400, detail="Тек image файл жүктеңіз: jpg, png, webp, gif")
    filename = f"{secrets.token_hex(12)}{suffix}"
    destination = UPLOAD_DIR / filename
    with destination.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return f"/static/uploads/{filename}"


def get_listing_or_404(db: Session, listing_id: int) -> Listing:
    listing = db.get(Listing, listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Объявление табылмады")
    return listing


def listing_to_dict(listing: Listing) -> dict:
    return {
        "id": listing.id,
        "title": listing.title,
        "brand": listing.brand,
        "model": listing.model,
        "year": listing.year,
        "price": listing.price,
        "mileage": listing.mileage,
        "city": listing.city,
        "body_type": listing.body_type,
        "fuel": listing.fuel,
        "transmission": listing.transmission,
        "engine_volume": listing.engine_volume,
        "color": listing.color,
        "phone": listing.phone,
        "description": listing.description,
        "image_path": listing.image_path,
        "is_paid": listing.is_paid,
        "is_active": listing.is_active,
        "created_at": listing.created_at.isoformat(),
    }


def seed_data() -> None:
    db = SessionLocal()
    try:
        has_any = db.scalar(select(func.count(Listing.id)))
        if has_any:
            return
        demo_user = User(name="Moto KZ Demo", email="demo@motokz.kz", password_hash=hash_password("demo12345"))
        db.add(demo_user)
        db.flush()
        demo_listings = [
            Listing(
                owner_id=demo_user.id,
                title="Toyota Camry 70, идеал состояние",
                brand="Toyota",
                model="Camry",
                year=2020,
                price=14_900_000,
                mileage=78_000,
                city="Алматы",
                body_type="Седан",
                fuel="Бензин",
                transmission="Автомат",
                engine_volume="2.5",
                color="Қара",
                phone="+7 777 111 22 33",
                description="Без ДТП, родной окрас, салон таза. Торг бар.",
                image_path=None,
                is_paid=True,
                is_active=True,
            ),
            Listing(
                owner_id=demo_user.id,
                title="Hyundai Tucson 2021, 4WD",
                brand="Hyundai",
                model="Tucson",
                year=2021,
                price=13_700_000,
                mileage=52_000,
                city="Астана",
                body_type="Кроссовер",
                fuel="Бензин",
                transmission="Автомат",
                engine_volume="2.0",
                color="Ақ",
                phone="+7 701 555 66 77",
                description="Қыстық/жаздық резина бар. Техосмотр өткен.",
                image_path=None,
                is_paid=True,
                is_active=True,
            ),
            Listing(
                owner_id=demo_user.id,
                title="Lexus RX 350 Premium",
                brand="Lexus",
                model="RX 350",
                year=2018,
                price=19_500_000,
                mileage=96_000,
                city="Шымкент",
                body_type="Кроссовер",
                fuel="Бензин",
                transmission="Автомат",
                engine_volume="3.5",
                color="Күміс",
                phone="+7 747 888 99 00",
                description="Америка емес, дилерлік. Комплектация Premium.",
                image_path=None,
                is_paid=True,
                is_active=True,
            ),
        ]
        db.add_all(demo_listings)
        db.commit()
    finally:
        db.close()


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    seed_data()


# ---------- pages ----------

@app.get("/", response_class=HTMLResponse)
def home(
    request: Request,
    brand: str = "",
    model: str = "",
    city: str = "",
    min_price: str = "",
    max_price: str = "",
    fuel: str = "",
    transmission: str = "",
    sort: str = "new",
    db: Session = Depends(get_db),
):
    query = select(Listing).where(and_(Listing.is_active.is_(True), Listing.is_paid.is_(True)))
    if brand:
        query = query.where(Listing.brand.ilike(f"%{brand}%"))
    if model:
        query = query.where(Listing.model.ilike(f"%{model}%"))
    if city:
        query = query.where(Listing.city.ilike(f"%{city}%"))
    if fuel:
        query = query.where(Listing.fuel == fuel)
    if transmission:
        query = query.where(Listing.transmission == transmission)
    if min_price.isdigit():
        query = query.where(Listing.price >= int(min_price))
    if max_price.isdigit():
        query = query.where(Listing.price <= int(max_price))

    if sort == "price_asc":
        query = query.order_by(Listing.price.asc())
    elif sort == "price_desc":
        query = query.order_by(Listing.price.desc())
    elif sort == "year_desc":
        query = query.order_by(Listing.year.desc())
    else:
        query = query.order_by(desc(Listing.created_at))

    listings = db.scalars(query).all()
    user = current_user(request, db)
    favorite_ids = set()
    if user:
        favorite_ids = set(db.scalars(select(Favorite.listing_id).where(Favorite.user_id == user.id)).all())

    return render(request, "home.html", {
        "listings": listings,
        "favorite_ids": favorite_ids,
        "filters": {
            "brand": brand,
            "model": model,
            "city": city,
            "min_price": min_price,
            "max_price": max_price,
            "fuel": fuel,
            "transmission": transmission,
            "sort": sort,
        },
    }, db)


@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request, db: Session = Depends(get_db)):
    return render(request, "register.html", {}, db)


@app.post("/register")
def register(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    email = email.strip().lower()
    if len(password) < 6:
        flash(request, "Пароль кемі 6 символ болу керек", "error")
        return redirect("/register")
    exists = db.scalar(select(User).where(User.email == email))
    if exists:
        flash(request, "Бұл email бұрын тіркелген", "error")
        return redirect("/register")
    user = User(name=name.strip(), email=email, password_hash=hash_password(password))
    db.add(user)
    db.commit()
    request.session["user_id"] = user.id
    flash(request, "Аккаунт ашылды. Енді объявление қоса аласыз.")
    return redirect("/listings/new")


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request, db: Session = Depends(get_db)):
    return render(request, "login.html", {}, db)


@app.post("/login")
def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.scalar(select(User).where(User.email == email.strip().lower()))
    if not user or not verify_password(password, user.password_hash):
        flash(request, "Email немесе пароль қате", "error")
        return redirect("/login")
    request.session["user_id"] = user.id
    flash(request, "Кірдіңіз")
    return redirect("/")


@app.post("/logout")
def logout(request: Request):
    request.session.clear()
    return redirect("/")


@app.get("/listings/new", response_class=HTMLResponse)
def new_listing_page(request: Request, db: Session = Depends(get_db), user: User = Depends(require_user)):
    return render(request, "listing_form.html", {"listing": None, "mode": "create"}, db)


@app.post("/listings")
def create_listing(
    request: Request,
    title: str = Form(...),
    brand: str = Form(...),
    model: str = Form(...),
    year: int = Form(...),
    price: int = Form(...),
    mileage: int = Form(0),
    city: str = Form(...),
    body_type: str = Form(...),
    fuel: str = Form(...),
    transmission: str = Form(...),
    engine_volume: str = Form(...),
    color: str = Form(...),
    phone: str = Form(...),
    description: str = Form(""),
    image: UploadFile = File(None),
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    if not (1950 <= year <= datetime.utcnow().year + 1):
        flash(request, "Жылды дұрыс енгізіңіз", "error")
        return redirect("/listings/new")
    if price <= 0:
        flash(request, "Баға 0-ден үлкен болу керек", "error")
        return redirect("/listings/new")
    image_path = save_upload(image)
    listing = Listing(
        owner_id=user.id,
        title=title.strip(),
        brand=brand.strip(),
        model=model.strip(),
        year=year,
        price=price,
        mileage=max(mileage, 0),
        city=city.strip(),
        body_type=body_type,
        fuel=fuel,
        transmission=transmission,
        engine_volume=engine_volume.strip(),
        color=color.strip(),
        phone=phone.strip(),
        description=description.strip(),
        image_path=image_path,
        is_paid=False,
        is_active=False,
    )
    db.add(listing)
    db.commit()
    flash(request, "Объявление сақталды. Жариялау үшін demo төлем жасаңыз.")
    return redirect(f"/payments/{listing.id}")


@app.get("/listings/{listing_id}", response_class=HTMLResponse)
def listing_detail(request: Request, listing_id: int, db: Session = Depends(get_db)):
    listing = get_listing_or_404(db, listing_id)
    user = current_user(request, db)
    if not listing.is_active and (not user or listing.owner_id != user.id):
        raise HTTPException(status_code=404, detail="Объявление жарияланбаған")
    is_favorite = False
    if user:
        is_favorite = db.scalar(select(Favorite).where(Favorite.user_id == user.id, Favorite.listing_id == listing.id)) is not None
    return render(request, "listing_detail.html", {"listing": listing, "is_favorite": is_favorite}, db)


@app.get("/my-listings", response_class=HTMLResponse)
def my_listings(request: Request, db: Session = Depends(get_db), user: User = Depends(require_user)):
    listings = db.scalars(select(Listing).where(Listing.owner_id == user.id).order_by(desc(Listing.created_at))).all()
    return render(request, "my_listings.html", {"listings": listings}, db)


@app.get("/listings/{listing_id}/edit", response_class=HTMLResponse)
def edit_listing_page(request: Request, listing_id: int, db: Session = Depends(get_db), user: User = Depends(require_user)):
    listing = get_listing_or_404(db, listing_id)
    if listing.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Бұл сіздің объявление емес")
    return render(request, "listing_form.html", {"listing": listing, "mode": "edit"}, db)


@app.post("/listings/{listing_id}/edit")
def update_listing(
    request: Request,
    listing_id: int,
    title: str = Form(...),
    brand: str = Form(...),
    model: str = Form(...),
    year: int = Form(...),
    price: int = Form(...),
    mileage: int = Form(0),
    city: str = Form(...),
    body_type: str = Form(...),
    fuel: str = Form(...),
    transmission: str = Form(...),
    engine_volume: str = Form(...),
    color: str = Form(...),
    phone: str = Form(...),
    description: str = Form(""),
    image: UploadFile = File(None),
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    listing = get_listing_or_404(db, listing_id)
    if listing.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Бұл сіздің объявление емес")
    listing.title = title.strip()
    listing.brand = brand.strip()
    listing.model = model.strip()
    listing.year = year
    listing.price = price
    listing.mileage = max(mileage, 0)
    listing.city = city.strip()
    listing.body_type = body_type
    listing.fuel = fuel
    listing.transmission = transmission
    listing.engine_volume = engine_volume.strip()
    listing.color = color.strip()
    listing.phone = phone.strip()
    listing.description = description.strip()
    uploaded = save_upload(image)
    if uploaded:
        listing.image_path = uploaded
    db.commit()
    flash(request, "Объявление жаңартылды")
    return redirect(f"/listings/{listing.id}")


@app.post("/listings/{listing_id}/delete")
def delete_listing(request: Request, listing_id: int, db: Session = Depends(get_db), user: User = Depends(require_user)):
    listing = get_listing_or_404(db, listing_id)
    if listing.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Бұл сіздің объявление емес")
    db.delete(listing)
    db.commit()
    flash(request, "Объявление өшірілді")
    return redirect("/my-listings")


@app.post("/listings/{listing_id}/favorite")
def toggle_favorite(request: Request, listing_id: int, db: Session = Depends(get_db), user: User = Depends(require_user)):
    listing = get_listing_or_404(db, listing_id)
    favorite = db.scalar(select(Favorite).where(Favorite.user_id == user.id, Favorite.listing_id == listing.id))
    if favorite:
        db.delete(favorite)
        flash(request, "Избранноеден алынды")
    else:
        db.add(Favorite(user_id=user.id, listing_id=listing.id))
        flash(request, "Избранноеге қосылды")
    db.commit()
    return redirect(request.headers.get("referer") or f"/listings/{listing.id}")


@app.get("/favorites", response_class=HTMLResponse)
def favorites_page(request: Request, db: Session = Depends(get_db), user: User = Depends(require_user)):
    favorites = db.scalars(select(Favorite).where(Favorite.user_id == user.id).order_by(desc(Favorite.created_at))).all()
    listings = [fav.listing for fav in favorites]
    favorite_ids = {listing.id for listing in listings}
    return render(request, "home.html", {
        "listings": listings,
        "favorite_ids": favorite_ids,
        "filters": {},
        "page_title": "Избранное",
    }, db)


@app.get("/payments/{listing_id}", response_class=HTMLResponse)
def payment_page(request: Request, listing_id: int, db: Session = Depends(get_db), user: User = Depends(require_user)):
    listing = get_listing_or_404(db, listing_id)
    if listing.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Бұл сіздің объявление емес")
    return render(request, "payment.html", {"listing": listing}, db)


@app.post("/payments/{listing_id}")
def pay_for_listing(
    request: Request,
    listing_id: int,
    payment_method: str = Form("kaspi"),
    kaspi_receipt: str = Form(""),
    card_number: str | None = Form(None),
    card_name: str | None = Form(None),
    expiry: str | None = Form(None),
    cvc: str | None = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    listing = get_listing_or_404(db, listing_id)
    if listing.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Бұл сіздің объявление емес")

    provider = "kaspi-link-demo"
    if payment_method == "card":
        cleaned_card = (card_number or "").replace(" ", "")
        if len(cleaned_card) < 12 or not cleaned_card.isdigit() or len(cvc or "") < 3:
            flash(request, "Demo карта деректері дұрыс емес", "error")
            return redirect(f"/payments/{listing.id}")
        provider = "demo-card"
    else:
        # Prototype mode: the user pays via the external Kaspi link/QR and confirms it here.
        # In production this must be replaced with Kaspi merchant status verification/webhook.
        provider = "kaspi-qr-demo" if not kaspi_receipt.strip() else "kaspi-receipt-demo"

    payment = Payment(user_id=user.id, listing_id=listing.id, amount=LISTING_FEE_KZT, status="paid", provider=provider)
    listing.is_paid = True
    listing.is_active = True
    db.add(payment)
    db.commit()
    flash(request, "Kaspi төлемі расталды. Объявление жарияланды!")
    return redirect(f"/listings/{listing.id}")


@app.get("/api/listings")
def api_listings(db: Session = Depends(get_db)):
    listings = db.scalars(select(Listing).where(Listing.is_active.is_(True), Listing.is_paid.is_(True)).order_by(desc(Listing.created_at))).all()
    return JSONResponse([listing_to_dict(item) for item in listings])


@app.get("/health")
def health():
    return {"status": "ok"}
