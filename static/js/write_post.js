document.addEventListener('DOMContentLoaded', function() {
    // 파일 업로드 관련 스크립트
    const fileInput = document.getElementById('files');
    const fileList = document.getElementById('file-list');
    const fileUploadWrapper = document.querySelector('.file-upload-wrapper');
    
    if (fileInput && fileList) {
        // 파일 선택 이벤트
        fileInput.addEventListener('change', function() {
            updateFileList();
        });
        
        // 드래그 앤 드롭 이벤트
        if (fileUploadWrapper) {
            fileUploadWrapper.addEventListener('dragover', function(e) {
                e.preventDefault();
                this.classList.add('dragover');
            });
            
            fileUploadWrapper.addEventListener('dragleave', function() {
                this.classList.remove('dragover');
            });
            
            fileUploadWrapper.addEventListener('drop', function(e) {
                e.preventDefault();
                this.classList.remove('dragover');
                fileInput.files = e.dataTransfer.files;
                updateFileList();
            });
        }
        
        // 파일 목록 업데이트 함수
        function updateFileList() {
            fileList.innerHTML = '';
            
            if (fileInput.files.length > 0) {
                for (let i = 0; i < fileInput.files.length; i++) {
                    const file = fileInput.files[i];
                    const fileSize = formatFileSize(file.size);
                    
                    const fileItem = document.createElement('div');
                    fileItem.className = 'file-item';
                    
                    const fileName = document.createElement('div');
                    fileName.className = 'file-name';
                    fileName.textContent = `${file.name} (${fileSize})`;
                    
                    const removeButton = document.createElement('button');
                    removeButton.className = 'remove-file';
                    removeButton.innerHTML = '<i class="fas fa-times"></i>';
                    removeButton.setAttribute('data-index', i);
                    
                    fileItem.appendChild(fileName);
                    fileItem.appendChild(removeButton);
                    fileList.appendChild(fileItem);
                }
                
                // 파일 제거 버튼 이벤트 추가
                const removeButtons = document.querySelectorAll('.remove-file');
                removeButtons.forEach(function(button) {
                    button.addEventListener('click', function() {
                        const dt = new DataTransfer();
                        const index = parseInt(this.getAttribute('data-index'));
                        
                        for (let i = 0; i < fileInput.files.length; i++) {
                            if (i !== index) {
                                dt.items.add(fileInput.files[i]);
                            }
                        }
                        
                        fileInput.files = dt.files;
                        updateFileList();
                    });
                });
            }
        }
        
        // 파일 크기 포맷 함수
        function formatFileSize(bytes) {
            if (bytes === 0) return '0 Bytes';
            const k = 1024;
            const sizes = ['Bytes', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        }
    }
    
    // 폼 유효성 검사
    const writeForm = document.querySelector('.write-form');
    if (writeForm) {
        writeForm.addEventListener('submit', function(e) {
            const title = document.getElementById('title');
            const content = document.getElementById('content');
            const category = document.getElementById('category');
            
            let isValid = true;
            
            // 제목 검사
            if (!title.value.trim()) {
                isValid = false;
                showError(title, '제목을 입력해주세요.');
            } else {
                clearError(title);
            }
            
            // 내용 검사
            if (!content.value.trim()) {
                isValid = false;
                showError(content, '내용을 입력해주세요.');
            } else {
                clearError(content);
            }
            
            // 카테고리 검사
            if (category && category.value === '') {
                isValid = false;
                showError(category, '카테고리를 선택해주세요.');
            } else if (category) {
                clearError(category);
            }
            
            // 폼 제출 방지
            if (!isValid) {
                e.preventDefault();
            }
        });
    }
    
    // 에러 메시지 표시 함수
    function showError(element, message) {
        let errorElement = element.nextElementSibling;
        
        if (!errorElement || !errorElement.classList.contains('error-message')) {
            errorElement = document.createElement('div');
            errorElement.className = 'error-message';
            errorElement.style.color = '#e74c3c';
            errorElement.style.fontSize = '0.9rem';
            errorElement.style.marginTop = '5px';
            
            element.parentNode.insertBefore(errorElement, element.nextSibling);
        }
        
        errorElement.textContent = message;
        element.style.borderColor = '#e74c3c';
    }
    
    // 에러 메시지 제거 함수
    function clearError(element) {
        const errorElement = element.nextElementSibling;
        
        if (errorElement && errorElement.classList.contains('error-message')) {
            errorElement.textContent = '';
        }
        
        element.style.borderColor = '';
    }
    
    // 취소 버튼 이벤트
    const cancelBtn = document.querySelector('.cancel-btn');
    if (cancelBtn) {
        cancelBtn.addEventListener('click', function(e) {
            const form = document.querySelector('.write-form');
            
            if (form && (title.value.trim() || content.value.trim() || (fileInput && fileInput.files.length > 0))) {
                if (!confirm('작성 중인 내용이 저장되지 않습니다. 정말 취소하시겠습니까?')) {
                    e.preventDefault();
                }
            }
        });
    }
}); 