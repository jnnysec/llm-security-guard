import psycopg2
import redis
from backend.config import POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB, POSTGRES_HOST, POSTGRES_PORT, REDIS_HOST, REDIS_PORT

# PostgreSQL
conn = psycopg2.connect(
    dbname=POSTGRES_DB,
    user=POSTGRES_USER,
    password=POSTGRES_PASSWORD,
    host=POSTGRES_HOST,
    port=POSTGRES_PORT
)
cursor = conn.cursor()
# 初始化日志表
cursor.execute("""
CREATE TABLE IF NOT EXISTS request_logs (
    id SERIAL PRIMARY KEY,
    prompt TEXT,
    safe BOOLEAN,
    reason TEXT,
    output_score INT,
    output_issues TEXT,
    created_at TIMESTAMP DEFAULT NOW()
)
""")
conn.commit()

# Redis
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
# 示例黑名单缓存
BLACKLIST_KEY = "prompt_blacklist"
BLACKLIST = ["eval", "exec", "curl", "wget", "os.system"]
for word in BLACKLIST:
    r.sadd(BLACKLIST_KEY, word)
