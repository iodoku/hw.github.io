from flask import Response,Flask, request, jsonify
from flask_mysqldb import MySQL
from flask_jwt_extended import JWTManager, create_access_token, create_refresh_token, jwt_required, get_jwt_identity
from flask_swagger_ui import get_swaggerui_blueprint
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from MySQLdb.cursors import DictCursor
import mysql.connector
import re
from collections import OrderedDict
import json


def add_experience_filter(experience_input):
    """
    경력 필터 조건 생성 함수
    """
    try:
        experience_years = int(re.search(r"\d+", experience_input).group())
        return f"""
        (
            (experience LIKE '%~%' 
            AND CAST(SUBSTRING_INDEX(experience, '~', 1) AS UNSIGNED) <= {experience_years} 
            AND CAST(SUBSTRING_INDEX(experience, '~', -1) AS UNSIGNED) >= {experience_years})
            OR (experience REGEXP '^[0-9]+년$' 
            AND CAST(REPLACE(experience, '년', '') AS UNSIGNED) >= {experience_years})
            OR experience LIKE '%경력무관%'
        )
        """
    except AttributeError:
        return "experience LIKE '%경력무관%' OR experience LIKE '%신입%'"


def postjobs(mysql):
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 20))
    start = (page - 1) * page_size

    # 필터링 및 검색 조건
    location = request.args.get('지역')
    experience = request.args.get('경력')
    stack = request.args.get('기술스택')
    search = request.args.get('검색')
    sort_by = request.args.get('정렬', '마감순')  # 기본 정렬 기준은 deadline

    # MySQL 쿼리 작성
    query = "SELECT * FROM jobs"
    filters = []

    # 필터 조건 추가
    if location:
        filters.append(f"location LIKE '%{location}%'")
    if experience:
        filters.append(add_experience_filter(experience))  # 경력 필터 추가 함수 (별도로 정의 필요)
    if stack:
        filters.append(f"sector LIKE '%{stack}%'")
    if search:
        filters = []  # 검색어가 있으면 다른 필터 조건 무시
        filters.append(f"(company LIKE '%{search}%' OR location LIKE '%{search}%' OR sector LIKE '%{search}%')")

    # WHERE 조건 추가 (filters가 있을 때만 추가)
    if filters:
        query += " WHERE " + " AND ".join(filters)

    # 정렬 조건 추가
    if sort_by == "마감순":
        query += " ORDER BY STR_TO_DATE(deadline, '%m/%d(%a)') ASC"
    elif sort_by == "수정순":
        query += " ORDER BY STR_TO_DATE(sector, '%y/%m/%d') DESC"

    # 페이지네이션 추가
    query += f" LIMIT {start}, {page_size}"

    # MySQL 연결 및 쿼리 실행
    try:
        connection = mysql.connection
        cursor = connection.cursor(DictCursor)
        cursor.execute(query)
        jobs = cursor.fetchall()
        


        # 전체 공고 수 가져오기
        cursor.execute("SELECT COUNT(*) AS total FROM jobs")
        total_jobs = cursor.fetchone()['total']

    
        # 성공 응답 반환
        pagination = {
            "currentPage": page,
            "totalPages": (total_jobs + page_size - 1) // page_size,
            "totalItems": total_jobs
        }
        
        if not jobs:
            response_data = {
                "status": "success",
                "data": {
                    "message": "만족하는 조건이 없습니다",
                    "pagination": pagination
                    "jobs": []
                },
                "pagination": None
            }
            return Response(json.dumps(response_data), status=200, mimetype="application/json")

        response_data = {
            "status": "success",
            "data": {
                "pagination": pagination
                "jobs": jobs
            },
        }
        return Response(json.dumps(response_data), status=200, mimetype="application/json")

    except Exception as e:
        # 실패 응답 반환
        response_data = {
            "status": "error",
            "message": str(e),
            "code": "500"
        }
        return Response(json.dumps(response_data), status=500, mimetype="application/json")

    finally:
        if cursor:
            cursor.close()
            
        
def postjobsid(job_id, mysql, app):
    try:
        connection = mysql.connection
        cursor = connection.cursor(DictCursor)

        # 조회수 증가 쿼리 실행
        update_query = "UPDATE jobs SET views = views + 1 WHERE id = %s"
        cursor.execute(update_query, (job_id,))
        connection.commit()  # 변경 사항 커밋

        # 현재 공고 가져오기
        query = "SELECT * FROM jobs WHERE id = %s"
        cursor.execute(query, (job_id,))
        job = cursor.fetchone()

        if not job:
            return jsonify({"error": "Job not found"}), 404

        # 현재 공고의 sector와 location 추출
        sector = job['sector'].split(',')[0].strip() if job.get('sector') else ''
        location = job['location'].split()[0].strip() if job.get('location') else ''

        # 비슷한 공고 검색
        filters = []
        params = [job_id]

        if sector:
            filters.append("sector LIKE %s")
            params.append(f"%{sector}%")
        if location:
            filters.append("location LIKE %s")
            params.append(f"%{location}%")

        similar_jobs_query = """
            SELECT id, title, location AS region
            FROM jobs
            WHERE id != %s
        """
        if filters:
            similar_jobs_query += " AND (" + " OR ".join(filters) + ")"
        similar_jobs_query += " LIMIT 3"

        cursor.execute(similar_jobs_query, tuple(params))
        recommendations = cursor.fetchall()

        # JSON 결과 반환 (OrderedDict로 순서 고정)
        response = OrderedDict([
            ("id", job['id']),
            ("title", job['title']),
            ("experience", job['experience']),
            ("region", job['location']),
            ("salary", job['salary']),
            ("tech_stack", job['sector']),
            ("views", job['views'] + 1),  # views는 이미 증가했으므로 +1 적용
            ("related_jobs", recommendations)
        ])

        return app.response_class(
            response=json.dumps(response, ensure_ascii=False, indent=4),
            mimetype='application/json'
        )

    except Exception as e:
        import traceback
        print("Error Traceback:", traceback.format_exc())
        return jsonify({"error": str(e)}), 500

    finally:
        if cursor:
            cursor.close()