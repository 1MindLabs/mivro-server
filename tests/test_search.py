import pytest
from flask import Flask
from server.search import search_blueprint


@pytest.fixture
def client():
    app = Flask(__name__)
    app.register_blueprint(search_blueprint, url_prefix="/api/v1/search")
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_barcode(client):
    response = client.get(
        "/api/v1/search/barcode",
        headers={"Mivro-Email": "test@mivro.org"},
        query_string={"product_barcode": "1234567890123"},
    )
    assert response.status_code == 200 or response.status_code == 404


def test_database(client):
    response = client.get(
        "/api/v1/search/database",
        headers={"Mivro-Email": "test@mivro.org"},
        query_string={"product_keyword": "test product"},
    )
    assert response.status_code == 200 or response.status_code == 404
