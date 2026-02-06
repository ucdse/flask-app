from flask import Blueprint, jsonify, request

from app.schemas.user_schema import UserSchemaError, validate_user_registration
from app.services.user_service import UserRegistrationError, register_user

user_bp = Blueprint("user", __name__, url_prefix="/api/users")


@user_bp.post("/register")
def register():
    payload = request.get_json(silent=True)

    try:
        validated_payload = validate_user_registration(payload)
        user_data = register_user(validated_payload)
    except UserSchemaError as exc:
        return jsonify({"code": 40001, "msg": str(exc), "data": None}), 400
    except UserRegistrationError as exc:
        code_map = {
            "username_exists": 40901,
            "email_exists": 40902,
            "user_conflict": 40903,
        }
        return jsonify({"code": code_map.get(exc.error_code, 40000), "msg": exc.message, "data": None}), exc.status_code

    return jsonify({"code": 0, "msg": "user registered", "data": user_data}), 201
