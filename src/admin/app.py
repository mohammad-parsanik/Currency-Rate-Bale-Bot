import secrets
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from src.config import settings
from src.database.repositories import UserRepository, InteractionRepository, ErrorRepository, PriceRepository, UserSourceLogRepository
from src.services.price_service import fetch_and_store

app = FastAPI(title="Bot Admin Panel")
security = HTTPBasic()
templates = Jinja2Templates(directory="src/admin/templates")

def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, settings.ADMIN_USERNAME)
    correct_password = secrets.compare_digest(credentials.password, settings.ADMIN_PASSWORD)
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, username: str = Depends(verify_credentials)):
    user_stats = await UserRepository.get_stats()
    most_used = await InteractionRepository.get_most_used_command()
    recent_errors = await ErrorRepository.get_recent_errors(limit=20)
    prices = await PriceRepository.get_all_prices("tgju")
    prices.extend(await PriceRepository.get_all_prices("nerkh"))
    source_logs = await UserSourceLogRepository.get_recent_logs(limit=20)
    
    # Calculate some summary stats about prices
    tgju_count = sum(1 for p in prices if p["source"] == "tgju")
    nerkh_count = sum(1 for p in prices if p["source"] == "nerkh")
    
    latest_update = max((p["fetched_at"] for p in prices), default="N/A")
    
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "request": request,
            "total_users": user_stats["total"],
            "active_users": user_stats["active"],
            "recent_users": user_stats["recent_users"],
            "most_used_command": most_used["command"] if most_used else "None",
            "most_used_count": most_used["count"] if most_used else 0,
            "recent_errors": recent_errors,
            "tgju_count": tgju_count,
            "nerkh_count": nerkh_count,
            "latest_update": latest_update,
            "source_logs": source_logs
        }
    )

@app.post("/api/scrape")
async def manual_scrape(username: str = Depends(verify_credentials)):
    try:
        await fetch_and_store()
        return {"status": "success", "message": "Scrape completed successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
