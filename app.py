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

app = Flask(__name__)

# MySQL Configuration
app.config['MYSQL_HOST'] = '113.198.66.75'
app.config['MYSQL_USER'] = 'jdh'
app.config['MYSQL_PASSWORD'] = '1234'
app.config['MYSQL_DB'] = 'hw3'
app.config['MYSQL_PORT'] = 13048
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
    save_to_mysql("113.198.66.75", "jdh", "1234", "hw3", 13048)

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
    user_id = get_jwt_identity()  # 인증된 사용자 ID 가져오기
    job_id = request.json.get('job_id')  # 요청 본문에서 job_id 가져오기

    # job_id가 유효한지 확인
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT id, title, company, location, salary FROM jobs WHERE id = %s", (job_id,))
    job = cursor.fetchone()
    
    if not job:
        cursor.close()
        return jsonify({"message": "Job not found"}), 404

    # 이미 북마크가 존재하는지 확인
    cursor.execute("SELECT id FROM bookmarks WHERE user_id = %s AND jVob_id = %s", (user_id, job_id))
    existing_bookmark = cursor.fetchone()

    if existing_bookmark:
        # 이미 북마크가 있으면 삭제
        cursor.execute("DELETE FROM bookmarks WHERE user_id = %s AND job_id = %s", (user_id, job_id))
        mysql.connection.commit()
        cursor.close()
        return jsonify({"message": "Bookmark removed successfully"}), 200

    # 북마크 추가
    cursor.execute("INSERT INTO bookmarks (user_id, job_id) VALUES (%s, %s)", (user_id, job_id))
    mysql.connection.commit()
    cursor.close()

    # 북마크 추가 성공 메시지와 함께 job 정보도 반환
    response_data = {
        "message": "Bookmark added successfully",
        "job": {
            "id": job[0],
            "title": job[1],
            "company": job[2],
            "location": job[3],
        }
    }

    return json.dumps(response_data), 201, {'Content-Type': 'application/json'}


@app.route('/bookmarks', methods=['GET'])
@jwt_required()
def get_bookmarks():
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


            
if __name__ == "__main__":
    initialize_data()
    app.run(host="0.0.0.0", port=8080, debug=True)
