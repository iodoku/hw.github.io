from flask import Response, Flask, request, jsonify
from flask_mysqldb import MySQL
from flask_jwt_extended import JWTManager, create_access_token, create_refresh_token, jwt_required, get_jwt_identity
from flask_swagger_ui import get_swaggerui_blueprint
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
import json


def authregister(mysql):
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    # 유효성 검사
    if not email or '@' not in email:
        response_data = {
            "status": "error",
            "message": "Invalid email format",
            "code": "400"
        }
        return Response(json.dumps(response_data), status=400, mimetype="application/json")

    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM users WHERE email = %s", (email,))
    user = cur.fetchone()
    if user:
        response_data = {
            "status": "error",
            "message": "Email already exists",
            "code": "400"
        }
        return Response(json.dumps(response_data), status=400, mimetype="application/json")

    # 비밀번호 해싱 및 사용자 등록
    hashed_password = generate_password_hash(password)
    cur.execute("INSERT INTO users (username, email, password) VALUES (%s, %s, %s)",
                (username, email, hashed_password))
    mysql.connection.commit()

    # 새로운 사용자의 ID 가져오기
    new_user_id = cur.lastrowid
    cur.close()

    # 성공 응답
    response_data = {
        "status": "success",
        "data": {
            "id": new_user_id,
            "username": username,
            "email": email
        },
        "pagination": None
    }
    return Response(json.dumps(response_data), status=201, mimetype="application/json")


def authregister(mysql):
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    # 유효성 검사
    if not email or '@' not in email:
        return jsonify({
            "status": "error",
            "message": "Invalid email format",
            "code": "400"
        }), 400

    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM users WHERE email = %s", (email,))
    user = cur.fetchone()
    if user:
        return jsonify({
            "status": "error",
            "message": "Email already exists",
            "code": "400"
        }), 400

    # 비밀번호 해싱 및 사용자 등록
    hashed_password = generate_password_hash(password)
    cur.execute("INSERT INTO users (username, email, password) VALUES (%s, %s, %s)",
                (username, email, hashed_password))
    mysql.connection.commit()

    # 새로운 사용자의 ID 가져오기
    new_user_id = cur.lastrowid
    cur.close()

    # 성공 응답
    return jsonify({
        "status": "success",
        "data": {
            "id": new_user_id,
            "username": username,
            "email": email
        },
        "pagination": None
    }), 201

def authrefresh(mysql):
    try:
        # 현재 사용자 가져오기
        current_user = get_jwt_identity()

        # 새 Access Token 생성
        new_access_token = create_access_token(identity=current_user)

        # 성공 응답
        response_data = {
            "status": "success",
            "data": {
                "access_token": new_access_token
            },
            "pagination": None  # 토큰 갱신에는 페이지네이션 필요 없음
        }
        return Response(json.dumps(response_data), status=200, mimetype="application/json")

    except Exception as e:
        # 실패 응답
        response_data = {
            "status": "error",
            "message": "Failed to refresh token",
            "code": "400"
        }
        return Response(json.dumps(response_data), status=400, mimetype="application/json")


def authprofile(mysql):
    # JWT에서 현재 사용자 ID 가져오기
    current_user_id = get_jwt_identity()
    if not isinstance(current_user_id, str):
        response_data = {
            "status": "error",
            "message": "Invalid user ID format",
            "code": "400"
        }
        return Response(json.dumps(response_data), status=400, mimetype="application/json")

    data = request.get_json()
    cur = mysql.connection.cursor()

    # 사용자 정보 업데이트
    if 'username' in data:
        cur.execute("UPDATE users SET username = %s WHERE id = %s", (data['username'], current_user_id))
    if 'password' in data:
        hashed_password = generate_password_hash(data['password'])
        cur.execute("UPDATE users SET password = %s WHERE id = %s", (hashed_password, current_user_id))

    mysql.connection.commit()
    cur.close()

    # 성공 응답
    response_data = {
        "status": "success",
        "data": {
            "message": "Profile updated successfully"
        },
        "pagination": None  # 페이지네이션 필요 없음
    }
    return Response(json.dumps(response_data), status=200, mimetype="application/json")