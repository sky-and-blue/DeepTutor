"""
Unified WebSocket Endpoint
==========================

Single ``/api/v1/ws`` endpoint for turn-based execution and replayable streaming.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
from deeptutor.services.auth import (
    decode_token,
    get_token,
    get_user_by_id,
)
from deeptutor.logging import get_logger

router = APIRouter()
logger = get_logger("UnifiedWS")


async def authenticate_websocket(ws: WebSocket, token: str | None = None) -> bool:
    """
    验证WebSocket连接的认证
    
    Args:
        ws: WebSocket对象
        token: 访问令牌
        
    Returns:
        bool: 是否认证成功
    """
    if not token:
        await ws.close(code=status.WS_1008_POLICY_VIOLATION, reason="未提供认证令牌")
        return False
    
    try:
        # 检查令牌是否在Redis中
        token_data = await get_token(token)
        if not token_data:
            await ws.close(code=status.WS_1008_POLICY_VIOLATION, reason="无效的认证令牌")
            return False
        
        # 解码令牌
        payload = decode_token(token)
        
        # 获取用户ID
        user_id_str = payload.get("sub")
        if not user_id_str:
            await ws.close(code=status.WS_1008_POLICY_VIOLATION, reason="无效的认证令牌")
            return False
        
        # 转换用户ID为整数
        try:
            user_id = int(user_id_str)
        except ValueError:
            await ws.close(code=status.WS_1008_POLICY_VIOLATION, reason="无效的用户ID")
            return False
        
        # 获取用户信息
        user = await get_user_by_id(user_id)
        if not user:
            await ws.close(code=status.WS_1008_POLICY_VIOLATION, reason="用户不存在")
            return False
        
        # 将用户信息存储到WebSocket状态中
        ws.state.user = user
        return True
        
    except Exception as e:
        logger.error(f"WebSocket认证失败: {str(e)}")
        await ws.close(code=status.WS_1008_POLICY_VIOLATION, reason="认证失败")
        return False


@router.websocket("/ws")
async def unified_websocket(ws: WebSocket, token: str = Query(..., description="访问令牌")) -> None:
    # 首先验证WebSocket连接的认证
    if not await authenticate_websocket(ws, token):
        return
    
    await ws.accept()
    closed = False
    subscription_tasks: dict[str, asyncio.Task[None]] = {}

    async def safe_send(data: dict[str, Any]) -> None:
        nonlocal closed
        if closed:
            return
        try:
            await ws.send_json(data)
        except Exception:
            closed = True

    async def stop_subscription(key: str) -> None:
        task = subscription_tasks.pop(key, None)
        if task is None:
            return
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    async def subscribe_turn(turn_id: str, after_seq: int = 0) -> None:
        from deeptutor.services.session import get_turn_runtime_manager

        async def _forward() -> None:
            runtime = get_turn_runtime_manager()
            async for event in runtime.subscribe_turn(turn_id, after_seq=after_seq):
                await safe_send(event)

        await stop_subscription(turn_id)
        subscription_tasks[turn_id] = asyncio.create_task(_forward())

    async def subscribe_session(session_id: str, after_seq: int = 0) -> None:
        from deeptutor.services.session import get_turn_runtime_manager

        async def _forward() -> None:
            runtime = get_turn_runtime_manager()
            async for event in runtime.subscribe_session(session_id, after_seq=after_seq):
                await safe_send(event)

        key = f"session:{session_id}"
        await stop_subscription(key)
        subscription_tasks[key] = asyncio.create_task(_forward())

    try:
        while not closed:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await safe_send({"type": "error", "content": "Invalid JSON."})
                continue

            msg_type = msg.get("type")

            if msg_type in {"message", "start_turn"}:
                from deeptutor.services.session import get_turn_runtime_manager

                runtime = get_turn_runtime_manager()
                try:
                    _, turn = await runtime.start_turn(msg)
                except RuntimeError as exc:
                    await safe_send(
                        {
                            "type": "error",
                            "source": "unified_ws",
                            "stage": "",
                            "content": str(exc),
                            "metadata": {"turn_terminal": True, "status": "rejected"},
                            "session_id": str(msg.get("session_id") or ""),
                            "turn_id": "",
                            "seq": 0,
                        }
                    )
                    continue
                await subscribe_turn(turn["id"], after_seq=0)
                continue

            if msg_type == "subscribe_turn":
                turn_id = str(msg.get("turn_id") or "").strip()
                if not turn_id:
                    await safe_send({"type": "error", "content": "Missing turn_id."})
                    continue
                await subscribe_turn(turn_id, after_seq=int(msg.get("after_seq") or 0))
                continue

            if msg_type == "subscribe_session":
                session_id = str(msg.get("session_id") or "").strip()
                if not session_id:
                    await safe_send({"type": "error", "content": "Missing session_id."})
                    continue
                await subscribe_session(session_id, after_seq=int(msg.get("after_seq") or 0))
                continue

            if msg_type == "resume_from":
                turn_id = str(msg.get("turn_id") or "").strip()
                if not turn_id:
                    await safe_send({"type": "error", "content": "Missing turn_id."})
                    continue
                await subscribe_turn(turn_id, after_seq=int(msg.get("seq") or 0))
                continue

            if msg_type == "unsubscribe":
                turn_id = str(msg.get("turn_id") or "").strip()
                if turn_id:
                    await stop_subscription(turn_id)
                session_id = str(msg.get("session_id") or "").strip()
                if session_id:
                    await stop_subscription(f"session:{session_id}")
                continue

            if msg_type == "cancel_turn":
                turn_id = str(msg.get("turn_id") or "").strip()
                if not turn_id:
                    await safe_send({"type": "error", "content": "Missing turn_id."})
                    continue
                from deeptutor.services.session import get_turn_runtime_manager

                runtime = get_turn_runtime_manager()
                cancelled = await runtime.cancel_turn(turn_id)
                if not cancelled:
                    await safe_send({"type": "error", "content": f"Turn not found: {turn_id}"})
                continue

            await safe_send({"type": "error", "content": f"Unknown type: {msg_type}"})

    except WebSocketDisconnect:
        logger.debug("Client disconnected from /ws")
    except Exception as exc:
        logger.error("Unified WS error: %s", exc, exc_info=True)
        await safe_send({"type": "error", "content": str(exc)})
    finally:
        closed = True
        for key in list(subscription_tasks.keys()):
            await stop_subscription(key)
