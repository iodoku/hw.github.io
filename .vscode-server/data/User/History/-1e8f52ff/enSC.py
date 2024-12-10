def communitypost(mysql):
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

def communityget(mysql):
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