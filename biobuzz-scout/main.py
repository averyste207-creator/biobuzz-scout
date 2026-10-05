from fastapi import FastAPI, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
import csv
import io
from datetime import datetime

from database import engine, get_db, Base
from models import Team, Event, Match, ScoutEntry

Base.metadata.create_all(bind=engine)

app = FastAPI(title="BIOBUZZ Scout", description="FTC 2026-2027 BIOBUZZ Scouting App")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# ---------- Helpers ----------
def get_or_create_team(db: Session, number: int, name: str = "") -> Team:
    team = db.query(Team).filter(Team.number == number).first()
    if not team:
        team = Team(number=number, name=name or f"Team {number}")
        db.add(team)
        db.commit()
        db.refresh(team)
    return team


def team_stats(db: Session, team_id: int):
    entries = db.query(ScoutEntry).filter(ScoutEntry.team_id == team_id).all()
    if not entries:
        return None
    n = len(entries)
    return {
        "matches": n,
        "avg_hive_tips": round(sum(e.auto_hive_tips + e.tele_hive_tips for e in entries) / n, 2),
        "avg_points": round(sum(e.estimated_points for e in entries) / n, 1),
        "total_deaths": sum(e.robot_deaths for e in entries),
        "death_rate": round(sum(1 for e in entries if e.robot_deaths > 0) / n * 100, 1),
        "avg_driver": round(sum(e.driver_skill for e in entries) / n, 2),
        "avg_consistency": round(sum(e.consistency for e in entries) / n, 2),
        "park_rate": round(sum(1 for e in entries if e.tele_park or e.auto_park) / n * 100, 1),
        "leave_rate": round(sum(1 for e in entries if e.auto_leave) / n * 100, 1),
    }


# ---------- Routes ----------
@app.get("/", response_class=HTMLResponse)
async def home(request: Request, db: Session = Depends(get_db)):
    events = db.query(Event).order_by(Event.created_at.desc()).limit(5).all()
    teams = db.query(Team).order_by(Team.number).limit(12).all()
    recent = (
        db.query(ScoutEntry)
        .order_by(ScoutEntry.created_at.desc())
        .limit(8)
        .all()
    )
    total_entries = db.query(func.count(ScoutEntry.id)).scalar() or 0
    total_teams = db.query(func.count(Team.id)).scalar() or 0
    total_matches = db.query(func.count(Match.id)).scalar() or 0
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "events": events,
            "teams": teams,
            "recent": recent,
            "stats": {
                "entries": total_entries,
                "teams": total_teams,
                "matches": total_matches,
            },
        },
    )


# ---- Teams ----
@app.get("/teams", response_class=HTMLResponse)
async def teams_list(request: Request, db: Session = Depends(get_db)):
    teams = db.query(Team).order_by(Team.number).all()
    stats_map = {t.id: team_stats(db, t.id) for t in teams}
    return templates.TemplateResponse(
        "teams.html", {"request": request, "teams": teams, "stats_map": stats_map}
    )


@app.post("/teams/add")
async def add_team(
    number: int = Form(...),
    name: str = Form(""),
    notes: str = Form(""),
    db: Session = Depends(get_db),
):
    existing = db.query(Team).filter(Team.number == number).first()
    if existing:
        existing.name = name or existing.name
        existing.notes = notes or existing.notes
    else:
        db.add(Team(number=number, name=name or f"Team {number}", notes=notes))
    db.commit()
    return RedirectResponse("/teams", status_code=303)


@app.get("/teams/{team_id}", response_class=HTMLResponse)
async def team_detail(request: Request, team_id: int, db: Session = Depends(get_db)):
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(404, "Team not found")
    entries = (
        db.query(ScoutEntry)
        .filter(ScoutEntry.team_id == team_id)
        .order_by(ScoutEntry.created_at.desc())
        .all()
    )
    stats = team_stats(db, team_id)
    return templates.TemplateResponse(
        "team_detail.html",
        {"request": request, "team": team, "entries": entries, "stats": stats},
    )


# ---- Events & Matches ----
@app.get("/events", response_class=HTMLResponse)
async def events_list(request: Request, db: Session = Depends(get_db)):
    events = db.query(Event).order_by(Event.created_at.desc()).all()
    return templates.TemplateResponse("events.html", {"request": request, "events": events})


@app.post("/events/add")
async def add_event(
    name: str = Form(...),
    location: str = Form(""),
    date: str = Form(""),
    db: Session = Depends(get_db),
):
    db.add(Event(name=name, location=location, date=date))
    db.commit()
    return RedirectResponse("/events", status_code=303)


@app.get("/events/{event_id}", response_class=HTMLResponse)
async def event_detail(request: Request, event_id: int, db: Session = Depends(get_db)):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(404, "Event not found")
    matches = (
        db.query(Match)
        .filter(Match.event_id == event_id)
        .order_by(Match.match_number)
        .all()
    )
    return templates.TemplateResponse(
        "event_detail.html", {"request": request, "event": event, "matches": matches}
    )


@app.post("/events/{event_id}/matches/add")
async def add_match(
    event_id: int,
    match_number: int = Form(...),
    match_type: str = Form("Qual"),
    red1: int = Form(...),
    red2: int = Form(...),
    blue1: int = Form(...),
    blue2: int = Form(...),
    db: Session = Depends(get_db),
):
    for num in (red1, red2, blue1, blue2):
        get_or_create_team(db, num)
    db.add(
        Match(
            event_id=event_id,
            match_number=match_number,
            match_type=match_type,
            red1=red1,
            red2=red2,
            blue1=blue1,
            blue2=blue2,
        )
    )
    db.commit()
    return RedirectResponse(f"/events/{event_id}", status_code=303)


# ---- Scouting ----
@app.get("/scout", response_class=HTMLResponse)
async def scout_form(
    request: Request,
    match_id: Optional[int] = None,
    team_number: Optional[int] = None,
    db: Session = Depends(get_db),
):
    matches = (
        db.query(Match)
        .order_by(Match.created_at.desc())
        .limit(50)
        .all()
    )
    teams = db.query(Team).order_by(Team.number).all()
    selected_match = None
    if match_id:
        selected_match = db.query(Match).filter(Match.id == match_id).first()
    return templates.TemplateResponse(
        "scout.html",
        {
            "request": request,
            "matches": matches,
            "teams": teams,
            "selected_match": selected_match,
            "prefill_team": team_number,
        },
    )


@app.post("/scout/submit")
async def submit_scout(
    match_id: int = Form(...),
    team_number: int = Form(...),
    alliance: str = Form(...),
    scout_name: str = Form(""),
    auto_leave: Optional[str] = Form(None),
    auto_park: Optional[str] = Form(None),
    auto_hive_tips: int = Form(0),
    auto_pollen: int = Form(0),
    auto_nectar: int = Form(0),
    tele_hive_tips: int = Form(0),
    tele_pollen: int = Form(0),
    tele_nectar: int = Form(0),
    flower_owned: int = Form(0),
    bottom_nectar_bonus: int = Form(0),
    garden_scored: int = Form(0),
    tele_park: Optional[str] = Form(None),
    robot_deaths: int = Form(0),
    death_reasons: str = Form(""),
    disabled_time_sec: int = Form(0),
    driver_skill: int = Form(3),
    consistency: int = Form(3),
    intake_reliability: int = Form(3),
    notes: str = Form(""),
    db: Session = Depends(get_db),
):
    team = get_or_create_team(db, team_number)
    entry = ScoutEntry(
        match_id=match_id,
        team_id=team.id,
        alliance=alliance.lower(),
        scout_name=scout_name,
        auto_leave=bool(auto_leave),
        auto_park=bool(auto_park),
        auto_hive_tips=auto_hive_tips,
        auto_pollen=auto_pollen,
        auto_nectar=auto_nectar,
        tele_hive_tips=tele_hive_tips,
        tele_pollen=tele_pollen,
        tele_nectar=tele_nectar,
        flower_owned=flower_owned,
        bottom_nectar_bonus=bottom_nectar_bonus,
        garden_scored=garden_scored,
        tele_park=bool(tele_park),
        robot_deaths=robot_deaths,
        death_reasons=death_reasons,
        disabled_time_sec=disabled_time_sec,
        driver_skill=max(1, min(5, driver_skill)),
        consistency=max(1, min(5, consistency)),
        intake_reliability=max(1, min(5, intake_reliability)),
        notes=notes,
    )
    db.add(entry)
    db.commit()
    return RedirectResponse(f"/teams/{team.id}", status_code=303)


@app.get("/entries/{entry_id}", response_class=HTMLResponse)
async def entry_detail(request: Request, entry_id: int, db: Session = Depends(get_db)):
    entry = db.query(ScoutEntry).filter(ScoutEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(404, "Entry not found")
    return templates.TemplateResponse(
        "entry_detail.html", {"request": request, "entry": entry}
    )


@app.post("/entries/{entry_id}/delete")
async def delete_entry(entry_id: int, db: Session = Depends(get_db)):
    entry = db.query(ScoutEntry).filter(ScoutEntry.id == entry_id).first()
    if entry:
        team_id = entry.team_id
        db.delete(entry)
        db.commit()
        return RedirectResponse(f"/teams/{team_id}", status_code=303)
    return RedirectResponse("/", status_code=303)


# ---- Rankings / Analytics ----
@app.get("/rankings", response_class=HTMLResponse)
async def rankings(request: Request, db: Session = Depends(get_db)):
    teams = db.query(Team).order_by(Team.number).all()
    ranked = []
    for t in teams:
        s = team_stats(db, t.id)
        if s and s["matches"] > 0:
            ranked.append({"team": t, "stats": s})
    # Sort by avg points then death rate (lower better)
    ranked.sort(key=lambda x: (-x["stats"]["avg_points"], x["stats"]["death_rate"]))
    return templates.TemplateResponse(
        "rankings.html", {"request": request, "ranked": ranked}
    )


# ---- Export ----
@app.get("/export/csv")
async def export_csv(db: Session = Depends(get_db)):
    entries = db.query(ScoutEntry).order_by(ScoutEntry.created_at).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "id",
            "match_id",
            "match_number",
            "team_number",
            "alliance",
            "scout_name",
            "auto_leave",
            "auto_park",
            "auto_hive_tips",
            "auto_pollen",
            "auto_nectar",
            "tele_hive_tips",
            "tele_pollen",
            "tele_nectar",
            "flower_owned",
            "bottom_nectar_bonus",
            "garden_scored",
            "tele_park",
            "robot_deaths",
            "death_reasons",
            "disabled_time_sec",
            "driver_skill",
            "consistency",
            "intake_reliability",
            "estimated_points",
            "notes",
            "created_at",
        ]
    )
    for e in entries:
        writer.writerow(
            [
                e.id,
                e.match_id,
                e.match.match_number if e.match else "",
                e.team.number if e.team else "",
                e.alliance,
                e.scout_name,
                e.auto_leave,
                e.auto_park,
                e.auto_hive_tips,
                e.auto_pollen,
                e.auto_nectar,
                e.tele_hive_tips,
                e.tele_pollen,
                e.tele_nectar,
                e.flower_owned,
                e.bottom_nectar_bonus,
                e.garden_scored,
                e.tele_park,
                e.robot_deaths,
                e.death_reasons,
                e.disabled_time_sec,
                e.driver_skill,
                e.consistency,
                e.intake_reliability,
                e.estimated_points,
                e.notes,
                e.created_at.isoformat() if e.created_at else "",
            ]
        )
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=biobuzz_scout_export.csv"},
    )


@app.get("/health")
async def health():
    return {"status": "ok", "season": "BIOBUZZ 2026-2027"}
