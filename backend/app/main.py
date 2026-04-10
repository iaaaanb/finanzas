from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import select

from app.database import SessionLocal
from app.models import Base, Account
from app.routers import accounts, categories, budgets, transactions, auto_assign_rules, counterparts, emails


def seed_default_account():
    with SessionLocal() as db:
        exists = db.execute(
            select(Account).where(Account.name == "Efectivo")
        ).scalar_one_or_none()
        if not exists:
            db.add(Account(name="Efectivo", bank="Efectivo", color="#22c55e"))
            db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    seed_default_account()
    yield


app = FastAPI(title="Finanzas", lifespan=lifespan)

app.include_router(accounts.router)
app.include_router(categories.router)
app.include_router(budgets.router)
app.include_router(transactions.router)
app.include_router(auto_assign_rules.router)
app.include_router(counterparts.router)
app.include_router(emails.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
