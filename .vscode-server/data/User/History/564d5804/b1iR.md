## [Saramin Jobs API](https://hw-github-io.onrender.com/swagger/)
---
해당 사이트는 사람인 사이트의 채용공고 정보를 크롤링을 이용해 Swagger Ui로 백엔드를 구현한 사이트 입니다. 

![Screenshot](swagger.png)

## 작동 방법
1. python3 -m venv myenv로 myenv 생성
2. source myenv/bin/activate로 myenv 가상 서버 접속
3. python app.py 실행



## 파일 구조
- app.py (경로 관리용 파일로 사용 - 다른 py파일을 import해 사용)
- Auth.py (회원관리 구현 파일)
- Posting.py (일자리 공고 구현 파일)
- Apply.py (지원 관리 구현 파일)
- Bookmarks.py (찜한 목록 관리 구현 파일)
- Ratings.py (평점 관리 구현 파일)
- Recommands.py (조회수 조회 구현 파일)
- Community.py (커뮤니티 관리 구현 파일)
- jobcrawl.py (crawled-data.sql을 db에 저장하는 파일)

## 구현 API

- Auth(회원관리)
  -  /auth/register 회원가입(POST)
  -  /auth/login 로그인(POST)
  -  /auth/refresh 토큰갱신(POST)
  -  /auth/profile 회원정보수정(PUT)

- Jobs(일자리 공고 관리)
  -  /jobs 공고목록조회(GET)
  -  /jobs/{id} 공고상세조회(GET)

- Applications(지원 관리)
  -  /applications 지원하기(POST)
  -  /applications 지원내역조회(GET)
  -  /applications 지원취소(DELETE)

- Bookmarks(찜한 목록 관리)
  -  /bookmarks 북마크토글처리(POST)
  -  /bookmarks 북마크목록조회(GET)

- Ratings(평점 관리)
  -  /ratings 회사에대한평점생성1~5점(POST)
  -  /ratings 회사평점조회(GET)

- Recommands(조회수 조회)
  -  /recommands 조회수조회(GET)

- Community(커뮤니티 관리)
  -  /community 커뮤니티(POST)
  -  /community 커뮤니티(GET)


## 패키지설치

- pip install flask
- pip install flask-mysqldb
- pip install flask-jwt-extended
- pip install flask-swagger-ui
- pip install flask-cors
- pip install mysql-connector-python
- pip install beautifulsoup4
- pip install pandas
- pip install requests
- pip install pygobject