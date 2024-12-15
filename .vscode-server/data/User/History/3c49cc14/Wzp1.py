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
from jobcrawl import save_to_mysql
from MySQLdb.cursors import DictCursor
import mysql.connector
import re
from collections import OrderedDict
import json
from math import ceil


    
def postratings(mysql):
    cursor = None  # 커서 초기화
    try:
        # JWT에서 현재 사용자 ID 가져오기
        logged_in_user_id = get_jwt_identity()

        # 요청 데이터 가져오기
        data = request.json
        company_id = data.get("company_id")
        rating = data.get("rating")

        # 유효성 검사: company_id와 rating 확인
        if not company_id:
            response_data = {
                "status": "error",
                "message": "Company ID is required",
                "code": "400"
            }
            return Response(json.dumps(response_data), status=400, mimetype="application/json")

        if rating is None or not (1 <= rating <= 5):
            response_data = {
                "status": "error",
                "message": "Invalid rating. Must be between 1 and 5",
                "code": "400"
            }
            return Response(json.dumps(response_data), status=400, mimetype="application/json")

        # 평점 삽입 또는 업데이트
        cursor = mysql.connection.cursor()
        query = """
        INSERT INTO company_ratings (company_id, user_id, rating)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE rating = %s;
        """
        cursor.execute(query, (company_id, logged_in_user_id, rating, rating))
        mysql.connection.commit()

        # 성공 응답
        response_data = {
            "status": "success",
            "message": "Rating created or updated successfully",
            "data": {
                "company_id": company_id,
                "rating": rating
            }
        }
        return Response(json.dumps(response_data, ensure_ascii=False, indent=4), status=201, mimetype="application/json")

    except Exception as e:
        # 예외 처리
        response_data = {
            "status": "error",
            "message": "An error occurred",
            "details": str(e),
            "code": "500"
        }
        return Response(json.dumps(response_data), status=500, mimetype="application/json")

    finally:
        if cursor:
            cursor.close()



def getratings(mysql):
    cursor = None  # 커서 초기화
    try:
        # 입력된 최대 평점 및 페이지 관련 파라미터
        max_rating = request.args.get('min_rating', type=float)
        page = request.args.get('page', type=int, default=1)
        per_page = 20  # 한 페이지에 최대 20개 표시

        # 필수 파라미터 검증
        if max_rating is None:
            response_data = {
                "status": "error",
                "message": "min_rating is required",
                "code": "400"
            }
            return Response(json.dumps(response_data), status=400, mimetype="application/json")

        # DictCursor를 사용하여 딕셔너리 형태로 결과 반환
        cursor = mysql.connection.cursor(DictCursor)

        # 최대 평점 이하인 회사 가져오기 (평점 높은 순 정렬)
        offset = (page - 1) * per_page
        query = """
        SELECT c.id AS company_id, c.company AS company_name, AVG(r.rating) AS average_rating
        FROM company_ratings r
        JOIN jobs c ON r.company_id = c.id
        GROUP BY c.id
        HAVING AVG(r.rating) <= %s
        ORDER BY average_rating DESC
        LIMIT %s OFFSET %s;
        """
        cursor.execute(query, (max_rating, per_page, offset))
        companies = cursor.fetchall()

        # 총 회사 수 계산
        count_query = """
        SELECT COUNT(DISTINCT c.id) AS total_companies
        FROM company_ratings r
        JOIN jobs c ON r.company_id = c.id
        GROUP BY c.id
        HAVING AVG(r.rating) <= %s;
        """
        cursor.execute(count_query, (max_rating,))
        total_companies_result = cursor.fetchone()
        total_companies = total_companies_result['total_companies'] if total_companies_result else 0

        # 페이지네이션 정보 계산
        total_pages = ceil(total_companies / per_page)

        # 성공 응답 데이터 생성
        response_data = {
            "status": "success",
            "data": {
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total_pages": total_pages,
                    "total_companies": total_companies
                },
                "companies": [
                    {
                        "company_id": company["company_id"],
                        "company_name": company["company_name"],
                        "average_rating": round(company["average_rating"], 2) if company["average_rating"] else None
                    }
                    for company in companies
                ]
            }
        }
        return Response(json.dumps(response_data, ensure_ascii=False, indent=4), status=200, mimetype="application/json")

    except Exception as e:
        # 예외 처리
        response_data = {
            "status": "error",
            "message": "해당 평점보다 낮은 회사가 없습니다",
            "code": "500"
        }
        return Response(json.dumps(response_data), status=500, mimetype="application/json")

    finally:
        if cursor:
            cursor.close()