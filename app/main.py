import os
import sys
import datetime
from collections import defaultdict

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.db_client import NotesDb, DbError
from app.config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


def get_db() -> NotesDb:
    return NotesDb(DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD)


class NoteItem(BaseModel):
    culture: str = ""
    description: str = ""


class NotesBatch(BaseModel):
    date: str
    items: list[NoteItem]


class UpdateItem(BaseModel):
    id: int
    culture: str = ""
    description: str = ""


class UpdateBatch(BaseModel):
    items: list[UpdateItem]


@app.get("/", response_class=HTMLResponse)
def form_page(request: Request):
    return templates.TemplateResponse("form.html", {"request": request, "error": None, "active_tab": "notes"})


@app.get("/second", response_class=HTMLResponse)
def second_page(request: Request, year: int | None = None):
    current_year = year or datetime.date.today().year
    grouped = {}
    years = []
    cultures = []
    error = None
    try:
        db = get_db()
        years = db.list_seed_years()
        if current_year not in years:
            years = sorted(set(years) | {current_year}, reverse=True)
        cultures = db.list_cultures()
        seeds = db.list_seeds(current_year)
        g = defaultdict(list)
        for s in seeds:
            g[s["culture"]].append(s)
        grouped = dict(g)
    except DbError as e:
        error = e.message

    return templates.TemplateResponse(
        "second.html",
        {
            "request": request,
            "active_tab": "second",
            "grouped": grouped,
            "year": current_year,
            "years": years,
            "cultures": cultures,
            "error": error,
        },
    )


@app.post("/second/add")
def second_add(
    culture: str = Form(""),
    sort: str = Form(""),
    quantity: str = Form(""),
    quantity_unit: str = Form(""),
    year: int = Form(0),
):
    culture = (culture or "").strip()
    sort = (sort or "").strip()
    quantity_unit = (quantity_unit or "").strip() or None
    target_year = year or datetime.date.today().year

    if not culture:
        return RedirectResponse(url=f"/second?year={target_year}", status_code=303)

    def to_float(v):
        v = (v or "").strip().replace(",", ".")
        if not v:
            return None
        try:
            return float(v)
        except ValueError:
            return None

    try:
        db = get_db()
        db.create_seed(
            year=target_year,
            culture=culture,
            sort=sort or None,
            quantity=to_float(quantity),
            quantity_unit=quantity_unit,
        )
    except DbError:
        pass

    return RedirectResponse(url=f"/second?year={target_year}", status_code=303)


@app.post("/notes")
def create_notes(batch: NotesBatch):
    date = (batch.date or "").strip()
    if not date:
        return JSONResponse({"ok": False, "error": "Дата не указана"}, status_code=400)

    valid = []
    for it in batch.items:
        c = (it.culture or "").strip()
        d = (it.description or "").strip()
        if c or d:
            valid.append((c or None, d or None))

    if not valid:
        return JSONResponse({"ok": False, "error": "Заполните хотя бы одну строку"}, status_code=400)

    saved = 0
    try:
        db = get_db()
        for c, d in valid:
            db.create_note(c, d, date)
            saved += 1
    except DbError as e:
        return JSONResponse({"ok": False, "error": f"Ошибка после {saved} записей: {e.message}"}, status_code=500)

    return JSONResponse({"ok": True, "saved": saved})


@app.get("/history-json")
def history_json(limit: int = 50):
    try:
        db = get_db()
        notes = db.list_notes(limit=limit)
        return JSONResponse({"ok": True, "notes": notes})
    except DbError as e:
        return JSONResponse({"ok": False, "error": e.message}, status_code=500)


@app.post("/notes/update")
def update_notes(batch: UpdateBatch):
    updated = 0
    try:
        db = get_db()
        for it in batch.items:
            c = (it.culture or "").strip() or None
            d = (it.description or "").strip() or None
            db.update_note(it.id, c, d)
            updated += 1
    except DbError as e:
        return JSONResponse({"ok": False, "error": f"Ошибка после {updated}: {e.message}"}, status_code=500)
    return JSONResponse({"ok": True, "updated": updated})


@app.get("/history", response_class=HTMLResponse)
def history_page(request: Request):
    error = None
    notes = []
    try:
        db = get_db()
        notes = db.list_notes(limit=100)
    except DbError as e:
        error = e.message
    return templates.TemplateResponse(
        "history.html",
        {"request": request, "notes": notes, "error": error},
    )
