"""
Database Schemas for Apartment Society Management System

Each Pydantic model represents a collection in MongoDB. The collection name
is the lowercase of the class name.

Use these models to validate request payloads and structure data.
"""
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime

# -------------------- Users --------------------
class Resident(BaseModel):
    name: str = Field(..., description="Full name")
    email: EmailStr = Field(..., description="Email address")
    apartment: str = Field(..., description="Flat/Apartment number, e.g., A-302")
    phone: Optional[str] = Field(None, description="Contact number")
    role: str = Field("resident", description="Role: resident or admin")
    share_contact: bool = Field(False, description="Allow others to see phone/email in directory")

# -------------------- Maintenance --------------------
class MaintenanceRequest(BaseModel):
    title: str
    description: str
    category: Optional[str] = Field(None, description="Auto-categorized: plumbing, electrical, general, security, cleaning")
    status: str = Field("open", description="open, in_progress, resolved, closed")
    priority: str = Field("medium", description="low, medium, high, urgent")
    requested_by: str = Field(..., description="User id or email of requester")
    assigned_to: Optional[str] = Field(None, description="Assignee (staff name or vendor)")
    apartment: Optional[str] = None
    images: Optional[List[str]] = None  # URLs

# -------------------- Payments --------------------
class Payment(BaseModel):
    user_email: EmailStr
    amount: float
    purpose: str = Field(..., description="maintenance_fee, utility, fine, other")
    month: Optional[str] = Field(None, description="e.g., 2025-11")
    status: str = Field("pending", description="pending, success, failed")
    receipt_no: Optional[str] = None
    remarks: Optional[str] = None

# -------------------- Notices --------------------
class Notice(BaseModel):
    title: str
    body: str
    tags: Optional[List[str]] = None
    attachments: Optional[List[str]] = None  # URLs
    posted_by: str
    pinned: bool = False
    language: Optional[str] = Field("en", description="Language code of body")

# -------------------- Assets & Reservations --------------------
class Asset(BaseModel):
    name: str
    description: Optional[str] = None
    rules: Optional[str] = None

class Reservation(BaseModel):
    asset_name: str
    start_time: datetime
    end_time: datetime
    requested_by: str  # email
    status: str = Field("pending", description="pending, approved, rejected, cancelled")
    purpose: Optional[str] = None

# -------------------- Directory (same as Resident, plus filters) --------------------

# -------------------- Complaints & Suggestions --------------------
class Complaint(BaseModel):
    message: str
    anonymous: bool = False
    user_email: Optional[str] = None
    status: str = Field("open", description="open, acknowledged, responded, closed")
    response: Optional[str] = None

# -------------------- Documents --------------------
class Document(BaseModel):
    title: str
    url: str  # Public link for download
    category: Optional[str] = Field(None, description="bylaws, agreements, template, minutes, other")
    uploaded_by: str

# Note: The Flames database viewer can introspect these at /schema if implemented in backend.
