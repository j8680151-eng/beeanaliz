import os
import io
import re
import json
import secrets
import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, Request, Response, Depends, Cookie
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import barcode
from barcode import Code128
from barcode.writer import SVGWriter

# Paths
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
STORES_DIR = DATA_DIR / "stores"
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
USERS_FILE = DATA_DIR / "users.json"
LEADS_FILE = DATA_DIR / "leads.json"

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
STORES_DIR.mkdir(parents=True, exist_ok=True)
STATIC_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="BeeAnaliz - Do'kon va Kassa Ekotizimi")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------- DATA HELPERS ----------------- #

def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        if default is not None:
            save_json(path, default)
            return default
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default if default is not None else []

def save_json(path: Path, data: Any):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)

def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '_', text)
    return text or "dokon_" + datetime.datetime.now().strftime("%H%M%S")

def get_store_dir(store_slug: str) -> Path:
    store_dir = STORES_DIR / store_slug
    store_dir.mkdir(parents=True, exist_ok=True)
    return store_dir

# Initialize default demo store & user if not exists
def init_system():
    users = load_json(USERS_FILE, [])
    default_store_slug = "baraka_market"
    store_dir = get_store_dir(default_store_slug)
    
    # 1. Default user: 998901234567 / 123456
    if not any(u.get("phone") == "998901234567" for u in users):
        users.append({
            "phone": "998901234567",
            "password": "admin",
            "store_id": default_store_slug,
            "store_name": "Baraka Savdo Markazi",
            "owner_name": "Jaloliddin",
            "token": "demo_token_123"
        })
        save_json(USERS_FILE, users)

    # 2. Default store files
    settings_file = store_dir / "settings.json"
    if not settings_file.exists():
        save_json(settings_file, {
            "id": default_store_slug,
            "name": "Baraka Savdo Markazi",
            "owner_name": "Jaloliddin",
            "phone": "+998 90 123 45 67",
            "address": "Toshkent sh., Chilonzor tumani",
            "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        })

    products_file = store_dir / "products.json"
    if not products_file.exists():
        save_json(products_file, [
            {
                "id": "PRD-101",
                "barcode": "478001001",
                "sku": "PRD-101",
                "name": "Coca-Cola Classic 1.5L",
                "category": "Ichimliklar",
                "costPrice": 9500,
                "sellingPrice": 13000,
                "stock": 48,
                "unit": "dona"
            },
            {
                "id": "PRD-102",
                "barcode": "478001002",
                "sku": "PRD-102",
                "name": "Nestle Sut 3.2% 1L",
                "category": "Sut mahsulotlari",
                "costPrice": 11000,
                "sellingPrice": 14500,
                "stock": 24,
                "unit": "dona"
            },
            {
                "id": "PRD-103",
                "barcode": "478001003",
                "sku": "PRD-103",
                "name": "Makfa Oliy Navli Un 2kg",
                "category": "Baqqollik",
                "costPrice": 16000,
                "sellingPrice": 21000,
                "stock": 35,
                "unit": "dona"
            },
            {
                "id": "PRD-104",
                "barcode": "478001004",
                "sku": "PRD-104",
                "name": "Oq Shakar (Qopda / Kilolab)",
                "category": "Baqqollik",
                "costPrice": 9000,
                "sellingPrice": 11500,
                "stock": 120,
                "unit": "kg"
            },
            {
                "id": "PRD-105",
                "barcode": "478001005",
                "sku": "PRD-105",
                "name": "Kungaboqar Yog'i 'Zolotoe Semechko' 1L",
                "category": "Yog' mahsulotlari",
                "costPrice": 14500,
                "sellingPrice": 18500,
                "stock": 18,
                "unit": "dona"
            }
        ])

    orders_file = store_dir / "orders.json"
    if not orders_file.exists():
        save_json(orders_file, [
            {
                "id": "ORD-595",
                "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                "customerName": "Xaridor",
                "paymentMethod": "NAQD PUL",
                "itemsCount": 5,
                "totalAmount": 65000,
                "profit": 17500,
                "items": [
                    {
                        "name": "Coca-Cola Classic 1.5L",
                        "barcode": "478001001",
                        "quantity": 5,
                        "unit": "dona",
                        "price": 13000,
                        "cost": 9500
                    }
                ]
            }
        ])

    nasiya_file = store_dir / "nasiya.json"
    if not nasiya_file.exists():
        save_json(nasiya_file, [
            {
                "id": "NAS-201",
                "customerName": "Akmal aka (Qo'shni)",
                "phone": "+998 90 321 65 43",
                "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                "dueDate": "2026-09-30",
                "totalAmount": 345000,
                "paidAmount": 100000,
                "remainingDebt": 245000,
                "status": "Qisman to'langan",
                "items": [
                    {"name": "Makfa Oliy Navli Un 2kg", "quantity": 2, "price": 21000}
                ],
                "paymentsHistory": [
                    {"date": "2026-09-19", "amount": 100000, "note": "Avans to'lovi"}
                ]
            }
        ])

    suppliers_file = store_dir / "suppliers.json"
    if not suppliers_file.exists():
        save_json(suppliers_file, [
            {
                "id": "SUP-101",
                "name": "Toshkent Ichimliklar Distribyutsiyasi",
                "contactPerson": "Rustam aka",
                "phone": "+998 90 999 11 22",
                "totalDelivered": 14500000,
                "paidAmount": 11000000,
                "debt": 3500000,
                "lastDelivery": "2026-09-18",
                "paymentsHistory": []
            }
        ])

    expenses_file = store_dir / "expenses.json"
    if not expenses_file.exists():
        save_json(expenses_file, [
            {
                "id": "EXP-101",
                "title": "Do'kon tushlik va choyxona",
                "category": "Tushlik",
                "amount": 55000,
                "date": datetime.date.today().isoformat(),
                "note": "Sotuvchilar tushligi"
            }
        ])

init_system()

# ----------------- SCHEMAS ----------------- #

class LoginRequest(BaseModel):
    phone: str
    password: str

class RegisterRequest(BaseModel):
    store_name: str
    owner_name: str
    phone: str
    password: str
    address: Optional[str] = "O'zbekiston"

class ChangePasswordReq(BaseModel):
    old_password: Optional[str] = None
    new_password: str

class LeadRequest(BaseModel):
    store_name: str
    owner_name: str
    phone: str
    store_type: Optional[str] = "Supermarket"
    note: Optional[str] = ""

class ProductCreateReq(BaseModel):
    barcode: str
    name: str
    sku: Optional[str] = None
    category: Optional[str] = "Umumiy"
    costPrice: float
    sellingPrice: float
    quantity: float
    unit: Optional[str] = "dona"
    supplierId: Optional[str] = None
    paidAmount: Optional[float] = 0.0
    boxBarcode: Optional[str] = None
    boxQuantity: Optional[float] = 1.0
    boxCount: Optional[float] = 0.0
    countryOrigin: Optional[str] = None

def detect_country_by_barcode(code: str) -> str:
    if not code:
        return "Xalqaro standart"
    c = str(code).strip()
    if len(c) >= 3:
        p3 = c[:3]
        if p3 in [str(x) for x in range(690, 700)]:
            return "🇨🇳 Xitoy (GS1)"
        if p3 == "478":
            return "🇺🇿 O'zbekiston"
        if p3 in [str(x) for x in range(460, 470)]:
            return "🇷🇺 Rossiya"
        if p3 in ["868", "869"]:
            return "🇹🇷 Turkiya"
        if p3 == "880":
            return "🇰🇷 Janubiy Koreya"
        if p3 in [str(x) for x in range(500, 510)]:
            return "🇬🇧 Buyuk Britaniya"
        if p3 in [str(x) for x in range(400, 441)]:
            return "🇩🇪 Germaniya"
        if p3 == "481":
            return "🇧🇾 Belarus"
        if p3 == "487":
            return "🇰🇿 Qozog'iston"
        if p3 in [str(x) for x in range(300, 380)]:
            return "🇫🇷 Fransiya"
        if p3 in [str(x) for x in range(800, 840)]:
            return "🇮🇹 Italiya"
        if p3 in [str(x) for x in range(840, 850)]:
            return "🇪🇸 Ispaniya"
        if p3 == "890":
            return "🇮🇳 Hindiston"
        if p3 == "888":
            return "🇸🇬 Singapur"
        if p3 == "885":
            return "🇹🇭 Tailand"
        if p3 == "489":
            return "🇭🇰 Gonkong"
    if len(c) >= 2:
        p2 = c[:2]
        if p2 in [f"{x:02d}" for x in range(0, 14)]:
            return "🇺🇸 AQSh / Kanada"
    return "Xalqaro shtrix-kod"


class RepriceReq(BaseModel):
    sellingPrice: float
    costPrice: Optional[float] = None

class WriteOffReq(BaseModel):
    quantity: float
    reason: str

class CheckoutItem(BaseModel):
    id: Optional[str] = None
    name: str
    barcode: str
    sku: Optional[str] = ""
    quantity: float
    unit: Optional[str] = "dona"
    price: float
    cost: Optional[float] = 0.0

class CheckoutReq(BaseModel):
    paymentType: str
    cashGiven: Optional[float] = 0.0
    cashAmount: Optional[float] = 0.0
    cardAmount: Optional[float] = 0.0
    nasiyaCustomer: Optional[str] = None
    nasiyaPhone: Optional[str] = None
    nasiyaDueDate: Optional[str] = None
    employeeId: Optional[str] = None
    employeeName: Optional[str] = None
    items: List[CheckoutItem]

class EmployeeReq(BaseModel):
    name: str
    phone: Optional[str] = ""
    role: Optional[str] = "Kassir"
    salaryType: Optional[str] = "fixed" # "fixed" (qat'iy oylik) yoki "percent" (savdodan foiz)
    salaryValue: Optional[float] = 0.0
    status: Optional[str] = "Faol"

class EmployeePayoutReq(BaseModel):
    amount: float
    paymentMethod: Optional[str] = "Naqd pul"
    note: Optional[str] = ""

class PayReq(BaseModel):
    amount: float
    note: Optional[str] = ""
    paymentMethod: Optional[str] = "Naqd"

class ExpenseReq(BaseModel):
    title: str
    category: str
    amount: float
    note: Optional[str] = ""

class StoreSettingsReq(BaseModel):
    name: str
    owner_name: Optional[str] = ""
    phone: Optional[str] = ""
    address: Optional[str] = ""
    receipt_footer: Optional[str] = ""

class ReturnItem(BaseModel):
    name: str
    barcode: Optional[str] = ""
    quantity: float
    price: float

class OrderReturnReq(BaseModel):
    orderId: str
    items: List[ReturnItem]
    reason: Optional[str] = "Mijoz qaytardi"
    refundMethod: Optional[str] = "Naqd pul"
    totalRefund: float

# ----------------- AUTHENTICATION ----------------- #

def clean_phone(phone: str) -> str:
    return re.sub(r'\D', '', phone)

def get_current_user(request: Request) -> Optional[Dict[str, Any]]:
    # 1. Try Bearer header
    header_token = request.headers.get("Authorization")
    if header_token and header_token.startswith("Bearer "):
        clean_t = header_token[7:].strip()
        if clean_t and clean_t not in ("undefined", "null", "None", ""):
            users = load_json(USERS_FILE, [])
            for u in users:
                u_tokens = u.get("tokens", [])
                if clean_t == u.get("token") or (isinstance(u_tokens, list) and clean_t in u_tokens):
                    return u

    # 2. Try cookie fallback
    cookie_token = request.cookies.get("bee_token")
    if cookie_token and cookie_token not in ("undefined", "null", "None", ""):
        users = load_json(USERS_FILE, [])
        for u in users:
            u_tokens = u.get("tokens", [])
            if cookie_token == u.get("token") or (isinstance(u_tokens, list) and cookie_token in u_tokens):
                return u

    if header_token or cookie_token:
        print(f"[AUTH REJECTED] header={header_token} cookie={cookie_token}", flush=True)

    return None

def require_user(request: Request) -> Dict[str, Any]:
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Tizimga kirish talab etiladi")
    return user

def require_store(request: Request, store_id: Optional[str] = None) -> str:
    user = require_user(request)
    user_store = user.get("store_id")
    if store_id and store_id != user_store:
        raise HTTPException(status_code=403, detail="Ruxsat berilmagan! Siz faqat o'z do'koningiz ma'lumotlariga kira olasiz.")
    return user_store

@app.post("/api/auth/register")
def auth_register(req: RegisterRequest, response: Response):
    phone_clean = clean_phone(req.phone)
    if not phone_clean or len(phone_clean) < 7:
        raise HTTPException(status_code=400, detail="Telefon raqami noto'g'ri")

    users = load_json(USERS_FILE, [])
    if any(u.get("phone") == phone_clean for u in users):
        raise HTTPException(status_code=400, detail="Ushbu telefon raqami bilan do'kon mavjud! Iltimos, tizimga kiring.")

    slug = slugify(req.store_name)
    store_dir = get_store_dir(slug)
    
    # Store settings
    save_json(store_dir / "settings.json", {
        "id": slug,
        "name": req.store_name.strip(),
        "owner_name": req.owner_name.strip(),
        "phone": req.phone.strip(),
        "address": req.address.strip() if req.address else "O'zbekiston",
        "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    })

    # Empty store files
    save_json(store_dir / "products.json", [])
    save_json(store_dir / "orders.json", [])
    save_json(store_dir / "nasiya.json", [])
    save_json(store_dir / "suppliers.json", [])
    save_json(store_dir / "expenses.json", [])

    token = secrets.token_hex(24)
    user_record = {
        "phone": phone_clean,
        "password": req.password.strip(),
        "store_id": slug,
        "store_name": req.store_name.strip(),
        "owner_name": req.owner_name.strip(),
        "token": token
    }
    users.append(user_record)
    save_json(USERS_FILE, users)

    response.set_cookie(key="bee_token", value=token, max_age=86400*30, httponly=False)
    return {
        "token": token,
        "store_id": slug,
        "store_name": req.store_name.strip(),
        "owner_name": req.owner_name.strip()
    }

@app.post("/api/auth/login")
def auth_login(req: LoginRequest, response: Response):
    phone_clean = clean_phone(req.phone)
    users = load_json(USERS_FILE, [])
    
    user = next((u for u in users if u.get("phone") == phone_clean and u.get("password") == req.password.strip()), None)
    if not user:
        # Fallback check raw
        user = next((u for u in users if (u.get("phone") == req.phone.strip()) and u.get("password") == req.password.strip()), None)

    if not user:
        raise HTTPException(status_code=401, detail="Telefon raqami yoki parol noto'g'ri!")

    token = secrets.token_hex(24)
    raw_tokens = user.get("tokens", [])
    if isinstance(raw_tokens, list):
        tokens = list(raw_tokens)
    else:
        tokens = [user["token"]] if user.get("token") else []
    if user.get("token") and user.get("token") not in tokens:
        tokens.append(user.get("token"))
    if token not in tokens:
        tokens.append(token)
    if len(tokens) > 50:
        tokens = tokens[-50:]
    user["tokens"] = tokens
    user["token"] = token
    save_json(USERS_FILE, users)

    response.set_cookie(key="bee_token", value=token, max_age=86400*30, httponly=False)
    return {
        "token": token,
        "store_id": user["store_id"],
        "store_name": user["store_name"],
        "owner_name": user["owner_name"]
    }

@app.get("/api/auth/me")
def auth_me(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Kirilmagan")
    return {
        "phone": user["phone"],
        "store_id": user["store_id"],
        "store_name": user["store_name"],
        "owner_name": user["owner_name"]
    }

@app.post("/api/auth/logout")
def auth_logout(response: Response):
    response.delete_cookie(key="bee_token")
    return {"message": "Tizimdan chiqildi"}

@app.post("/api/my/change-password")
def change_my_password(req: ChangePasswordReq, request: Request):
    user = require_user(request)
    users = load_json(USERS_FILE, [])
    target = next((u for u in users if u.get("phone") == user.get("phone") or u.get("store_id") == user.get("store_id")), None)
    if not target:
        raise HTTPException(status_code=404, detail="Do'kon foydalanuvchisi topilmadi")
    
    if req.old_password and str(target.get("password", "")).strip() != str(req.old_password).strip():
        raise HTTPException(status_code=400, detail="Hozirgi parol noto'g'ri kiritildi!")

    new_pass = req.new_password.strip()
    if len(new_pass) < 4:
        raise HTTPException(status_code=400, detail="Yangi parol kamida 4 ta belgidan iborat bo'lishi kerak!")

    target["password"] = new_pass
    save_json(USERS_FILE, users)
    return {"message": "Parol muvaffaqiyatli o'zgartirildi! Endi sayt va mobil ilovaga yangi parol orqali kirishingiz mumkin."}


# ----------------- LEADS (Landing Page Inquiry) ----------------- #

@app.post("/api/leads")
def save_lead(req: LeadRequest):
    leads = load_json(LEADS_FILE, [])
    new_lead = {
        "id": f"LEAD-{datetime.datetime.now().strftime('%M%S')}",
        "store_name": req.store_name.strip(),
        "owner_name": req.owner_name.strip(),
        "phone": req.phone.strip(),
        "store_type": req.store_type,
        "note": req.note,
        "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    leads.insert(0, new_lead)
    save_json(LEADS_FILE, leads)
    return {"message": "Arizangiz qabul qilindi! Tez orada mutaxassisimiz siz bilan bog'lanadi."}

# ----------------- STORE APIS ----------------- #

@app.get("/api/stores")
def get_all_stores():
    stores = []
    if STORES_DIR.exists():
        for d in STORES_DIR.iterdir():
            if d.is_dir():
                settings = load_json(d / "settings.json", {"id": d.name, "name": d.name})
                stores.append({
                    "id": d.name,
                    "name": settings.get("name", d.name),
                    "owner_name": settings.get("owner_name", "")
                })
    return stores

@app.get("/api/stores/{store_id}/settings")
def get_store_settings(store_id: str):
    return load_json(get_store_dir(store_id) / "settings.json", {"name": "Do'kon"})

@app.get("/api/stores/{store_id}/products")
def get_products(store_id: str):
    p_file = get_store_dir(store_id) / "products.json"
    return load_json(p_file, [])

@app.post("/api/stores/{store_id}/products/intake")
def intake_product(store_id: str, req: ProductCreateReq):
    store_dir = get_store_dir(store_id)
    p_file = store_dir / "products.json"
    products = load_json(p_file, [])
    
    barcode_clean = req.barcode.strip()
    box_barcode_clean = req.boxBarcode.strip() if req.boxBarcode else ""
    
    box_count = float(req.boxCount or 0.0)
    box_qty = float(req.boxQuantity or 1.0)
    if box_qty <= 0:
        box_qty = 1.0

    if box_count > 0:
        qty = box_count * box_qty
    else:
        qty = float(req.quantity) if req.quantity > 0 else 1.0

    cost = float(req.costPrice) if req.costPrice > 0 else 0.0
    sell = float(req.sellingPrice) if req.sellingPrice > 0 else 0.0
    total_batch_cost = qty * cost
    paid = float(req.paidAmount or 0.0)

    detected_country = req.countryOrigin or detect_country_by_barcode(box_barcode_clean or barcode_clean)

    existing_idx = None
    for i, p in enumerate(products):
        p_bar = str(p.get("barcode", "")).strip()
        p_box = str(p.get("boxBarcode", "")).strip()
        if p_bar == barcode_clean or (box_barcode_clean and (p_box == box_barcode_clean or p_bar == box_barcode_clean)):
            existing_idx = i
            break
    
    if existing_idx is not None:
        target = products[existing_idx]
        target["stock"] = float(target.get("stock", 0)) + qty
        if cost > 0: target["costPrice"] = cost
        if sell > 0: target["sellingPrice"] = sell
        if req.name: target["name"] = req.name.strip()
        if req.unit: target["unit"] = req.unit
        if box_barcode_clean: target["boxBarcode"] = box_barcode_clean
        if box_qty > 1: target["boxQuantity"] = box_qty
        target["countryOrigin"] = detected_country
        products[existing_idx] = target
        saved_product = target
    else:
        new_sku = req.sku.strip() if req.sku else f"PRD-{datetime.datetime.now().strftime('%H%M%S')}"
        saved_product = {
            "id": f"PRD-{datetime.datetime.now().strftime('%M%S%f')[:8]}",
            "barcode": barcode_clean,
            "boxBarcode": box_barcode_clean,
            "boxQuantity": box_qty,
            "countryOrigin": detected_country,
            "sku": new_sku,
            "name": req.name.strip(),
            "category": req.category or "Umumiy",
            "costPrice": cost,
            "sellingPrice": sell,
            "stock": qty,
            "unit": req.unit or "dona"
        }
        products.insert(0, saved_product)

    save_json(p_file, products)

    if req.supplierId:
        s_file = store_dir / "suppliers.json"
        suppliers = load_json(s_file, [])
        for s in suppliers:
            if s.get("id") == req.supplierId:
                s["totalDelivered"] = float(s.get("totalDelivered", 0)) + total_batch_cost
                s["paidAmount"] = float(s.get("paidAmount", 0)) + paid
                s["debt"] = max(0.0, s["totalDelivered"] - s["paidAmount"])
                s["lastDelivery"] = datetime.date.today().isoformat()
                now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                if total_batch_cost > 0:
                    debt_hist = s.setdefault("debtHistory", [])
                    debt_hist.insert(0, {
                        "date": now_str,
                        "productName": saved_product.get("name", ""),
                        "quantity": f"{qty} {saved_product.get('unit', 'dona')}",
                        "amount": total_batch_cost,
                        "note": f"Tovar kirimi: {saved_product.get('name', '')}"
                    })
                if paid > 0:
                    hist = s.setdefault("paymentsHistory", [])
                    hist.insert(0, {
                        "date": now_str,
                        "amount": paid,
                        "paymentMethod": "Naqd",
                        "note": f"Tovar kirimida to'landi ({saved_product.get('name', '')})"
                    })
                break
        save_json(s_file, suppliers)

    return saved_product


@app.post("/api/stores/{store_id}/products/{product_id}/reprice")
def reprice(store_id: str, product_id: str, req: RepriceReq):
    p_file = get_store_dir(store_id) / "products.json"
    products = load_json(p_file, [])
    for p in products:
        if p.get("id") == product_id or p.get("barcode") == product_id:
            p["sellingPrice"] = float(req.sellingPrice)
            if req.costPrice is not None:
                p["costPrice"] = float(req.costPrice)
            save_json(p_file, products)
            return p
    raise HTTPException(status_code=404, detail="Mahsulot topilmadi")

@app.post("/api/stores/{store_id}/products/{product_id}/write-off")
def write_off(store_id: str, product_id: str, req: WriteOffReq):
    store_dir = get_store_dir(store_id)
    p_file = store_dir / "products.json"
    products = load_json(p_file, [])
    
    target = None
    for p in products:
        if p.get("id") == product_id or p.get("barcode") == product_id:
            p["stock"] = max(0.0, float(p.get("stock", 0)) - float(req.quantity))
            target = p
            break
            
    if not target:
        raise HTTPException(status_code=404, detail="Mahsulot topilmadi")
        
    save_json(p_file, products)

    e_file = store_dir / "expenses.json"
    expenses = load_json(e_file, [])
    expenses.insert(0, {
        "id": f"EXP-{datetime.datetime.now().strftime('%H%M%S')}",
        "title": f"Hisobdan chiqarish: {target['name']}",
        "category": "Hisobdan chiqarish",
        "amount": float(target.get("costPrice", 0)) * float(req.quantity),
        "date": datetime.date.today().isoformat(),
        "note": f"{req.quantity} {target.get('unit', 'dona')} hisobdan chiqarildi: {req.reason}"
    })
    save_json(e_file, expenses)

    return {"message": "Hisobdan chiqarildi", "stock": target["stock"]}

@app.post("/api/stores/{store_id}/pos/checkout")
def pos_checkout(store_id: str, req: CheckoutReq):
    if not req.items:
        raise HTTPException(status_code=400, detail="Savat bo'sh")

    store_dir = get_store_dir(store_id)
    p_file = store_dir / "products.json"
    products = load_json(p_file, [])

    total_amount = sum(float(i.price) * float(i.quantity) for i in req.items)
    total_cost = sum(float(i.cost or 0) * float(i.quantity) for i in req.items)
    profit = total_amount - total_cost

    # 1. Strict Stock Validation: prevent selling out-of-stock or exceeding items
    for item in req.items:
        for p in products:
            p_id = str(p.get("id", ""))
            p_bar = str(p.get("barcode", ""))
            p_box = str(p.get("boxBarcode", ""))
            if p_id == item.id or p_bar == item.barcode or (p_box and p_box == item.barcode):
                avail_stock = float(p.get("stock", 0))
                req_qty = float(item.quantity)
                if avail_stock <= 0:
                    raise HTTPException(
                        status_code=400,
                        detail=f"'{p.get('name', 'Tovar')}' omborda tugagan (qoldiq: 0), sotish mumkin emas!"
                    )
                if req_qty > avail_stock:
                    raise HTTPException(
                        status_code=400,
                        detail=f"'{p.get('name', 'Tovar')}' omborda yetarli emas (so'ralgan: {req_qty}, mavjud: {avail_stock})!"
                    )
                break

    for item in req.items:
        for p in products:
            p_id = str(p.get("id", ""))
            p_bar = str(p.get("barcode", ""))
            p_box = str(p.get("boxBarcode", ""))
            if p_id == item.id or p_bar == item.barcode or (p_box and p_box == item.barcode):
                p["stock"] = max(0.0, float(p.get("stock", 0)) - float(item.quantity))
                break
    save_json(p_file, products)

    settings = load_json(store_dir / "settings.json", {})
    store_name_val = settings.get("name", "Do'kon")
    store_phone_val = settings.get("phone", "")
    store_addr_val = settings.get("address", "")
    receipt_footer_val = settings.get("receipt_footer", "")

    req_pay_type = req.paymentType.upper()
    cash_amount = float(req.cashAmount or 0.0)
    card_amount = float(req.cardAmount or 0.0)
    if "ARALASH" in req_pay_type:
        if cash_amount <= 0 and card_amount <= 0:
            cash_amount = total_amount
            card_amount = 0.0
    elif "KARTA" in req_pay_type or "PLASTIK" in req_pay_type:
        card_amount = total_amount
        cash_amount = 0.0
    else:
        cash_amount = total_amount
        card_amount = 0.0

    order_id = f"ORD-{datetime.datetime.now().strftime('%M%S')}"
    order_record = {
        "id": order_id,
        "storeId": store_id,
        "storeName": store_name_val,
        "storePhone": store_phone_val,
        "storeAddress": store_addr_val,
        "receiptFooter": receipt_footer_val,
        "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "customerName": "Xaridor",
        "employeeId": req.employeeId or "",
        "employeeName": req.employeeName or "Bosh Kassir",
        "paymentMethod": req_pay_type,
        "cashAmount": cash_amount,
        "cardAmount": card_amount,
        "cashGiven": float(req.cashGiven or cash_amount),
        "itemsCount": sum(int(i.quantity) for i in req.items),
        "totalAmount": total_amount,
        "profit": profit,
        "items": [
            {
                "name": i.name,
                "barcode": i.barcode,
                "quantity": i.quantity,
                "unit": i.unit,
                "price": i.price,
                "cost": i.cost or 0.0
            }
            for i in req.items
        ]
    }

    # Active smenaga biriktirish
    s_file = store_dir / "shifts.json"
    shifts = load_json(s_file, [])
    active_shift = next((s for s in shifts if s.get("status") == "open"), None)
    if active_shift:
        order_record["shiftId"] = active_shift["id"]
        order_record["shiftNumber"] = active_shift.get("shiftNumber", 1)
        active_shift["totalSales"] = float(active_shift.get("totalSales", 0)) + total_amount
        active_shift["cashSales"] = float(active_shift.get("cashSales", 0)) + cash_amount
        active_shift["cardSales"] = float(active_shift.get("cardSales", 0)) + card_amount
        if "ARALASH" in req_pay_type:
            active_shift["splitSales"] = float(active_shift.get("splitSales", 0)) + total_amount
        active_shift["ordersCount"] = int(active_shift.get("ordersCount", 0)) + 1
        active_shift.setdefault("orders", []).insert(0, order_id)
        save_json(s_file, shifts)

    o_file = store_dir / "orders.json"
    orders = load_json(o_file, [])
    orders.insert(0, order_record)
    save_json(o_file, orders)

    return order_record

@app.get("/api/stores/{store_id}/nasiya")
def get_nasiya(store_id: str):
    return load_json(get_store_dir(store_id) / "nasiya.json", [])

@app.post("/api/stores/{store_id}/nasiya/{nasiya_id}/pay")
def pay_nasiya(store_id: str, nasiya_id: str, req: PayReq):
    n_file = get_store_dir(store_id) / "nasiya.json"
    nasiya_list = load_json(n_file, [])
    for nas in nasiya_list:
        if nas.get("id") == nasiya_id:
            pay_num = float(req.amount)
            nas["paidAmount"] = float(nas.get("paidAmount", 0)) + pay_num
            nas["remainingDebt"] = max(0.0, float(nas.get("remainingDebt", 0)) - pay_num)
            nas["status"] = "To'liq yopilgan" if nas["remainingDebt"] == 0 else "Qisman to'langan"
            hist = nas.setdefault("paymentsHistory", [])
            hist.insert(0, {
                "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                "amount": pay_num,
                "note": req.note or "Qarz to'landi"
            })
            save_json(n_file, nasiya_list)
            return nas
    raise HTTPException(status_code=404, detail="Nasiya topilmadi")

@app.get("/api/stores/{store_id}/suppliers")
def get_suppliers(store_id: str):
    return load_json(get_store_dir(store_id) / "suppliers.json", [])

@app.post("/api/stores/{store_id}/suppliers/{supplier_id}/pay")
def pay_supplier(store_id: str, supplier_id: str, req: PayReq):
    s_file = get_store_dir(store_id) / "suppliers.json"
    suppliers = load_json(s_file, [])
    for sup in suppliers:
        if sup.get("id") == supplier_id:
            pay_num = float(req.amount)
            sup["paidAmount"] = float(sup.get("paidAmount", 0)) + pay_num
            sup["debt"] = max(0.0, float(sup.get("debt", 0)) - pay_num)
            hist = sup.setdefault("paymentsHistory", [])
            hist.insert(0, {
                "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                "amount": pay_num,
                "paymentMethod": req.paymentMethod or "Naqd",
                "note": req.note or "Qarz to'lovi"
            })
            save_json(s_file, suppliers)
            return sup
    raise HTTPException(status_code=404, detail="Ta'minotchi topilmadi")

@app.get("/api/stores/{store_id}/expenses")
def get_expenses(store_id: str):
    return load_json(get_store_dir(store_id) / "expenses.json", [])

@app.post("/api/stores/{store_id}/expenses")
def add_expense(store_id: str, req: ExpenseReq):
    e_file = get_store_dir(store_id) / "expenses.json"
    expenses = load_json(e_file, [])
    new_exp = {
        "id": f"EXP-{datetime.datetime.now().strftime('%H%M%S')}",
        "title": req.title.strip(),
        "category": req.category,
        "amount": float(req.amount),
        "date": datetime.date.today().isoformat(),
        "note": req.note or ""
    }
    expenses.insert(0, new_exp)
    save_json(e_file, expenses)
    return new_exp

@app.get("/api/stores/{store_id}/orders")
def get_orders(store_id: str, month: Optional[str] = None):
    orders = load_json(get_store_dir(store_id) / "orders.json", [])
    if month:
        clean_month = month.strip()
        orders = [o for o in orders if str(o.get("date", "")).startswith(clean_month)]
    return orders

# ----------------- BARCODE COUNTRY DETECT ----------------- #

@app.get("/api/barcode-detect")
def api_barcode_detect(code: str):
    return {
        "code": code,
        "country": detect_country_by_barcode(code)
    }

# ----------------- MY STORE (STRICT TENANT ISOLATION) ----------------- #

@app.get("/api/my/profile")
def get_my_profile(request: Request):
    user = require_user(request)
    store_dir = get_store_dir(user["store_id"])
    settings = load_json(store_dir / "settings.json", {
        "id": user["store_id"],
        "name": user.get("store_name", user["store_id"]),
        "owner_name": user.get("owner_name", ""),
        "phone": user.get("phone", ""),
        "address": "O'zbekiston",
        "receipt_footer": "Xaridingiz uchun rahmat!\nYana kutib qolamiz."
    })
    return {
        "user": user,
        "store": settings
    }

@app.get("/api/my/store/settings")
def get_my_store_settings(request: Request):
    user = require_user(request)
    store_dir = get_store_dir(user["store_id"])
    settings = load_json(store_dir / "settings.json", {
        "id": user["store_id"],
        "name": user.get("store_name", "Do'kon"),
        "owner_name": user.get("owner_name", ""),
        "phone": user.get("phone", ""),
        "address": "",
        "receipt_footer": "Xaridingiz uchun rahmat!\nYana kutib qolamiz."
    })
    return settings

@app.post("/api/my/store/settings")
def update_my_store_settings(req: StoreSettingsReq, request: Request):
    user = require_user(request)
    store_id = user["store_id"]
    store_dir = get_store_dir(store_id)
    settings_file = store_dir / "settings.json"
    settings = load_json(settings_file, {})

    new_name = req.name.strip() if req.name and req.name.strip() else settings.get("name", "Do'kon")
    settings["id"] = store_id
    settings["name"] = new_name
    if req.owner_name is not None:
        settings["owner_name"] = req.owner_name.strip()
    if req.phone is not None:
        settings["phone"] = req.phone.strip()
    if req.address is not None:
        settings["address"] = req.address.strip()
    if req.receipt_footer is not None:
        settings["receipt_footer"] = req.receipt_footer.strip()

    save_json(settings_file, settings)

    # Sync store_name with users.json
    users = load_json(USERS_FILE, [])
    for u in users:
        if u.get("store_id") == store_id:
            u["store_name"] = new_name
            if req.owner_name:
                u["owner_name"] = req.owner_name.strip()
    save_json(USERS_FILE, users)

    return {"message": "Do'kon sozlamalari muvaffaqiyatli saqlandi", "store": settings}

@app.get("/api/my/products")
def get_my_products(request: Request):
    store_id = require_store(request)
    return get_products(store_id)

@app.post("/api/my/products/intake")
def my_intake_product(req: ProductCreateReq, request: Request):
    store_id = require_store(request)
    return intake_product(store_id, req)

@app.post("/api/my/products/{product_id}/reprice")
def my_reprice(product_id: str, req: RepriceReq, request: Request):
    store_id = require_store(request)
    return reprice(store_id, product_id, req)

@app.post("/api/my/products/{product_id}/write-off")
def my_write_off(product_id: str, req: WriteOffReq, request: Request):
    store_id = require_store(request)
    return write_off(store_id, product_id, req)

@app.post("/api/my/pos/checkout")
def my_pos_checkout(req: CheckoutReq, request: Request):
    store_id = require_store(request)
    return pos_checkout(store_id, req)

@app.get("/api/my/nasiya")
def get_my_nasiya(request: Request):
    store_id = require_store(request)
    return get_nasiya(store_id)

@app.post("/api/my/nasiya/{nasiya_id}/pay")
def my_pay_nasiya(nasiya_id: str, req: PayReq, request: Request):
    store_id = require_store(request)
    return pay_nasiya(store_id, nasiya_id, req)

@app.get("/api/my/suppliers")
def get_my_suppliers(request: Request):
    store_id = require_store(request)
    return get_suppliers(store_id)

class SupplierCreateReq(BaseModel):
    name: str
    contactPerson: Optional[str] = ""
    phone: Optional[str] = ""
    products: Optional[str] = ""

class SupplierDebtReq(BaseModel):
    productName: Optional[str] = ""
    quantity: Optional[str] = ""
    amount: float
    note: Optional[str] = ""

@app.post("/api/my/suppliers")
def create_my_supplier(req: SupplierCreateReq, request: Request):
    store_id = require_store(request)
    s_file = get_store_dir(store_id) / "suppliers.json"
    suppliers = load_json(s_file, [])
    new_sup = {
        "id": f"SUP-{datetime.datetime.now().strftime('%H%M%S%f')[:10]}",
        "name": req.name.strip(),
        "contactPerson": (req.contactPerson or "").strip(),
        "phone": (req.phone or "").strip(),
        "products": (req.products or "").strip(),
        "totalDelivered": 0.0,
        "paidAmount": 0.0,
        "debt": 0.0,
        "lastDelivery": "",
        "paymentsHistory": [],
        "debtHistory": []
    }
    suppliers.insert(0, new_sup)
    save_json(s_file, suppliers)
    return new_sup

@app.delete("/api/my/suppliers/{supplier_id}")
def delete_my_supplier(supplier_id: str, request: Request):
    store_id = require_store(request)
    s_file = get_store_dir(store_id) / "suppliers.json"
    suppliers = load_json(s_file, [])
    suppliers = [s for s in suppliers if s.get("id") != supplier_id]
    save_json(s_file, suppliers)
    return {"message": "Ta'minotchi o'chirildi"}

@app.post("/api/my/suppliers/{supplier_id}/add-debt")
def add_debt_to_supplier(supplier_id: str, req: SupplierDebtReq, request: Request):
    store_id = require_store(request)
    s_file = get_store_dir(store_id) / "suppliers.json"
    suppliers = load_json(s_file, [])
    for sup in suppliers:
        if sup.get("id") == supplier_id:
            sup["totalDelivered"] = float(sup.get("totalDelivered", 0)) + req.amount
            sup["debt"] = float(sup.get("debt", 0)) + req.amount
            sup["lastDelivery"] = datetime.date.today().isoformat()
            debt_hist = sup.setdefault("debtHistory", [])
            debt_hist.insert(0, {
                "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                "productName": req.productName or "",
                "quantity": req.quantity or "",
                "amount": req.amount,
                "note": req.note or ""
            })
            save_json(s_file, suppliers)
            return sup
    raise HTTPException(status_code=404, detail="Ta'minotchi topilmadi")

@app.post("/api/my/suppliers/{supplier_id}/pay")
def my_pay_supplier(supplier_id: str, req: PayReq, request: Request):
    store_id = require_store(request)
    return pay_supplier(store_id, supplier_id, req)

@app.get("/api/my/expenses")
def get_my_expenses(request: Request):
    store_id = require_store(request)
    return get_expenses(store_id)

@app.post("/api/my/expenses")
def my_add_expense(req: ExpenseReq, request: Request):
    store_id = require_store(request)
    return add_expense(store_id, req)

@app.get("/api/my/orders")
def get_my_orders(request: Request, month: Optional[str] = None):
    store_id = require_store(request)
    return get_orders(store_id, month)

@app.post("/api/my/orders/{order_id}/return")
def return_order(order_id: str, req: OrderReturnReq, request: Request):
    store_id = require_store(request)
    store_dir = get_store_dir(store_id)
    
    o_file = store_dir / "orders.json"
    orders = load_json(o_file, [])
    
    order = None
    for o in orders:
        if o.get("id") == order_id:
            order = o
            break
            
    if not order:
        raise HTTPException(status_code=404, detail="Buyurtma topilmadi")
        
    # 1. Restock returned items to products
    p_file = store_dir / "products.json"
    products = load_json(p_file, [])
    
    for ret_item in req.items:
        qty_to_return = float(ret_item.quantity)
        if qty_to_return <= 0:
            continue
        # Find product by barcode or name
        for p in products:
            p_bar = str(p.get("barcode", "")).strip()
            ret_bar = str(ret_item.barcode or "").strip()
            if (ret_bar and p_bar == ret_bar) or (p.get("name") == ret_item.name):
                p["stock"] = float(p.get("stock", 0)) + qty_to_return
                break
                
    save_json(p_file, products)
    
    # 2. Update order record
    returns_hist = order.setdefault("returnsHistory", [])
    returns_hist.insert(0, {
        "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "items": [item.dict() for item in req.items],
        "reason": req.reason or "Mijoz qaytardi",
        "refundMethod": req.refundMethod or "Naqd pul",
        "refundAmount": req.totalRefund
    })
    
    total_returned_so_far = float(order.get("returnedAmount", 0)) + float(req.totalRefund)
    order["returnedAmount"] = total_returned_so_far
    
    original_total = float(order.get("totalAmount", 0))
    if total_returned_so_far >= original_total:
        order["status"] = "Qaytarilgan"
    else:
        order["status"] = "Qisman qaytarilgan"
        
    save_json(o_file, orders)
    return {"message": "Tovarlar muvaffaqiyatli qaytarildi va omborga qo'shildi", "order": order}

# ----------------- XODIMLAR & KASSIRLAR APISI ----------------- #

@app.get("/api/my/employees")
def get_my_employees(request: Request):
    store_id = require_store(request)
    e_file = get_store_dir(store_id) / "employees.json"
    employees = load_json(e_file, [])
    if not employees:
        # Default birinchi asosiy kassir
        employees = [
            {
                "id": "EMP-001",
                "name": "Bosh Kassir",
                "phone": "+998 90 000 00 00",
                "role": "Bosh Kassir",
                "salaryType": "fixed",
                "salaryValue": 0.0,
                "status": "Faol",
                "createdAt": datetime.date.today().isoformat()
            }
        ]
        save_json(e_file, employees)
    return employees

@app.post("/api/my/employees")
def create_my_employee(req: EmployeeReq, request: Request):
    store_id = require_store(request)
    e_file = get_store_dir(store_id) / "employees.json"
    employees = load_json(e_file, [])
    new_emp = {
        "id": f"EMP-{datetime.datetime.now().strftime('%H%M%S%f')[:8]}",
        "name": req.name.strip(),
        "phone": (req.phone or "").strip(),
        "role": (req.role or "Kassir").strip(),
        "salaryType": req.salaryType or "fixed",
        "salaryValue": float(req.salaryValue or 0),
        "status": req.status or "Faol",
        "createdAt": datetime.date.today().isoformat()
    }
    employees.insert(0, new_emp)
    save_json(e_file, employees)
    return new_emp

@app.put("/api/my/employees/{employee_id}")
def update_my_employee(employee_id: str, req: EmployeeReq, request: Request):
    store_id = require_store(request)
    e_file = get_store_dir(store_id) / "employees.json"
    employees = load_json(e_file, [])
    for emp in employees:
        if emp.get("id") == employee_id:
            emp["name"] = req.name.strip()
            emp["phone"] = (req.phone or "").strip()
            emp["role"] = (req.role or "Kassir").strip()
            emp["salaryType"] = req.salaryType or "fixed"
            emp["salaryValue"] = float(req.salaryValue or 0)
            emp["status"] = req.status or "Faol"
            save_json(e_file, employees)
            return emp
    raise HTTPException(status_code=404, detail="Xodim topilmadi")

@app.delete("/api/my/employees/{employee_id}")
def delete_my_employee(employee_id: str, request: Request):
    store_id = require_store(request)
    e_file = get_store_dir(store_id) / "employees.json"
    employees = load_json(e_file, [])
    employees = [e for e in employees if e.get("id") != employee_id]
    save_json(e_file, employees)
    return {"message": "Xodim o'chirildi"}

@app.post("/api/my/employees/{employee_id}/payout")
def payout_employee(employee_id: str, req: EmployeePayoutReq, request: Request):
    if req.amount <= 0:
        raise HTTPException(status_code=400, detail="To'lov summasi musbat bo'lishi kerak")
    store_id = require_store(request)
    store_dir = get_store_dir(store_id)
    
    # 1. Update employee payoutsHistory
    e_file = store_dir / "employees.json"
    employees = load_json(e_file, [])
    target_emp = None
    for emp in employees:
        if emp.get("id") == employee_id:
            target_emp = emp
            break
    if not target_emp:
        raise HTTPException(status_code=404, detail="Xodim topilmadi")
        
    payout_record = {
        "id": f"PAY-{datetime.datetime.now().strftime('%M%S%f')[:8]}",
        "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "amount": float(req.amount),
        "paymentMethod": req.paymentMethod or "Naqd pul",
        "note": (req.note or "").strip()
    }
    if "payoutsHistory" not in target_emp or not isinstance(target_emp["payoutsHistory"], list):
        target_emp["payoutsHistory"] = []
    target_emp["payoutsHistory"].insert(0, payout_record)
    save_json(e_file, employees)
    
    # 2. Add to store expenses (deducts from Asosiy Balans & Finans)
    exp_file = store_dir / "expenses.json"
    expenses = load_json(exp_file, [])
    new_exp = {
        "id": f"EXP-{datetime.datetime.now().strftime('%H%M%S')}",
        "title": f"Maosh: {target_emp['name']}",
        "category": "Oylik Maosh",
        "amount": float(req.amount),
        "date": datetime.date.today().isoformat(),
        "note": req.note or f"{target_emp['name']} ({target_emp.get('role', 'Xodim')}) oylik maoshi to'lovi"
    }
    expenses.insert(0, new_exp)
    save_json(exp_file, expenses)
    
    return {"message": "Maosh muvaffaqiyatli to'landi va do'kon hisobidan yechildi", "payout": payout_record, "employee": target_emp}


# ----------------- KASSA SMENASI & Z-HISOBOT (SHIFTS) ----------------- #

class ShiftOpenReq(BaseModel):
    openingCash: float = 0.0
    openedBy: Optional[str] = None
    cashierName: Optional[str] = None
    openedById: Optional[str] = None
    cashierId: Optional[str] = None
    note: Optional[str] = ""

class ShiftCloseReq(BaseModel):
    closingCashActual: Optional[float] = None
    actualCash: Optional[float] = None
    closedBy: Optional[str] = None
    closedByName: Optional[str] = None
    closedById: Optional[str] = None
    note: Optional[str] = ""

def get_shift_details(shift: dict, store_dir: Path) -> dict:
    orders = load_json(store_dir / "orders.json", [])
    shift_id = shift.get("id")
    opened_at = shift.get("openedAt", "")
    closed_at = shift.get("closedAt", "")
    
    shift_orders = []
    for o in orders:
        if o.get("shiftId") == shift_id:
            shift_orders.append(o)
        elif not o.get("shiftId") and opened_at:
            o_date = o.get("date", "")
            if o_date >= opened_at and (not closed_at or o_date <= closed_at):
                shift_orders.append(o)
                
    emp_map = {}
    total_sales = 0.0
    cash_sales = 0.0
    card_sales = 0.0
    split_sales = 0.0
    
    for o in shift_orders:
        emp_id = o.get("employeeId") or "EMP-001"
        emp_name = o.get("employeeName") or "Bosh Kassir"
        tot = float(o.get("totalAmount", 0))
        c_amt = float(o.get("cashAmount", 0))
        k_amt = float(o.get("cardAmount", 0))
        pay = (o.get("paymentMethod") or "").upper()
        
        total_sales += tot
        cash_sales += c_amt
        card_sales += k_amt
        if "ARALASH" in pay or (c_amt > 0 and k_amt > 0):
            split_sales += tot
            
        if emp_id not in emp_map:
            emp_map[emp_id] = {
                "id": emp_id,
                "name": emp_name,
                "ordersCount": 0,
                "totalSales": 0.0,
                "cashSales": 0.0,
                "cardSales": 0.0,
                "splitSales": 0.0
            }
        emp_map[emp_id]["ordersCount"] += 1
        emp_map[emp_id]["totalSales"] += tot
        emp_map[emp_id]["cashSales"] += c_amt
        emp_map[emp_id]["cardSales"] += k_amt
        if "ARALASH" in pay or (c_amt > 0 and k_amt > 0):
            emp_map[emp_id]["splitSales"] += tot

    returns_sum = 0.0
    returns_cnt = 0
    for o in shift_orders:
        for ret in o.get("returnsHistory", []):
            ret_d = ret.get("date", "")
            if not opened_at or (ret_d >= opened_at and (not closed_at or ret_d <= closed_at)):
                returns_sum += float(ret.get("refundAmount", 0))
                returns_cnt += 1

    expenses_sum = 0.0
    exp_file = store_dir / "expenses.json"
    if exp_file.exists():
        expenses = load_json(exp_file, [])
        opened_day = opened_at[:10] if opened_at else ""
        closed_day = closed_at[:10] if closed_at else opened_day
        for ex in expenses:
            ex_date = ex.get("date", "")
            if opened_day and opened_day <= ex_date <= (closed_day or opened_day):
                expenses_sum += float(ex.get("amount", 0))

    opening_cash = float(shift.get("openingCash", 0))
    expected_cash = opening_cash + cash_sales - returns_sum - expenses_sum
    actual_cash = shift.get("closingCashActual")
    cash_diff = (float(actual_cash) - expected_cash) if actual_cash is not None else None

    enriched = dict(shift)
    enriched.update({
        "totalSales": total_sales,
        "cashSales": cash_sales,
        "cardSales": card_sales,
        "splitSales": split_sales,
        "ordersCount": len(shift_orders),
        "returnsAmount": returns_sum,
        "returnsTotal": returns_sum,
        "returnsCount": returns_cnt,
        "expensesAmount": expenses_sum,
        "expensesTotal": expenses_sum,
        "expectedCash": expected_cash,
        "cashDifference": cash_diff,
        "difference": cash_diff,
        "actualCash": float(actual_cash) if actual_cash is not None else None,
        "closingCashActual": float(actual_cash) if actual_cash is not None else None,
        "employees": list(emp_map.values()),
        "orders": [
            {
                "id": o.get("id"),
                "date": o.get("date"),
                "customerName": o.get("customerName", "Xaridor"),
                "employeeName": o.get("employeeName", "Kassir"),
                "paymentMethod": o.get("paymentMethod", "Naqd"),
                "totalAmount": float(o.get("totalAmount", 0)),
                "cashAmount": float(o.get("cashAmount", 0)),
                "cardAmount": float(o.get("cardAmount", 0)),
                "itemsCount": int(o.get("itemsCount", 1))
            }
            for o in shift_orders
        ]
    })
    return enriched

@app.get("/api/my/shifts/current")
def get_current_shift(request: Request):
    store_id = require_store(request)
    store_dir = get_store_dir(store_id)
    s_file = store_dir / "shifts.json"
    shifts = load_json(s_file, [])
    active = next((s for s in shifts if s.get("status") == "open"), None)
    if active:
        return {"active": True, "shift": get_shift_details(active, store_dir)}
    last_shift = shifts[0] if shifts else None
    last_details = get_shift_details(last_shift, store_dir) if last_shift else None
    return {"active": False, "shift": None, "last_shift": last_details}

@app.get("/api/my/shifts")
def get_all_shifts(request: Request, month: Optional[str] = None, date: Optional[str] = None):
    store_id = require_store(request)
    store_dir = get_store_dir(store_id)
    s_file = store_dir / "shifts.json"
    shifts = load_json(s_file, [])
    
    filtered = shifts
    if date:
        filtered = [s for s in filtered if (s.get("openedAt") or "").startswith(date)]
    elif month and month != "all":
        filtered = [s for s in filtered if (s.get("openedAt") or "").startswith(month)]

    result = [get_shift_details(s, store_dir) for s in filtered]
    return result

@app.get("/api/my/shifts/{shift_id}")
def get_single_shift(shift_id: str, request: Request):
    store_id = require_store(request)
    store_dir = get_store_dir(store_id)
    s_file = store_dir / "shifts.json"
    shifts = load_json(s_file, [])
    target = next((s for s in shifts if s.get("id") == shift_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="Smena topilmadi")
    return get_shift_details(target, store_dir)

@app.post("/api/my/shifts/open")
def open_shift(req: ShiftOpenReq, request: Request):
    store_id = require_store(request)
    store_dir = get_store_dir(store_id)
    s_file = store_dir / "shifts.json"
    shifts = load_json(s_file, [])
    
    active = next((s for s in shifts if s.get("status") == "open"), None)
    if active:
        raise HTTPException(status_code=400, detail=f"Smena #{active.get('shiftNumber', 1)} allaqachon ochiq! Avval uni yoping.")
        
    next_num = max((s.get("shiftNumber", 0) for s in shifts), default=0) + 1
    shift_id = f"SMN-{next_num:04d}"
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    
    new_shift = {
        "id": shift_id,
        "shiftNumber": next_num,
        "status": "open",
        "openedAt": now_str,
        "openedBy": (req.openedBy or req.cashierName or "Bosh Kassir").strip(),
        "openedById": req.openedById or req.cashierId or "",
        "openingCash": float(req.openingCash or 0.0),
        "closedAt": None,
        "closedBy": None,
        "closedById": None,
        "closingCashActual": None,
        "expectedCash": float(req.openingCash or 0.0),
        "cashDifference": 0.0,
        "totalSales": 0.0,
        "cashSales": 0.0,
        "cardSales": 0.0,
        "splitSales": 0.0,
        "ordersCount": 0,
        "returnsCount": 0,
        "returnsAmount": 0.0,
        "expensesAmount": 0.0,
        "note": (req.note or "").strip(),
        "orders": []
    }
    shifts.insert(0, new_shift)
    save_json(s_file, shifts)
    return get_shift_details(new_shift, store_dir)

@app.post("/api/my/shifts/close")
def close_shift(req: ShiftCloseReq, request: Request):
    store_id = require_store(request)
    store_dir = get_store_dir(store_id)
    s_file = store_dir / "shifts.json"
    shifts = load_json(s_file, [])
    
    active = next((s for s in shifts if s.get("status") == "open"), None)
    if not active:
        raise HTTPException(status_code=400, detail="Hozirda yopish uchun ochiq smena topilmadi")
        
    # Recalculate full stats up to now
    enriched = get_shift_details(active, store_dir)
    cash_val = req.closingCashActual if req.closingCashActual is not None else req.actualCash
    closing_actual = float(cash_val or 0.0)
    expected_c = enriched["expectedCash"]
    diff = closing_actual - expected_c
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    
    active["closedAt"] = now_str
    active["closedBy"] = (req.closedBy or req.closedByName or "Bosh Kassir").strip()
    active["closedById"] = req.closedById or ""
    active["closingCashActual"] = closing_actual
    active["expectedCash"] = expected_c
    active["cashDifference"] = diff
    active["totalSales"] = enriched["totalSales"]
    active["cashSales"] = enriched["cashSales"]
    active["cardSales"] = enriched["cardSales"]
    active["splitSales"] = enriched["splitSales"]
    active["ordersCount"] = enriched["ordersCount"]
    active["returnsAmount"] = enriched["returnsAmount"]
    active["returnsCount"] = enriched["returnsCount"]
    active["expensesAmount"] = enriched["expensesAmount"]
    active["status"] = "closed"
    active["closeNote"] = (req.note or "").strip()
    
    save_json(s_file, shifts)
    return get_shift_details(active, store_dir)

@app.post("/api/my/shifts/{shift_id}/reopen")
def reopen_shift(shift_id: str, request: Request):
    store_id = require_store(request)
    store_dir = get_store_dir(store_id)
    s_file = store_dir / "shifts.json"
    shifts = load_json(s_file, [])
    
    active = next((s for s in shifts if s.get("status") == "open" and s.get("id") != shift_id), None)
    if active:
        raise HTTPException(status_code=400, detail=f"Boshqa smena #{active.get('shiftNumber', 1)} ochiq turibdi! Avval uni yoping.")
        
    target = next((s for s in shifts if s.get("id") == shift_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="Smena topilmadi")
        
    target["status"] = "open"
    target["closedAt"] = None
    target["closingCashActual"] = None
    target["cashDifference"] = None
    save_json(s_file, shifts)
    return get_shift_details(target, store_dir)

@app.get("/api/my/shifts/{shift_id}/z-report", response_class=HTMLResponse)
def get_z_report_html(shift_id: str, request: Request):
    store_id = require_store(request)
    store_dir = get_store_dir(store_id)
    s_file = store_dir / "shifts.json"
    shifts = load_json(s_file, [])
    target = next((s for s in shifts if s.get("id") == shift_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="Smena topilmadi")
        
    data = get_shift_details(target, store_dir)
    settings = load_json(store_dir / "settings.json", {})
    store_name = settings.get("name") or "Do'kon"
    phone_str = settings.get("phone", "")
    address_str = settings.get("address", "")
    
    diff_val = data.get("cashDifference") or 0.0
    if abs(diff_val) < 1:
        diff_text = "0 so'm (ANIQ)"
        diff_color = "#059669"
    elif diff_val < 0:
        diff_text = f"{abs(diff_val):,.0f} so'm (KAMOMAD)"
        diff_color = "#dc2626"
    else:
        diff_text = f"+{diff_val:,.0f} so'm (ORTIQCHA)"
        diff_color = "#2563eb"
        
    emp_rows = ""
    for idx, emp in enumerate(data.get("employees", [])):
        emp_rows += f"""
        <div style="display: flex; justify-content: space-between; font-size: 11px; padding: 2px 0;">
            <span>{idx+1}. {emp['name']} ({emp.get('ordersCount', 0)} chek)</span>
            <span style="font-weight: bold;">{float(emp.get('totalSales', 0)):,.0f} so'm</span>
        </div>
        """
    if not emp_rows:
        emp_rows = "<div style='font-size: 10px; color: #888;'>Savdo qilinmagan</div>"
        
    html = f"""
    <!DOCTYPE html>
    <html lang="uz">
    <head>
        <meta charset="utf-8">
        <title>Z-Hisobot #{data.get('shiftNumber', 1)}</title>
        <style>
            @page {{ margin: 0; size: 80mm auto; }}
            * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: monospace, sans-serif; color: #000; }}
            body {{ background: #fff; width: 80mm; padding: 5mm; margin: 0 auto; font-size: 12px; }}
            .center {{ text-align: center; }}
            .dashed {{ border-top: 1px dashed #000; margin: 6px 0; }}
            .row {{ display: flex; justify-content: space-between; margin: 2px 0; font-size: 11px; }}
            .bold {{ font-weight: bold; }}
            .title {{ font-size: 15px; font-weight: 900; text-transform: uppercase; margin-bottom: 2px; }}
            .sub {{ font-size: 10px; color: #555; }}
            .badge {{ font-size: 12px; font-weight: bold; padding: 4px; background: #eee; text-align: center; margin: 6px 0; }}
        </style>
    </head>
    <body onload="window.print()">
        <div class="center">
            <div class="title">{store_name}</div>
            <div class="sub">{phone_str} {('• ' + address_str) if address_str else ''}</div>
            <div class="badge">*** KASSA Z-HISOBOTI ***</div>
            <div style="font-size: 13px; font-weight: 900;">SMENA #{data.get('shiftNumber', 1)}</div>
        </div>

        <div class="dashed"></div>
        <div class="row"><span>Holat:</span><span class="bold">{'YOPILGAN' if data.get('status') == 'closed' else 'OCHIQ (FAOL)'}</span></div>
        <div class="row"><span>Ochilgan vaqti:</span><span>{data.get('openedAt', '-')}</span></div>
        <div class="row"><span>Ochgan xodim:</span><span class="bold">{data.get('openedBy', '-')}</span></div>
        <div class="row"><span>Yopilgan vaqti:</span><span>{data.get('closedAt', 'Hozirgi vaqt')}</span></div>
        <div class="row"><span>Yopgan xodim:</span><span class="bold">{data.get('closedBy', '-')}</span></div>

        <div class="dashed"></div>
        <div class="row"><span>Boshlang'ich kassa:</span><span class="bold">{float(data.get('openingCash', 0)):,.0f} so'm</span></div>
        <div class="row bold" style="font-size: 12px; margin-top: 4px;">
            <span>JAMI SAVDO TUSHUMI:</span>
            <span>{float(data.get('totalSales', 0)):,.0f} so'm</span>
        </div>
        <div class="row" style="padding-left: 8px;"><span>- Naqd tushum:</span><span>{float(data.get('cashSales', 0)):,.0f} so'm</span></div>
        <div class="row" style="padding-left: 8px;"><span>- Karta tushum:</span><span>{float(data.get('cardSales', 0)):,.0f} so'm</span></div>
        <div class="row" style="padding-left: 8px;"><span>- Aralash savdolar:</span><span>{float(data.get('splitSales', 0)):,.0f} so'm</span></div>
        <div class="row"><span>Jami cheklar soni:</span><span class="bold">{data.get('ordersCount', 0)} ta</span></div>
        <div class="row"><span>Vozvrat (qaytarish):</span><span>-{float(data.get('returnsAmount', 0)):,.0f} so'm</span></div>
        <div class="row"><span>Chiqimlar (xarajat):</span><span>-{float(data.get('expensesAmount', 0)):,.0f} so'm</span></div>

        <div class="dashed"></div>
        <div class="row"><span>Kassada kutilgan naqd:</span><span class="bold">{float(data.get('expectedCash', 0)):,.0f} so'm</span></div>
        <div class="row"><span>Haqiqiy sanalgan naqd:</span><span class="bold">{float(data.get('closingCashActual') or data.get('expectedCash') or 0):,.0f} so'm</span></div>
        <div class="row bold" style="font-size: 12px; color: {diff_color}; margin-top: 2px;">
            <span>KASSA FARQI:</span>
            <span>{diff_text}</span>
        </div>

        <div class="dashed"></div>
        <div style="font-size: 11px; font-weight: bold; margin-bottom: 4px;">XODIMLAR BO'YICHA SAVDO:</div>
        {emp_rows}

        <div class="dashed"></div>
        <div class="center sub" style="margin-top: 6px;">
            <div>Chop etildi: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
            <div style="margin-top: 2px;">BeeAnaliz POS Tizimi</div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


# ----------------- PRINTING (SHTRIX-KOD & CHEK) ----------------- #

LABEL_SIZES = {
    "58x40": {
        "title": "58 x 40 mm (Standart Etiketka)",
        "page_size": "58mm 40mm",
        "width_mm": 58,
        "height_mm": 40,
        "is_tape": False,
        "padding": "2mm 2.5mm",
        "name_font_size": "13px",
        "name_line_height": "1.15",
        "name_max_lines": 2,
        "svg_height": "18mm",
        "svg_width": "92%",
        "num_font_size": "13px",
        "num_letter_spacing": "2.5px",
    },
    "58x30": {
        "title": "58 x 30 mm (Ixcham Etiketka)",
        "page_size": "58mm 30mm",
        "width_mm": 58,
        "height_mm": 30,
        "is_tape": False,
        "padding": "1.5mm 2mm",
        "name_font_size": "11.5px",
        "name_line_height": "1.1",
        "name_max_lines": 1,
        "svg_height": "13.5mm",
        "svg_width": "90%",
        "num_font_size": "11.5px",
        "num_letter_spacing": "2px",
    },
    "40x30": {
        "title": "40 x 30 mm (Kichik Etiketka)",
        "page_size": "40mm 30mm",
        "width_mm": 40,
        "height_mm": 30,
        "is_tape": False,
        "padding": "1.2mm 1.5mm",
        "name_font_size": "10px",
        "name_line_height": "1.1",
        "name_max_lines": 1,
        "svg_height": "12.5mm",
        "svg_width": "92%",
        "num_font_size": "10.5px",
        "num_letter_spacing": "1.5px",
    },
    "50x30": {
        "title": "50 x 30 mm (O'rta Etiketka)",
        "page_size": "50mm 30mm",
        "width_mm": 50,
        "height_mm": 30,
        "is_tape": False,
        "padding": "1.5mm 2mm",
        "name_font_size": "11px",
        "name_line_height": "1.1",
        "name_max_lines": 1,
        "svg_height": "13.5mm",
        "svg_width": "92%",
        "num_font_size": "11px",
        "num_letter_spacing": "2px",
    },
    "58x60": {
        "title": "58 x 60 mm (Katta Etiketka)",
        "page_size": "58mm 60mm",
        "width_mm": 58,
        "height_mm": 60,
        "is_tape": False,
        "padding": "3mm 3mm",
        "name_font_size": "14px",
        "name_line_height": "1.2",
        "name_max_lines": 2,
        "svg_height": "28mm",
        "svg_width": "94%",
        "num_font_size": "14px",
        "num_letter_spacing": "3px",
    },
    "58tape": {
        "title": "58 mm Chek Lentasi (Uzluksiz)",
        "page_size": "58mm auto",
        "width_mm": 58,
        "height_mm": 0,
        "is_tape": True,
        "padding": "2.5mm 2mm",
        "name_font_size": "12px",
        "name_line_height": "1.15",
        "name_max_lines": 2,
        "svg_height": "16mm",
        "svg_width": "90%",
        "num_font_size": "12px",
        "num_letter_spacing": "2px",
    }
}

def make_crisp_barcode_svg(code_str: str) -> str:
    """
    Termoprinterlar va skanerlar (telefon kamerasi / lazer skaner) uchun 
    100% to'g'ri, kesilmagan, to'g'ri proporsiyali va o'qiluvchan Code128 SVG generatsiyasi.
    """
    clean_code = str(code_str).strip()
    if not clean_code:
        return "<div style='font-family: monospace; font-size: 11px;'>[KOD YO'Q]</div>"
    try:
        fp = io.BytesIO()
        code_obj = Code128(clean_code, writer=SVGWriter())
        # quiet_zone: 6.0mm (oq bo'shliq skaner tanishi uchun shart)
        # module_width: 0.35mm
        # module_height: 18.0mm
        code_obj.write(fp, options={
            'write_text': False,
            'quiet_zone': 6.0,
            'module_height': 18.0,
            'module_width': 0.35,
            'margin_top': 0.8,
            'margin_bottom': 0.8
        })
        raw_svg = fp.getvalue().decode('utf-8')
        
        w_match = re.search(r'width="([0-9\.]+)mm"', raw_svg)
        h_match = re.search(r'height="([0-9\.]+)mm"', raw_svg)
        w = float(w_match.group(1)) if w_match else 40.0
        h = float(h_match.group(1)) if h_match else 20.0
        
        svg_clean = re.sub(r'<\?xml[^>]*\?>', '', raw_svg)
        svg_clean = re.sub(r'<!DOCTYPE[^>]*>', '', svg_clean).strip()
        # MUHIM: Ichki koordinatalardan 'mm' ni olib tashlash (chunki viewBox birliksiz)
        svg_clean = re.sub(r'([0-9\.]+)mm', r'\1', svg_clean)
        
        svg_clean = re.sub(
            r'<svg[^>]*>',
            f'<svg viewBox="0 0 {w} {h}" preserveAspectRatio="xMidYMid meet" style="width: 100%; height: 100%; shape-rendering: crispEdges; display: block;" xmlns="http://www.w3.org/2000/svg">',
            svg_clean,
            count=1
        )
        svg_clean = svg_clean.replace('style="fill:black;"', 'style="fill:#000000; shape-rendering: crispEdges;"')
        svg_clean = svg_clean.replace('style="fill:white"', 'style="fill:#ffffff;"')
        return svg_clean
    except Exception:
        return "<div style='font-family: monospace; letter-spacing: 2px; font-weight: bold;'>||||||||||||||||</div>"

@app.get("/api/barcode-svg/{code}")
def get_barcode_svg(code: str):
    svg = make_crisp_barcode_svg(code)
    return Response(content=svg, media_type="image/svg+xml")

@app.get("/api/barcode-print", response_class=HTMLResponse)
def print_barcode(
    name: str, 
    barcode_num: str, 
    size: str = "58x40", 
    copies: int = 1,
    auto_print: int = 1
):
    """
    Termoprinterlar (Xprinter, Rongta, HPRT, POS-58) uchun mukammallashtirilgan shtrix-kod chop etish sahifasi.
    Foydalanuvchi talabi: faqat tovar nomi, |||||| chiziqlari va shtrix raqami.
    """
    clean_code = str(barcode_num).strip()
    clean_name = str(name).strip() or "Mahsulot"
    copies_count = max(1, min(int(copies), 200))
    
    cfg = LABEL_SIZES.get(size, LABEL_SIZES["58x40"])
    svg_markup = make_crisp_barcode_svg(clean_code)
    
    # Options for sizes dropdown
    size_options_html = ""
    for k, v in LABEL_SIZES.items():
        sel = "selected" if k == size else ""
        size_options_html += f'<option value="{k}" {sel}>{v["title"]}</option>'
    
    # Stikerlar HTML blokini tayyorlash
    stickers_html = ""
    for i in range(copies_count):
        tape_class = "tape-sticker" if cfg["is_tape"] else "label-sticker"
        stickers_html += f"""
        <div class="sticker {tape_class}">
            <div class="prod-name" title="{clean_name}">{clean_name}</div>
            <div class="barcode-wrapper">
                {svg_markup}
            </div>
            <div class="prod-number">{clean_code}</div>
        </div>
        """

    html = f"""<!DOCTYPE html>
<html lang="uz">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{clean_name} - Shtrix-kod ({cfg['title']})</title>
    <style>
        /* Standart sahifa va printer parametrlari */
        @page {{
            size: {cfg['page_size']};
            margin: 0mm;
        }}
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            -webkit-print-color-adjust: exact !important;
            print-color-adjust: exact !important;
        }}
        body {{
            background: #f1f5f9;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
            color: #000;
            display: flex;
            flex-direction: column;
            align-items: center;
        }}

        /* Faqat ekranda ko'rinadigan qulay asboblar paneli */
        .no-print-toolbar {{
            width: 100%;
            max-width: 650px;
            background: #ffffff;
            border: 1px solid #cbd5e1;
            border-radius: 16px;
            padding: 14px 20px;
            margin: 16px auto;
            box-shadow: 0 10px 25px -5px rgba(0,0,0,0.1);
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            font-family: inherit;
        }}
        .toolbar-group {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .toolbar-group label {{
            font-size: 12px;
            font-weight: 700;
            color: #334155;
        }}
        .toolbar-select, .toolbar-input {{
            padding: 6px 10px;
            border-radius: 8px;
            border: 1.5px solid #cbd5e1;
            font-size: 12px;
            font-weight: 600;
            background: #f8fafc;
            color: #0f172a;
            outline: none;
        }}
        .toolbar-btn-print {{
            background: #f59e0b;
            color: #000;
            border: none;
            padding: 8px 16px;
            border-radius: 10px;
            font-size: 12px;
            font-weight: 900;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            box-shadow: 0 4px 10px rgba(245, 158, 11, 0.3);
            transition: all 0.15s ease;
        }}
        .toolbar-btn-print:hover {{
            background: #d97706;
            color: #fff;
        }}
        .toolbar-tip {{
            width: 100%;
            font-size: 11px;
            color: #64748b;
            border-top: 1px solid #f1f5f9;
            padding-top: 8px;
            margin-top: 2px;
        }}

        /* Qog'oz / Stiker konteyneri */
        .print-container {{
            display: flex;
            flex-direction: column;
            align-items: center;
        }}

        /* Har bir yorliq stikeri */
        .sticker {{
            background: #ffffff;
            width: {cfg['width_mm']}mm;
            {f"height: {cfg['height_mm']}mm; max-height: {cfg['height_mm']}mm;" if not cfg["is_tape"] else "min-height: 35mm;"}
            padding: {cfg['padding']};
            box-sizing: border-box;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            align-items: center;
            text-align: center;
            overflow: hidden;
            border: 1px dashed #cbd5e1;
            margin-bottom: 8px;
            page-break-after: always;
            break-after: page;
        }}
        .sticker:last-child {{
            page-break-after: avoid;
            break-after: avoid;
            margin-bottom: 0;
        }}
        .tape-sticker {{
            border-bottom: 1.5px dashed #000000;
            padding-bottom: 3mm;
            margin-bottom: 2mm;
        }}

        /* 1. Tovar Nomi */
        .prod-name {{
            font-size: {cfg['name_font_size']};
            font-weight: 800;
            line-height: {cfg['name_line_height']};
            max-width: 100%;
            color: #000000;
            text-transform: uppercase;
            overflow: hidden;
            display: -webkit-box;
            -webkit-line-clamp: {cfg['name_max_lines']};
            -webkit-box-orient: vertical;
            word-break: break-word;
        }}

        /* 2. Shtrix-kod |||||| chiziqlari */
        .barcode-wrapper {{
            width: {cfg['svg_width']};
            height: {cfg['svg_height']};
            display: flex;
            justify-content: center;
            align-items: center;
            margin: 1mm 0;
            overflow: hidden;
        }}
        .barcode-wrapper svg {{
            width: 100%;
            height: 100%;
            display: block;
            shape-rendering: crispEdges;
        }}

        /* 3. Shtrix raqami */
        .prod-number {{
            font-size: {cfg['num_font_size']};
            font-weight: 900;
            font-family: "Courier New", Courier, monospace, monospace;
            letter-spacing: {cfg['num_letter_spacing']};
            color: #000000;
            white-space: nowrap;
        }}

        /* CHOP ETISH HOLATI (@media print) */
        @media print {{
            body {{
                background: #ffffff !important;
                margin: 0 !important;
                padding: 0 !important;
                width: {cfg['width_mm']}mm !important;
            }}
            .no-print, .no-print-toolbar {{
                display: none !important;
            }}
            .sticker {{
                border: none !important;
                margin: 0 !important;
                box-shadow: none !important;
                width: {cfg['width_mm']}mm !important;
                {f"height: {cfg['height_mm']}mm !important; max-height: {cfg['height_mm']}mm !important;" if not cfg["is_tape"] else ""}
                page-break-after: always !important;
                break-after: page !important;
            }}
            .sticker:last-child {{
                page-break-after: avoid !important;
                break-after: avoid !important;
            }}
            .tape-sticker {{
                border-bottom: 1px dashed #000 !important;
            }}
        }}
    </style>
</head>
<body>

    <!-- Ekranda boshqaruv paneli -->
    <div class="no-print-toolbar no-print">
        <div class="toolbar-group">
            <label for="sizeSelect">O'lcham:</label>
            <select id="sizeSelect" class="toolbar-select" onchange="changeLabelSize(this.value)">
                {size_options_html}
            </select>
        </div>

        <div class="toolbar-group">
            <label for="copiesInput">Nusxalar soni:</label>
            <input type="number" id="copiesInput" class="toolbar-input" min="1" max="100" value="{copies_count}" style="width: 60px;" onchange="changeCopies(this.value)">
        </div>

        <div class="toolbar-group">
            <button onclick="window.print()" class="toolbar-btn-print">
                <span>🖨️ Chop Etish</span>
            </button>
        </div>

        <div class="toolbar-tip">
            💡 <b>Maslahat:</b> Termoprinter uchun brauzer chop etish drayverida <b>Margins: None (Hoshiyasiz)</b> va <b>Headers & footers: O'chiq</b> qiling.
        </div>
    </div>

    <!-- Chop etiladigan stikerlar ro'yxati -->
    <div class="print-container">
        {stickers_html}
    </div>

    <script>
        // Tanlangan stiker o'lchamini eslab qolish
        try {{
            localStorage.setItem('be_preferred_label_size', '{size}');
        }} catch(e) {{}}

        function changeLabelSize(newSize) {{
            const url = new URL(window.location.href);
            url.searchParams.set('size', newSize);
            url.searchParams.set('auto_print', '0');
            window.location.href = url.toString();
        }}

        function changeCopies(val) {{
            const c = parseInt(val) || 1;
            const url = new URL(window.location.href);
            url.searchParams.set('copies', Math.max(1, Math.min(c, 100)));
            url.searchParams.set('auto_print', '0');
            window.location.href = url.toString();
        }}

        // Agar auto_print=1 bo'lsa, printer dialogini ochish
        if ({str(auto_print).lower() == '1' or auto_print == 1}) {{
            window.addEventListener('load', () => {{
                setTimeout(() => {{
                    window.print();
                }}, 300);
            }});
        }}
    </script>
</body>
</html>
"""
    return HTMLResponse(content=html)

@app.get("/api/receipt-print", response_class=HTMLResponse)
def print_receipt(store_id: str = "", order_id: str = ""):
    order = None
    target_store_dir = None

    # 1. Store ID orqali buyurtmani qidirish
    if store_id and str(store_id).strip() not in ("null", "undefined", ""):
        candidate_dir = get_store_dir(store_id)
        if (candidate_dir / "orders.json").exists():
            orders = load_json(candidate_dir / "orders.json", [])
            order = next((o for o in orders if str(o.get("id")) == str(order_id)), None)
            if order:
                target_store_dir = candidate_dir

    # 2. Agar topilmasa, barcha do'konlar papkasidan qidirish (Avtomatik do'konni aniqlash)
    if not order:
        if STORES_DIR.exists():
            for d in STORES_DIR.iterdir():
                if d.is_dir() and (d / "orders.json").exists():
                    orders = load_json(d / "orders.json", [])
                    order = next((o for o in orders if str(o.get("id")) == str(order_id)), None)
                    if order:
                        target_store_dir = d
                        store_id = d.name
                        break

    if not order:
        raise HTTPException(status_code=404, detail="Chek topilmadi")

    # Do'kon sozlamalarini yuklash
    settings = {}
    if target_store_dir:
        settings = load_json(target_store_dir / "settings.json", {})

    # Har bir do'konning o'ziga xos nomi: settings.name -> order.storeName -> users.json -> Do'kon
    store_name_str = settings.get("name") or order.get("storeName")
    if not store_name_str:
        users = load_json(USERS_FILE, [])
        u = next((u for u in users if u.get("store_id") == store_id), None)
        store_name_str = u.get("store_name") if u else "Do'kon"

    phone_str = settings.get("phone") or order.get("storePhone", "")
    address_str = settings.get("address") or order.get("storeAddress", "")
    footer_text = settings.get("receipt_footer") or order.get("receiptFooter") or "Xaridingiz uchun rahmat!\nYana kutib qolamiz."

    items_html = ""
    for idx, it in enumerate(order.get("items", [])):
        q = float(it.get("quantity", 1))
        p = float(it.get("price", 0))
        total = q * p
        barcode_str = it.get("barcode", "-")
        unit_str = it.get("unit", "dona")
        it_name = it.get("name", "Tovar")
        items_html += f"""
        <div style="border-bottom: 1px dashed #ccc; padding: 4px 0;">
            <div style="display: flex; justify-content: space-between; font-weight: bold; font-size: 11px;">
                <span>{idx+1}. {it_name}</span>
                <span>{total:,.0f} so'm</span>
            </div>
            <div style="display: flex; justify-content: space-between; font-size: 10px; color: #444; font-family: monospace;">
                <span>Shtrix: {barcode_str}</span>
                <span>{q} {unit_str} x {p:,.0f} so'm</span>
            </div>
        </div>
        """

    order_id_str = str(order.get("id", "Chek"))
    order_date_str = str(order.get("date", ""))
    customer_name_str = str(order.get("customerName", "Xaridor"))
    employee_name_str = str(order.get("employeeName", "Kassir"))
    total_amount_str = f"{float(order.get('totalAmount', 0)):,.0f} so'm"
    payment_method_str = str(order.get("paymentMethod", "Naqd pul")).upper()
    cash_val = float(order.get("cashAmount") or 0.0)
    card_val = float(order.get("cardAmount") or 0.0)

    split_html = ""
    if "ARALASH" in payment_method_str or (cash_val > 0 and card_val > 0):
        split_html = f"""
        <div style="font-size: 11px; margin-top: 4px; padding-top: 4px; border-top: 1px dotted #888;">
            <div style="display: flex; justify-content: space-between; font-weight: bold;">
                <span>💵 Naqd pul:</span>
                <span>{cash_val:,.0f} so'm</span>
            </div>
            <div style="display: flex; justify-content: space-between; font-weight: bold; margin-top: 2px;">
                <span>💳 Plastik karta:</span>
                <span>{card_val:,.0f} so'm</span>
            </div>
        </div>
        """

    contact_html = ""
    if phone_str or address_str:
        parts = []
        if phone_str: parts.append(f"Tel: {phone_str}")
        if address_str: parts.append(address_str)
        contact_html = f"""<div style="font-size: 10px; color: #444; margin-top: 2px;">{' | '.join(parts)}</div>"""

    footer_lines = footer_text.split('\n')
    footer_line_1 = footer_lines[0] if len(footer_lines) > 0 else "Xaridingiz uchun rahmat!"
    footer_line_2 = footer_lines[1] if len(footer_lines) > 1 else "Yana kutib qolamiz."

    html = f"""
    <!DOCTYPE html>
    <html lang="uz">
    <head>
        <meta charset="utf-8">
        <title>Chek #{order_id_str}</title>
        <style>
            @page {{
                margin: 0;
                size: 80mm auto;
            }}
            * {{
                box-sizing: border-box;
                margin: 0;
                padding: 0;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                color: #000;
            }}
            body {{
                background: #fff;
                width: 80mm;
                padding: 5mm;
                margin: 0 auto;
                font-size: 12px;
            }}
            .header {{
                text-align: center;
                border-bottom: 1px dashed #000;
                padding-bottom: 6px;
                margin-bottom: 6px;
            }}
            .store-name {{
                font-size: 14px;
                font-weight: 900;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            .total-box {{
                display: flex;
                justify-content: space-between;
                font-size: 14px;
                font-weight: 900;
                border-top: 1px dashed #000;
                border-bottom: 1px dashed #000;
                padding: 6px 0;
                margin: 8px 0;
            }}
            .footer {{
                text-align: center;
                font-size: 11px;
                font-weight: bold;
                margin-top: 8px;
            }}
        </style>
    </head>
    <body onload="window.print()">
        <div class="header">
            <div class="store-name">{store_name_str}</div>
            {contact_html}
            <div style="font-size: 10px; color: #555; margin-top: 2px;">Kassir: {employee_name_str}</div>
            <div style="font-size: 10px; font-weight: bold; margin-top: 2px;">Sana: {order_date_str}</div>
            <div style="font-size: 10px;">Chek: #{order_id_str} | Xaridor: {customer_name_str}</div>
        </div>
        <div>{items_html}</div>
        <div class="total-box">
            <span>TO'LANGAN:</span>
            <span>{total_amount_str}</span>
        </div>
        <div style="font-size: 11px; display: flex; justify-content: space-between;">
            <span>To'lov usuli:</span>
            <span style="font-weight: bold;">{payment_method_str}</span>
        </div>
        {split_html}
        <div class="footer">
            <div>{footer_line_1}</div>
            <div style="font-size: 9px; font-weight: normal; color: #666; margin-top: 2px;">{footer_line_2}</div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)

try:
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
except Exception as e:
    print(f"StaticFiles mount warning: {e}")

# 1. Asosiy sahifa (Landing Page)
@app.get("/", response_class=HTMLResponse)
def page_landing():
    landing_file = TEMPLATES_DIR / "landing.html"
    if not landing_file.exists():
        return HTMLResponse("<h1>BeeAnaliz Asosiy Sahifa yuklanmoqda...</h1>")
    with open(landing_file, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

# 2. Login & Ro'yxatdan o'tish sahifasi
@app.get("/login", response_class=HTMLResponse)
def page_login():
    login_file = TEMPLATES_DIR / "login.html"
    if not login_file.exists():
        return HTMLResponse("<h1>Login sahifasi yuklanmoqda...</h1>")
    with open(login_file, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

# 3. Sotuvchi Dashboardi (Kabinet)
@app.get("/dashboard", response_class=HTMLResponse)
def page_dashboard(request: Request):
    dashboard_file = TEMPLATES_DIR / "dashboard.html"
    if not dashboard_file.exists():
        return HTMLResponse("<h1>Sotuvchi Dashboardi yuklanmoqda...</h1>")
    with open(dashboard_file, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

if __name__ == "__main__":
    import uvicorn
    print("BeeAnaliz 100% Python Server ishga tushirilmoqda...")
    print("Manzil: http://localhost:5000")
    uvicorn.run("app:app", host="0.0.0.0", port=5000, reload=True)
