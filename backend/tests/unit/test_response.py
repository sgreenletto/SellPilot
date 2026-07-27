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
