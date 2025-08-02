from sqlmodel import SQLModel, Field, Relationship, JSON, Column
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any
from enum import Enum


# Enums for better type safety
class UserRole(str, Enum):
    ADMIN = "admin"  # Chefão - full access
    MANAGER = "manager"  # OG team with restricted permissions
    EXPERT = "expert"  # Expert partner with own business panel


class ExpertStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    SUSPENDED = "suspended"


class CostCategory(str, Enum):
    MARKETING = "marketing"
    OPERATIONS = "operations"
    TECHNOLOGY = "technology"
    SUPPORT = "support"
    OTHER = "other"


class TransactionType(str, Enum):
    SALE = "sale"
    REFUND = "refund"
    ADJUSTMENT = "adjustment"


# Persistent models (stored in database)
class User(SQLModel, table=True):
    __tablename__ = "users"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, max_length=255, regex=r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
    password_hash: str = Field(max_length=255)
    name: str = Field(max_length=100)
    role: UserRole = Field(default=UserRole.EXPERT)
    is_active: bool = Field(default=True)
    permissions: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))  # Module-based permissions for managers
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    expert_business: Optional["Expert"] = Relationship(back_populates="owner")
    created_experts: List["Expert"] = Relationship(
        back_populates="created_by", sa_relationship_kwargs={"foreign_keys": "Expert.created_by_id"}
    )
    created_costs: List["OperationalCost"] = Relationship(back_populates="created_by")


class Expert(SQLModel, table=True):
    __tablename__ = "experts"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    business_name: str = Field(max_length=200)
    expert_name: str = Field(max_length=100)
    email: str = Field(max_length=255)
    phone: Optional[str] = Field(default=None, max_length=20)
    status: ExpertStatus = Field(default=ExpertStatus.PENDING)
    partnership_start_date: datetime = Field(default_factory=datetime.utcnow)
    revenue_split_percentage: Decimal = Field(
        default=Decimal("50.0"), max_digits=5, decimal_places=2
    )  # Expert's percentage

    # Contact and business info
    business_description: Optional[str] = Field(default=None, max_length=1000)
    website: Optional[str] = Field(default=None, max_length=255)
    social_media: Dict[str, str] = Field(default={}, sa_column=Column(JSON))  # {platform: url}

    # Multi-tenant configuration
    subdomain: Optional[str] = Field(default=None, max_length=50, unique=True)  # For dedicated panels
    branding_config: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))  # Colors, logos, etc.

    # Foreign keys
    owner_id: Optional[int] = Field(default=None, foreign_key="users.id")
    created_by_id: int = Field(foreign_key="users.id")

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    owner: Optional[User] = Relationship(
        back_populates="expert_business", sa_relationship_kwargs={"foreign_keys": "Expert.owner_id"}
    )
    created_by: User = Relationship(
        back_populates="created_experts", sa_relationship_kwargs={"foreign_keys": "Expert.created_by_id"}
    )
    sales: List["Sale"] = Relationship(back_populates="expert")
    operational_costs: List["OperationalCost"] = Relationship(back_populates="expert")
    financial_reports: List["FinancialReport"] = Relationship(back_populates="expert")


class Sale(SQLModel, table=True):
    __tablename__ = "sales"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    expert_id: int = Field(foreign_key="experts.id")

    # Transaction details
    transaction_type: TransactionType = Field(default=TransactionType.SALE)
    gross_amount: Decimal = Field(max_digits=12, decimal_places=2)
    net_amount: Decimal = Field(max_digits=12, decimal_places=2)  # After platform fees, etc.

    # Product/service details
    product_name: Optional[str] = Field(default=None, max_length=200)
    product_category: Optional[str] = Field(default=None, max_length=100)
    quantity: int = Field(default=1)

    # Customer info (anonymized for privacy)
    customer_id: Optional[str] = Field(default=None, max_length=100)  # External platform customer ID
    customer_country: Optional[str] = Field(default=None, max_length=3)  # ISO country code

    # Timestamps
    sale_date: datetime = Field(default_factory=datetime.utcnow)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationship
    expert: Expert = Relationship(back_populates="sales")


class OperationalCost(SQLModel, table=True):
    __tablename__ = "operational_costs"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    expert_id: int = Field(foreign_key="experts.id")
    created_by_id: int = Field(foreign_key="users.id")

    # Cost details
    category: CostCategory
    description: str = Field(max_length=500)
    amount: Decimal = Field(max_digits=12, decimal_places=2)

    # Period information
    cost_date: datetime = Field(default_factory=datetime.utcnow)
    is_recurring: bool = Field(default=False)
    recurring_frequency: Optional[str] = Field(default=None, max_length=20)  # monthly, weekly, etc.

    # Additional metadata
    external_reference: Optional[str] = Field(default=None, max_length=100)  # Invoice number, etc.
    notes: Optional[str] = Field(default=None, max_length=1000)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    expert: Expert = Relationship(back_populates="operational_costs")
    created_by: User = Relationship(back_populates="created_costs")


class FinancialReport(SQLModel, table=True):
    __tablename__ = "financial_reports"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    expert_id: int = Field(foreign_key="experts.id")

    # Report period
    period_start: datetime
    period_end: datetime
    report_type: str = Field(max_length=50)  # monthly, quarterly, yearly

    # Financial metrics
    gross_revenue: Decimal = Field(max_digits=15, decimal_places=2)
    total_costs: Decimal = Field(max_digits=15, decimal_places=2)
    net_profit: Decimal = Field(max_digits=15, decimal_places=2)
    og_share: Decimal = Field(max_digits=15, decimal_places=2)
    expert_share: Decimal = Field(max_digits=15, decimal_places=2)

    # Additional metrics
    total_sales_count: int = Field(default=0)
    average_sale_value: Decimal = Field(default=Decimal("0.00"), max_digits=12, decimal_places=2)

    # Cost breakdown
    cost_breakdown: Dict[str, Decimal] = Field(default={}, sa_column=Column(JSON))

    # Metadata
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    is_finalized: bool = Field(default=False)

    # Relationship
    expert: Expert = Relationship(back_populates="financial_reports")


# Non-persistent schemas (for validation, forms, API requests/responses)
class UserCreate(SQLModel, table=False):
    email: str = Field(max_length=255, regex=r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
    password: str = Field(min_length=8, max_length=100)
    name: str = Field(max_length=100)
    role: UserRole = Field(default=UserRole.EXPERT)
    permissions: Dict[str, Any] = Field(default={})


class UserUpdate(SQLModel, table=False):
    name: Optional[str] = Field(default=None, max_length=100)
    role: Optional[UserRole] = Field(default=None)
    is_active: Optional[bool] = Field(default=None)
    permissions: Optional[Dict[str, Any]] = Field(default=None)


class ExpertCreate(SQLModel, table=False):
    business_name: str = Field(max_length=200)
    expert_name: str = Field(max_length=100)
    email: str = Field(max_length=255, regex=r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
    phone: Optional[str] = Field(default=None, max_length=20)
    business_description: Optional[str] = Field(default=None, max_length=1000)
    website: Optional[str] = Field(default=None, max_length=255)
    revenue_split_percentage: Decimal = Field(default=Decimal("50.0"), max_digits=5, decimal_places=2)
    subdomain: Optional[str] = Field(default=None, max_length=50)


class ExpertUpdate(SQLModel, table=False):
    business_name: Optional[str] = Field(default=None, max_length=200)
    expert_name: Optional[str] = Field(default=None, max_length=100)
    email: Optional[str] = Field(default=None, max_length=255)
    phone: Optional[str] = Field(default=None, max_length=20)
    status: Optional[ExpertStatus] = Field(default=None)
    business_description: Optional[str] = Field(default=None, max_length=1000)
    website: Optional[str] = Field(default=None, max_length=255)
    revenue_split_percentage: Optional[Decimal] = Field(default=None, max_digits=5, decimal_places=2)
    branding_config: Optional[Dict[str, Any]] = Field(default=None)


class SaleCreate(SQLModel, table=False):
    expert_id: int
    transaction_type: TransactionType = Field(default=TransactionType.SALE)
    gross_amount: Decimal = Field(max_digits=12, decimal_places=2)
    net_amount: Decimal = Field(max_digits=12, decimal_places=2)
    product_name: Optional[str] = Field(default=None, max_length=200)
    product_category: Optional[str] = Field(default=None, max_length=100)
    quantity: int = Field(default=1)
    customer_id: Optional[str] = Field(default=None, max_length=100)
    customer_country: Optional[str] = Field(default=None, max_length=3)
    sale_date: Optional[datetime] = Field(default=None)


class OperationalCostCreate(SQLModel, table=False):
    expert_id: int
    category: CostCategory
    description: str = Field(max_length=500)
    amount: Decimal = Field(max_digits=12, decimal_places=2)
    cost_date: Optional[datetime] = Field(default=None)
    is_recurring: bool = Field(default=False)
    recurring_frequency: Optional[str] = Field(default=None, max_length=20)
    external_reference: Optional[str] = Field(default=None, max_length=100)
    notes: Optional[str] = Field(default=None, max_length=1000)


class OperationalCostUpdate(SQLModel, table=False):
    category: Optional[CostCategory] = Field(default=None)
    description: Optional[str] = Field(default=None, max_length=500)
    amount: Optional[Decimal] = Field(default=None, max_digits=12, decimal_places=2)
    cost_date: Optional[datetime] = Field(default=None)
    is_recurring: Optional[bool] = Field(default=None)
    recurring_frequency: Optional[str] = Field(default=None, max_length=20)
    external_reference: Optional[str] = Field(default=None, max_length=100)
    notes: Optional[str] = Field(default=None, max_length=1000)


class FinancialSummary(SQLModel, table=False):
    """Summary for dashboard display"""

    total_experts: int
    active_experts: int
    total_gross_revenue: Decimal
    total_og_share: Decimal
    total_expert_share: Decimal
    period_start: datetime
    period_end: datetime


class ExpertFinancialSummary(SQLModel, table=False):
    """Financial summary for a specific expert"""

    expert_id: int
    expert_name: str
    business_name: str
    gross_revenue: Decimal
    total_costs: Decimal
    net_profit: Decimal
    og_share: Decimal
    expert_share: Decimal
    sales_count: int
    average_sale_value: Decimal
    period_start: datetime
    period_end: datetime
