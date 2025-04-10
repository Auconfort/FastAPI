import os
import re
import httpx
from fastapi import FastAPI
from pydantic import BaseModel
from openai import OpenAI

from fastapi import FastAPI
import httpx
import os

app = FastAPI()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")

@app.get("/test-products")
async def test_products():
    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}"
    }
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{SUPABASE_URL}/rest/v1/products",
            headers=headers,
            params={"select": "title,ref,price_dz", "limit": 5}
        )
        response.raise_for_status()
        return response.json()



# Env vars
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

print("Loaded SUPABASE_ANON_KEY:", SUPABASE_ANON_KEY)

# Initialize OpenAI client
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# FastAPI setup
app = FastAPI()

# Schema
class ProductQuery(BaseModel):
    message: str

# SKU Parser
def parse_sku(ref: str):
    match = re.search(r"D(\d+)-Ep(\d+)-(\d+x\d+)", ref)
    if match:
        return {
            "density": match.group(1),
            "thickness": match.group(2),
            "dimensions": match.group(3)
        }
    return {}

# Supabase Fetch
async def fetch_products():
    async with httpx.AsyncClient() as client:
        headers = {
            "apikey": SUPABASE_ANON_KEY,
            "Authorization": f"Bearer {SUPABASE_ANON_KEY}"
        }
        response = await client.get(
            f"{SUPABASE_URL}/rest/v1/products",
            headers=headers,
            params={"select": "*"}
        )
        response.raise_for_status()
        return response.json()

# Webhook Endpoint
@app.post("/webhook")
async def product_info(req: ProductQuery):
    user_prompt = req.message
    products = await fetch_products()

    enriched_data = []
    for product in products:
        parsed = parse_sku(product["ref"]) if product.get("has_thickness") else {}
        context_entry = {**product, **parsed}
        enriched_data.append(context_entry)

    context_text = "\n".join([
        f"{p.get('title', '')} | {p.get('subcategory', '')} | Ref: {p.get('ref', '')} | {p.get('description', '')} | Prix: {p.get('price', '')} DA | Taille: {p.get('dimensions', '')} | Densité: {p.get('density', '')} | Épaisseur: {p.get('thickness', '')}"
        for p in enriched_data
    ])

    system_prompt = (
        "Tu es un assistant produit d'Auconfort. Réponds avec précision uniquement à partir des données suivantes :\n"
        f"{context_text}"
    )

    response = openai_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.2
    )

    return {"answer": response.choices[0].message.content}
