import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import time
from flask_mysqldb import MySQL
import mysql.connector

    

def save_to_mysql(localhost, username, userpassword, userdatabase, userport):     
    # MySQL 연결
    connection = mysql.connector.connect(
        host=localhost,
        user=username,
        password=userpassword,
        database=userdatabase,
        port=userport,
    )
    cursor = connection.cursor()
    
    # SQL 파일 읽기
    with open("saramin_python.sql", "r", encoding="utf-8") as file:
        sql_commands = file.read()

    # SQL 파일의 각 명령어 실행
    for command in sql_commands.split(";"):
        command = command.strip()  # 양쪽 공백 제거
        if command:  # 빈 명령어 제외
            cursor.execute(command)

    # 변경사항 커밋
    connection.commit()

    print(f"{cursor.rowcount}개의 데이터가 MySQL에 저장되었습니다.")

    # 연결 종료
    cursor.close()
    connection.close()
