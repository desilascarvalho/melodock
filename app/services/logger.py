from datetime import datetime
from collections import deque

class SystemLogger:
    def __init__(self):
        self.history = deque(maxlen=200)

    def log(self, tag, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = {
            "time": timestamp,
            "tag": tag.upper(),
            "message": message
        }
        self.history.append(entry)
        print(f"[{timestamp}] {tag.upper().ljust(10)} | {message}")

    def get_logs(self):
        return list(self.history)

sys_logger = SystemLogger()