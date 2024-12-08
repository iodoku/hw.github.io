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
from Bookmarks import postbookmarks,getbookmarks
from jobcrawl import save_to_mysql
from MySQLdb.cursors import DictCursor
import mysql.connector
import re
from collections import OrderedDict
import json
from math import ceil


    
def postratings(mysql):
    # JWT에서 현재 사용자 ID 가져오기
    logged_in_user_id = get_jwt_identity()

    data = request.json
    company_id = data.get("company_id")
    rating = data.get("rating")

    # 유효성 검사: rating이 1~5 사이인지 확인
    if rating is None or not (1 <= rating <= 5):
        return jsonify({"error": "Invalid rating. Must be between 1 and 5."}), 400

    # 평점 삽입 또는 업데이트
    cursor = mysql.connection.cursor()
    query = """
    INSERT INTO company_ratings (company_id, user_id, rating)
    VALUES (%s, %s, %s)
    ON DUPLICATE KEY UPDATE rating = %s;
    """
    cursor.execute(query, (company_id, logged_in_user_id, rating, rating))
    mysql.connection.commit()
    cursor.close()

    return jsonify({"message": "Rating created or updated successfully"}), 201



def getratings(mysql): 
    # 최대 평점 및 페이지 관련 파라미터
    max_rating = request.args.get('max_rating', type=float, default=5)
    page = request.args.get('page', type=int, default=1)
    per_page = 20  # 한 페이지에 최대 20개

    # DictCursor를 사용하여 딕셔너리 형태로 결과 반환
    cursor = mysql.connection.cursor(DictCursor)

    # 최대 평점 이하인 회사 가져오기 (평점 높은 순 정렬)
    query = """
    SELECT c.id AS company_id, c.company AS company_name, AVG(r.rating) AS average_rating
    FROM company_ratings r
    JOIN jobs c ON r.company_id = c.id
    GROUP BY c.id
    HAVING average_rating <= %s
    ORDER BY average_rating DESC
    LIMIT %s OFFSET %s;
    """
    offset = (page - 1) * per_page
    cursor.execute(query, (max_rating, per_page, offset))
    companies = cursor.fetchall()

    # 총 회사 수 계산
    cursor.execute("""
    SELECT COUNT(DISTINCT c.id) AS total_companies
    FROM company_ratings r
    JOIN jobs c ON r.company_id = c.id
    GROUP BY c.id
    HAVING AVG(r.rating) <= %s;
    """, (max_rating,))
    total_companies_result = cursor.fetchone()
    total_companies = total_companies_result['total_companies'] if total_companies_result else 0

    cursor.close()

    # 페이지네이션 정보 계산
    total_pages = ceil(total_companies / per_page)
    response = {
        'page': page,
        'per_page': per_page,
        'total_pages': total_pages,
        'total_companies': total_companies,
        'companies': companies
    }
    return jsonify(response)