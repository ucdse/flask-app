# app/api/chat_routes.py
import logging

from flask import Blueprint, request, jsonify, Response, stream_with_context

from app.services.chat_service import generate_chat_response, generate_chat_stream
from app.services.user_service import AuthError, verify_access_token

logger = logging.getLogger(__name__)
chat_bp = Blueprint('chat', __name__, url_prefix='/api/chat')


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


def _build_secure_session_id(user_id: int, chat_id: str) -> str:
    """由 JWT 中的 user_id 与前端传来的 chat_id 组装 session_id，避免越权访问。"""
    return f"user_{user_id}_chat_{chat_id or 'default'}"


@chat_bp.route('/', methods=['POST'])
def chat():
    payload, err = _require_auth()
    if err is not None:
        return err[0], err[1]

    data = request.json
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    message = data.get("message")
    chat_id = data.get("chat_id") or "default"

    if not message:
        return jsonify({"error": "Missing 'message'"}), 400

    user_id = payload["sub"]
    secure_session_id = _build_secure_session_id(user_id, chat_id)

    try:
        reply = generate_chat_response(secure_session_id, message)
        return jsonify({"chat_id": chat_id, "reply": reply})
    except Exception:
        logger.exception("Chat request failed")
        return jsonify({"error": "服务暂时不可用，请稍后重试"}), 500


@chat_bp.route('/stream', methods=['POST'])
def chat_stream_api():
    payload, err = _require_auth()
    if err is not None:
        return err[0], err[1]

    data = request.json
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    message = data.get("message")
    chat_id = data.get("chat_id") or "default"

    if not message:
        return jsonify({"error": "Missing 'message'"}), 400

    user_id = payload["sub"]
    secure_session_id = _build_secure_session_id(user_id, chat_id)

    return Response(
        stream_with_context(generate_chat_stream(secure_session_id, message)),
        mimetype='text/event-stream'
    )
