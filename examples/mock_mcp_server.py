#!/usr/bin/env python3
"""
Standalone Mock Model Context Protocol (MCP) Server.
Communicates via stdio JSON-RPC 2.0.
Provides 3 tools:
- get_system_time
- text_transformer
- query_sensor
"""
from datetime import datetime
import json
import sys


def handle_request(req: dict) -> dict:
    method = req.get("method")
    req_id = req.get("id")
    params = req.get("params") or {}

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {},
                },
                "serverInfo": {
                    "name": "mock-mcp-server",
                    "version": "1.0.0",
                },
            },
        }

    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": [
                    {
                        "name": "get_system_time",
                        "description": "Returns current UTC system time and date formatted as ISO-8601",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "format": {
                                    "type": "string",
                                    "description": "Optional strftime format string (e.g. '%Y-%m-%d %H:%M:%S')",
                                }
                            },
                        },
                    },
                    {
                        "name": "text_transformer",
                        "description": "Transform text via uppercase, lowercase, reverse, or count_words",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "text": {"type": "string", "description": "Text to transform"},
                                "operation": {
                                    "type": "string",
                                    "enum": ["uppercase", "lowercase", "reverse", "count_words"],
                                    "description": "Transformation operation to apply",
                                },
                            },
                            "required": ["text", "operation"],
                        },
                    },
                    {
                        "name": "query_sensor",
                        "description": "Query telemetry reading from an IoT or drone sensor ID",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "sensor_id": {"type": "string", "description": "Sensor identifier, e.g. 'gps_01' or 'temp_04'"}
                            },
                            "required": ["sensor_id"],
                        },
                    },
                ]
            },
        }

    elif method == "tools/call":
        tool_name = params.get("name")
        args = params.get("arguments") or {}

        if tool_name == "get_system_time":
            fmt = args.get("format") or "%Y-%m-%d %H:%M:%S UTC"
            now_str = datetime.utcnow().strftime(fmt)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": f"Current system time: {now_str}"}],
                    "isError": False,
                },
            }

        elif tool_name == "text_transformer":
            txt = args.get("text", "")
            op = args.get("operation", "uppercase")
            if op == "uppercase":
                res = txt.upper()
            elif op == "lowercase":
                res = txt.lower()
            elif op == "reverse":
                res = txt[::-1]
            elif op == "count_words":
                res = f"Word count: {len(txt.split())}"
            else:
                res = f"Unknown operation: {op}"

            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": res}],
                    "isError": False,
                },
            }

        elif tool_name == "query_sensor":
            s_id = args.get("sensor_id", "")
            val = {
                "sensor_id": s_id,
                "status": "ONLINE",
                "battery": "94%",
                "signal_dbm": -42,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(val, indent=2)}],
                    "isError": False,
                },
            }

        else:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Tool '{tool_name}' not found"},
            }

    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": f"Method '{method}' not found"},
    }


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except Exception:
            continue

        # Ignore notifications (no id)
        if "id" not in req:
            continue

        resp = handle_request(req)
        sys.stdout.write(json.dumps(resp) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
