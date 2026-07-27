from sellpilot.core.response import ApiResponse, PageResult, success_response


def test_uniform_success_response():
    response = success_response({"status": "ok"}, "request-id")
    assert response == ApiResponse[dict[str, str]](
        code=0,
        message="success",
        data={"status": "ok"},
        request_id="request-id",
    )


def test_page_result():
    page = PageResult[int](items=[1, 2], total=2, page=1, page_size=20)
    assert page.total == 2
    assert page.items == [1, 2]
    assert page.pages == 1


def test_empty_page_result_keeps_shape():
    page = PageResult[int](items=[], total=0, page=1, page_size=20)
    assert page.model_dump() == {
        "items": [],
        "total": 0,
        "page": 1,
        "page_size": 20,
        "pages": 0,
    }


def test_page_count_rounds_up():
    page = PageResult[int](items=[], total=41, page=3, page_size=20)
    assert page.pages == 3
