from typing import TypeVar, Generic, Sequence, List
from pydantic import BaseModel, Field

T = TypeVar("T")

class PaginationParams(BaseModel):
    page: int = Field(1, ge=1, description="Page number starting at 1")
    page_size: int = Field(20, ge=1, le=100, description="Items per page")
    
    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int
    
    @classmethod
    def create(cls, items: Sequence[T], total: int, params: PaginationParams):
        total_pages = (total + params.page_size - 1) // params.page_size if params.page_size > 0 else 1
        return cls(
            items=list(items),
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=total_pages
        )
