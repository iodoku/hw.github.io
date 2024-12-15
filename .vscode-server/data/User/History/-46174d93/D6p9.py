# -*- coding: utf-8 -*-
from flask import Flask, request, jsonify
from flask_mysqldb import MySQL
from flask_jwt_extended import JWTManager, create_access_token, create_refresh_token, jwt_required, get_jwt_identity
from flask_swagger_ui import get_swaggerui_blueprint
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from Auth import authregister, authlogin, authrefresh, authprofile
from Posting import postjobs, postjobsid
from Apply import applypostapplications,applygetapplications,applydeleteapplications
from jobcrawl import save_to_mysql
from MySQLdb.cursors import DictCursor
import mysql.connector
import re
from collections import OrderedDict
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


def getbookmarks(mysql):
    user_id = get_jwt_identity()  # 인증된 사용자 ID 가져오기
    page = request.args.get('page', 1, type=int)  # 페이지 번호 (기본값 1)
    page_size = request.args.get('page_size', 20, type=int)  # 페이지 당 항목 수 (기본값 20)
    
    # 시작 인덱스 계산
    offset = (page - 1) * page_size

    # 사용자 북마크 조회 쿼리
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT b.id, b.job_id, j.title, j.company, j.location 
        FROM bookmarks b
        JOIN jobs j ON b.job_id = j.id
        WHERE b.user_id = %s
        ORDER BY b.created_at DESC
        LIMIT %s OFFSET %s
    """, (user_id, page_size, offset))
    bookmarks = cursor.fetchall()
    
    cursor.close()

    if not bookmarks:
        return jsonify({"message": "No bookmarks found"}), 404

    # 북마크 정보 반환
    response_data = {
        "bookmarks": [
            {
                "id": bookmark[0],
                "job_id": bookmark[1],
                "title": bookmark[2],
                "company": bookmark[3],
                "location": bookmark[4],
            }
            for bookmark in bookmarks
        ]
    }
    return json.dumps(response_data), 200, {'Content-Type': 'application/json'}