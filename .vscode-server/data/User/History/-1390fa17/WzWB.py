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




app = Flask(__name__)

# MySQL Configuration
app.config['MYSQL_HOST'] = '113.198.66.75'
app.config['MYSQL_USER'] = 'jdh'
app.config['MYSQL_PASSWORD'] = '1234'
app.config['MYSQL_DB'] = 'hw3'
app.config['MYSQL_PORT'] = 13228
mysql = MySQL(app)

# CORS Configuration
CORS(app)

# JWT Configuration
app.config['JWT_SECRET_KEY'] = 'your_jwt_secret_key'
jwt = JWTManager(app)

# Swagger Configuration
SWAGGER_URL = '/swagger'
API_URL = '/static/swagger.json'
swaggerui_blueprint = get_swaggerui_blueprint(SWAGGER_URL, API_URL, config={'app_name': "Saramin Jobs API"})
app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)

def initialize_data(): #앱 시작시 1번만 수행 (채용공고 지역별로 100개씩 크롤링)

    # MySQL 저장
    save_to_mysql("113.198.66.75", "jdh", "1234", "hw3", 13228)

    print("Initial data has been crawled and saved to MySQL.")  

################################################################################################
################################################################################################
# 회원가입 API
@app.route('/auth/register', methods=['POST'])
def register():
    return authregister(mysql)

# 로그인 API
@app.route('/auth/login', methods=['POST'])
def login():
    return authlogin(mysql)


# 토큰 갱신 API
@app.route('/auth/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    return authrefresh(mysql)   

# 회원 정보 수정 API
@app.route('/auth/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    return authprofile(mysql)

################################################################################################
################################################################################################  
    
@app.route('/jobs', methods=['GET'])
def get_jobs():
    return postjobs(mysql)

# 공고 상세 조회 (GET /jobs/:id)
@app.route('/jobs/<int:job_id>', methods=['GET'])
def get_job_and_recommendations(job_id):
    return postjobsid(job_id,mysql,app)
   
################################################################################################
################################################################################################  

@app.route('/applications', methods=['POST'])
@jwt_required()
def apply():
    return applypostapplications(mysql)

# 지원 내역 조회 (GET /applications)
@app.route('/applications', methods=['GET'])
@jwt_required()
def get_applications():
    return applygetapplications(mysql)

# 지원 취소 (DELETE /applications/:id)
@app.route('/applications/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_application(id):
    return applydeleteapplications(mysql,id)

################################################################################################
################################################################################################ 

@app.route('/bookmarks', methods=['POST'])
@jwt_required()
def add_bookmark():
    return postbookmarks(mysql)


@app.route('/bookmarks', methods=['GET'])
@jwt_required()
def get_bookmarks():
    return getbookmarks(mysql)

################################################################################################
################################################################################################ 
@app.route('/ratings', methods=['POST'])
@jwt_required()
def create_or_update_rating():
    return postratings(mysql)  

@app.route('/ratings', methods=['GET'])
@jwt_required()
def list_companies_by_rating():
    return getratings(mysql)

################################################################################################
################################################################################################ 
@app.route('/recommands', methods=['GET'])
def get_recommands():
    # 정렬 기준 및 페이지 관련 파라미터
    sort_order = request.args.get('sort', default='desc', type=str).lower()  # 기본값: desc
    page = request.args.get('page', type=int, default=1)
    per_page = 20  # 한 페이지에 최대 20개

    # 정렬 기준 검증
    if sort_order not in ['asc', 'desc']:
        return jsonify({"error": "Invalid sort parameter. Use 'asc' or 'desc'."}), 400

    cursor = mysql.connection.cursor(DictCursor)

    # 조회수 기준으로 회사 목록 가져오기
    query = f"""
    SELECT id AS company_id, company AS company_name, views
    FROM jobs
    ORDER BY views {sort_order}
    LIMIT %s OFFSET %s;
    """
    offset = (page - 1) * per_page
    cursor.execute(query, (per_page, offset))
    companies = cursor.fetchall()

    # 총 회사 수 계산
    cursor.execute("SELECT COUNT(*) AS total_companies FROM jobs;")
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

            
if __name__ == "__main__":
    initialize_data()
    app.run(host="0.0.0.0", port=8080, debug=True)
