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
from Recommands import getrecommands
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
    return getrecommands(mysql)

################################################################################################
################################################################################################ 


@app.route('/community', methods=['POST'])
@jwt_required()  # JWT를 통해 로그인한 사용자만 접근 가능
def post_community():
    try:
        # JWT에서 사용자 ID 가져오기
        user_id = get_jwt_identity()

        # 요청 데이터
        data = request.get_json()
        title = data.get('title')
        content = data.get('content')

        # 제목과 내용이 없는 경우 예외 처리
        if not title or not content:
            return jsonify({"error": "Title and content are required."}), 400

        # 게시글 저장
        connection = mysql.connection
        cursor = connection.cursor()
        query = """
        INSERT INTO posts (user_id, title, content, created_at)
        VALUES (%s, %s, %s, %s)
        """
        cursor.execute(query, (user_id, title, content, datetime.now()))
        connection.commit()

        return jsonify({"message": "Post created successfully."}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()

@app.route('/community', methods=['GET'])
def get_community():
    try:
        # 정렬 기준 및 페이지 관련 파라미터
        sort_order = request.args.get('sort', default='작성느린순', type=str)  # 기본값: 작성느린순
        page = request.args.get('page', type=int, default=1)  # 페이지 번호
        per_page = 20  # 한 페이지에 최대 20개

        # 정렬 기준 변환
        if sort_order == '작성빠른순':
            sql_sort_order = 'ASC'
        elif sort_order == '작성느린순':
            sql_sort_order = 'DESC'
        else:
            return jsonify({"error": "Invalid sort parameter. Use '작성빠른순' or '작성느린순'."}), 400

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
        response = {
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "total_posts": total_posts,
            "posts": posts
        }

        return jsonify(response), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()

            

################################################################################################
################################################################################################ 

if __name__ == "__main__":
    initialize_data()
    app.run(host="0.0.0.0", port=8080, debug=True)
