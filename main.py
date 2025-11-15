import os
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import db, create_document, get_documents
from schemas import (
    Resident,
    MaintenanceRequest,
    Payment,
    Notice,
    Asset,
    Reservation,
    Complaint,
    Document,
)

app = FastAPI(title="Apartment Society Management API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "Apartment Society Management API running"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": [],
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = db.name
            response["connection_status"] = "Connected"
            try:
                response["collections"] = db.list_collection_names()[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️ Connected but Error: {str(e)[:80]}"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:80]}"
    return response


# -------------------- Auth (simplified) --------------------
class LoginPayload(BaseModel):
    email: str
    name: Optional[str] = None
    apartment: Optional[str] = None


@app.post("/auth/login")
def login(payload: LoginPayload):
    # For demo: upsert resident by email
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    existing = db["resident"].find_one({"email": payload.email})
    if not existing:
        create_document(
            "resident",
            {
                "name": payload.name or payload.email.split("@")[0],
                "email": payload.email,
                "apartment": payload.apartment or "",
                "role": "resident",
                "share_contact": False,
            },
        )
    return {"ok": True, "email": payload.email}


# -------------------- Maintenance Requests --------------------
@app.post("/maintenance")
def create_ticket(ticket: MaintenanceRequest):
    ticket_id = create_document("maintenancerequest", ticket)
    return {"id": ticket_id}


@app.get("/maintenance")
def list_tickets(status: Optional[str] = None, email: Optional[str] = None):
    q = {}
    if status:
        q["status"] = status
    if email:
        q["requested_by"] = email
    items = get_documents("maintenancerequest", q)
    for it in items:
        it["_id"] = str(it["_id"])  # serialize
    return items


@app.patch("/maintenance/{ticket_id}/status")
def update_ticket_status(ticket_id: str, status: str = Query(..., pattern="^(open|in_progress|resolved|closed)$")):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    res = db["maintenancerequest"].update_one({"_id": __import__("bson").ObjectId(ticket_id)}, {"$set": {"status": status, "updated_at": datetime.utcnow()}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return {"ok": True}


# -------------------- Payments --------------------
@app.post("/payments")
def create_payment(p: Payment):
    pid = create_document("payment", p)
    return {"id": pid}


@app.get("/payments")
def list_payments(email: Optional[str] = None, month: Optional[str] = None, status: Optional[str] = None):
    q = {}
    if email:
        q["user_email"] = email
    if month:
        q["month"] = month
    if status:
        q["status"] = status
    items = get_documents("payment", q)
    for it in items:
        it["_id"] = str(it["_id"])  # serialize
    return items


# -------------------- Notices --------------------
@app.post("/notices")
def create_notice(n: Notice):
    nid = create_document("notice", n)
    return {"id": nid}


@app.get("/notices")
def list_notices(tag: Optional[str] = None):
    q = {"pinned": {"$in": [True, False]}}
    if tag:
        q["tags"] = {"$in": [tag]}
    items = get_documents("notice", q)
    items.sort(key=lambda i: i.get("created_at", datetime.min), reverse=True)
    for it in items:
        it["_id"] = str(it["_id"])  # serialize
    return items


# -------------------- Assets & Reservations --------------------
@app.post("/assets")
def create_asset(a: Asset):
    aid = create_document("asset", a)
    return {"id": aid}


@app.get("/assets")
def list_assets():
    items = get_documents("asset", {})
    for it in items:
        it["_id"] = str(it["_id"])  # serialize
    return items


@app.post("/reservations")
def create_reservation(r: Reservation):
    # Conflict check
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    overlap = db["reservation"].find_one(
        {
            "asset_name": r.asset_name,
            "$or": [
                {"start_time": {"$lt": r.end_time}, "end_time": {"$gt": r.start_time}},
            ],
        }
    )
    if overlap:
        raise HTTPException(status_code=409, detail="Time slot conflicts with existing reservation")
    rid = create_document("reservation", r)
    return {"id": rid}


@app.get("/reservations")
def list_reservations(asset: Optional[str] = None, email: Optional[str] = None):
    q = {}
    if asset:
        q["asset_name"] = asset
    if email:
        q["requested_by"] = email
    items = get_documents("reservation", q)
    for it in items:
        it["_id"] = str(it["_id"])  # serialize
    return items


# -------------------- Complaints & Suggestions --------------------
@app.post("/complaints")
def create_complaint(c: Complaint):
    if c.anonymous:
        data = c.model_dump()
        data.pop("user_email", None)
        cid = create_document("complaint", data)
    else:
        cid = create_document("complaint", c)
    return {"id": cid}


@app.get("/complaints")
def list_complaints(status: Optional[str] = None):
    q = {}
    if status:
        q["status"] = status
    items = get_documents("complaint", q)
    for it in items:
        it["_id"] = str(it["_id"])  # serialize
    return items


# -------------------- Documents --------------------
@app.post("/documents")
def create_doc(d: Document):
    did = create_document("document", d)
    return {"id": did}


@app.get("/documents")
def list_docs(category: Optional[str] = None):
    q = {}
    if category:
        q["category"] = category
    items = get_documents("document", q)
    for it in items:
        it["_id"] = str(it["_id"])  # serialize
    return items


# -------------------- Schema Introspection for Viewer --------------------
@app.get("/schema")
def get_schema_models():
    # For admin tooling to read available collections
    return {
        "collections": [
            "resident",
            "maintenancerequest",
            "payment",
            "notice",
            "asset",
            "reservation",
            "complaint",
            "document",
        ]
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
