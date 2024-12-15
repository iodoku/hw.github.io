from flask import Flask, request, jsonify
from flask_mysqldb import MySQL
from flask_jwt_extended import JWTManager, create_access_token, create_refresh_token, jwt_required, get_jwt_identity
from flask_swagger_ui import get_swaggerui_blueprint
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import datetime


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


def authlogin(mysql):
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    # 데이터베이스에서 사용자 정보 조회
    cur = mysql.connection.cursor()
    cur.execute("SELECT id, password FROM users WHERE email = %s", (email,))
    user = cur.fetchone()
    cur.close()

    if not user or not check_password_hash(user[1], password):
        return jsonify({"message": "Invalid email or password"}), 400

    # JWT 토큰 생성
    access_token = create_access_token(identity=str(user[0]))
    refresh_token = create_refresh_token(identity=str(user[0]))

    # 로그인 이력 저장
    cur = mysql.connection.cursor()
    cur.execute(
        "INSERT INTO login_logs (user_id, login_time, ip_address) VALUES (%s, %s, %s)",
        (user[0], datetime.datetime.now(), request.remote_addr)
    )
    mysql.connection.commit()
    cur.close()

    return jsonify({"access_token": access_token, "refresh_token": refresh_token}), 200

def authrefresh(mysql):
    current_user = get_jwt_identity()
    new_access_token = create_access_token(identity=current_user)
    return jsonify({"access_token": new_access_token}), 200


def authprofile(mysql):
    current_user_id = get_jwt_identity()  # JWT에서 가져온 사용자 ID
    if not isinstance(current_user_id, str):
        return jsonify({"message": "Invalid user ID format"}), 400

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

    return jsonify({"message": "Profile updated successfully"}), 200
