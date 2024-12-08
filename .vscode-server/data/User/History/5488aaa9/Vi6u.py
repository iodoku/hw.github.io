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
from Ratings import postratings,getratings
from jobcrawl import save_to_mysql
from MySQLdb.cursors import DictCursor
import mysql.connector
import re
from collections import OrderedDict
import json
from math import ceil


def getrecommands(mysql):
    sort_order = request.args.get('sort', default='조회수낮은순', type=str)  # 기본값: 조회수낮은순
    page = request.args.get('page', type=int, default=1)
    per_page = 20  # 한 페이지에 최대 20개

    # 정렬 기준 변환
    if sort_order == '조회수높은순':
        sql_sort_order = 'DESC'
    elif sort_order == '조회수낮은순':
        sql_sort_order = 'ASC'
    else:
        return jsonify({"error": "Invalid sort parameter. Use '조회수높은순' or '조회수낮은순'."}), 400

    # MySQL 커서 생성
    cursor = mysql.connection.cursor(DictCursor)

    try:
        # 조회수 기준으로 회사 목록 가져오기
        query = f"""
        SELECT id AS company_id, company AS company_name, views
        FROM jobs
        ORDER BY views {sql_sort_order}
        LIMIT %s OFFSET %s;
        """
        offset = (page - 1) * per_page
        cursor.execute(query, (per_page, offset))
        companies = cursor.fetchall()

        # 총 회사 수 계산
        cursor.execute("SELECT COUNT(*) AS total_companies FROM jobs;")
        total_companies_result = cursor.fetchone()
        total_companies = total_companies_result['total_companies'] if total_companies_result else 0

    finally:
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