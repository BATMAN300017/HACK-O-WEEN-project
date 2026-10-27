from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import sqlite3
import json
import asyncio
import time
from app.api.dependencies import get_db, require_permission
from app.core.permissions import Permission
from app.services.transaction_simulator import simulation_service

router = APIRouter()

class SimulationStartRequest(BaseModel):
    scenario: str = "NORMAL_OPERATIONS"
    interval_seconds: float = 1.5

@router.get("/transactions")
async def stream_live_transactions():
    async def event_generator():
        while True:
            # Yield heartbeat/live telemetry update
            status = simulation_service.get_status()
            data_json = json.dumps({
                "type": "SIMULATION_HEARTBEAT",
                "status": status["status"],
                "events_emitted": status["events_emitted"],
                "alerts_triggered": status["alerts_triggered"],
                "timestamp": time.time()
            })
            yield f"data: {data_json}\n\n"
            await asyncio.sleep(2.0)
            
    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.get("/alerts")
async def stream_live_alerts():
    async def alert_generator():
        while True:
            yield f"data: {json.dumps({'type': 'PING', 'time': time.time()})}\n\n"
            await asyncio.sleep(3.0)
    return StreamingResponse(alert_generator(), media_type="text/event-stream")

@router.get("/simulation/status")
def get_simulation_status():
    return simulation_service.get_status()

@router.post("/simulation/start")
def post_start_simulation(req: SimulationStartRequest):
    simulation_service.start_simulation(scenario=req.scenario, interval_sec=req.interval_seconds)
    return {"message": "Simulation started", "scenario": req.scenario}

@router.post("/simulation/pause")
def post_pause_simulation():
    simulation_service.pause_simulation()
    return {"message": "Simulation paused"}

@router.post("/simulation/resume")
def post_resume_simulation():
    simulation_service.resume_simulation()
    return {"message": "Simulation resumed"}

@router.post("/simulation/reset")
def post_reset_simulation():
    simulation_service.stop_simulation()
    return {"message": "Simulation stopped and reset"}

@router.post("/simulation/scenario/{scenario_name}")
def post_run_scenario(scenario_name: str):
    return simulation_service.run_named_scenario(scenario_name)
