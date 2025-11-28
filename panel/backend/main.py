"""
Refill Timer Backend API
FastAPI + WebSocket managing timer lifecycle
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, List
import asyncio
import logging
from datetime import datetime, timedelta
import json
import os

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI App
# Use environment variable for root path, default to English version if not set or customizable
root_path = os.getenv('ROOT_PATH', '/tools/wos/refill-bot-en')

app = FastAPI(
    title="Refill Timer API",
    version="1.0.0",
    root_path=root_path
)

# CORS Settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Should restrict origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global State (Use Redis or DB in production)
timers: Dict[str, dict] = {}
websocket_connections: List[WebSocket] = []
discord_bot_callback = None  # To be set by bot.py
MAX_ACTIVE_TIMERS = 6

# Pydantic Models
class TimerCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    minutes: int = Field(default=0, ge=0, le=59)
    seconds: int = Field(default=0, ge=0, le=59)

class TimerUpdate(BaseModel):
    adjust_seconds: int = Field(..., ge=-60, le=60)

class TimerResponse(BaseModel):
    id: str
    name: str
    remaining_seconds: int
    total_seconds: int
    status: str  # 'active', 'completed', 'deleted'
    discord_message_id: Optional[str] = None

# Utility Functions
def get_remaining_seconds(t_end: datetime) -> int:
    """Calculate remaining seconds (prevent drift)"""
    remaining = (t_end - datetime.now()).total_seconds()
    return max(0, int(remaining))

async def broadcast_state():
    """Broadcast current timer states to all WebSocket clients"""
    if not websocket_connections:
        return
    
    timer_list = []
    for timer_id, timer in timers.items():
        remaining = get_remaining_seconds(timer["t_end"])
        timer_list.append({
            "id": timer_id,
            "name": timer["name"],
            "remaining_seconds": remaining,
            "minutes": remaining // 60,
            "seconds": remaining % 60,
            "total_seconds": timer["total_seconds"],
            "status": timer["status"],
            "discord_message_id": timer.get("discord_message_id")
        })
    
    state = {
        "type": "state_update",
        "timers": timer_list
    }
    
    message = json.dumps(state)
    disconnected = []
    
    for ws in websocket_connections:
        try:
            await ws.send_text(message)
        except Exception as e:
            logger.error(f"WebSocket send failed: {e}")
            disconnected.append(ws)
    
    # Remove disconnected connections
    for ws in disconnected:
        if ws in websocket_connections:
            websocket_connections.remove(ws)

async def timer_task(timer_id: str):
    """Timer Task: Updates every second and triggers Discord updates when appropriate"""
    timer = timers.get(timer_id)
    if not timer:
        return
    
    logger.info(f"Timer started: {timer_id} - {timer['name']}")
    
    try:
        last_update_time = datetime.now()
        
        while True:
            now = datetime.now()
            remaining = get_remaining_seconds(timer["t_end"])
            
            # Check if completed
            if remaining <= 0:
                timer["status"] = "completed"
                logger.info(f"Timer completed: {timer_id}")
                
                # Notify Discord Bot to show REFILL
                if discord_bot_callback:
                    try:
                        loop = asyncio.get_event_loop()
                        await loop.run_in_executor(
                            None, discord_bot_callback, "timer_complete", timer_id
                        )
                    except Exception as e:
                        logger.error(f"Discord callback failed: {e}")
                
                # Broadcast completion status
                await broadcast_state()
                
                # Timer remains in list, not deleted automatically
                # User can click "Restart" or "Delete"
                break
            
            # Update Discord every second (not limited to 60s)
            if discord_bot_callback:
                try:
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(
                        None, discord_bot_callback, "timer_tick", timer_id, remaining
                    )
                except Exception as e:
                    logger.error(f"Discord tick failed: {e}")
            
            # Broadcast state every second
            if (now - last_update_time).total_seconds() >= 1:
                await broadcast_state()
                last_update_time = now
            
            # Precise wait for next second
            next_tick = now + timedelta(seconds=1)
            sleep_duration = (next_tick - datetime.now()).total_seconds()
            if sleep_duration > 0:
                await asyncio.sleep(sleep_duration)
            
    except asyncio.CancelledError:
        logger.info(f"Timer cancelled: {timer_id}")
        timer["status"] = "deleted"
        await broadcast_state()
    except Exception as e:
        logger.error(f"Timer task error {timer_id}: {e}")
        timer["status"] = "error"

# API Routes
@app.get("/api/health")
async def health_check():
    """Health Check"""
    return {
        "status": "healthy",
        "active_timers": len([t for t in timers.values() if t["status"] == "active"]),
        "total_timers": len(timers)
    }

@app.get("/api/timers")
async def get_timers():
    """Get all timers"""
    result = []
    for timer_id, timer in timers.items():
        remaining = get_remaining_seconds(timer["t_end"])
        result.append({
            "id": timer_id,
            "name": timer["name"],
            "remaining_seconds": remaining,
            "minutes": remaining // 60,
            "seconds": remaining % 60,
            "total_seconds": timer["total_seconds"],
            "status": timer["status"],
            "discord_message_id": timer.get("discord_message_id")
        })
    return result

@app.post("/api/timers", response_model=TimerResponse, status_code=201)
async def create_timer(timer_data: TimerCreate):
    """Create new timer"""
    # Check limit
    active_count = len([t for t in timers.values() if t["status"] == "active"])
    if active_count >= MAX_ACTIVE_TIMERS:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum active timers limit reached ({MAX_ACTIVE_TIMERS})"
        )
    
    # Calculate end time
    total_seconds = timer_data.minutes * 60 + timer_data.seconds
    if total_seconds == 0:
        raise HTTPException(status_code=400, detail="Time cannot be 0")
    
    t_end = datetime.now() + timedelta(seconds=total_seconds)
    
    # Generate ID
    timer_id = f"timer_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    
    # Create timer
    timer = {
        "id": timer_id,
        "name": timer_data.name,
        "t_end": t_end,
        "total_seconds": total_seconds,
        "status": "active",
        "discord_message_id": None,
        "task": None
    }
    
    timers[timer_id] = timer
    
    # Start task
    timer["task"] = asyncio.create_task(timer_task(timer_id))
    
    # Notify Discord Bot
    if discord_bot_callback:
        try:
            # Run sync callback in executor
            loop = asyncio.get_event_loop()
            message_id = await loop.run_in_executor(
                None, discord_bot_callback, "timer_create", timer_id
            )
            timer["discord_message_id"] = message_id
        except Exception as e:
            logger.error(f"Discord create message failed: {e}", exc_info=True)
    
    logger.info(f"Timer created: {timer_id} - {timer_data.name}")
    await broadcast_state()
    
    return TimerResponse(
        id=timer_id,
        name=timer["name"],
        remaining_seconds=total_seconds,
        total_seconds=total_seconds,
        status="active",
        discord_message_id=timer.get("discord_message_id")
    )

@app.patch("/api/timers/{timer_id}")
async def update_timer(timer_id: str, update_data: TimerUpdate):
    """Adjust timer (+1s/-1s)"""
    if timer_id not in timers:
        raise HTTPException(status_code=404, detail="Timer does not exist")
    
    timer = timers[timer_id]
    
    if timer["status"] != "active":
        raise HTTPException(status_code=400, detail="Timer has finished")
    
    # Adjust end time
    timer["t_end"] += timedelta(seconds=update_data.adjust_seconds)
    
    # Update total seconds
    timer["total_seconds"] += update_data.adjust_seconds
    
    logger.info(f"Timer adjusted: {timer_id} ({update_data.adjust_seconds:+d}s)")
    await broadcast_state()
    
    return {"message": "Adjusted", "remaining": get_remaining_seconds(timer["t_end"])}

@app.post("/api/timers/{timer_id}/restart")
async def restart_timer(timer_id: str):
    """Restart timer (countdown from initial time)"""
    if timer_id not in timers:
        raise HTTPException(status_code=404, detail="Timer does not exist")
    
    timer = timers[timer_id]
    
    # Cancel existing task if running
    if timer.get("task") and not timer["task"].done():
        timer["task"].cancel()
        try:
            await timer["task"]
        except asyncio.CancelledError:
            pass
    
    # Recalculate end time (using original total seconds)
    total_seconds = timer["total_seconds"]
    timer["t_end"] = datetime.now() + timedelta(seconds=total_seconds)
    timer["status"] = "active"
    
    # Start new timer task
    timer["task"] = asyncio.create_task(timer_task(timer_id))
    
    logger.info(f"Timer restarted: {timer_id} ({total_seconds}s)")
    await broadcast_state()
    
    return {
        "message": "Restarted",
        "remaining": total_seconds,
        "total_seconds": total_seconds
    }

@app.delete("/api/timers/{timer_id}")
async def delete_timer(timer_id: str):
    """Delete timer"""
    if timer_id not in timers:
        raise HTTPException(status_code=404, detail="Timer does not exist")
    
    timer = timers[timer_id]
    
    # Cancel task
    if timer.get("task"):
        timer["task"].cancel()
        try:
            await timer["task"]
        except asyncio.CancelledError:
            pass
    
    # Notify Discord Bot to delete message
    if discord_bot_callback:
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, discord_bot_callback, "timer_delete", timer_id
            )
        except Exception as e:
            logger.error(f"Discord delete message failed: {e}", exc_info=True)
    
    # Remove timer
    del timers[timer_id]
    
    logger.info(f"Timer deleted: {timer_id}")
    await broadcast_state()
    
    return {"message": "Deleted"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket Endpoint: Push real-time timer updates"""
    await websocket.accept()
    websocket_connections.append(websocket)
    
    logger.info(f"WebSocket Connected: {len(websocket_connections)} active connections")
    
    try:
        # Send initial state
        await broadcast_state()
        
        # Keep connection open and receive messages
        while True:
            data = await websocket.receive_text()
            # Can handle client commands here
            logger.debug(f"Received WebSocket message: {data}")
            
    except WebSocketDisconnect:
        logger.info("WebSocket Disconnected")
    except Exception as e:
        logger.error(f"WebSocket Error: {e}")
    finally:
        if websocket in websocket_connections:
            websocket_connections.remove(websocket)

# Functions called by bot.py
def set_discord_callback(callback):
    """Set Discord Bot callback function"""
    global discord_bot_callback
    discord_bot_callback = callback
    logger.info("Discord Bot callback set")

def get_timer(timer_id: str) -> Optional[dict]:
    """Get specific timer"""
    return timers.get(timer_id)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv('PORT', 8000))
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
