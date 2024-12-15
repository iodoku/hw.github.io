# -*- coding: utf-8 -*-
from flask import Response,Flask, request, jsonify
from flask_mysqldb import MySQL
from flask_jwt_extended import JWTManager, create_access_token, create_refresh_token, jwt_required, get_jwt_identity
from flask_swagger_ui import get_swaggerui_blueprint
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from Auth import authregister, authlogin, authrefresh, authprofile
from Posting import postjobs, postjobsid
from Apply import applypostapplications,applygetapplications,applydeleteapplications
from Bookmarks import postbookmarks,getbookmarks
from Ratings import postratings,getratings
from Recommands import getrecommands
from jobcrawl import save_to_mysql
from MySQLdb.cursors import DictCursor
import mysql.connector
import re
from collections import OrderedDict
import json
from math import ceil


def communitypost(mysql):
    cursor = None  # 커서 초기화
    try:
        # JWT에서 사용자 ID 가져오기
        user_id = get_jwt_identity()

        # 요청 데이터
        data = request.get_json()
        title = data.get('title')
        content = data.get('content')

        # 제목과 내용 검증
        if not title or not content:
            response_data = {
                "status": "error",
                "message": "Title and content are required.",
                "code": "400"
            }
            return Response(json.dumps(response_data), status=400, mimetype="application/json")

        # 게시글 저장
        connection = mysql.connection
        cursor = connection.cursor()
        query = """
        INSERT INTO posts (user_id, title, content, created_at)
        VALUES (%s, %s, %s, %s)
        """
        cursor.execute(query, (user_id, title, content, datetime.now()))
        connection.commit()

        # 성공 응답
        response_data = {
            "status": "success",
            "message": "Post created successfully.",
            "data": {
                "post_id": cursor.lastrowid,
                "title": title,
                "content": content,
                "user_id": user_id,
                "created_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        }
        return Response(json.dumps(response_data, ensure_ascii=False, indent=4), status=201, mimetype="application/json")

    except Exception as e:
        # 예외 처리
        response_data = {
            "status": "error",
            "message": "An error occurred while creating the post.",
            "details": str(e),
            "code": "500"
        }
        return Response(json.dumps(response_data), status=500, mimetype="application/json")

    finally:
        if cursor:
            cursor.close()

def communityget(mysql):
    cursor = None  # 커서 초기화
    try:
        # 정렬 기준 및 페이지 관련 파라미터
        sort_order = request.args.get('sort', default='작성느린순', type=str)  # 기본값: 작성느린순
        page = request.args.get('page', type=int, default=1)  # 페이지 번호
        per_page = 20  # 한 페이지에 최대 20개 표시

        # 정렬 기준 변환
        if sort_order == '작성빠른순':
            sql_sort_order = 'ASC'
        elif sort_order == '작성느린순':
            sql_sort_order = 'DESC'
        else:
            response_data = {
                "status": "error",
                "message": "Invalid sort parameter. Use '작성빠른순' or '작성느린순'.",
                "code": "400"
            }
            return Response(json.dumps(response_data), status=400, mimetype="application/json")

        # 게시글 가져오기
        connection = mysql.connection
        cursor = connection.cursor(DictCursor)
        query = f"""
        SELECT id, user_id, title, content, created_at, updated_at
        FROM posts
        ORDER BY created_at {sql_sort_order}
        LIMIT %s OFFSET %s
        """
        offset = (page - 1) * per_page
        cursor.execute(query, (per_page, offset))
        posts = cursor.fetchall()

        # 총 게시글 수 계산
        cursor.execute("SELECT COUNT(*) AS total_posts FROM posts;")
        total_posts_result = cursor.fetchone()
        total_posts = total_posts_result['total_posts'] if total_posts_result else 0

        # 페이지네이션 정보 계산
        total_pages = ceil(total_posts / per_page)

        # 성공 응답 데이터 생성
        response_data = {
            "status": "success",
            "data": {
                "pagination": {
                    "page": page,
                    "total_pages": total_pages,
                    "total_posts": total_posts
                },
                "posts": [
                    {
                        "id": post["id"],
                        "user_id": post["user_id"],
                        "title": post["title"],
                        "content": post["content"],
                        "created_at": post["created_at"].strftime('%Y-%m-%d %H:%M:%S') if post["created_at"] else None,
                        "updated_at": post["updated_at"].strftime('%Y-%m-%d %H:%M:%S') if post["updated_at"] else None
                    }
                    for post in posts
                ]
            }
        }
        return Response(json.dumps(response_data, ensure_ascii=False, indent=4), status=200, mimetype="application/json")

    except Exception as e:
        # 예외 처리
        response_data = {
            "status": "error",
            "message": "An unexpected error occurred",
            "details": str(e),
            "code": "500"
        }
        return Response(json.dumps(response_data), status=500, mimetype="application/json")

    finally:
        if cursor:
            cursor.close()