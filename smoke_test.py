#!/usr/bin/env python3
"""Тест собранного Docker-образа: поднимаем контейнер и говорим с ним по MCP.

Проверяем не «собралось», а что сервер внутри контейнера реально отвечает:
initialize → tools/list → tools/call topup_link → tools/call get_balance без ключа.
"""
from __future__ import annotations

import json
import subprocess
import sys

msgs = [
    {"jsonrpc": "2.0", "id": 1, "method": "initialize",
     "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                "clientInfo": {"name": "docker-smoke", "version": "1.0"}}},
    {"jsonrpc": "2.0", "method": "notifications/initialized"},
    {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
    {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
     "params": {"name": "topup_link", "arguments": {"amount_eur": 8}}},
    {"jsonrpc": "2.0", "id": 4, "method": "tools/call",
     "params": {"name": "get_balance", "arguments": {}}},
]

proc = subprocess.Popen(
    ["docker", "run", "-i", "--rm", "--network", "none", "duebuddy-mcp:test"],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

for m in msgs:
    proc.stdin.write(json.dumps(m) + "\n")
proc.stdin.flush()

seen = {}
for _ in range(20):
    line = proc.stdout.readline()
    if not line:
        break
    try:
        data = json.loads(line)
    except json.JSONDecodeError:
        continue
    if "id" in data:
        seen[data["id"]] = data
    if len(seen) == 4:
        break

ok = True
init = seen.get(1, {})
if init.get("result", {}).get("serverInfo"):
    print("initialize:", init["result"]["serverInfo"].get("name"),
          init["result"]["serverInfo"].get("version") or "")
else:
    print("initialize: ОШИБКА", init)
    ok = False

tools = seen.get(2, {}).get("result", {}).get("tools", [])
print(f"tools/list: {len(tools)} инструментов —", ", ".join(t["name"] for t in tools))
ok = ok and len(tools) == 4

topup = seen.get(3, {}).get("result", {})
topup_body = topup.get("structuredContent") or {}
print("tools/call topup_link:", json.dumps(topup_body, ensure_ascii=False)[:160])
ok = ok and bool(topup_body.get("url"))

bal = seen.get(4, {}).get("result", {})
bal_body = bal.get("structuredContent") or {}
print("tools/call get_balance без ключа:", json.dumps(bal_body, ensure_ascii=False)[:160])
ok = ok and bal_body.get("error") == "api_key_required"

proc.kill()
err = proc.stderr.read()[:400]
if err.strip():
    print("stderr:", err.strip()[:300])

print("\nИТОГ:", "все проверки пройдены" if ok else "ЕСТЬ ОШИБКИ")
sys.exit(0 if ok else 1)
