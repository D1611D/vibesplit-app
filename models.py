"""
Pydantic data models and schemas for VibeSplit API.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime

# --- User & OTP Models ---
class SendOTPRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=100)
    full_name: Optional[str] = "Friend"

class VerifyOTPRequest(BaseModel):
    email: str
    otp_code: str

class OTPResponse(BaseModel):
    message: str
    email: str
    dev_otp: Optional[str] = None

class UserCreate(BaseModel):
    username: str = Field(..., min_length=2, max_length=30)
    email: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=4)
    full_name: str = Field(..., min_length=1, max_length=50)
    otp_code: Optional[str] = None
    avatar_url: Optional[str] = ""
    persona: Optional[str] = "Boba Baron"
    payment_handle: Optional[str] = ""

class UserLogin(BaseModel):
    username_or_email: str
    password: str

class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    persona: Optional[str] = None
    payment_handle: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: str
    avatar_url: str
    persona: str
    payment_handle: str
    created_at: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# --- Group Models ---
class GroupCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=50)
    description: Optional[str] = ""
    emoji: Optional[str] = "🏖️"
    theme_color: Optional[str] = "violet"
    initial_member_ids: Optional[List[int]] = []

class GroupMemberAdd(BaseModel):
    username_or_email: str
    role: Optional[str] = "member"

class GroupMemberResponse(BaseModel):
    user_id: int
    username: str
    full_name: str
    avatar_url: str
    persona: str
    payment_handle: str
    role: str
    joined_at: str

class GroupResponse(BaseModel):
    id: int
    name: str
    description: str
    emoji: str
    theme_color: str
    created_by_user_id: int
    created_at: str
    member_count: int = 0
    total_expense: float = 0.0
    user_net_balance: float = 0.0


# --- Expense Models ---
class ExpenseSplitInput(BaseModel):
    user_id: int
    owed_amount: float
    split_value: Optional[float] = 1.0  # share weight, percentage or exact

class ExpenseCreate(BaseModel):
    group_id: int
    title: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = ""
    category: Optional[str] = "food"
    amount: float = Field(..., gt=0)
    currency: Optional[str] = "₹"
    paid_by_user_id: int
    split_type: Optional[str] = "equal"  # equal, exact, percentage, shares
    receipt_url: Optional[str] = ""
    splits: List[ExpenseSplitInput]

class ExpenseSplitResponse(BaseModel):
    id: int
    expense_id: int
    user_id: int
    username: str
    full_name: str
    avatar_url: str
    owed_amount: float
    split_value: float
    is_settled: bool
    settled_at: Optional[str] = None
    settled_by_user_id: Optional[int] = None
    settler_name: Optional[str] = None

class ReactionResponse(BaseModel):
    emoji: str
    count: int
    users: List[str]

class ExpenseResponse(BaseModel):
    id: int
    group_id: int
    title: str
    description: str
    category: str
    amount: float
    currency: str
    created_by_user_id: int
    creator_username: str
    creator_name: str
    paid_by_user_id: int
    payer_username: str
    payer_name: str
    split_type: str
    receipt_url: str
    created_at: str
    can_manage: bool = False  # True ONLY if current user is created_by_user_id or paid_by_user_id
    splits: List[ExpenseSplitResponse] = []
    reactions: List[ReactionResponse] = []


# --- Settlement Models ---
class SettlementCreate(BaseModel):
    group_id: int
    to_user_id: int
    amount: float = Field(..., gt=0)
    currency: Optional[str] = "₹"
    payment_method: Optional[str] = "upi"  # upi, venmo, cash, paypal, bank
    notes: Optional[str] = ""

class SettleSplitRequest(BaseModel):
    expense_id: int
    user_id: int

class SettlementResponse(BaseModel):
    id: int
    group_id: int
    from_user_id: int
    from_username: str
    from_name: str
    to_user_id: int
    to_username: str
    to_name: str
    amount: float
    currency: str
    payment_method: str
    notes: str
    created_at: str


# --- Balance & Simplified Debt Graph Models ---
class UserBalance(BaseModel):
    user_id: int
    username: str
    full_name: str
    avatar_url: str
    persona: str
    payment_handle: str
    total_paid: float
    total_owed: float
    net_balance: float

class SimplifiedDebt(BaseModel):
    from_user_id: int
    from_username: str
    from_name: str
    to_user_id: int
    to_username: str
    to_name: str
    to_payment_handle: str
    amount: float
    currency: str = "₹"


# --- AI Features Models ---
class NLPParseRequest(BaseModel):
    prompt: str
    group_id: int

class ParsedSplitSuggestion(BaseModel):
    user_id: int
    username: str
    amount: float

class NLPParseResponse(BaseModel):
    title: str
    amount: float
    category: str
    currency: str = "₹"
    paid_by_user_id: Optional[int] = None
    paid_by_username: Optional[str] = None
    split_type: str = "equal"
    splits: List[ParsedSplitSuggestion] = []
    confidence_score: float = 0.95
    ai_note: str = ""

class RoastToneEnum(str):
    PASSIVE_AGGRESSIVE = "passive_aggressive"
    SAVAGE = "savage"
    CORPORATE = "corporate"
    SWEET = "sweet"
    SHAKESPEARE = "shakespeare"
    HINDI_SLANG = "desi_roast"

class RoastRequest(BaseModel):
    debtor_name: str
    creditor_name: str
    amount: float
    currency: str = "₹"
    expense_title: str
    tone: str = "savage"
    payment_handle: Optional[str] = ""

class RoastResponse(BaseModel):
    roast_text: str
    tone: str
    whatsapp_share_url: str
    telegram_share_url: str
    copy_ready_text: str

class ReceiptItem(BaseModel):
    name: str
    qty: int = 1
    price: float

class ReceiptScanRequest(BaseModel):
    group_id: int
    raw_text: Optional[str] = ""
    receipt_data_url: Optional[str] = ""

class ReceiptScanResponse(BaseModel):
    merchant: str
    date: str
    items: List[ReceiptItem]
    subtotal: float
    tax: float
    tip: float
    total: float
    detected_category: str

class UserVibeBadge(BaseModel):
    user_id: int
    username: str
    badge_title: str
    badge_emoji: str
    description: str

class GroupVibeCheckResponse(BaseModel):
    group_id: int
    group_name: str
    vibe_score: int
    vibe_title: str
    vibe_summary: str
    top_spender: Dict[str, Any]
    frugal_king: Dict[str, Any]
    user_badges: List[UserVibeBadge]
    category_breakdown: Dict[str, float]
    fun_facts: List[str]
