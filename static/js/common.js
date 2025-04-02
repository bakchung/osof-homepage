/**
 * 공통 JavaScript 함수 모음
 */

// 에러 메시지 표시 함수
function showError(message, elementId = 'error-message') {
    const errorElement = document.getElementById(elementId);
    if (errorElement) {
        errorElement.textContent = message;
        errorElement.style.display = 'block';
        
        // 3초 후 메시지 숨기기
        setTimeout(() => {
            errorElement.style.display = 'none';
        }, 3000);
    }
}

// 성공 메시지 표시 함수
function showSuccess(message, elementId = 'success-message') {
    const successElement = document.getElementById(elementId);
    if (successElement) {
        successElement.textContent = message;
        successElement.style.display = 'block';
        
        // 3초 후 메시지 숨기기
        setTimeout(() => {
            successElement.style.display = 'none';
        }, 3000);
    }
}

// API 요청 함수
async function apiRequest(url, method = 'GET', data = null) {
    try {
        const options = {
            method: method,
            headers: {
                'Content-Type': 'application/json'
            }
        };
        
        if (data) {
            options.body = JSON.stringify(data);
        }
        
        const response = await fetch(url, options);
        const result = await response.json();
        
        return {
            success: response.ok,
            status: response.status,
            data: result
        };
    } catch (error) {
        console.error('API 요청 오류:', error);
        return {
            success: false,
            status: 500,
            data: { message: '서버 요청 중 오류가 발생했습니다.' }
        };
    }
}

// 로그인 함수
async function login(username, password) {
    const response = await apiRequest('/login', 'POST', { username, password });
    
    if (response.success) {
        showSuccess(response.data.message);
        
        // 리디렉션
        if (response.data.redirect) {
            setTimeout(() => {
                window.location.href = response.data.redirect;
            }, 1000);
        }
    } else {
        showError(response.data.message);
    }
    
    return response;
}

// 회원가입 함수
async function register(username, password) {
    const response = await apiRequest('/register', 'POST', { username, password });
    
    if (response.success) {
        showSuccess(response.data.message);
        
        // 로그인 폼으로 전환
        setTimeout(() => {
            document.getElementById('login-form').style.display = 'block';
            document.getElementById('register-form').style.display = 'none';
        }, 1000);
    } else {
        showError(response.data.message);
    }
    
    return response;
}

// 모달 열기 함수
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'flex';
    }
}

// 모달 닫기 함수
function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'none';
    }
}

// 사용자 버튼 추가 함수
async function addButton(name, url) {
    const response = await apiRequest('/add_button', 'POST', { name, url });
    
    if (response.success) {
        showSuccess(response.data.message);
        return response.data.button;
    } else {
        showError(response.data.message);
        return null;
    }
}

// 사용자 버튼 삭제 함수
async function deleteButton(name) {
    const response = await apiRequest('/delete_button', 'POST', { name });
    
    if (response.success) {
        showSuccess(response.data.message);
        return true;
    } else {
        showError(response.data.message);
        return false;
    }
}

// 버튼 클릭 로깅 함수
async function logButtonClick(name, url) {
    await apiRequest('/button_click', 'POST', { name, url });
}

// 사용자 삭제 함수 (관리자용)
async function deleteUser(username) {
    const response = await apiRequest('/admin/delete_user', 'POST', { username });
    
    if (response.success) {
        showSuccess(response.data.message);
        return true;
    } else {
        showError(response.data.message);
        return false;
    }
}

// 로그아웃 함수
async function logout() {
    try {
        // GET 요청으로 변경 (서버가 GET 및 POST 모두 지원함)
        window.location.href = '/logout';
    } catch (error) {
        console.error('로그아웃 처리 중 오류 발생:', error);
    }
}

// 세션 체크 함수
async function checkSession() {
    try {
        // 현재 경로를 확인하여 로그인, 등록, 로그아웃, 홈 페이지에서는 세션 체크를 하지 않음
        const currentPath = window.location.pathname;
        const excludedPaths = ['/login', '/register', '/logout', '/home', '/index', '/club/intro', '/club/history'];
        
        if (excludedPaths.includes(currentPath)) {
            return true; // 제외된 페이지에서는 세션 체크를 하지 않고 유효하다고 반환
        }
        
        console.log('세션 체크 수행 중...');
        const response = await fetch('/check_session', {
            method: 'GET',
            credentials: 'same-origin',
            cache: 'no-store' // 캐시 방지
        });
        
        if (!response.ok) {
            console.log('세션이 만료되었습니다. 로그인 페이지로 이동합니다.');
            window.location.href = '/login';
            return false;
        }
        
        console.log('세션이 유효합니다.');
        return true;
    } catch (error) {
        console.error('세션 체크 중 오류:', error);
        return false;
    }
}

// 주기적 세션 체크 (5분마다)
let sessionCheckInterval;
function startSessionCheck() {
    // 제외할 경로 목록
    const excludedPaths = ['/login', '/register', '/logout', '/home', '/index', '/club/intro', '/club/history'];
    const currentPath = window.location.pathname;
    
    // 제외 목록에 없을 때만 세션 체크 실행
    if (!excludedPaths.includes(currentPath)) {
        console.log('세션 체크 시작');
        // 즉시 한 번 체크
        checkSession();
        
        // 이전 인터벌 제거
        if (sessionCheckInterval) {
            clearInterval(sessionCheckInterval);
        }
        
        // 새로운 인터벌 설정 (5분)
        sessionCheckInterval = setInterval(checkSession, 5 * 60 * 1000);
    } else {
        console.log('제외된 페이지에서는 세션 체크 건너뜀:', currentPath);
    }
}

// 페이지 로드 시 세션 체크 시작
document.addEventListener('DOMContentLoaded', function() {
    startSessionCheck();
});

// 페이지 로드 시 실행할 초기화 함수
function initPage() {
    // 모달 닫기 버튼 이벤트 리스너 등록
    document.querySelectorAll('.close-modal').forEach(button => {
        const modalId = button.closest('.modal').id;
        button.addEventListener('click', () => closeModal(modalId));
    });
    
    // 모달 외부 클릭 시 닫기
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('click', (event) => {
            if (event.target === modal) {
                closeModal(modal.id);
            }
        });
    });
}

// 페이지 로드 시 초기화 함수 실행
document.addEventListener('DOMContentLoaded', initPage); 