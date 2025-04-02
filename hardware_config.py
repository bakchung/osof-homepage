import subprocess
import re
import uuid
import platform
import wmi
import pythoncom
import hashlib
import hmac
import os
import json
import time

# ===== 암호화 키 설정 =====
SECRET_KEY = b'mysecretkey12345'  # 비밀키

def hash_data(data):
    """문자열을 해시화합니다."""
    return hmac.new(SECRET_KEY, data.encode(), hashlib.sha256).hexdigest()

# ===== 설정 부분 =====
# 관리자 접근이 허용된 하드웨어 정보 목록 (해시된 형태)
ALLOWED_MAC_ADDRESSES = [
    'a1b2c3d4e5f6a7b8c9d0a1b2c3d4e5f6a7b8c9d0a1b2c3d4e5f6a7b8c9d0a1b2',  # 관리자 컴퓨터의 MAC 주소 (해시됨)
]

ALLOWED_CPU_IDS = [
    'b2c3d4e5f6a7b8c9d0a1b2c3d4e5f6a7b8c9d0a1b2c3d4e5f6a7b8c9d0a1b2c3',  # 관리자 컴퓨터의 CPU ID (해시됨)
]

ALLOWED_MOTHERBOARD_SERIALS = [
    'c3d4e5f6a7b8c9d0a1b2c3d4e5f6a7b8c9d0a1b2c3d4e5f6a7b8c9d0a1b2c3d4',  # 관리자 컴퓨터의 메인보드 시리얼 번호 (해시됨)
]

# 캐시 파일 경로
HARDWARE_CACHE_FILE = 'hardware_cache.json'
CACHE_LIFETIME = 86400  # 캐시 유효 기간 (초) - 1일

# 세션 설정
SESSION_LIFETIME_DAYS = 7  # 세션 유지 기간 (일)

# ===== 하드웨어 정보 수집 함수 =====
def get_mac_address():
    """현재 컴퓨터의 MAC 주소를 가져옵니다."""
    return ':'.join(re.findall('..', '%012x' % uuid.getnode()))

def get_hardware_info():
    """시스템의 하드웨어 정보를 가져옵니다. 캐시된 정보가 있으면 사용합니다."""
    # 캐시된 정보 확인
    if os.path.exists(HARDWARE_CACHE_FILE):
        try:
            with open(HARDWARE_CACHE_FILE, 'r') as f:
                cache_data = json.load(f)
                
            # 캐시 유효 기간 확인
            if time.time() - cache_data.get('timestamp', 0) < CACHE_LIFETIME:
                print("캐시된 하드웨어 정보 사용")
                return cache_data.get('hardware_info')
        except Exception as e:
            print(f"캐시 파일 읽기 오류: {str(e)}")
    
    # 캐시가 없거나 만료된 경우 새로 정보 수집
    try:
        print("하드웨어 정보 새로 수집 시작")
        # WMI 사용 전 COM 초기화 (스레드 문제 해결)
        pythoncom.CoInitialize()
        
        c = wmi.WMI()
        
        # CPU 정보
        cpu_info = c.Win32_Processor()[0]
        cpu_id = cpu_info.ProcessorId.strip()
        
        # 메인보드 정보
        board_info = c.Win32_BaseBoard()[0]
        board_serial = board_info.SerialNumber.strip()
        
        # BIOS 정보
        bios_info = c.Win32_BIOS()[0]
        bios_serial = bios_info.SerialNumber.strip()
        
        hardware_info = {
            'mac_address': get_mac_address(),
            'cpu_id': cpu_id,
            'motherboard_serial': board_serial,
            'bios_serial': bios_serial
        }
        
        # 정보 캐싱
        try:
            with open(HARDWARE_CACHE_FILE, 'w') as f:
                json.dump({
                    'timestamp': time.time(),
                    'hardware_info': hardware_info
                }, f)
            print("하드웨어 정보 캐싱 완료")
        except Exception as e:
            print(f"캐시 파일 쓰기 오류: {str(e)}")
        
        # COM 해제
        pythoncom.CoUninitialize()
        
        return hardware_info
    except Exception as e:
        import traceback
        print(f"하드웨어 정보 수집 중 오류 발생: {str(e)}")
        print(traceback.format_exc())
        try:
            # 오류 발생 시에도 COM 해제 시도
            pythoncom.CoUninitialize()
        except:
            pass
            
        # 오류 발생 시 하드웨어 인증이 실패하도록 더미 데이터 반환
        return {
            'mac_address': 'error',
            'cpu_id': 'error',
            'motherboard_serial': 'error',
            'bios_serial': 'error'
        }

def is_admin_hardware():
    """현재 컴퓨터가 관리자 하드웨어인지 확인합니다.
    하드웨어 정보(MAC 주소, CPU ID, 메인보드 시리얼) 중 하나라도 일치하면 관리자로 인정합니다."""
    try:
        print("\n===== 하드웨어 검증 시작 =====")
        hw_info = get_hardware_info()
        if not hw_info:
            print("하드웨어 정보를 가져올 수 없습니다.")
            return False
            
        print(f"가져온 하드웨어 정보: {hw_info}")
            
        # 현재 하드웨어 정보를 해시화하여 저장된 값과 비교
        current_mac = hash_data(hw_info['mac_address'])
        current_cpu = hash_data(hw_info['cpu_id'])
        current_board = hash_data(hw_info['motherboard_serial'])
        
        # 해시값 로그
        print(f"현재 MAC: {hw_info['mac_address']} -> 해시: {current_mac}")
        print(f"현재 CPU: {hw_info['cpu_id']} -> 해시: {current_cpu}")
        print(f"현재 메인보드: {hw_info['motherboard_serial']} -> 해시: {current_board}")
        
        # 저장된 해시값 출력
        print(f"저장된 MAC 해시: {ALLOWED_MAC_ADDRESSES}")
        print(f"저장된 CPU 해시: {ALLOWED_CPU_IDS}")
        print(f"저장된 메인보드 해시: {ALLOWED_MOTHERBOARD_SERIALS}")
        
        # 저장된 해시값과 비교 - 문자열 비교 방식으로 변경
        mac_check = current_mac in ALLOWED_MAC_ADDRESSES
        cpu_check = current_cpu in ALLOWED_CPU_IDS
        board_check = current_board in ALLOWED_MOTHERBOARD_SERIALS
        
        # 하나라도 일치하면 True 반환
        result = mac_check or cpu_check or board_check
        
        # 길이 확인
        print(f"해시 길이 - 현재 MAC: {len(current_mac)}, 저장된 MAC: {len(ALLOWED_MAC_ADDRESSES[0])}")
        print(f"해시 길이 - 현재 CPU: {len(current_cpu)}, 저장된 CPU: {len(ALLOWED_CPU_IDS[0])}")
        print(f"해시 길이 - 현재 MB: {len(current_board)}, 저장된 MB: {len(ALLOWED_MOTHERBOARD_SERIALS[0])}")
        
        print(f"검증 결과: MAC={mac_check}, CPU={cpu_check}, 메인보드={board_check}, 최종={result}")
        print("===== 하드웨어 검증 완료 =====\n")
        
        return result
    except Exception as e:
        print(f"하드웨어 확인 중 오류 발생: {str(e)}")
        return False 