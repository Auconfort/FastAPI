from fastapi import FastAPI, Request
from pydantic import BaseModel
import openai
import asyncpg
import os
import re

# 🔐 Config
openai.api_key = "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"
SUPABASE_DB_URL = "postgresql://postgres:service_rolesecret@db.bqeqwntbvvitylniwkfm.supabase.co:5432/postgres"

# 🚀 App init
app = FastAPI()

# 📦 Request model
class ProductQuery(BaseModel):
    message: str  # natural language prompt (e.g. “Quel est le prix du Matelas Basic D30 160x190 ?”)

# 🧠 SKU Parser
def parse_sku(ref: str):
    match = re.search(r"D(\d+)-Ep(\d+)-(\d+x\d+)", ref)
    if match:
        return {
            "density": match.group(1),
            "thickness": match.group(2),
            "dimensions": match.group(3)
        }
    return {}

# 🔄 Query Supabase
async def fetch_products_from_db():
    conn = await asyncpg.connect(SUPABASE_DB_URL)
    rows = await conn.fetch("SELECT * FROM products")
    await conn.close()
    return [dict(r) for r in rows]

# 🔥 Webhook route
@app.post("/webhook")
async def product_info(req: ProductQuery):
    user_prompt = req.message

    # 1. Fetch all product data
    products = await fetch_products_from_db()

    # 2. Build product context
    enriched_data = []
    for product in products:
        parsed = parse_sku(product["ref"]) if product.get("has_thickness") else {}
        context_entry = {
            **product,
            **parsed
        }
        enriched_data.append(context_entry)

    # 3. Prepare AI context
    context_text = "\n".join([
        f"{p['title']} | {p['subcategory']} | Ref: {p['ref']} | {p['description']} | Prix: {p['price']} DA | Taille: {p.get('dimensions')} | Densité: {p.get('density')} | Épaisseur: {p.get('thickness')}"
        for p in enriched_data
    ])

    # 4. Run OpenAI query
    system_prompt = (
        "Tu es un assistant produit d'Auconfort. Réponds avec précision uniquement à partir des données suivantes :\n"
        f"{context_text}"
    )

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.2
    )

    answer = response["choices"][0]["message"]["content"]
    return {"answer": answer}
