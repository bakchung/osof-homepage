// 글 작성 페이지 JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // 파일 업로드 처리
    const fileUpload = document.querySelector('input[type="file"].file-upload');
    if (fileUpload) {
        const fileNames = document.querySelector('.attached-files');
        const uploadArea = document.querySelector('.file-upload-wrapper');
        
        // 업로드 영역 클릭 시 파일 선택 창 열기
        if (uploadArea) {
            uploadArea.addEventListener('click', function() {
                fileUpload.click();
            });
        }
        
        // 드래그 앤 드롭 이벤트 처리
        if (uploadArea) {
            uploadArea.addEventListener('dragover', function(e) {
                e.preventDefault();
                uploadArea.classList.add('drag-over');
            });
            
            uploadArea.addEventListener('dragleave', function() {
                uploadArea.classList.remove('drag-over');
            });
            
            uploadArea.addEventListener('drop', function(e) {
                e.preventDefault();
                uploadArea.classList.remove('drag-over');
                fileUpload.files = e.dataTransfer.files;
                updateFileList();
            });
        }
        
        // 파일 선택 시 파일 목록 업데이트
        fileUpload.addEventListener('change', function() {
            updateFileList();
        });
        
        // 파일 목록 업데이트 함수
        function updateFileList() {
            if (fileNames) {
                fileNames.innerHTML = '';
                
                if (fileUpload.files.length > 0) {
                    for (let i = 0; i < fileUpload.files.length; i++) {
                        const fileItem = document.createElement('div');
                        fileItem.className = 'attached-file';
                        
                        const fileName = document.createElement('div');
                        fileName.className = 'file-name';
                        fileName.textContent = fileUpload.files[i].name;
                        
                        fileItem.appendChild(fileName);
                        fileNames.appendChild(fileItem);
                    }
                }
            }
        }
    }
    
    // 폼 제출 전 유효성 검사
    const writeForms = document.querySelectorAll('#postForm, #scheduleForm, #activityForm, #inquiryForm');
    writeForms.forEach(function(form) {
        form.addEventListener('submit', function(e) {
            const titleField = form.querySelector('input[name="title"]');
            const contentField = form.querySelector('textarea[name="content"]');
            
            let valid = true;
            
            // 제목 필드 검사
            if (titleField && !titleField.value.trim()) {
                valid = false;
                titleField.classList.add('invalid');
                showError(titleField, '제목을 입력해주세요.');
            } else if (titleField) {
                titleField.classList.remove('invalid');
                clearError(titleField);
            }
            
            // 내용 필드 검사
            if (contentField && !contentField.value.trim()) {
                valid = false;
                contentField.classList.add('invalid');
                showError(contentField, '내용을 입력해주세요.');
            } else if (contentField) {
                contentField.classList.remove('invalid');
                clearError(contentField);
            }
            
            // 유효성 검사 실패 시 폼 제출 취소
            if (!valid) {
                e.preventDefault();
            }
        });
    });
    
    // 에러 메시지 표시 함수
    function showError(element, message) {
        let errorElement = element.nextElementSibling;
        
        if (!errorElement || !errorElement.classList.contains('error-message')) {
            errorElement = document.createElement('div');
            errorElement.className = 'error-message';
            element.parentNode.insertBefore(errorElement, element.nextSibling);
        }
        
        errorElement.textContent = message;
    }
    
    // 에러 메시지 제거 함수
    function clearError(element) {
        const errorElement = element.nextElementSibling;
        
        if (errorElement && errorElement.classList.contains('error-message')) {
            errorElement.textContent = '';
        }
    }
    
    // 취소 버튼 동작
    const cancelButtons = document.querySelectorAll('.cancel-btn');
    cancelButtons.forEach(function(button) {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            
            // 취소 확인 메시지
            if (confirm('작성 중인 내용이 저장되지 않습니다. 정말 취소하시겠습니까?')) {
                const returnUrl = button.getAttribute('data-return-url');
                
                if (returnUrl) {
                    window.location.href = returnUrl;
                } else {
                    window.history.back();
                }
            }
        });
    });
}); 