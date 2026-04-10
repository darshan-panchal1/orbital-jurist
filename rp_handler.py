# rp_handler.py
import runpod
import os
from dotenv import load_dotenv

load_dotenv()

from mcp_servers.registry import load_tools
from workflow.graph import OrbitalJuristWorkflow

# Load tools and initialize workflow once at cold-start (not per request)
print("Loading MCP tools...")
orbital_tools, legal_tools = load_tools()
workflow = OrbitalJuristWorkflow(orbital_tools, legal_tools)
print("Workflow initialized.")


async def handler(job):
    job_input = job.get("input", {})

    object_1_id      = job_input.get("object_1_id")
    object_2_id      = job_input.get("object_2_id")
    conjunction_time = job_input.get("conjunction_time")  # Optional ISO string

    if not object_1_id or not object_2_id:
        return {"error": "Missing required fields: 'object_1_id' and 'object_2_id'"}

    if not isinstance(object_1_id, int) or not isinstance(object_2_id, int):
        return {"error": "'object_1_id' and 'object_2_id' must be integers (NORAD IDs)"}

    if object_1_id == object_2_id:
        return {"error": "'object_1_id' and 'object_2_id' must be different NORAD IDs"}

    from datetime import datetime, timezone
    conjunction_time = conjunction_time or datetime.now(timezone.utc).isoformat()

    try:
        final_state = await workflow.run(
            object_1_id=object_1_id,
            object_2_id=object_2_id,
            conjunction_time=conjunction_time,
        )
    except Exception as e:
        return {"error": f"Workflow execution failed: {str(e)}"}

    if final_state.get("error_message"):
        return {"error": final_state["error_message"]}

    judgment  = final_state.get("final_judgment", {})
    obj1      = final_state.get("object_1_data", {})
    obj2      = final_state.get("object_2_data", {})
    miss_data = final_state.get("miss_distance_data") or {}

    return {
        "judgment": judgment,
        "metadata": {
            "case_id":            final_state.get("case_id"),
            "object_1_name":      obj1.get("sat_name", f"NORAD {object_1_id}"),
            "object_2_name":      obj2.get("sat_name", f"NORAD {object_2_id}"),
            "object_1_status":    obj1.get("status"),
            "object_2_status":    obj2.get("status"),
            "conjunction_time":   conjunction_time,
            "miss_distance_km":   miss_data.get("minimum_distance_km"),
            "collision_occurred": miss_data.get("minimum_distance_km", float("inf")) < 1.0,
            "verdict_complete":   final_state.get("verdict_complete", False),
            "prompt_version":     judgment.get("prompt_version"),
        },
    }


if __name__ == "__main__":
    runpod.serverless.start({"handler": handler})