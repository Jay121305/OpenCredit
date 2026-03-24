from pydantic import BaseModel


class SpendingCategoryItem(BaseModel):
    category: str
    total_amount: float


class SpendingSummaryResponse(BaseModel):
    month_total: float
    utilization_pct: float
    by_category: list[SpendingCategoryItem]
