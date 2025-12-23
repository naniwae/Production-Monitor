import os
import socket
import getpass

def get_info():
    user = getpass.getuser()
    hostname = socket.gethostname()

    # -------- IP アドレス取得--------
    ip = "0.0.0.0"

    try:
        # 一番安定：外部接続不要
        ip = socket.gethostbyname(hostname)
        # Debian/Ubuntu/RaspberryPi は 127.0.1.1 を返す場合がある
        if ip.startswith("127."):
            raise ValueError("loopback だったため再取得")
    except Exception:
        try:
            # 代替案：擬似接続（外に出ない）
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("10.255.255.255", 1))
            ip = s.getsockname()[0]
        except Exception:
            ip = "0.0.0.0"  # 最終フォールバック
        finally:
            try:
                s.close()
            except:
                pass

    return {"user": user, "hostname": hostname, "deviceip": ip}