import pytest
from app import create_app


@pytest.fixture
def client(tmp_path):
    app = create_app({"TESTING": True, "DATABASE": str(tmp_path / "test.db")})
    with app.test_client() as client:
        yield client

def test_list_categories(client):
    res = client.get("/categories/")
    assert res.status_code == 200
    assert len(res.get_json()["data"]) > 0

def test_create_and_delete_category(client):
    res = client.post("/categories/", json={"name": "Investimentos", "type": "receita"})
    assert res.status_code == 201
    cat_id = res.get_json()["data"]["id"]
    assert client.post("/categories/", json={"name": "Investimentos", "type": "receita"}).status_code == 409
    assert client.delete(f"/categories/{cat_id}").status_code == 200

def test_create_transaction(client):
    res = client.post("/transactions/", json={
        "description": "Salário junho",
        "amount": 3500.00,
        "type": "receita",
        "date": "2024-06-05",
    })
    assert res.status_code == 201

def test_invalid_transaction(client):
    assert client.post("/transactions/", json={"description": "Teste"}).status_code == 400
    assert client.post("/transactions/", json={
        "description": "Teste", "amount": -100, "type": "despesa", "date": "2024-06-01"
    }).status_code == 400

def test_get_update_delete_transaction(client):
    res = client.post("/transactions/", json={
        "description": "Aluguel", "amount": 1200.00, "type": "despesa", "date": "2024-06-01"
    })
    t_id = res.get_json()["data"]["id"]
    assert client.get(f"/transactions/{t_id}").status_code == 200
    res2 = client.put(f"/transactions/{t_id}", json={"amount": 1300.00})
    assert res2.get_json()["data"]["amount"] == 1300.00
    assert client.delete(f"/transactions/{t_id}").status_code == 200
    assert client.get(f"/transactions/{t_id}").status_code == 404

def test_summary(client):
    client.post("/transactions/", json={"description": "Salário", "amount": 5000, "type": "receita", "date": "2024-06-01"})
    client.post("/transactions/", json={"description": "Aluguel", "amount": 1500, "type": "despesa", "date": "2024-06-05"})
    data = client.get("/summary/").get_json()["data"]
    assert data["saldo"] == 3500.0

def test_monthly_summary(client):
    assert client.get("/summary/monthly").status_code == 200
    