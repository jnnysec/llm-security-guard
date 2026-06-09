from __future__ import annotations

import csv
import io
import time
from dataclasses import asdict, dataclass
from threading import Lock
from typing import Any, Dict, List, Optional, Sequence

from backend.config import settings


DEFAULT_BLACKLIST = {
    "eval",
    "exec",
    "curl",
    "wget",
    "os.system",
    "subprocess",
    "rm -rf",
    "ignore previous instructions",
    "system prompt",
    "developer message",
    "泄露密钥",
    "忽略之前",
    "绕过限制",
}

BLACKLIST_KEY = "prompt_blacklist"


@dataclass
class RequestLog:
    id: int
    kind: str
    prompt: str
    safe: bool
    reason: str
    risk_types: str = ""
    output_score: Optional[int] = None
    output_issues: str = ""
    safe_text: str = ""
    latency_ms: float = 0.0
    created_at: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        row = asdict(self)
        row["created_at"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.created_at))
        return row


class AuditStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._logs: List[RequestLog] = []
        self._next_id = 1
        self._conn = None
        self._cursor = None
        self._redis = None
        self._external_ready = False

        if settings.use_external_services:
            self._connect_external_services()

    def _connect_external_services(self) -> None:
        try:
            import psycopg2
            import redis

            self._conn = psycopg2.connect(
                dbname=settings.postgres_db,
                user=settings.postgres_user,
                password=settings.postgres_password,
                host=settings.postgres_host,
                port=settings.postgres_port,
                connect_timeout=3,
            )
            self._cursor = self._conn.cursor()
            self._init_postgres()

            self._redis = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
            )
            self._redis.ping()
            self._seed_blacklist()
            self._external_ready = True
        except Exception:
            self._conn = None
            self._cursor = None
            self._redis = None
            self._external_ready = False

    def _init_postgres(self) -> None:
        assert self._cursor is not None
        assert self._conn is not None
        self._cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS request_logs (
                id SERIAL PRIMARY KEY,
                kind TEXT DEFAULT 'filter',
                prompt TEXT,
                safe BOOLEAN,
                reason TEXT,
                risk_types TEXT,
                output_score INT,
                output_issues TEXT,
                safe_text TEXT,
                latency_ms DOUBLE PRECISION,
                created_at TIMESTAMP DEFAULT NOW()
            )
            """
        )
        for column_sql in [
            "ALTER TABLE request_logs ADD COLUMN IF NOT EXISTS kind TEXT DEFAULT 'filter'",
            "ALTER TABLE request_logs ADD COLUMN IF NOT EXISTS risk_types TEXT",
            "ALTER TABLE request_logs ADD COLUMN IF NOT EXISTS safe_text TEXT",
            "ALTER TABLE request_logs ADD COLUMN IF NOT EXISTS latency_ms DOUBLE PRECISION",
        ]:
            self._cursor.execute(column_sql)
        self._conn.commit()

    def _seed_blacklist(self) -> None:
        if self._redis is None:
            return
        for word in DEFAULT_BLACKLIST:
            self._redis.sadd(BLACKLIST_KEY, word)

    def health(self) -> Dict[str, Any]:
        return {
            "storage": "postgres" if self._external_ready else "memory",
            "redis": bool(self._redis),
        }

    def blacklist(self) -> List[str]:
        if self._redis is not None:
            try:
                values = self._redis.smembers(BLACKLIST_KEY)
                return sorted(values or DEFAULT_BLACKLIST)
            except Exception:
                pass
        return sorted(DEFAULT_BLACKLIST)

    def add_blacklist_word(self, word: str) -> List[str]:
        word = word.strip()
        if not word:
            return self.blacklist()
        DEFAULT_BLACKLIST.add(word)
        if self._redis is not None:
            try:
                self._redis.sadd(BLACKLIST_KEY, word)
            except Exception:
                pass
        return self.blacklist()

    def log_request(
        self,
        *,
        kind: str,
        prompt: str,
        safe: bool,
        reason: str,
        risk_types: Sequence[str] = (),
        output_score: Optional[int] = None,
        output_issues: Sequence[str] = (),
        safe_text: str = "",
        latency_ms: float = 0.0,
    ) -> RequestLog:
        risk_value = ",".join(risk_types)
        issue_value = ",".join(output_issues)

        if self._external_ready and self._cursor is not None and self._conn is not None:
            try:
                self._cursor.execute(
                    """
                    INSERT INTO request_logs
                        (kind, prompt, safe, reason, risk_types, output_score,
                         output_issues, safe_text, latency_ms)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    RETURNING id
                    """,
                    (
                        kind,
                        prompt,
                        safe,
                        reason,
                        risk_value,
                        output_score,
                        issue_value,
                        safe_text,
                        latency_ms,
                    ),
                )
                log_id = self._cursor.fetchone()[0]
                self._conn.commit()
                return RequestLog(
                    id=log_id,
                    kind=kind,
                    prompt=prompt,
                    safe=safe,
                    reason=reason,
                    risk_types=risk_value,
                    output_score=output_score,
                    output_issues=issue_value,
                    safe_text=safe_text,
                    latency_ms=latency_ms,
                    created_at=time.time(),
                )
            except Exception:
                if self._conn is not None:
                    self._conn.rollback()

        with self._lock:
            log = RequestLog(
                id=self._next_id,
                kind=kind,
                prompt=prompt,
                safe=safe,
                reason=reason,
                risk_types=risk_value,
                output_score=output_score,
                output_issues=issue_value,
                safe_text=safe_text,
                latency_ms=latency_ms,
                created_at=time.time(),
            )
            self._next_id += 1
            self._logs.append(log)
            self._logs = self._logs[-1000:]
            return log

    def recent_logs(self, limit: int = 100, query: str = "") -> List[Dict[str, Any]]:
        limit = max(1, min(limit, 500))
        query = query.strip().lower()

        if self._external_ready and self._cursor is not None:
            try:
                if query:
                    self._cursor.execute(
                        """
                        SELECT id, kind, prompt, safe, reason, COALESCE(risk_types, ''),
                               output_score, COALESCE(output_issues, ''),
                               COALESCE(safe_text, ''), COALESCE(latency_ms, 0),
                               created_at
                        FROM request_logs
                        WHERE LOWER(prompt) LIKE %s OR LOWER(reason) LIKE %s
                        ORDER BY created_at DESC
                        LIMIT %s
                        """,
                        (f"%{query}%", f"%{query}%", limit),
                    )
                else:
                    self._cursor.execute(
                        """
                        SELECT id, kind, prompt, safe, reason, COALESCE(risk_types, ''),
                               output_score, COALESCE(output_issues, ''),
                               COALESCE(safe_text, ''), COALESCE(latency_ms, 0),
                               created_at
                        FROM request_logs
                        ORDER BY created_at DESC
                        LIMIT %s
                        """,
                        (limit,),
                    )
                rows = []
                for row in self._cursor.fetchall():
                    rows.append(
                        {
                            "id": row[0],
                            "kind": row[1],
                            "prompt": row[2],
                            "safe": row[3],
                            "reason": row[4],
                            "risk_types": row[5],
                            "output_score": row[6],
                            "output_issues": row[7],
                            "safe_text": row[8],
                            "latency_ms": row[9],
                            "created_at": str(row[10]),
                        }
                    )
                return rows
            except Exception:
                pass

        with self._lock:
            rows = list(reversed(self._logs))
        if query:
            rows = [
                item
                for item in rows
                if query in item.prompt.lower() or query in item.reason.lower()
            ]
        return [item.to_dict() for item in rows[:limit]]

    def metrics(self) -> Dict[str, Any]:
        rows = self.recent_logs(limit=500)
        filter_rows = [row for row in rows if row["kind"] == "filter"]
        total = len(filter_rows)
        blocked = sum(1 for row in filter_rows if not row["safe"])
        latencies = sorted(float(row.get("latency_ms") or 0) for row in rows)
        p95_index = int((len(latencies) - 1) * 0.95) if latencies else 0

        issues: Dict[str, int] = {}
        for row in rows:
            for field in ("risk_types", "output_issues"):
                value = row.get(field) or ""
                for item in value.split(","):
                    item = item.strip()
                    if item:
                        issues[item] = issues.get(item, 0) + 1

        return {
            "total_requests": total,
            "blocked_requests": blocked,
            "intercept_rate": round(blocked / total * 100, 2) if total else 0.0,
            "avg_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else 0.0,
            "p95_latency_ms": round(latencies[p95_index], 2) if latencies else 0.0,
            "top_issues": issues,
            "storage": self.health()["storage"],
        }

    def export_csv(self, limit: int = 100, query: str = "") -> str:
        rows = self.recent_logs(limit=limit, query=query)
        output = io.StringIO()
        fields = [
            "id",
            "created_at",
            "kind",
            "prompt",
            "safe",
            "reason",
            "risk_types",
            "output_score",
            "output_issues",
            "latency_ms",
        ]
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})
        return output.getvalue()


store = AuditStore()
