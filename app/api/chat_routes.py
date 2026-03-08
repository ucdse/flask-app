# app/api/chat_routes.py
from flask import Blueprint, request, jsonify
from app.services.chat_service import generate_chat_response

chat_bp = Blueprint('chat', __name__, url_prefix='/api/chat')


@chat_bp.route('/', methods=['POST'])
def chat():
    data = request.json
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    session_id = data.get("session_id")
    message = data.get("message")

    if not session_id or not message:
        return jsonify({"error": "Missing 'session_id' or 'message'"}), 400

    try:
        # 调用 Service 层获取回复
        reply = generate_chat_response(session_id, message)
        return jsonify({"session_id": session_id, "reply": reply})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
