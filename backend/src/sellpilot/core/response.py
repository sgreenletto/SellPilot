from pydantic import BaseModel, Field, computed_field


class ApiResponse[T](BaseModel):
    code: int | str = 0
    message: str = "success"
    data: T | None = None
    request_id: str


class PageResult[T](BaseModel):
    items: list[T]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)

    @computed_field
    @property
    def pages(self) -> int:
        if self.total == 0:
            return 0
        return (self.total + self.page_size - 1) // self.page_size


class ValidationIssue(BaseModel):
    field: str
    message: str
    type: str


def success_response[T](data: T, request_id: str) -> ApiResponse[T]:
    return ApiResponse[T](data=data, request_id=request_id)
