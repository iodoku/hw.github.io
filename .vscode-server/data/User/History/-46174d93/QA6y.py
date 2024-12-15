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
from jobcrawl import save_to_mysql
from MySQLdb.cursors import DictCursor
import mysql.connector
import re
from collections import OrderedDict
import json

def postbookmarks(mysql):
    cursor = None  # 커서 초기화
    try:
        # 인증된 사용자 ID 가져오기
        user_id = get_jwt_identity()
        
        # 요청 본문에서 job_id 가져오기
        job_id = request.json.get('job_id')

        if not job_id:
            response_data = {
                "status": "error",
                "message": "존재하지 않는 Job ID",
                "code": "400"
            }
            return Response(json.dumps(response_data), status=400, mimetype="application/json")

        # 데이터베이스 커서 생성
        cursor = mysql.connection.cursor()

        # job_id가 유효한지 확인
        cursor.execute("SELECT id, title, company, location, salary FROM jobs WHERE id = %s", (job_id,))
        job = cursor.fetchone()
        if not job:
            response_data = {
                "status": "error",
                "message": "Job not found",
                "code": "404"
            }
            return Response(json.dumps(response_data), status=404, mimetype="application/json")

        # 이미 북마크가 존재하는지 확인
        cursor.execute("SELECT id FROM bookmarks WHERE user_id = %s AND job_id = %s", (user_id, job_id))
        existing_bookmark = cursor.fetchone()

        if existing_bookmark:
            # 이미 북마크가 있으면 삭제
            cursor.execute("DELETE FROM bookmarks WHERE user_id = %s AND job_id = %s", (user_id, job_id))
            mysql.connection.commit()
            response_data = {
                "status": "success",
                "message": "Bookmark removed successfully"
            }
            return Response(json.dumps(response_data), status=200, mimetype="application/json")

        # 북마크 추가
        cursor.execute("INSERT INTO bookmarks (user_id, job_id) VALUES (%s, %s)", (user_id, job_id))
        mysql.connection.commit()

        # 북마크 추가 성공 메시지와 함께 job 정보도 반환
        response_data = {
            "status": "success",
            "message": "Bookmark added successfully",
            "data": {
                "job": {
                    "id": job[0],
                    "title": job[1],
                    "company": job[2],
                    "location": job[3],
                    "salary": job[4]
                }
            }
        }
        return Response(json.dumps(response_data, ensure_ascii=False, indent=4), status=201, mimetype="application/json")

    except KeyError as e:
        # 요청 본문에 job_id 키가 없는 경우 처리
        response_data = {
            "status": "error",
            "message": f"Missing field: {str(e)}",
            "code": "400"
        }
        return Response(json.dumps(response_data), status=400, mimetype="application/json")

    except mysql.connection.Error as db_error:
        # 데이터베이스 관련 오류 처리
        response_data = {
            "status": "error",
            "message": "Database error occurred",
            "details": str(db_error),
            "code": "500"
        }
        return Response(json.dumps(response_data), status=500, mimetype="application/json")

    except Exception as e:
        # 기타 예외 처리
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