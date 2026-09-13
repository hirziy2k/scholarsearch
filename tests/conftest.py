import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--pdf-engine-url",
        action="store",
        default="http://localhost:8000",
        help="Base URL for pdf-engine API",
    )
    parser.addoption(
        "--scholarsearch-url",
        action="store",
        default="http://localhost:3001",
        help="Base URL for scholarsearch API",
    )


@pytest.fixture(scope="session")
def pdf_engine_url(request):
    return request.config.getoption("--pdf-engine-url")


@pytest.fixture(scope="session")
def scholarsearch_url(request):
    return request.config.getoption("--scholarsearch-url")
