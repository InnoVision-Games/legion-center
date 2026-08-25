#!/usr/bin/env python3
"""Call a deployed plugin method through Decky Loader's local WebSocket API."""

import argparse
import asyncio
import json

import aiohttp


async def call_plugin(plugin: str, method: str, arguments):
    async with aiohttp.ClientSession() as session:
        async with session.get("http://127.0.0.1:1337/auth/token") as response:
            response.raise_for_status()
            token = await response.text()

        url = f"ws://127.0.0.1:1337/ws?auth={token}"
        async with session.ws_connect(url) as websocket:
            request_id = 900001
            await websocket.send_json(
                {
                    "type": 0,
                    "route": "loader/call_plugin_method",
                    "args": [plugin, method, *arguments],
                    "id": request_id,
                }
            )

            async for message in websocket:
                if message.type != aiohttp.WSMsgType.TEXT:
                    continue
                payload = json.loads(message.data)
                if payload.get("id") != request_id:
                    continue

                await websocket.send_json({"type": 3, "id": request_id})
                if payload.get("type") == 1:
                    return payload.get("result")
                if payload.get("type") == -1:
                    error = payload.get("error") or {}
                    raise RuntimeError(
                        error.get("message")
                        or error.get("error")
                        or json.dumps(error, sort_keys=True)
                    )
                raise RuntimeError(f"Decky discarded request {request_id}")

    raise RuntimeError("Decky WebSocket closed without replying")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("plugin")
    parser.add_argument("method")
    parser.add_argument(
        "arguments",
        nargs="?",
        default="[]",
        help="JSON array containing positional method arguments",
    )
    args = parser.parse_args()
    arguments = json.loads(args.arguments)
    if not isinstance(arguments, list):
        parser.error("arguments must be a JSON array")

    result = asyncio.run(call_plugin(args.plugin, args.method, arguments))
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
