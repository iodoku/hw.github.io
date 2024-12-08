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


    
def postratings(mysql):   
    data = request.json
    company_id = data.get('company_id')
    user_id = data.get('user_id')
    rating = data.get('rating')

    if not (1 <= rating <= 5):
        return jsonify({'error': 'Rating must be between 1 and 5'}), 400

    cursor = db.cursor()
    # 회사 평점 삽입 또는 업데이트
    query = """
    INSERT INTO company_ratings (company_id, user_id, rating)
    VALUES (%s, %s, %s)
    ON DUPLICATE KEY UPDATE rating = %s;
    """
    cursor.execute(query, (company_id, user_id, rating, rating))
    db.commit()
    cursor.close()
    return jsonify({'message': 'Rating created or updated successfully'}), 201



def getratings(mysql): 
    min_rating = request.args.get('min_rating', type=float, default=1)
    page = request.args.get('page', type=int, default=1)
    per_page = 20

    cursor = db.cursor(dictionary=True)
    # 평점 이상인 회사 가져오기
    query = """
    SELECT c.id AS company_id, c.company, AVG(r.rating) AS average_rating
    FROM company_ratings r
    JOIN jobs c ON r.company_id = c.id
    GROUP BY c.id
    HAVING average_rating >= %s
    ORDER BY average_rating DESC
    LIMIT %s OFFSET %s;
    """
    offset = (page - 1) * per_page
    cursor.execute(query, (min_rating, per_page, offset))
    companies = cursor.fetchall()

    # 총 회사 수 계산
    cursor.execute("""
    SELECT COUNT(DISTINCT c.id) AS total_companies
    FROM company_ratings r
    JOIN jobs c ON r.company_id = c.id
    HAVING AVG(r.rating) >= %s;
    """, (min_rating,))
    total_companies = cursor.fetchone()['total_companies']
    cursor.close()

    # 페이지네이션 정보
    total_pages = ceil(total_companies / per_page)
    response = {
        'page': page,
        'per_page': per_page,
        'total_pages': total_pages,
        'total_companies': total_companies,
        'companies': companies
    }
    return jsonify(response)