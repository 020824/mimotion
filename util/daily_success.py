import hashlib
import json
from pathlib import Path
import threading


class DailySuccess:
    def __init__(self, date, path='daily_success.json'):
        self.path = Path(path)
        self._lock = threading.Lock()
        self._account_locks = {}
        self.data = {'date': date, 'completed': False, 'accounts': {}}
        if self.path.exists():
            saved = json.loads(self.path.read_text(encoding='utf-8'))
            if (
                not isinstance(saved, dict)
                or not isinstance(saved.get('accounts'), dict)
                or not isinstance(saved.get('completed'), bool)
                or not isinstance(saved.get('date'), str)
                or any(not isinstance(step, int) or step <= 8000 for step in saved['accounts'].values())
            ):
                raise ValueError('每日成功记录格式不正确，停止执行以避免重复修改')
            if saved['date'] == date:
                self.data = saved

    @property
    def completed(self):
        return self.data['completed']

    def _key(self, user):
        user = str(user)
        if not user.startswith('+86') and '@' not in user:
            user = '+86' + user
        return hashlib.sha256(user.encode('utf-8')).hexdigest()

    def account_lock(self, user):
        with self._lock:
            return self._account_locks.setdefault(self._key(user), threading.Lock())

    def get_step(self, user):
        with self._lock:
            return self.data['accounts'].get(self._key(user))

    def record(self, user, step):
        step = int(step)
        if step <= 8000:
            raise ValueError('成功记录的步数必须超过8000')
        with self._lock:
            self.data['accounts'][self._key(user)] = step
            self._save()

    def mark_completed(self):
        with self._lock:
            self.data['completed'] = True
            self._save()

    def _save(self):
        temporary = self.path.with_suffix(self.path.suffix + '.tmp')
        temporary.write_text(json.dumps(self.data, sort_keys=True, indent=2) + '\n', encoding='utf-8')
        temporary.replace(self.path)
