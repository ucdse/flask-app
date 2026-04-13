# app/api/chat_routes.py
import logging

from flask import Blueprint, request, jsonify, Response, stream_with_context

from app.extensions import db
from app.models import Session
from app.services.chat_service import (
    generate_chat_response,
    generate_chat_stream,
    get_session_messages,
    generate_session_id,
)
from app.services.user_service import AuthError, verify_access_token

logger = logging.getLogger(__name__)
chat_bp = Blueprint("chat", __name__, url_prefix="/api/chat")


def _require_auth():
    """要求请求携带有效 access_token，成功返回 (payload, None)，失败返回 (None, (response, status_code))。"""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.strip().lower().startswith("bearer "):
        return None, (jsonify({"error": "missing or invalid Authorization header"}), 401)
    token = auth_header.strip()[7:].strip()
    try:
        payload = verify_access_token(token)
        return payload, None
    except AuthError as exc:
        return None, (jsonify({"error": exc.message}), 401)


@chat_bp.route("/", methods=["POST"])
def chat():
    payload, err = _require_auth()
    if err is not None:
        return err[0], err[1]

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return (
            jsonify(
                {
                    "code": 40001,
                    "msg": "Request body must be a JSON object",
                    "data": None,
                }
            ),
            400,
        )

    message = data.get("message")
    chat_id = data.get("chat_id")

    if not message or not isinstance(message, str):
        return (
            jsonify(
                {
                    "code": 40001,
                    "msg": "message field is required",
                    "data": None,
                }
            ),
            400,
        )

    user_id = payload["sub"]
    session_id = generate_session_id(user_id, chat_id)

    try:
        reply = generate_chat_response(session_id, message, user_id)
        data = {
            "chat_id": chat_id,
            "reply": reply,
        }
        return jsonify({"code": 0, "msg": "ok", "data": data}), 200
    except Exception:
        logger.exception("Chat request failed")
        return (
            jsonify(
                {
                    "code": 50000,
                    "msg": "Service temporarily unavailable, please try again later",
                    "data": None,
                }
            ),
            500,
        )


@chat_bp.route("/stream", methods=["POST"])
def chat_stream_api():
    payload, err = _require_auth()
    if err is not None:
        return err[0], err[1]

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Request body must be a JSON object"}), 400

    message = data.get("message")
    chat_id = data.get("chat_id")

    if not message or not isinstance(message, str):
        return jsonify({"error": "message field is required"}), 400

    user_id = payload["sub"]
    session_id = generate_session_id(user_id, chat_id)

    return Response(
        stream_with_context(generate_chat_stream(session_id, message, user_id)),
        mimetype="text/event-stream",
        headers={
            "X-Accel-Buffering": "no",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@chat_bp.route("/sessions", methods=["GET"])
def list_sessions():
    """
    返回当前用户的历史会话列表。
    认证方式与聊天接口一致：需要携带 Authorization: Bearer <access_token>。
    """
    payload, err = _require_auth()
    if err is not None:
        return err[0], err[1]

    user_id = payload["sub"]
    sessions = (
        db.session.query(Session)
        .filter_by(user_id=user_id)
        .order_by(Session.updated_at.desc())
        .all()
    )

    data = [
        {
            "session_id": s.id,
            "title": s.title or "New Chat",
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in sessions
    ]

    return jsonify({"code": 0, "msg": "ok", "data": data}), 200


@chat_bp.route("/sessions/<path:session_id>/messages", methods=["GET"])
def get_session_history(session_id: str):
    """
    获取指定 session 的历史对话记录。
    需要携带 Authorization: Bearer <access_token>，并且只能访问自己的会话。
    """
    payload, err = _require_auth()
    if err is not None:
        return err[0], err[1]

    user_id = payload["sub"]

    messages = get_session_messages(session_id, user_id)
    if messages is None:
        # 会话不存在或不属于当前用户
        return (
            jsonify(
                {
                    "code": 404,
                    "msg": "session not found",
                    "data": None,
                }
            ),
            404,
        )

    return jsonify(
        {
            "code": 0,
            "msg": "ok",
            "data": {
                "session_id": session_id,
                "messages": messages,
            },
        }
    )
