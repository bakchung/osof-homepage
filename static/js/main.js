// 문서가 로드되면 실행
document.addEventListener('DOMContentLoaded', function() {
    // 모바일 메뉴 토글 기능
    const mobileMenuToggle = document.querySelector('.mobile-menu-toggle');
    if (mobileMenuToggle) {
        mobileMenuToggle.addEventListener('click', function() {
            const navMenu = document.querySelector('.nav-menu');
            navMenu.classList.toggle('active');
        });
    }

    // 플래시 메시지 자동 닫기
    const flashMessages = document.querySelectorAll('.flash-message');
    flashMessages.forEach(function(message) {
        setTimeout(function() {
            message.style.opacity = '0';
            setTimeout(function() {
                message.style.display = 'none';
            }, 500);
        }, 3000);
    });

    // 파일 업로드 필드 사용자 정의
    const fileInputs = document.querySelectorAll('input[type="file"]');
    fileInputs.forEach(function(input) {
        const fileLabel = input.nextElementSibling;
        if (fileLabel && fileLabel.classList.contains('file-label')) {
            input.addEventListener('change', function() {
                let fileName = '';
                if (this.files && this.files.length > 0) {
                    fileName = this.files.length > 1 
                        ? this.files.length + '개 파일 선택됨' 
                        : this.files[0].name;
                }
                fileLabel.textContent = fileName || '파일 선택';
            });
        }
    });

    // 텍스트 에디터 초기화 (텍스트 영역에 class='editor'가 있는 경우)
    const editors = document.querySelectorAll('textarea.editor');
    if (editors.length > 0) {
        editors.forEach(function(editor) {
            // 여기에 WYSIWYG 에디터 초기화 코드를 추가할 수 있습니다.
            // 예: ClassicEditor.create(editor) 등
        });
    }

    // 테이블 행 클릭시 링크 이동
    const clickableRows = document.querySelectorAll('tr[data-href]');
    clickableRows.forEach(function(row) {
        row.addEventListener('click', function() {
            window.location.href = this.getAttribute('data-href');
        });
    });

    // 이미지 미리보기 기능
    const imageInputs = document.querySelectorAll('input[type="file"][accept*="image"]');
    imageInputs.forEach(function(input) {
        const previewContainer = document.querySelector(input.getAttribute('data-preview'));
        if (previewContainer) {
            input.addEventListener('change', function() {
                previewContainer.innerHTML = '';
                if (this.files && this.files.length > 0) {
                    for (let i = 0; i < this.files.length; i++) {
                        const file = this.files[i];
                        if (file.type.startsWith('image/')) {
                            const reader = new FileReader();
                            reader.onload = function(e) {
                                const img = document.createElement('img');
                                img.src = e.target.result;
                                img.className = 'preview-image';
                                previewContainer.appendChild(img);
                            };
                            reader.readAsDataURL(file);
                        }
                    }
                }
            });
        }
    });

    // 모달 창 기능
    const modalTriggers = document.querySelectorAll('[data-modal]');
    modalTriggers.forEach(function(trigger) {
        trigger.addEventListener('click', function(e) {
            e.preventDefault();
            const modalId = this.getAttribute('data-modal');
            const modal = document.getElementById(modalId);
            if (modal) {
                modal.style.display = 'flex';
                // 모달 닫기 버튼
                const closeButtons = modal.querySelectorAll('.modal-close');
                closeButtons.forEach(function(button) {
                    button.addEventListener('click', function() {
                        modal.style.display = 'none';
                    });
                });
                // 모달 바깥 클릭시 닫기
                modal.addEventListener('click', function(e) {
                    if (e.target === modal) {
                        modal.style.display = 'none';
                    }
                });
            }
        });
    });

    // 폼 유효성 검사
    const forms = document.querySelectorAll('form[data-validate]');
    forms.forEach(function(form) {
        form.addEventListener('submit', function(e) {
            const requiredFields = form.querySelectorAll('[required]');
            let isValid = true;
            
            requiredFields.forEach(function(field) {
                if (!field.value.trim()) {
                    isValid = false;
                    field.classList.add('invalid');
                    
                    const errorMessage = field.getAttribute('data-error') || '이 필드는 필수입니다.';
                    let errorElement = field.nextElementSibling;
                    
                    if (!errorElement || !errorElement.classList.contains('error-message')) {
                        errorElement = document.createElement('div');
                        errorElement.className = 'error-message';
                        field.parentNode.insertBefore(errorElement, field.nextSibling);
                    }
                    
                    errorElement.textContent = errorMessage;
                } else {
                    field.classList.remove('invalid');
                    const errorElement = field.nextElementSibling;
                    if (errorElement && errorElement.classList.contains('error-message')) {
                        errorElement.textContent = '';
                    }
                }
            });
            
            if (!isValid) {
                e.preventDefault();
            }
        });
    });
}); 