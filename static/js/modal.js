// 모달 관련 JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // 모달 열기 함수
    window.openModal = function(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.style.display = 'flex';
            document.body.style.overflow = 'hidden'; // 배경 스크롤 방지
            
            // 모달이 열릴 때 포커스 설정
            const firstInput = modal.querySelector('input, button, textarea, select');
            if (firstInput) {
                firstInput.focus();
            }
            
            // ESC 키로 모달 닫기
            document.addEventListener('keydown', function(e) {
                if (e.key === 'Escape') {
                    closeModal(modalId);
                }
            });
        }
    };
    
    // 모달 닫기 함수
    window.closeModal = function(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.style.display = 'none';
            document.body.style.overflow = ''; // 배경 스크롤 다시 허용
        }
    };
    
    // 모달 열기 버튼 이벤트 핸들러
    const modalTriggers = document.querySelectorAll('[data-modal]');
    modalTriggers.forEach(function(trigger) {
        trigger.addEventListener('click', function(e) {
            e.preventDefault();
            const modalId = this.getAttribute('data-modal');
            openModal(modalId);
        });
    });
    
    // 모달 닫기 버튼 이벤트 핸들러
    const modalCloseButtons = document.querySelectorAll('.modal-close, [data-dismiss="modal"]');
    modalCloseButtons.forEach(function(button) {
        button.addEventListener('click', function() {
            const modal = this.closest('.modal');
            if (modal) {
                closeModal(modal.id);
            }
        });
    });
    
    // 모달 바깥 클릭 시 닫기
    const modals = document.querySelectorAll('.modal');
    modals.forEach(function(modal) {
        modal.addEventListener('click', function(e) {
            if (e.target === this) {
                closeModal(this.id);
            }
        });
    });
    
    // 모달 내에서 폼 제출 처리
    const modalForms = document.querySelectorAll('.modal form');
    modalForms.forEach(function(form) {
        form.addEventListener('submit', function(e) {
            // 폼 유효성 검사
            const requiredFields = form.querySelectorAll('[required]');
            let isValid = true;
            
            requiredFields.forEach(function(field) {
                if (!field.value.trim()) {
                    isValid = false;
                    field.classList.add('invalid');
                    
                    // 에러 메시지 표시
                    let errorElement = field.nextElementSibling;
                    if (!errorElement || !errorElement.classList.contains('error-message')) {
                        errorElement = document.createElement('div');
                        errorElement.className = 'error-message';
                        field.parentNode.insertBefore(errorElement, field.nextSibling);
                    }
                    
                    errorElement.textContent = field.getAttribute('data-error') || '이 필드는 필수입니다.';
                } else {
                    field.classList.remove('invalid');
                    
                    // 에러 메시지 제거
                    const errorElement = field.nextElementSibling;
                    if (errorElement && errorElement.classList.contains('error-message')) {
                        errorElement.textContent = '';
                    }
                }
            });
            
            // 유효성 검사 실패 시 제출 방지
            if (!isValid) {
                e.preventDefault();
            }
        });
    });
    
    // 동적으로 모달 생성 함수
    window.createModal = function(options) {
        // 기본 옵션
        const defaultOptions = {
            id: 'dynamicModal',
            title: '알림',
            content: '',
            buttons: [
                { text: '확인', class: 'btn btn-primary', click: function() { closeModal(options.id || 'dynamicModal'); } }
            ]
        };
        
        // 옵션 병합
        const modalOptions = Object.assign({}, defaultOptions, options);
        
        // 기존 모달이 있으면 제거
        const existingModal = document.getElementById(modalOptions.id);
        if (existingModal) {
            existingModal.remove();
        }
        
        // 모달 요소 생성
        const modal = document.createElement('div');
        modal.id = modalOptions.id;
        modal.className = 'modal';
        
        // 모달 내용 생성
        const modalContent = document.createElement('div');
        modalContent.className = 'modal-content';
        
        // 모달 헤더 생성
        const modalHeader = document.createElement('div');
        modalHeader.className = 'modal-header';
        
        const modalTitle = document.createElement('h3');
        modalTitle.className = 'modal-title';
        modalTitle.textContent = modalOptions.title;
        
        const closeButton = document.createElement('button');
        closeButton.className = 'modal-close';
        closeButton.innerHTML = '&times;';
        closeButton.addEventListener('click', function() {
            closeModal(modalOptions.id);
        });
        
        modalHeader.appendChild(modalTitle);
        modalHeader.appendChild(closeButton);
        
        // 모달 바디 생성
        const modalBody = document.createElement('div');
        modalBody.className = 'modal-body';
        
        if (typeof modalOptions.content === 'string') {
            modalBody.innerHTML = modalOptions.content;
        } else if (modalOptions.content instanceof HTMLElement) {
            modalBody.appendChild(modalOptions.content);
        }
        
        // 모달 푸터 생성
        const modalFooter = document.createElement('div');
        modalFooter.className = 'modal-footer';
        
        // 버튼 추가
        if (modalOptions.buttons && modalOptions.buttons.length > 0) {
            modalOptions.buttons.forEach(function(buttonOptions) {
                const button = document.createElement('button');
                button.className = buttonOptions.class || 'btn';
                button.textContent = buttonOptions.text;
                
                if (typeof buttonOptions.click === 'function') {
                    button.addEventListener('click', buttonOptions.click);
                }
                
                modalFooter.appendChild(button);
            });
        }
        
        // 모달 조립
        modalContent.appendChild(modalHeader);
        modalContent.appendChild(modalBody);
        modalContent.appendChild(modalFooter);
        modal.appendChild(modalContent);
        
        // 페이지에 모달 추가
        document.body.appendChild(modal);
        
        // 모달 열기
        openModal(modalOptions.id);
        
        return modal;
    };
    
    // 확인 모달 함수
    window.confirmModal = function(message, confirmCallback, cancelCallback) {
        return createModal({
            id: 'confirmModal',
            title: '확인',
            content: `<p>${message}</p>`,
            buttons: [
                {
                    text: '확인',
                    class: 'btn btn-primary',
                    click: function() {
                        closeModal('confirmModal');
                        if (typeof confirmCallback === 'function') {
                            confirmCallback();
                        }
                    }
                },
                {
                    text: '취소',
                    class: 'btn btn-secondary',
                    click: function() {
                        closeModal('confirmModal');
                        if (typeof cancelCallback === 'function') {
                            cancelCallback();
                        }
                    }
                }
            ]
        });
    };
    
    // 알림 모달 함수
    window.alertModal = function(message, callback) {
        return createModal({
            id: 'alertModal',
            title: '알림',
            content: `<p>${message}</p>`,
            buttons: [
                {
                    text: '확인',
                    class: 'btn btn-primary',
                    click: function() {
                        closeModal('alertModal');
                        if (typeof callback === 'function') {
                            callback();
                        }
                    }
                }
            ]
        });
    };
}); 