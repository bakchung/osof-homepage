"""
유틸리티 함수 모듈
"""
import json
import os
import bcrypt
from datetime import datetime

# 필요한 디렉토리와 파일 경로 설정
USERS_FILE = 'users.json'
BUTTONS_DIR = 'user_buttons'
LOGS_DIR = 'logs'

# 디렉토리 초기화
def init_directories():
    """필요한 디렉토리를 생성합니다."""
    for directory in [BUTTONS_DIR, LOGS_DIR]:
        if not os.path.exists(directory):
            os.makedirs(directory)

# 비밀번호 관련 함수
def hash_password(password):
    """비밀번호를 해시화합니다."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12)).decode('utf-8')

def check_password(password, stored_password):
    """비밀번호가 일치하는지 확인합니다."""
    try:
        return bcrypt.checkpw(password.encode('utf-8'), stored_password.encode('utf-8'))
    except:
        return False  # 패스워드 검증 실패 시 항상 False 반환

def validate_password(password):
    """비밀번호 복잡성을 검증합니다."""
    if len(password) < 8:
        return False, "비밀번호는 최소 8자 이상이어야 합니다."
    if not any(c.isupper() for c in password):
        return False, "비밀번호는 최소 1개의 대문자를 포함해야 합니다."
    if not any(c.islower() for c in password):
        return False, "비밀번호는 최소 1개의 소문자를 포함해야 합니다."
    if not any(c.isdigit() for c in password):
        return False, "비밀번호는 최소 1개의 숫자를 포함해야 합니다."
    if not any(c in "!@#$%^&*(),.?\":{}|<>" for c in password):
        return False, "비밀번호는 최소 1개의 특수문자를 포함해야 합니다."
    return True, ""

# 사용자 관련 함수
def load_users():
    """사용자 정보를 로드합니다."""
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_users(users):
    """사용자 정보를 저장합니다."""
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

# 버튼 관련 함수
def get_user_buttons_file(username):
    """사용자의 버튼 파일 경로를 반환합니다."""
    return os.path.join(BUTTONS_DIR, f'{username}_buttons.json')

def load_user_buttons(username):
    """사용자의 버튼 정보를 로드합니다."""
    buttons_file = get_user_buttons_file(username)
    if os.path.exists(buttons_file):
        with open(buttons_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_user_buttons(username, buttons):
    """사용자의 버튼 정보를 저장합니다."""
    buttons_file = get_user_buttons_file(username)
    with open(buttons_file, 'w', encoding='utf-8') as f:
        json.dump(buttons, f, ensure_ascii=False, indent=2)

# 로그 관련 함수
def add_log(username, action, page=None, content_id=None, content_title=None):
    """사용자 활동을 로그에 기록합니다.
    
    Args:
        username (str): 사용자 이름
        action (str): 수행한 액션 설명
        page (str, optional): 액션이 수행된 페이지(예: 'notice', 'freeboard')
        content_id (int, optional): 관련 콘텐츠의 ID (글 ID 등)
        content_title (str, optional): 관련 콘텐츠의 제목
    """
    log_file = os.path.join(LOGS_DIR, f'{username}.json')
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    try:
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                logs = json.load(f)
        else:
            logs = []
        
        log_entry = {
            'timestamp': current_time,
            'action': action
        }
        
        # 추가 정보가 있는 경우 로그에 포함
        if page:
            log_entry['page'] = page
        
        if content_id:
            log_entry['content_id'] = content_id
            
        if content_title:
            log_entry['content_title'] = content_title
        
        logs.append(log_entry)
        
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"로그 기록 중 오류 발생: {str(e)}")

def load_user_logs(username):
    """사용자의 로그를 로드합니다."""
    log_file = os.path.join(LOGS_DIR, f'{username}.json')
    if os.path.exists(log_file):
        with open(log_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return [] 