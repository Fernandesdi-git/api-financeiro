from flask import Blueprint, request
from .database import get_db
from .helpers import success, error

# TRANSACTIONS
transactions_bp = Blueprint("transactions", __name__, url_prefix="/transactions")

@transactions_bp.get("/")
def list_transactions():
    db = get_db()
    query = "SELECT t.*, c.name AS category_name FROM transactions t LEFT JOIN categories c ON t.category_id = c.id WHERE 1=1"
    params = []
    tipo = request.args.get("type")
    if tipo:
        query += " AND t.type = ?"
        params.append(tipo)
    month = request.args.get("month")
    if month:
        query += " AND t.date LIKE ?"
        params.append(f"{month}%")
    category_id = request.args.get("category_id")
    if category_id:
        query += " AND t.category_id = ?"
        params.append(category_id)
    query += " ORDER BY t.date DESC"
    rows = db.execute(query, params).fetchall()
    return success([dict(r) for r in rows])

@transactions_bp.post("/")
def create_transaction():
    data = request.get_json()
    if not data:
        return error("JSON inválido ou ausente.")
    required = ["description", "amount", "type", "date"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        return error(f"Campos obrigatórios ausentes: {', '.join(missing)}")
    if data["type"] not in ("receita", "despesa"):
        return error("O campo 'type' deve ser 'receita' ou 'despesa'.")
    try:
        amount = float(data["amount"])
        if amount <= 0:
            raise ValueError
    except ValueError:
        return error("O campo 'amount' deve ser um número positivo.")
    db = get_db()
    cursor = db.execute(
        "INSERT INTO transactions (description, amount, type, category_id, date) VALUES (?, ?, ?, ?, ?)",
        (data["description"], amount, data["type"], data.get("category_id"), data["date"]),
    )
    db.commit()
    new = db.execute("SELECT * FROM transactions WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return success(dict(new), status=201)

@transactions_bp.get("/<int:transaction_id>")
def get_transaction(transaction_id):
    db = get_db()
    row = db.execute(
        "SELECT t.*, c.name AS category_name FROM transactions t LEFT JOIN categories c ON t.category_id = c.id WHERE t.id = ?",
        (transaction_id,),
    ).fetchone()
    if not row:
        return error("Transação não encontrada.", 404)
    return success(dict(row))

@transactions_bp.put("/<int:transaction_id>")
def update_transaction(transaction_id):
    db = get_db()
    existing = db.execute("SELECT * FROM transactions WHERE id = ?", (transaction_id,)).fetchone()
    if not existing:
        return error("Transação não encontrada.", 404)
    data = request.get_json()
    if not data:
        return error("JSON inválido ou ausente.")
    description = data.get("description", existing["description"])
    amount      = data.get("amount",      existing["amount"])
    tipo        = data.get("type",        existing["type"])
    category_id = data.get("category_id", existing["category_id"])
    date        = data.get("date",        existing["date"])
    if tipo not in ("receita", "despesa"):
        return error("O campo 'type' deve ser 'receita' ou 'despesa'.")
    try:
        amount = float(amount)
        if amount <= 0:
            raise ValueError
    except ValueError:
        return error("O campo 'amount' deve ser um número positivo.")
    db.execute(
        "UPDATE transactions SET description=?, amount=?, type=?, category_id=?, date=? WHERE id=?",
        (description, amount, tipo, category_id, date, transaction_id),
    )
    db.commit()
    updated = db.execute("SELECT * FROM transactions WHERE id = ?", (transaction_id,)).fetchone()
    return success(dict(updated))

@transactions_bp.delete("/<int:transaction_id>")
def delete_transaction(transaction_id):
    db = get_db()
    existing = db.execute("SELECT id FROM transactions WHERE id = ?", (transaction_id,)).fetchone()
    if not existing:
        return error("Transação não encontrada.", 404)
    db.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
    db.commit()
    return success({"message": f"Transação {transaction_id} removida com sucesso."})

# CATEGORIES
categories_bp = Blueprint("categories", __name__, url_prefix="/categories")

@categories_bp.get("/")
def list_categories():
    db = get_db()
    rows = db.execute("SELECT * FROM categories ORDER BY type, name").fetchall()
    return success([dict(r) for r in rows])

@categories_bp.post("/")
def create_category():
    data = request.get_json()
    if not data:
        return error("JSON inválido ou ausente.")
    name = data.get("name", "").strip()
    tipo = data.get("type", "")
    if not name:
        return error("O campo 'name' é obrigatório.")
    if tipo not in ("receita", "despesa"):
        return error("O campo 'type' deve ser 'receita' ou 'despesa'.")
    db = get_db()
    try:
        cursor = db.execute("INSERT INTO categories (name, type) VALUES (?, ?)", (name, tipo))
        db.commit()
    except Exception:
        return error("Já existe uma categoria com esse nome.", 409)
    new = db.execute("SELECT * FROM categories WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return success(dict(new), status=201)

@categories_bp.delete("/<int:category_id>")
def delete_category(category_id):
    db = get_db()
    existing = db.execute("SELECT id FROM categories WHERE id = ?", (category_id,)).fetchone()
    if not existing:
        return error("Categoria não encontrada.", 404)
    linked = db.execute("SELECT COUNT(*) AS n FROM transactions WHERE category_id = ?", (category_id,)).fetchone()
    if linked["n"] > 0:
        return error("Não é possível remover: existem transações vinculadas.", 409)
    db.execute("DELETE FROM categories WHERE id = ?", (category_id,))
    db.commit()
    return success({"message": f"Categoria {category_id} removida com sucesso."})

# SUMMARY
summary_bp = Blueprint("summary", __name__, url_prefix="/summary")

@summary_bp.get("/")
def get_summary():
    db = get_db()
    month = request.args.get("month")
    params = [f"{month}%"] if month else []
    filter_clause = "AND date LIKE ?" if month else ""
    receitas = db.execute(
        f"SELECT COALESCE(SUM(amount), 0) AS total FROM transactions WHERE type='receita' {filter_clause}", params
    ).fetchone()["total"]
    despesas = db.execute(
        f"SELECT COALESCE(SUM(amount), 0) AS total FROM transactions WHERE type='despesa' {filter_clause}", params
    ).fetchone()["total"]
    cat_query = "SELECT c.name AS category, SUM(t.amount) AS total FROM transactions t JOIN categories c ON t.category_id = c.id WHERE t.type = 'despesa'"
    cat_params = []
    if month:
        cat_query += " AND t.date LIKE ?"
        cat_params.append(f"{month}%")
    cat_query += " GROUP BY c.name ORDER BY total DESC"
    by_category = db.execute(cat_query, cat_params).fetchall()