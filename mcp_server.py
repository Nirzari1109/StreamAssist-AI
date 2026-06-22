"""
pagila-support-mcp: Local MCP-style JSON-RPC server exposing database-backed tools.

Runs on stdio transport.

Start:
    python mcp_server.py

Tools exposed:
    - search_film_catalog
    - get_customer_streaming_subscription
    - get_customer_rental_history

Notes:
    - Uses one JSON-RPC request per line over stdin/stdout.
    - Logs diagnostic messages to stderr so stdout remains clean JSON-RPC.
    - Includes Windows asyncio compatibility for PowerShell/stdin pipes.
"""
import asyncio
import json
import sys
from typing import Any

from app.tools.tools import (
    search_film_catalog,
    get_customer_streaming_subscription,
    get_customer_rental_history,
    TOOL_REGISTRY,
)
from app.models.schemas import FilmSearchInput, SubscriptionInput, RentalHistoryInput
from app.db.database import AsyncSessionLocal


MCP_TOOL_NAMES = [
    "search_film_catalog",
    "get_customer_streaming_subscription",
    "get_customer_rental_history",
]


def jsonrpc_result(req_id: Any, result: dict) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "result": result,
    }


def jsonrpc_error(req_id: Any, code: int, message: str) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {
            "code": code,
            "message": message,
        },
    }


async def handle_request(request: dict) -> dict | None:
    method = request.get("method")
    params = request.get("params", {})
    req_id = request.get("id")

    # Notifications do not require a response.
    if method == "notifications/initialized":
        return None

    if method == "initialize":
        return jsonrpc_result(
            req_id,
            {
                "protocolVersion": "2024-11-05",
                "serverInfo": {
                    "name": "pagila-support-mcp",
                    "version": "1.0.0",
                },
                "capabilities": {
                    "tools": {},
                },
            },
        )

    if method == "tools/list":
        tools = []

        for name in MCP_TOOL_NAMES:
            meta = TOOL_REGISTRY[name]
            tools.append(
                {
                    "name": meta["name"],
                    "description": meta["description"],
                    "inputSchema": meta["input_schema"],
                }
            )

        return jsonrpc_result(req_id, {"tools": tools})

    if method == "tools/call":
        tool_name = params.get("name")
        arguments = dict(params.get("arguments", {}))
        conversation_id = arguments.pop("conversation_id", "mcp_call")

        try:
            async with AsyncSessionLocal() as db:
                if tool_name == "search_film_catalog":
                    result = await search_film_catalog(
                        FilmSearchInput(**arguments),
                        db=db,
                        conversation_id=conversation_id,
                    )

                elif tool_name == "get_customer_streaming_subscription":
                    result = await get_customer_streaming_subscription(
                        SubscriptionInput(**arguments),
                        db=db,
                        conversation_id=conversation_id,
                    )

                elif tool_name == "get_customer_rental_history":
                    result = await get_customer_rental_history(
                        RentalHistoryInput(**arguments),
                        db=db,
                        conversation_id=conversation_id,
                    )

                else:
                    return jsonrpc_error(
                        req_id,
                        -32601,
                        f"Unknown tool: {tool_name}",
                    )

            return jsonrpc_result(
                req_id,
                {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result.model_dump(), default=str),
                        }
                    ]
                },
            )

        except Exception as exc:
            return jsonrpc_error(req_id, -32603, str(exc))

    return jsonrpc_error(req_id, -32601, f"Method not found: {method}")


async def main() -> None:
    """
    MCP-style stdio transport loop.

    Reads one JSON-RPC message per line from stdin and writes one JSON-RPC
    response per line to stdout.
    """
    print(
        "pagila-support-mcp started. Waiting for JSON-RPC requests on stdin...",
        file=sys.stderr,
        flush=True,
    )

    while True:
        line = await asyncio.to_thread(sys.stdin.readline)

        if not line:
            break

        line = line.strip()

        if not line:
            continue

        try:
            request = json.loads(line)
            response = await handle_request(request)

            if response is not None:
                print(json.dumps(response, default=str), flush=True)

        except json.JSONDecodeError as exc:
            error_response = jsonrpc_error(None, -32700, f"Parse error: {exc}")
            print(json.dumps(error_response), flush=True)

        except Exception as exc:
            error_response = jsonrpc_error(None, -32603, str(exc))
            print(json.dumps(error_response), flush=True)


if __name__ == "__main__":
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(main())