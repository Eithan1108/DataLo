from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
from typing import Dict

# Support both `python -m src.api.server` and direct script execution
try:
    from src.chatbot.app import MCP_ChatBot
except ModuleNotFoundError:
    import sys
    from pathlib import Path
    ROOT_DIR = Path(__file__).resolve().parents[2]
    if str(ROOT_DIR) not in sys.path:
        sys.path.append(str(ROOT_DIR))
    from src.chatbot.app import MCP_ChatBot
from pymongo import MongoClient
import jwt
import os
from datetime import datetime, timedelta, timezone
import re

app = FastAPI(title="MCP Chat API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class InitRequest(BaseModel):
    user_id: str


class MessageRequest(BaseModel):
    session_id: str
    message: str


class MessageResponse(BaseModel):
    reply: str


chatbot_sessions: Dict[str, MCP_ChatBot] = {}
JWT_SECRET = os.environ.get("JWT_SECRET", "dev-secret-change-me")
JWT_ALG = "HS256"
mongo_client = MongoClient("mongodb://localhost:27017/")
USERS_DB_NAME = os.environ.get("USERS_DB_NAME", "admin")
USERS_COLLECTION_NAME = os.environ.get("USERS_COLLECTION_NAME", "users")


class LoginRequest(BaseModel):
    email: str


class LoginResponse(BaseModel):
    token: str
    user_id: str


@app.post("/api/init")
async def init_chat(req: InitRequest):
    # Use user_id as session for simplicity; a real app would create unique session ids
    session_id = req.user_id
    if session_id in chatbot_sessions:
        return {"session_id": session_id}

    bot = MCP_ChatBot()
    await bot.connect_to_servers()
    bot.user_id = req.user_id
    chatbot_sessions[session_id] = bot
    return {"session_id": session_id}
def get_user_id_from_auth(authorization: str | None = Header(default=None)) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = authorization.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        return payload.get("user_id")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


@app.post("/auth/login", response_model=LoginResponse)
async def login(req: LoginRequest):
    # Lookup user by email in 'users' database, 'users' collection
    users_db = mongo_client[USERS_DB_NAME]
    email_norm = (req.email or "").strip()
    # Case-insensitive exact match using regex anchor
    pattern = f"^{re.escape(email_norm)}$"
    user_doc = users_db[USERS_COLLECTION_NAME].find_one({"email": {"$regex": pattern, "$options": "i"}})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")

    user_id = str(user_doc.get("_id"))
    payload = {
        "user_id": user_id,
        "email": req.email,
        "exp": datetime.now(timezone.utc) + timedelta(days=7)
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)
    return LoginResponse(token=token, user_id=user_id)



@app.post("/api/message", response_model=MessageResponse)
async def send_message(req: MessageRequest, user_id: str = Depends(get_user_id_from_auth)):
    bot = chatbot_sessions.get(req.session_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Session not found. Initialize with /api/init")

    # Ensure session user_id matches token's user
    bot.user_id = user_id
    reply = await bot.ask(req.message)
    return MessageResponse(reply=reply or "")


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    # Prefer running as a module for package-aware imports
    # Equivalent CLI: `uv run -m src.api.server`
    uvicorn.run("src.api.server:app", host="0.0.0.0", port=8000, reload=False)


