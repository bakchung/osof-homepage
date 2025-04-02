"""
메인 애플리케이션 파일
"""
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash, g
from functools import wraps
import secrets
from datetime import timedelta, datetime
import base64
import re
import os
import time
import json
from werkzeug.utils import secure_filename
import bcrypt
import uuid

# 유틸리티 함수 및 설정 가져오기
from utils import (
    hash_password, check_password, validate_password,
    load_users, save_users, load_user_buttons, save_user_buttons,
    get_user_buttons_file, add_log, load_user_logs
)
from hardware_config import is_admin_hardware, SECRET_KEY, SESSION_LIFETIME_DAYS

# Flask 앱 초기화
app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # 실제 운영시에는 더 복잡한 키로 변경해주세요

# 전역 변수로 문의 내용을 저장할 리스트 생성
inquiries = []

# 사용자 역할 정보
USER_ROLES = {
    'ksw14137': 'admin',  # 관리자 계정
    'wjddbswoals': '팀장',  # 가정: 윤영준 계정
    'wlghks': '팀장'       # 가정: 장지훈 계정
}

# 모든 템플릿에 now 객체 제공
@app.context_processor
def inject_now():
    return {'now': datetime.now()}

# 사용자 실제 표시 이름 가져오기 함수
def get_display_name(username):
    """사용자의 표시 이름을 반환합니다."""
    # 관리자 계정이면 'admin'으로 표시
    if username == 'ksw14137':
        return 'admin'
    
    # 지정된 역할이 있으면 '사용자명(역할)' 형태로 표시
    if username in USER_ROLES:
        role = USER_ROLES[username]
        # 관리자는 'admin'으로만 표시
        if role == 'admin':
            return 'admin'
        # 팀장 등 다른 역할은 이름과 함께 표시
        else:
            return f"{username}({role})"
    
    # 일반 사용자는 그대로 표시
    return username

# max와 min 함수를 템플릿에서 사용할 수 있도록 추가
@app.context_processor
def utility_functions():
    return {
        'max': max, 
        'min': min,
        'get_display_name': get_display_name  # 템플릿에서 사용자 표시 이름 가져오기 함수 추가
    }

# Jinja2 템플릿 필터 추가
@app.template_filter('nl2br')
def nl2br(value):
    """줄바꿈을 <br> 태그로 변환하고 공백 처리"""
    if value:
        # 공백 문자 유지하며 줄바꿈을 <br>로 변환
        value = value.rstrip()  # 오른쪽 공백만 제거
        # 줄바꿈을 <br>로 변환
        value = value.replace('\n', '<br>')
        # 연속된 공백을 HTML 공백으로 변환 (선택적)
        value = re.sub(' {2,}', lambda m: '&nbsp;' * len(m.group(0)), value)
        return value
    return ''

# 기본 세션 설정
app.permanent_session_lifetime = timedelta(days=7)

# 게시판 관련 파일 경로 설정
POSTS_DIR = os.path.join('data', 'posts')
NOTICES_DIR = os.path.join('data', 'notices')
SCHEDULES_DIR = os.path.join('data', 'schedules')
GALLERY_DIR = os.path.join('data', 'gallery')
SUGGESTIONS_DIR = os.path.join('data', 'suggestions')
UPLOAD_FOLDER = os.path.join('static', 'uploads')
GALLERY_UPLOAD_FOLDER = os.path.join('static', 'uploads', 'gallery')
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'zip', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx'}
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
DONATIONS_DIR = os.path.join('data', 'donations')  # 후원 정보 저장 디렉토리 추가

# 활동 내용 관련 디렉토리 설정
ACTIVITIES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'activities')
os.makedirs(ACTIVITIES_DIR, exist_ok=True)

# 질문 관련 디렉토리 설정
QUESTIONS_DIR = os.path.join('data', 'questions')
os.makedirs(QUESTIONS_DIR, exist_ok=True)

# 필요한 디렉토리 초기화
def init_directories():
    """필요한 디렉토리들을 초기화"""
    directories = [
        'data',
        'data/users',
        'data/buttons',
        'data/logs',
        POSTS_DIR,
        NOTICES_DIR,
        SCHEDULES_DIR,
        GALLERY_DIR,
        SUGGESTIONS_DIR,
        UPLOAD_FOLDER,
        GALLERY_UPLOAD_FOLDER,
        'data/inquiries',
        DONATIONS_DIR,  # 후원 디렉토리 추가
        QUESTIONS_DIR  # 질문 디렉토리 추가
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)

# 디렉토리 초기화 실행
init_directories()

USERS_DIR = os.path.join('data', 'users')
INQUIRY_DIR = os.path.join('data', 'inquiries')

# 데코레이터 함수
def login_required(f):
    """로그인이 필요한 페이지에 대한 데코레이터"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session or not session['logged_in']:
            return redirect(url_for('login'))  # 로그인 페이지로 리디렉션
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """관리자 권한이 필요한 페이지에 대한 데코레이터"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session or not session.get('is_admin', False):
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# 라우트 정의
@app.route('/')
def root():
    """루트 페이지 - 항상 홈으로 리디렉션"""
    return redirect(url_for('home'))  # 항상 홈으로 리디렉션

@app.route('/login', methods=['GET', 'POST'])
def login():
    """로그인 페이지"""
    if request.method == 'GET':
        return render_template('login.html')  # 로그인 템플릿 렌더링
    elif request.method == 'POST':
        # JSON 요청처리
        if request.is_json:
            data = request.get_json()
            username = data.get('username')
            password = data.get('password')
        # 폼 데이터 처리
        else:
            username = request.form.get('username')
            password = request.form.get('password')
                
        # 데이터베이스에서 사용자 정보 불러오기
        users = load_users()
        
        # 사용자 확인 및 비밀번호 검증
        if username in users and check_password(password, users[username]['password']):
            # 로그인 성공
            session['logged_in'] = True
            session['username'] = username
            
            # 관리자 권한 검증 - 하드웨어 검증 추가
            is_admin = users[username].get('is_admin', False)
            
            # 관리자 권한이 있더라도 현재 하드웨어가 허용된 하드웨어가 아니면 일반 사용자로 취급
            if is_admin and not is_admin_hardware():
                is_admin = False
                print(f"경고: {username} 계정은 관리자이지만 현재 하드웨어에서는 관리자 권한이 비활성화됩니다.")
                
            session['is_admin'] = is_admin
            
            # 로그인 시간 및 시도 횟수 업데이트
            users[username]['login_attempts'] = 0
            users[username]['last_login'] = datetime.now().isoformat()
            save_users(users)
            
            # 로그 기록
            add_log(username, f"로그인 성공 (관리자 권한: {is_admin})")
            
            if request.is_json:
                return jsonify({'success': True, 'message': '로그인 성공', 'redirect': url_for('home')})
            else:
                return redirect(url_for('home'))
        else:
            # 로그인 실패 시 로그인 시도 횟수 증가
            if username in users:
                users[username]['login_attempts'] = users[username].get('login_attempts', 0) + 1
                save_users(users)
                
            if request.is_json:
                return jsonify({'success': False, 'message': '로그인 실패: 잘못된 아이디 또는 비밀번호'}), 401
            else:
                flash('로그인 실패: 잘못된 아이디 또는 비밀번호')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """회원가입 페이지"""
    if request.method == 'GET':
        return render_template('register.html')
    
    elif request.method == 'POST':
        # JSON 요청 처리
        if request.is_json:
            data = request.get_json()
            username = data.get('username')
            password = data.get('password')
            password_confirm = data.get('password_confirm')
        # 폼 데이터 처리
        else:
            username = request.form.get('username')
            password = request.form.get('password')
            password_confirm = request.form.get('password_confirm')
        
        # 입력값 검증
        if not username or not password:
            if request.is_json:
                return jsonify({"error": "사용자 이름과 비밀번호를 모두 입력해주세요."})
            flash('사용자 이름과 비밀번호를 모두 입력해주세요.')
            return redirect(url_for('register'))
            
        if password != password_confirm:
            if request.is_json:
                return jsonify({"error": "비밀번호와 비밀번호 확인이 일치하지 않습니다."})
            flash('비밀번호와 비밀번호 확인이 일치하지 않습니다.')
            return redirect(url_for('register'))
            
        # 사용자 이름 중복 검사
        users = load_users()
        if username in users:
            if request.is_json:
                return jsonify({"error": "이미 사용 중인 사용자 이름입니다."})
            flash('이미 사용 중인 사용자 이름입니다.')
            return redirect(url_for('register'))
            
        # 비밀번호 해싱
        hashed_password = hash_password(password)
        
        # UUID 생성
        user_uuid = str(uuid.uuid4())
        
        # 새 사용자 추가
        users[username] = {
            'password': hashed_password,
            'is_admin': False,
            'login_attempts': 0,
            'created_at': datetime.now().isoformat(),
            'uuid': user_uuid  # UUID 추가
        }
        
        # 사용자 정보 저장
        save_users(users)
        
        # 성공 메시지
        if request.is_json:
            return jsonify({"success": "회원가입이 완료되었습니다. 로그인해주세요."})
            
        # 성공 메시지 표시 (폼 제출 시)
        flash('회원가입이 완료되었습니다. 로그인해주세요.')
        
        # 로그인 페이지로 리디렉션
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/home')
def home():
    """홈페이지"""
    return render_template('home.html')  # 홈 템플릿 렌더링

@app.route('/index')
def index():
    """소개 페이지 - 로그인 없이 접근 가능"""
    username = session.get('username')
    user_buttons = load_user_buttons(username) if username else []
    is_admin = session.get('is_admin', False)
    return render_template('index.html', 
                         custom_buttons=user_buttons,
                         is_admin=is_admin)

@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    """로그아웃 처리"""
    # 세션에서 사용자 이름 가져오기(로그 기록용)
    username = session.get('username', 'unknown')
    # 세션 데이터 삭제
    session.clear()
    # 로그 기록
    add_log(username, "로그아웃 완료")
    return redirect(url_for('home'))  # 로그아웃 후 홈으로 리디렉션

@app.route('/admin')
@login_required
def admin():
    # 관리자가 아니면 액세스 거부
    if not session.get('is_admin', False):
        flash('관리자 권한이 필요합니다.', 'error')
        return redirect(url_for('home'))
    
    # 관리자인 경우 admin.html 렌더링
    return render_template('admin.html')

@app.route('/admin_users')
@login_required
def admin_users():
    # 관리자가 아니면 액세스 거부
    if not session.get('is_admin', False):
        flash('관리자 권한이 필요합니다.', 'error')
        return redirect(url_for('home'))
    
    # 사용자 목록 가져오기
    users = load_users()
    search_query = request.args.get('search', '')
    
    # 검색어가 있으면 필터링
    filtered_users = {}
    for username, user_data in users.items():
        if not search_query or search_query.lower() in username.lower():
            filtered_users[username] = user_data
    
    return render_template('admin_users.html', users=filtered_users, search_query=search_query)

@app.route('/admin_dashboard')
@admin_required
def admin_dashboard():
    """관리자 대시보드"""
    users = load_users()
    
    # 각 사용자의 로그 정보 추가
    for username, user_data in users.items():
        user_data['logs'] = load_user_logs(username)
    
    return render_template('admin.html', users=users)

@app.route('/admin/delete_user', methods=['POST'])
@admin_required
def delete_user():
    """사용자 삭제"""
    data = request.get_json()
    username = data.get('username')
    
    users = load_users()
    
    if username not in users:
        return jsonify({
            'success': False,
            'message': '존재하지 않는 회원입니다.'
        })
    
    # 관리자는 삭제할 수 없음
    if users[username].get('is_admin', False):
        return jsonify({
            'success': False,
            'message': '관리자는 삭제할 수 없습니다.'
        })
    
    # 회원 정보 삭제
    del users[username]
    save_users(users)
    
    # 회원의 버튼 데이터 파일 삭제
    buttons_file = get_user_buttons_file(username)
    if os.path.exists(buttons_file):
        os.remove(buttons_file)
    
    return jsonify({
        'success': True,
        'message': f'{username} 회원이 삭제되었습니다.'
    })

@app.route('/admin/user_info/<username>')
@admin_required
def user_info(username):
    """사용자 정보 페이지"""
    users = load_users()
    
    if username not in users:
        return "사용자를 찾을 수 없습니다.", 404
    
    user = users[username]
    # 해시된 비밀번호를 그대로 사용
    hashed_password = user['password']
    
    # 로그 파일 읽기
    user['logs'] = load_user_logs(username)
    
    return render_template('user_info.html', user=user, decrypted_password=hashed_password)

@app.route('/club/intro')
def club_intro():
    """소개 페이지 - 로그인 없이 접근 가능"""
    return render_template('club/intro.html')

@app.route('/club/history')
@login_required
def club_history():
    """동아리 연혁 - 로그인 필요"""
    return render_template('club/history.html')

@app.route('/club/activities')
@login_required
def club_activities():
    return render_template('club/activities.html')

@app.route('/club/news')
@login_required
def club_news():
    return render_template('club/news.html')

@app.route('/club/photos')
@login_required
def club_photos():
    return render_template('club/photos.html')

@app.route('/club/join')
@login_required
def club_join():
    return render_template('club/join.html')

@app.route('/notice')
@login_required
def notice():
    """공지사항 페이지"""
    page = request.args.get('page', 1, type=int)
    search_type = request.args.get('search_type', 'all')
    search_query = request.args.get('search_query', '')
    
    notices = load_content(NOTICES_DIR, 'notices.json')
    
    # 최신 글이 맨 위에 오도록 정렬
    notices = sorted(notices, key=lambda x: x['created_at'], reverse=True)
    
    # 검색 필터링
    if search_query:
        if search_type == 'title':
            notices = [item for item in notices if search_query.lower() in item.get('title', '').lower()]
        elif search_type == 'content':
            notices = [item for item in notices if search_query.lower() in item.get('content', '').lower()]
        elif search_type == 'author':
            notices = [item for item in notices if search_query.lower() in item.get('author', '').lower()]
        else:  # 'all'
            notices = [item for item in notices if 
                    search_query.lower() in item.get('title', '').lower() or 
                    search_query.lower() in item.get('content', '').lower() or 
                    search_query.lower() in item.get('author', '').lower()]
    
    # 페이지네이션 처리
    per_page = 5
    current_notices, page, total_pages, total_items = paginate_items(notices, page, per_page)
    
    return render_template('notice.html', 
                          items=current_notices,
                          page=page,
                          total_pages=total_pages,
                          items_total=total_items,
                          per_page=per_page,
                          search_type=search_type,
                          search_query=search_query)

@app.route('/notice/write', methods=['GET', 'POST'])
@admin_required
def write_notice():
    """공지사항 작성 페이지 (관리자만)"""
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        
        if not title:
            flash('제목을 입력해주세요.')
            return redirect(url_for('write_notice'))
        
        if not content:
            flash('내용을 입력해주세요.')
            return redirect(url_for('write_notice'))
        
        # 파일 업로드 처리
        files = []
        if 'files[]' in request.files:
            uploaded_files = request.files.getlist('files[]')
            for file in uploaded_files:
                if file and file.filename and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    # 파일명 중복 방지를 위해 타임스탬프 추가
                    timestamp = int(time.time())
                    filename = f"{timestamp}_{filename}"
                    file_path = os.path.join(UPLOAD_FOLDER, filename)
                    file.save(file_path)
                    
                    files.append({
                        'filename': file.filename,
                        'stored_filename': filename,
                        'path': f"/static/uploads/{filename}"
                    })
        
        notices = load_content(NOTICES_DIR, 'notices.json')
        
        # 새 공지사항 ID 생성
        item_id = 1
        if notices:
            item_id = max(item['id'] for item in notices) + 1
        
        # 관리자 계정이거나 특정 역할이 있는 경우 표시 이름 변경
        display_name = get_display_name(session['username'])
        
        # 새 공지사항 데이터
        new_notice = {
            'id': item_id,
            'title': title,
            'content': content.strip(),  # 내용 앞뒤 공백 제거
            'author': display_name,      # 표시 이름 사용
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'views': 0,
            'files': files,
            'raw_author': session['username']  # 원래 사용자명도 저장
        }
        
        notices.append(new_notice)
        save_content(NOTICES_DIR, 'notices.json', notices)
        
        # 로그 기록 - 상세 정보 포함
        add_log(
            session['username'], 
            "공지사항 작성", 
            page="notice", 
            content_id=item_id, 
            content_title=title
        )
        
        flash('공지사항이 등록되었습니다.')
        return redirect(url_for('notice'))
    
    return render_template('write_notice.html')

@app.route('/notice/<int:item_id>')
def view_notice(item_id):
    """공지사항 상세 보기"""
    notices = load_content(NOTICES_DIR, 'notices.json')
    item = next((n for n in notices if n['id'] == item_id), None)
    
    if not item:
        flash('존재하지 않는 공지사항입니다.')
        return redirect(url_for('notice'))
    
    # 조회수 증가 호출
    if increment_view_count(item_id, 'notice'):
        item['views'] += 1
        save_content(NOTICES_DIR, 'notices.json', notices)
    
    return render_template('view_notice.html', item=item)

@app.route('/notice/delete/<int:item_id>', methods=['GET'])
@admin_required
def delete_notice(item_id):
    """공지사항 삭제"""
    item = get_content_item(NOTICES_DIR, 'notices.json', item_id)
    
    if not item:
        flash('존재하지 않는 공지사항입니다.')
        return redirect(url_for('notice'))
    
    # 첨부 파일이 있다면 삭제
    if 'files' in item and item['files']:
        for file in item['files']:
            if 'stored_filename' in file:
                file_path = os.path.join(os.getcwd(), 'static', 'uploads', file['stored_filename'])
                if os.path.exists(file_path):
                    os.remove(file_path)
    
    # 공지사항 삭제
    notices = load_content(NOTICES_DIR, 'notices.json')
    notices = [n for n in notices if n['id'] != item_id]
    save_content(NOTICES_DIR, 'notices.json', notices)
    
    flash('공지사항이 삭제되었습니다.')
    return redirect(url_for('notice'))

@app.route('/schedule')
@login_required
def schedule():
    """활동 일정 페이지"""
    page = request.args.get('page', 1, type=int)
    search_type = request.args.get('search_type', 'all')
    search_query = request.args.get('search_query', '')
    
    schedules = load_content(SCHEDULES_DIR, 'schedules.json')
    
    # 날짜 순으로 정렬 (미래 일정이 먼저)
    schedules = sorted(schedules, key=lambda x: x['event_date'])
    
    # 검색 필터링
    if search_query:
        if search_type == 'title':
            schedules = [item for item in schedules if search_query.lower() in item.get('title', '').lower()]
        elif search_type == 'content':
            schedules = [item for item in schedules if search_query.lower() in item.get('content', '').lower()]
        else:  # 'all'
            schedules = [item for item in schedules if 
                    search_query.lower() in item.get('title', '').lower() or 
                    search_query.lower() in item.get('content', '').lower()]
    
    # 페이지네이션 처리
    per_page = 5
    current_schedules, page, total_pages, total_items = paginate_items(schedules, page, per_page)
    
    return render_template('schedule.html', 
                          items=current_schedules,
                          page=page,
                          total_pages=total_pages,
                          items_total=total_items,
                          per_page=per_page,
                          search_type=search_type,
                          search_query=search_query)

@app.route('/schedule/write', methods=['GET', 'POST'])
@admin_required
def write_schedule():
    """활동 일정 작성 페이지 (관리자만)"""
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        event_date = request.form.get('event_date', '').strip()
        event_time = request.form.get('event_time', '').strip()
        location = request.form.get('location', '').strip()
        
        if not title or not event_date:
            flash('제목과 일정 날짜는 필수 입력 항목입니다.')
            return redirect(url_for('write_schedule'))
        
        schedules = load_content(SCHEDULES_DIR, 'schedules.json')
        
        # 새 일정 ID 생성
        item_id = 1
        if schedules:
            item_id = max(item['id'] for item in schedules) + 1
        
        # 새 일정 데이터
        new_schedule = {
            'id': item_id,
            'title': title,
            'content': content.strip(),  # 내용 앞뒤 공백 제거
            'event_date': event_date,
            'event_time': event_time,
            'location': location,
            'author': session['username'],
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'views': 0
        }
        
        schedules.append(new_schedule)
        save_content(SCHEDULES_DIR, 'schedules.json', schedules)
        
        flash('활동 일정이 등록되었습니다.')
        return redirect(url_for('schedule'))
    
    return render_template('write_schedule.html')

@app.route('/schedule/<int:item_id>')
def view_schedule(item_id):
    """일정 상세 보기"""
    schedules = load_content(SCHEDULES_DIR, 'schedules.json')
    item = next((s for s in schedules if s['id'] == item_id), None)
    
    if not item:
        flash('존재하지 않는 일정입니다.')
        return redirect(url_for('schedule'))
    
    # 조회수 증가 호출
    if increment_view_count(item_id, 'schedule'):
        item['views'] += 1
        save_content(SCHEDULES_DIR, 'schedules.json', schedules)
    
    return render_template('view_schedule.html', item=item)

@app.route('/gallery')
@login_required
def gallery():
    """갤러리 페이지"""
    page = request.args.get('page', 1, type=int)
    search_type = request.args.get('search_type', 'all')
    search_query = request.args.get('search_query', '')
    
    gallery_items = load_content(GALLERY_DIR, 'gallery.json')
    
    # 최신 갤러리 항목이 먼저 표시
    gallery_items = sorted(gallery_items, key=lambda x: x['created_at'], reverse=True)
    
    # 검색 필터링
    if search_query:
        if search_type == 'title':
            gallery_items = [item for item in gallery_items if search_query.lower() in item.get('title', '').lower()]
        elif search_type == 'content':
            gallery_items = [item for item in gallery_items if search_query.lower() in item.get('content', '').lower()]
        else:  # 'all'
            gallery_items = [item for item in gallery_items if 
                    search_query.lower() in item.get('title', '').lower() or 
                    search_query.lower() in item.get('content', '').lower()]
    
    # 페이지네이션 처리
    per_page = 5  # 갤러리도 동일하게 5개로 변경
    current_gallery, page, total_pages, total_items = paginate_items(gallery_items, page, per_page)
    
    return render_template('gallery.html', 
                          items=current_gallery,
                          page=page,
                          total_pages=total_pages,
                          items_total=total_items,
                          per_page=per_page,
                          search_type=search_type,
                          search_query=search_query)

@app.route('/gallery/<int:item_id>')
def view_gallery(item_id):
    """갤러리 상세 보기"""
    gallery_items = load_content(GALLERY_DIR, 'gallery.json')
    item = next((g for g in gallery_items if g['id'] == item_id), None)
    
    if not item:
        flash('존재하지 않는 갤러리 항목입니다.')
        return redirect(url_for('gallery'))
    
    # 조회수 증가 호출
    if increment_view_count(item_id, 'gallery'):
        item['views'] += 1
        save_content(GALLERY_DIR, 'gallery.json', gallery_items)
    
    return render_template('view_gallery.html', item=item)

@app.route('/gallery/delete/<int:item_id>', methods=['GET'])
@login_required
def delete_gallery(item_id):
    """갤러리 항목 삭제"""
    item = get_content_item(GALLERY_DIR, 'gallery.json', item_id)
    
    if not item:
        flash('존재하지 않는 갤러리 항목입니다.')
        return redirect(url_for('gallery'))
    
    # 관리자이거나 작성자인 경우에만 삭제 가능
    if not session.get('is_admin') and session['username'] != item['author']:
        flash('삭제 권한이 없습니다.')
        return redirect(url_for('view_gallery', item_id=item_id))
    
    # 이미지 파일 삭제
    if 'image_path' in item:
        image_filename = os.path.basename(item['image_path'])
        image_path = os.path.join(os.getcwd(), 'static', 'uploads', 'gallery', image_filename)
        if os.path.exists(image_path):
            os.remove(image_path)
    
    # 갤러리 항목 삭제
    gallery_items = load_content(GALLERY_DIR, 'gallery.json')
    gallery_items = [g for g in gallery_items if g['id'] != item_id]
    save_content(GALLERY_DIR, 'gallery.json', gallery_items)
    
    flash('갤러리 항목이 삭제되었습니다.')
    return redirect(url_for('gallery'))

@app.route('/gallery/upload', methods=['GET', 'POST'])
@login_required
def upload_gallery():
    """갤러리 이미지 업로드"""
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        
        if not title:
            flash('제목을 입력해주세요.')
            return redirect(url_for('upload_gallery'))
        
        # 이미지 파일 업로드 처리
        if 'image' not in request.files:
            flash('이미지 파일을 선택해주세요.')
            return redirect(url_for('upload_gallery'))
        
        image_file = request.files['image']
        
        if not image_file or not image_file.filename:
            flash('이미지 파일을 선택해주세요.')
            return redirect(url_for('upload_gallery'))
        
        if not allowed_image_file(image_file.filename):
            flash('지원하지 않는 이미지 형식입니다. JPG, PNG, GIF 형식만 업로드 가능합니다.')
            return redirect(url_for('upload_gallery'))
        
        # 파일 저장
        filename = secure_filename(image_file.filename)
        timestamp = int(time.time())
        filename = f"{timestamp}_{filename}"
        file_path = os.path.join(GALLERY_UPLOAD_FOLDER, filename)
        image_file.save(file_path)
        
        gallery_items = load_content(GALLERY_DIR, 'gallery.json')
        
        # 새 갤러리 항목 ID 생성
        item_id = 1
        if gallery_items:
            item_id = max(item['id'] for item in gallery_items) + 1
        
        # 새 갤러리 항목 데이터
        new_gallery_item = {
            'id': item_id,
            'title': title,
            'content': content.strip(),  # 내용 앞뒤 공백 제거
            'image_path': f"/static/uploads/gallery/{filename}",
            'author': session['username'],
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'views': 0
        }
        
        gallery_items.append(new_gallery_item)
        save_content(GALLERY_DIR, 'gallery.json', gallery_items)
        
        flash('갤러리 이미지가 업로드되었습니다.')
        return redirect(url_for('gallery'))
    
    return render_template('upload_gallery.html')

@app.route('/suggestion')
@login_required
def suggestion():
    """건의사항 페이지"""
    page = request.args.get('page', 1, type=int)
    search_type = request.args.get('search_type', 'all')
    search_query = request.args.get('search_query', '')
    
    suggestions = load_content(SUGGESTIONS_DIR, 'suggestions.json')
    
    # 최신 건의사항이 먼저 표시
    suggestions = sorted(suggestions, key=lambda x: x['created_at'], reverse=True)
    
    # 현재 사용자가 작성한 건의사항만 표시 (관리자는 모두 볼 수 있음)
    if not session.get('is_admin', False):
        suggestions = [item for item in suggestions if item['author'] == session['username']]
    
    # 검색 필터링
    if search_query:
        if search_type == 'title':
            suggestions = [item for item in suggestions if search_query.lower() in item.get('title', '').lower()]
        elif search_type == 'content':
            suggestions = [item for item in suggestions if search_query.lower() in item.get('content', '').lower()]
        elif search_type == 'author' and session.get('is_admin', False):
            suggestions = [item for item in suggestions if search_query.lower() in item.get('author', '').lower()]
        else:  # 'all'
            suggestions = [item for item in suggestions if 
                    search_query.lower() in item.get('title', '').lower() or 
                    search_query.lower() in item.get('content', '').lower()]
    
    # 페이지네이션 처리
    per_page = 5
    current_suggestions, page, total_pages, total_items = paginate_items(suggestions, page, per_page)
    
    return render_template('suggestion.html', 
                          items=current_suggestions,
                          page=page,
                          total_pages=total_pages,
                          items_total=total_items,
                          per_page=per_page,
                          search_type=search_type,
                          search_query=search_query,
                          now=datetime.now(),
                          is_admin=session.get('is_admin', False))

@app.route('/suggestion/write', methods=['GET', 'POST'])
@login_required
def write_suggestion():
    """건의사항 작성 페이지"""
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        is_anonymous = 'anonymous' in request.form
        
        if not title:
            flash('제목을 입력해주세요.')
            return redirect(url_for('write_suggestion'))
        
        if not content:
            flash('내용을 입력해주세요.')
            return redirect(url_for('write_suggestion'))
        
        suggestions = load_content(SUGGESTIONS_DIR, 'suggestions.json')
        
        # 새 건의사항 ID 생성
        item_id = 1
        if suggestions:
            item_id = max(item['id'] for item in suggestions) + 1
        
        # 새 건의사항 데이터
        new_suggestion = {
            'id': item_id,
            'title': title,
            'content': content.strip(),  # 내용 앞뒤 공백 제거
            'author': session['username'],
            'display_name': '익명' if is_anonymous else session['username'],
            'is_anonymous': is_anonymous,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'views': 0,
            'answered': False,
            'answer': '',
            'answer_date': '',
            'answer_author': ''
        }
        
        suggestions.append(new_suggestion)
        save_content(SUGGESTIONS_DIR, 'suggestions.json', suggestions)
        
        flash('건의사항이 등록되었습니다.')
        return redirect(url_for('suggestion'))
    
    return render_template('write_suggestion.html')

@app.route('/suggestion/<int:item_id>')
def view_suggestion(item_id):
    """건의사항 상세 보기"""
    suggestions = load_content(SUGGESTIONS_DIR, 'suggestions.json')
    item = next((s for s in suggestions if s['id'] == item_id), None)
    
    if not item:
        flash('존재하지 않는 건의사항입니다.')
        return redirect(url_for('suggestion'))
    
    # 조회수 증가 호출
    if increment_view_count(item_id, 'suggestion'):
        item['views'] += 1
        save_content(SUGGESTIONS_DIR, 'suggestions.json', suggestions)
    
    return render_template('view_suggestion.html', item=item)

@app.route('/suggestion/answer/<int:item_id>', methods=['POST'])
@admin_required
def answer_suggestion(item_id):
    """건의사항 답변 (관리자만)"""
    answer = request.form.get('answer', '').strip()
    
    if not answer:
        flash('답변 내용을 입력해주세요.')
        return redirect(url_for('view_suggestion', item_id=item_id))
    
    suggestions = load_content(SUGGESTIONS_DIR, 'suggestions.json')
    
    # 건의사항 제목 찾기 (로그 기록용)
    title = None
    for suggestion in suggestions:
        if suggestion['id'] == item_id:
            title = suggestion.get('title')
            break
    
    # 관리자 계정이거나 특정 역할이 있는 경우 표시 이름 변경
    display_name = get_display_name(session['username'])
    
    for suggestion in suggestions:
        if suggestion['id'] == item_id:
            suggestion['answered'] = True
            suggestion['answer'] = answer
            suggestion['answer_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            suggestion['answer_author'] = display_name  # 표시 이름 사용
            suggestion['raw_answer_author'] = session['username']  # 원래 사용자명도 저장
            break
    
    save_content(SUGGESTIONS_DIR, 'suggestions.json', suggestions)
    
    # 로그 기록 - 상세 정보 포함
    add_log(
        session['username'], 
        "건의사항 답변", 
        page="suggestion", 
        content_id=item_id, 
        content_title=title
    )
    
    flash('답변이 등록되었습니다.')
    return redirect(url_for('view_suggestion', item_id=item_id))

@app.route('/freeboard')
@login_required
def freeboard():
    """자율 자료 게시판 페이지"""
    page = request.args.get('page', 1, type=int)
    search_type = request.args.get('search_type', 'all')
    search_query = request.args.get('search_query', '')
    
    posts = load_posts()
    
    # 검색 필터링
    if search_query:
        if search_type == 'title':
            posts = [item for item in posts if search_query.lower() in item.get('title', '').lower()]
        elif search_type == 'content':
            posts = [item for item in posts if search_query.lower() in item.get('content', '').lower()]
        elif search_type == 'author':
            posts = [item for item in posts if search_query.lower() in item.get('author', '').lower()]
        else:  # 'all'
            posts = [item for item in posts if 
                    search_query.lower() in item.get('title', '').lower() or 
                    search_query.lower() in item.get('content', '').lower() or 
                    search_query.lower() in item.get('author', '').lower()]
    
    # 페이지네이션 처리
    per_page = 5
    current_posts, page, total_pages, total_items = paginate_items(posts, page, per_page)
    
    return render_template('freeboard.html', 
                          items=current_posts,
                          page=page,
                          total_pages=total_pages,
                          items_total=total_items,
                          per_page=per_page,
                          search_type=search_type,
                          search_query=search_query,
                          now=datetime.now())

@app.route('/freeboard/write', methods=['GET', 'POST'])
@login_required
def write_post():
    """자료 게시글 작성 페이지"""
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        
        if not title:
            flash('제목을 입력해주세요.')
            return redirect(url_for('write_post'))
        
        if not content:
            flash('내용을 입력해주세요.')
            return redirect(url_for('write_post'))
        
        # 파일 업로드 처리
        files = []
        if 'file' in request.files:
            uploaded_files = request.files.getlist('file')
            for file in uploaded_files:
                if file and file.filename and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    # 파일명 중복 방지를 위해 타임스탬프 추가
                    timestamp = int(time.time())
                    filename = f"{timestamp}_{filename}"
                    file_path = os.path.join(UPLOAD_FOLDER, filename)
                    file.save(file_path)
                    
                    files.append({
                        'filename': file.filename,
                        'stored_filename': filename,
                        'path': f"/static/uploads/{filename}"
                    })
        
        posts = load_posts()
        
        # 새 게시글 ID 생성
        post_id = 1
        if posts:
            post_id = max(post['id'] for post in posts) + 1
        
        # 관리자 계정이거나 특정 역할이 있는 경우 표시 이름 변경
        display_name = get_display_name(session['username'])
        
        # 새 게시글 데이터
        new_post = {
            'id': post_id,
            'title': title,
            'content': content.strip(),  # 내용 앞뒤 공백 제거
            'author': display_name,     # 표시 이름 사용
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'views': 0,
            'files': files,
            'raw_author': session['username']  # 원래 사용자명도 저장
        }
        
        posts.append(new_post)
        save_posts(posts)
        
        # 로그 기록 - 상세 정보 포함
        add_log(
            session['username'], 
            "게시글 작성", 
            page="freeboard", 
            content_id=post_id, 
            content_title=title
        )
        
        flash('게시글이 등록되었습니다.')
        return redirect(url_for('freeboard'))
    
    return render_template('write_post.html')

@app.route('/post/<int:post_id>')
def view_post(post_id):
    """게시글 상세 보기"""
    try:
        posts = load_posts()
        post = next((p for p in posts if p['id'] == post_id), None)
        
        if not post:
            flash('존재하지 않는 게시글입니다.')
            return redirect(url_for('freeboard'))
        
        # 조회수 증가 호출
        if increment_view_count(post_id, 'post'):
            post['views'] += 1
            save_posts(posts)
        
        return render_template('view_post.html', post=post)
    except Exception as e:
        print(f"Error in view_post: {e}")
        flash('게시글을 불러오는 중 오류가 발생했습니다.')
        return redirect(url_for('freeboard'))

@app.route('/freeboard/delete/<int:post_id>', methods=['GET'])
@login_required
def delete_post(post_id):
    """게시글 삭제"""
    post = get_post(post_id)
    
    if not post:
        flash('존재하지 않는 게시글입니다.')
        return redirect(url_for('freeboard'))
    
    # 관리자이거나 작성자인 경우에만 삭제 가능
    if not session.get('is_admin') and session['username'] != post['author']:
        flash('삭제 권한이 없습니다.')
        return redirect(url_for('view_post', post_id=post_id))
    
    # 첨부 파일이 있다면 삭제
    if 'files' in post:
        for file in post['files']:
            file_path = os.path.join(os.getcwd(), 'static', 'uploads', file['stored_filename'])
            if os.path.exists(file_path):
                os.remove(file_path)
    
    # 게시글 삭제
    posts = load_posts()
    posts = [p for p in posts if p['id'] != post_id]
    save_posts(posts)
    
    flash('게시글이 삭제되었습니다.')
    return redirect(url_for('freeboard'))

@app.route('/freeboard/edit/<int:post_id>', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    """게시글 수정 페이지"""
    posts = load_posts()
    post = next((p for p in posts if p['id'] == post_id), None)
    
    if not post:
        flash('존재하지 않는 게시글입니다.')
        return redirect(url_for('freeboard'))
    
    # 관리자이거나 작성자인 경우에만 수정 가능
    if not session.get('is_admin') and session['username'] != post['raw_author']:
        flash('수정 권한이 없습니다.')
        return redirect(url_for('view_post', post_id=post_id))
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        
        if not title:
            flash('제목을 입력해주세요.')
            return render_template('edit_post.html', post=post)
        
        if not content:
            flash('내용을 입력해주세요.')
            return render_template('edit_post.html', post=post)
        
        # 파일 업로드 처리
        files = post.get('files', [])
        if 'file' in request.files:
            uploaded_files = request.files.getlist('file')
            for file in uploaded_files:
                if file and file.filename and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    # 파일명 중복 방지를 위해 타임스탬프 추가
                    timestamp = int(time.time())
                    filename = f"{timestamp}_{filename}"
                    file_path = os.path.join(UPLOAD_FOLDER, filename)
                    file.save(file_path)
                    
                    files.append({
                        'filename': file.filename,
                        'stored_filename': filename,
                        'path': f"/static/uploads/{filename}"
                    })
        
        # 게시글 수정
        post['title'] = title
        post['content'] = content.strip()
        post['modified_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        post['files'] = files
        
        # 변경사항 저장
        save_posts(posts)
        
        # 로그 기록
        add_log(
            session['username'], 
            "게시글 수정", 
            page="freeboard", 
            content_id=post_id, 
            content_title=title
        )
        
        flash('게시글이 수정되었습니다.')
        return redirect(url_for('view_post', post_id=post_id))
    
    return render_template('edit_post.html', post=post)

@app.route('/schedule/delete/<int:item_id>', methods=['GET'])
@login_required
def delete_schedule(item_id):
    """일정 삭제"""
    item = get_content_item(SCHEDULES_DIR, 'schedules.json', item_id)
    
    if not item:
        flash('존재하지 않는 일정입니다.')
        return redirect(url_for('schedule'))
    
    # 관리자이거나 작성자인 경우에만 삭제 가능
    if not session.get('is_admin') and session['username'] != item['author']:
        flash('삭제 권한이 없습니다.')
        return redirect(url_for('view_schedule', item_id=item_id))
    
    # 일정 삭제
    schedules = load_content(SCHEDULES_DIR, 'schedules.json')
    schedules = [s for s in schedules if s['id'] != item_id]
    save_content(SCHEDULES_DIR, 'schedules.json', schedules)
    
    flash('일정이 삭제되었습니다.')
    return redirect(url_for('schedule'))

@app.route('/activities')
@login_required
def activities():
    """활동 내용 페이지"""
    page = request.args.get('page', 1, type=int)
    search_type = request.args.get('search_type', 'all')
    search_query = request.args.get('search_query', '')
    
    # 데이터 로드
    activity_items = load_content(ACTIVITIES_DIR, 'activities.json')
    
    # 검색 필터링
    if search_query:
        if search_type == 'title':
            activity_items = [item for item in activity_items if search_query.lower() in item.get('title', '').lower()]
        elif search_type == 'content':
            activity_items = [item for item in activity_items if search_query.lower() in item.get('content', '').lower()]
        elif search_type == 'author':
            activity_items = [item for item in activity_items if search_query.lower() in item.get('author', '').lower()]
        else:  # 'all'
            activity_items = [item for item in activity_items if 
                    search_query.lower() in item.get('title', '').lower() or 
                    search_query.lower() in item.get('content', '').lower() or 
                    search_query.lower() in item.get('author', '').lower()]
    
    # 페이지네이션 처리
    per_page = 5
    current_activities, page, total_pages, total_items = paginate_items(activity_items, page, per_page)
    
    return render_template('activities.html', 
                          items=current_activities,
                          page=page,
                          total_pages=total_pages,
                          items_total=total_items,
                          per_page=per_page,
                          search_type=search_type,
                          search_query=search_query,
                          now=datetime.now())

@app.route('/activities/write', methods=['GET', 'POST'])
@login_required
def write_activity():
    """활동 내용 작성 페이지"""
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        activity_date = request.form.get('activity_date', '').strip()
        activity_location = request.form.get('activity_location', '').strip()
        participants = request.form.get('participants', '').strip()
        
        if not title or not activity_date:
            flash('제목과 활동 날짜는 필수 입력 항목입니다.')
            return redirect(url_for('write_activity'))
        
        activities = load_content(ACTIVITIES_DIR, 'activities.json')
        
        # 새 활동 내용 ID 생성
        item_id = 1
        if activities:
            item_id = max(item['id'] for item in activities) + 1
        
        # 파일 업로드 처리
        files = []
        if 'files' in request.files:
            uploaded_files = request.files.getlist('files')
            for file in uploaded_files:
                if file and file.filename and allowed_file(file.filename):
                    # 저장할 파일명 생성
                    filename = secure_filename(file.filename)
                    timestamp = int(time.time())
                    stored_filename = f"{timestamp}_{filename}"
                    
                    # 파일 저장
                    file_path = os.path.join(UPLOAD_FOLDER, stored_filename)
                    file.save(file_path)
                    
                    # 파일 정보 저장
                    files.append({
                        'filename': filename,
                        'stored_filename': stored_filename,
                        'path': f"/static/uploads/{stored_filename}"
                    })
        
        # 새 활동 내용 데이터
        new_activity = {
            'id': item_id,
            'title': title,
            'content': content.strip(),  # 내용 앞뒤 공백 제거
            'activity_date': activity_date,
            'activity_location': activity_location,
            'participants': participants,
            'author': session['username'],
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'views': 0,
            'files': files
        }
        
        activities.append(new_activity)
        save_content(ACTIVITIES_DIR, 'activities.json', activities)
        
        flash('활동 내용이 등록되었습니다.')
        return redirect(url_for('activities'))
    
    return render_template('write_activity.html')

@app.route('/activity/<int:activity_id>')
def view_activity(activity_id):
    """활동 내용 상세 보기"""
    activities = load_content(ACTIVITIES_DIR, 'activities.json')
    item = next((a for a in activities if a['id'] == activity_id), None)
    
    if not item:
        flash('존재하지 않는 활동입니다.')
        return redirect(url_for('activities'))
    
    # 조회수 증가 호출
    if increment_view_count(activity_id, 'activity'):
        item['views'] += 1
        save_content(ACTIVITIES_DIR, 'activities.json', activities)
    
    return render_template('view_activity.html', item=item)

@app.route('/activities/delete/<int:activity_id>', methods=['GET'])
@login_required
def delete_activity(activity_id):
    """활동 내용 삭제"""
    item = get_content_item(ACTIVITIES_DIR, 'activities.json', activity_id)
    
    if not item:
        flash('존재하지 않는 활동입니다.')
        return redirect(url_for('activities'))
    
    # 관리자이거나 작성자인 경우에만 삭제 가능
    if not session.get('is_admin') and session['username'] != item['author']:
        flash('삭제 권한이 없습니다.')
        return redirect(url_for('view_activity', activity_id=activity_id))
    
    # 첨부 파일이 있다면 삭제
    if 'files' in item and item['files']:
        for file in item['files']:
            if 'stored_filename' in file:
                file_path = os.path.join(UPLOAD_FOLDER, file['stored_filename'])
                if os.path.exists(file_path):
                    os.remove(file_path)
    
    # 활동 내용 삭제
    activities = load_content(ACTIVITIES_DIR, 'activities.json')
    activities = [a for a in activities if a['id'] != activity_id]
    save_content(ACTIVITIES_DIR, 'activities.json', activities)
    
    flash('활동 내용이 삭제되었습니다.')
    return redirect(url_for('activities'))

# 자율 자료 게시판 및 기타 게시판 관련 함수
def allowed_file(filename):
    """파일 확장자 체크"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def allowed_image_file(filename):
    """이미지 파일 확장자 체크"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS

def load_content(directory, filename):
    """콘텐츠 데이터 불러오기"""
    content_file = os.path.join(directory, filename)
    
    if not os.path.exists(content_file):
        return []
    
    try:
        with open(content_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []

def save_content(directory, filename, content):
    """콘텐츠 데이터 저장하기"""
    content_file = os.path.join(directory, filename)
    
    with open(content_file, 'w', encoding='utf-8') as f:
        json.dump(content, f, ensure_ascii=False, indent=4)

def get_content_item(directory, filename, item_id):
    """특정 콘텐츠 항목 가져오기"""
    items = load_content(directory, filename)
    for item in items:
        if item['id'] == item_id:
            return item
    return None

def load_posts():
    """게시글 목록 불러오기"""
    return load_content(POSTS_DIR, 'posts.json')

def save_posts(posts):
    """게시글 목록 저장하기"""
    save_content(POSTS_DIR, 'posts.json', posts)

def get_post(post_id):
    """특정 게시글 가져오기"""
    return get_content_item(POSTS_DIR, 'posts.json', post_id)

# 세션 체크 라우트 추가
@app.route('/check_session')
def check_session():
    """클라이언트 측 세션 체크 API"""
    # 요청 헤더에서 referer URL을 가져옵니다
    referer = request.headers.get('Referer', '')
    
    # 로그인이 필요없는 경로들
    public_paths = ['login', 'register', 'logout', 'home', 'index', 'club/intro', 'club/history']
    
    # Referer가 로그인이 필요없는 경로 중 하나에서 온 경우 유효한 세션으로 처리
    for path in public_paths:
        if path in referer:
            return jsonify({'status': 'valid', 'message': '공개 페이지 - 세션 체크 생략'}), 200
    
    # 그 외의 경우 세션 체크
    if 'logged_in' in session and session['logged_in']:
        return jsonify({'status': 'valid', 'message': '세션이 유효합니다.'}), 200
    else:
        return jsonify({'status': 'invalid', 'message': '세션이 만료되었습니다.'}), 401

# 시간 객체 생성을 위한 함수
def parse_datetime(datetime_str):
    """문자열 형태의 날짜/시간을 datetime 객체로 변환"""
    try:
        return datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S')
    except:
        # 형식이 다르거나 오류가 있는 경우 현재 시간 반환
        return datetime.now()

# 페이지네이션 처리를 위한 함수 정의
def paginate_items(items, page, per_page=5):
    """아이템 목록을 페이지네이션 처리하는 유틸리티 함수"""
    # datetime 객체 추가
    for item in items:
        if 'created_at' in item and 'created_at_datetime' not in item:
            item['created_at_datetime'] = parse_datetime(item['created_at'])
    
    # 정확한 시간 기준 정렬 (최신순)
    items = sorted(items, key=lambda x: x.get('created_at_datetime', datetime.now()), reverse=True)
    
    # 총 아이템 수와 페이지 수 계산
    total_items = len(items)
    total_pages = (total_items - 1) // per_page + 1 if items else 1
    page = min(max(page, 1), total_pages)
    
    # 현재 페이지 아이템 슬라이싱
    start_idx = (page - 1) * per_page
    end_idx = min(start_idx + per_page, total_items)
    
    current_items = items[start_idx:end_idx]
    
    # 정렬된 상태로 반환 (최신순)
    return current_items, page, total_pages, total_items

@app.route('/write_inquiry')
@login_required
def write_inquiry():
    """문의 작성 페이지"""
    return render_template('write_문의.html')

@app.route('/submit_inquiry', methods=['POST'])
@login_required
def submit_inquiry():
    name = request.form['name']
    email = request.form['email']
    message = request.form['message']
    
    # 문의 내용을 딕셔너리 형태로 저장
    inquiry = {
        'name': name,
        'email': email,
        'message': message
    }
    
    # 리스트에 추가
    inquiries.append(inquiry)  # 문의 내용을 리스트에 추가
    
    # 문의 제출 후 view_inquiry로 리다이렉션
    return redirect(url_for('view_inquiry'))

@app.route('/view_inquiry')
@admin_required
def view_inquiry():
    # 관리자가 아니면 액세스 거부
    if session.get('username') != 'admin':
        flash('관리자 권한이 필요합니다.', 'error')
        return redirect(url_for('home'))
    
    inquiries = []
    
    # 문의 데이터 폴더가 없으면 생성
    if not os.path.exists(INQUIRY_DIR):
        os.makedirs(INQUIRY_DIR)
    
    # 문의 파일들을 읽어옴
    for filename in os.listdir(INQUIRY_DIR):
        if filename.endswith('.json'):
            with open(os.path.join(INQUIRY_DIR, filename)) as f:
                inquiry_data = json.load(f)
                # 제출 시간 기준으로 내림차순 정렬을 위해 타임스탬프 추가
                if 'timestamp' not in inquiry_data and 'submit_date' in inquiry_data:
                    try:
                        # submit_date를 타임스탬프로 변환
                        dt = datetime.strptime(inquiry_data['submit_date'], '%Y-%m-%d %H:%M:%S')
                        inquiry_data['timestamp'] = dt.timestamp()
                    except:
                        inquiry_data['timestamp'] = 0
                inquiries.append(inquiry_data)
    
    # 최신 문의가 위로 오도록 정렬
    inquiries.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
    
    return render_template('view_inquiry.html', inquiries=inquiries)

@app.route('/admin/inquiries/<int:inquiry_id>')
@login_required
def view_inquiry_detail(inquiry_id):
    # 관리자가 아니면 액세스 거부
    if session.get('username') != 'admin':
        flash('관리자 권한이 필요합니다.', 'error')
        return redirect(url_for('view_inquiry'))
    
    # 문의 파일 경로
    inquiry_file = os.path.join(INQUIRY_DIR, f'inquiry_{inquiry_id}.json')
    
    # 파일이 존재하지 않는 경우
    if not os.path.exists(inquiry_file):
        flash('존재하지 않는 문의입니다.', 'error')
        return redirect(url_for('view_inquiry'))
    
    # 문의 데이터 읽기
    with open(inquiry_file) as f:
        inquiry_data = json.load(f)
    
    return render_template('view_inquiry_detail.html', inquiry=inquiry_data)

@app.route('/admin/inquiries/<int:inquiry_id>/reply', methods=['POST'])
@login_required
def reply_inquiry(inquiry_id):
    # 관리자가 아니면 액세스 거부
    if session.get('username') != 'admin':
        flash('관리자 권한이 필요합니다.', 'error')
        return redirect(url_for('home'))
    
    reply_content = request.form.get('reply', '')
    
    if not reply_content:
        flash('답변 내용을 입력해주세요.', 'error')
        return redirect(url_for('view_inquiry_detail', inquiry_id=inquiry_id))
    
    # 문의 파일 경로
    inquiry_file = os.path.join(INQUIRY_DIR, f'inquiry_{inquiry_id}.json')
    
    # 파일이 존재하지 않는 경우
    if not os.path.exists(inquiry_file):
        flash('존재하지 않는 문의입니다.', 'error')
        return redirect(url_for('view_inquiry'))
    
    # 문의 데이터 읽기
    with open(inquiry_file) as f:
        inquiry_data = json.load(f)
    
    # 답변 추가
    inquiry_data['reply'] = reply_content
    inquiry_data['reply_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    inquiry_data['status'] = '답변 완료'
    
    # 변경된 내용 저장
    with open(inquiry_file, 'w') as f:
        json.dump(inquiry_data, f, indent=2)
    
    # 로그 추가
    author = session.get('username')
    add_log(author, f"문의 {inquiry_id}번에 답변 등록", "inquiry", inquiry_id, f"문의 답변: {inquiry_data.get('title', '')}")
    
    flash('답변이 등록되었습니다.', 'success')
    return redirect(url_for('view_inquiry'))

@app.route('/donation')
def donation():
    """후원 페이지"""
    # 최근 후원자 목록 로드
    donations = load_donations()
    recent_donations = sorted(donations, key=lambda x: x.get('date', ''), reverse=True)[:10]
    return render_template('donation.html', recent_donations=recent_donations)

@app.route('/club/donation')
def club_donation():
    """클럽 후원 페이지"""
    # 최근 후원자 목록 로드
    donations = load_donations()
    recent_donations = sorted(donations, key=lambda x: x.get('date', ''), reverse=True)[:10]
    return render_template('club/donation.html', recent_donations=recent_donations)

@app.route('/club/submit_donation', methods=['POST'])
def club_submit_donation():
    """후원 신청 처리"""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        amount = request.form.get('amount', '').strip()
        payment_method = request.form.get('payment_method', '').strip()
        anonymous = 'anonymous' in request.form
        message = request.form.get('message', '').strip()
        
        # 필수 필드 검증
        if not name or not email or not amount or not payment_method:
            flash('필수 항목을 모두 입력해주세요.')
            return redirect(url_for('club_donation'))
        
        # 금액 검증
        try:
            amount = int(amount)
            if amount < 1000:
                flash('후원 금액은 1,000원 이상이어야 합니다.')
                return redirect(url_for('club_donation'))
        except ValueError:
            flash('올바른 금액을 입력해주세요.')
            return redirect(url_for('club_donation'))
        
        # 후원 정보 저장
        donations = load_donations()
        
        # 새 후원 ID 생성
        donation_id = 1
        if donations:
            donation_id = max(int(d.get('id', 0)) for d in donations) + 1
        
        # 새 후원 데이터
        new_donation = {
            'id': donation_id,
            'name': name,
            'email': email,
            'amount': amount,
            'payment_method': payment_method,
            'anonymous': anonymous,
            'message': message,
            'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        donations.append(new_donation)
        save_donations(donations)
        
        flash('후원 신청이 완료되었습니다. 감사합니다!')
        return redirect(url_for('club_donation'))
    
    return redirect(url_for('club_donation'))

def load_donations():
    """후원 목록 불러오기"""
    return load_content(DONATIONS_DIR, 'donations.json')

def save_donations(donations):
    """후원 목록을 저장합니다."""
    save_content(DONATIONS_DIR, 'donations.json', donations)

@app.route('/club/questions/<int:question_id>/edit', methods=['GET', 'POST'])
@login_required
def club_edit_question(question_id):
    questions = load_questions()
    question = next((q for q in questions if q['id'] == question_id), None)
    
    if not question:
        flash('존재하지 않는 질문입니다.')
        return redirect(url_for('club_questions'))
    
    # 권한 검사: 작성자 또는 관리자만 수정 가능
    if not (question['username'] == session['username'] or session['username'] == 'admin'):
        flash('질문을 수정할 권한이 없습니다.')
        return redirect(url_for('club_view_question', question_id=question_id))
    
    # 이미 답변이 있는 경우 수정 불가
    if question.get('answer'):
        flash('이미 답변이 등록된 질문은 수정할 수 없습니다.')
        return redirect(url_for('club_view_question', question_id=question_id))
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        question_text = request.form.get('question', '').strip()
        is_private = 'is_private' in request.form
        
        if not title or not question_text:
            flash('제목과 내용은 필수 입력 항목입니다.')
            return render_template('edit_question.html', item=question)
        
        # 질문 업데이트
        question['title'] = title
        question['question'] = question_text
        question['is_private'] = is_private
        question['modified_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 변경사항 저장
        save_questions(questions)
        
        # 로그 기록
        add_log(session['username'], '질문 수정', f'질문 수정: {title}')
        
        flash('질문이 성공적으로 수정되었습니다.')
        return redirect(url_for('club_view_question', question_id=question_id))
    
    return render_template('edit_question.html', item=question)

def load_questions():
    """질문 목록 불러오기"""
    return load_content(QUESTIONS_DIR, 'questions.json')

def save_questions(questions):
    """질문 목록 저장하기"""
    save_content(QUESTIONS_DIR, 'questions.json', questions)

def get_question(question_id):
    """특정 질문 가져오기"""
    return get_content_item(QUESTIONS_DIR, 'questions.json', question_id)

# 조회수 증가 헬퍼 함수 추가
def increment_view_count(item_id, content_type):
    """
    조회수 증가 함수 - 24시간 내에 같은 사용자가 같은 글을 볼 때 조회수가 증가하지 않도록 처리
    
    Args:
        item_id: 게시글 ID
        content_type: 게시글 유형 (notice, schedule, gallery, suggestion, post, activity)
    
    Returns:
        bool: 조회수가 증가했으면 True, 아니면 False
    """
    # 세션에 조회 기록이 없으면 초기화
    if 'viewed_items' not in session:
        session['viewed_items'] = {}
    
    # item_id를 문자열로 변환하여 저장
    item_id_str = str(item_id)
    
    # 현재 시간 가져오기
    current_time = int(datetime.now().timestamp())
    
    # 세션에 해당 유형이 없으면 초기화
    if content_type not in session['viewed_items']:
        session['viewed_items'][content_type] = {}
    
    # 24시간(86400초)이 지나지 않았으면 조회수 증가하지 않음
    if item_id_str in session['viewed_items'][content_type]:
        last_view_time = int(session['viewed_items'][content_type][item_id_str])
        if current_time - last_view_time < 86400:
            return False
    
    # 조회 시간 기록
    session['viewed_items'][content_type][item_id_str] = current_time
    session.modified = True
    
    return True

# 갤러리 수정 기능
@app.route('/gallery/<int:item_id>/rewrite', methods=['GET', 'POST'])
@login_required
def rewrite_gallery(item_id):
    """갤러리 항목 수정 페이지"""
    gallery_items = load_content(GALLERY_DIR, 'gallery.json')
    item = next((g for g in gallery_items if g['id'] == item_id), None)
    
    if not item:
        flash('존재하지 않는 갤러리 항목입니다.')
        return redirect(url_for('gallery'))
    
    # 작성자 또는 관리자만 수정 가능
    if not (session.get('is_admin') or (item['author'] == session.get('username'))):
        flash('본인이 작성한 항목만 수정할 수 있습니다.')
        return redirect(url_for('gallery'))
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        
        if not title:
            flash('제목은 필수 입력 항목입니다.')
            return render_template('rewrite_gallery.html', item=item)
        
        # 기본 정보 업데이트
        item['title'] = title
        item['description'] = description
        item['modified_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 새 이미지 업로드 처리
        if 'image' in request.files and request.files['image'].filename:
            image_file = request.files['image']
            if allowed_image_file(image_file.filename):
                # 기존 이미지 백업
                old_image_path = item.get('image_path')
                
                # 새 이미지 저장
                filename = secure_filename(image_file.filename)
                file_path = os.path.join(GALLERY_UPLOAD_FOLDER, filename)
                if not os.path.exists(GALLERY_UPLOAD_FOLDER):
                    os.makedirs(GALLERY_UPLOAD_FOLDER)
                
                image_file.save(file_path)
                item['image_path'] = '/static/uploads/gallery/' + filename
            else:
                flash('허용되지 않는 이미지 형식입니다.')
                return render_template('rewrite_gallery.html', item=item)
        
        # 새 첨부 파일 업로드 처리
        if 'files' in request.files:
            uploaded_files = request.files.getlist('files')
            new_files = []
            
            for file in uploaded_files:
                if file.filename:
                    if allowed_file(file.filename):
                        filename = secure_filename(file.filename)
                        file_path = os.path.join(GALLERY_UPLOAD_FOLDER, filename)
                        file.save(file_path)
                        
                        new_files.append({
                            'filename': filename,
                            'path': '/static/uploads/gallery/' + filename
                        })
                    else:
                        flash('허용되지 않는 파일 형식이 포함되어 있습니다.')
                        return render_template('rewrite_gallery.html', item=item)
            
            # 기존 파일에 새 파일 추가
            if not item.get('files'):
                item['files'] = []
            
            item['files'].extend(new_files)
        
        # 갤러리 항목 저장
        save_content(GALLERY_DIR, 'gallery.json', gallery_items)
        
        # 로그 기록
        add_log(session['username'], '갤러리 수정', f'갤러리 항목 수정: {title}')
        
        flash('갤러리 항목이 수정되었습니다.')
        return redirect(url_for('gallery', item_id=item_id))
    
    return render_template('rewrite_gallery.html', item=item)

# 활동 내용 수정 기능
@app.route('/activity/<int:activity_id>/rewrite', methods=['GET', 'POST'])
@login_required
def rewrite_activity(activity_id):
    """활동 내용 수정 페이지"""
    activities = load_content(ACTIVITIES_DIR, 'activities.json')
    item = next((a for a in activities if a['id'] == activity_id), None)
    
    if not item:
        flash('존재하지 않는 활동입니다.')
        return redirect(url_for('activities'))
    
    # 작성자 또는 관리자만 수정 가능
    if not (session.get('is_admin') or (item['author'] == session.get('username'))):
        flash('본인이 작성한 활동만 수정할 수 있습니다.')
        return redirect(url_for('activities'))
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        activity_date = request.form.get('activity_date', '').strip()
        activity_location = request.form.get('activity_location', '').strip()
        category = request.form.get('category', '일반').strip()
        participants = request.form.get('participants', '').strip()
        
        if not title or not content or not activity_date:
            flash('제목, 내용, 활동 날짜는 필수 입력 항목입니다.')
            return render_template('rewrite_activity.html', item=item)
        
        # 기본 정보 업데이트
        item['title'] = title
        item['content'] = content
        item['activity_date'] = activity_date
        item['activity_location'] = activity_location
        item['category'] = category
        item['participants'] = participants
        item['modified_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 새 첨부 파일 업로드 처리
        if 'files' in request.files:
            uploaded_files = request.files.getlist('files')
            new_files = []
            
            for file in uploaded_files:
                if file.filename:
                    if allowed_file(file.filename):
                        filename = secure_filename(file.filename)
                        file_path = os.path.join(ACTIVITIES_DIR, 'uploads', filename)
                        
                        # 디렉토리가 없으면 생성
                        os.makedirs(os.path.dirname(file_path), exist_ok=True)
                        
                        file.save(file_path)
                        
                        new_files.append({
                            'filename': filename,
                            'path': f'/data/activities/uploads/{filename}'
                        })
                    else:
                        flash('허용되지 않는 파일 형식이 포함되어 있습니다.')
                        return render_template('rewrite_activity.html', item=item)
            
            # 기존 파일에 새 파일 추가
            if not item.get('files'):
                item['files'] = []
            
            item['files'].extend(new_files)
        
        # 활동 내용 저장
        save_content(ACTIVITIES_DIR, 'activities.json', activities)
        
        # 로그 기록
        add_log(session['username'], '활동 내용 수정', f'활동 내용 수정: {title}')
        
        flash('활동 내용이 수정되었습니다.')
        return redirect(url_for('activity', activity_id=activity_id))
    
    return render_template('rewrite_activity.html', item=item)

if __name__ == '__main__':
    app.run(
        host='0.0.0.0', 
        port=5000,
        debug=True  # 디버그 모드 활성화
    ) 