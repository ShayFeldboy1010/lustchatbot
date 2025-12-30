from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class OrderData(BaseModel):
    """Order data model for Google Sheets"""
    customer_name: str
    customer_email: str
    customer_phone: str
    product_name: str
    quantity: int = 1
    full_address: str
    payment_method: str  # 'bit', 'cash', 'credit'
    delivery_notes: Optional[str] = ""
    status: str = "חדש"
    created_at: datetime = None

    def __init__(self, **data):
        if 'created_at' not in data or data['created_at'] is None:
            data['created_at'] = datetime.now()
        super().__init__(**data)

    def to_sheet_row(self) -> list:
        """Convert to Google Sheets row format
        Columns: תאריך ושעה | שם | אימייל | טלפון | מוצר רצוי | הערות לשליח | כתובת | אמצעי תשלום | סוג משלוח | סטטוס
        """
        return [
            self.created_at.strftime("%d/%m/%Y %H:%M"),  # תאריך ושעה
            self.customer_name,                          # שם
            self.customer_email,                         # אימייל
            self.customer_phone,                         # טלפון
            f"{self.product_name} x{self.quantity}",     # מוצר רצוי
            self.delivery_notes or "",                   # הערות לשליח
            self.full_address,                           # כתובת
            self.payment_method,                         # אמצעי תשלום
            "",                                          # סוג משלוח (ריק)
            self.status                                  # סטטוס
        ]
