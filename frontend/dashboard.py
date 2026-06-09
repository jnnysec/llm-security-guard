import os

import pandas as pd
import requests
import streamlit as st


BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000").rstrip("/")


def api_get(path: str, **params):
    resp = requests.get(f"{BACKEND_URL}{path}", params=params, timeout=8)
    resp.raise_for_status()
    return resp.json()


def api_post(path: str, payload: dict):
    resp = requests.post(f"{BACKEND_URL}{path}", json=payload, timeout=8)
    resp.raise_for_status()
    return resp.json()


st.set_page_config(page_title="LLM 安全护栏", layout="wide")
st.title("LLM 安全护栏 Dashboard")

try:
    health = api_get("/health")
    metrics = api_get("/metrics")

    metric_cols = st.columns(5)
    metric_cols[0].metric("总请求", metrics["total_requests"])
    metric_cols[1].metric("拦截数", metrics["blocked_requests"])
    metric_cols[2].metric("拦截率", f'{metrics["intercept_rate"]}%')
    metric_cols[3].metric("P95 响应", f'{metrics["p95_latency_ms"]} ms')
    metric_cols[4].metric("存储", health["storage"])

    tab_overview, tab_test, tab_logs, tab_rules = st.tabs(["红队评测", "在线检测", "请求日志", "规则管理"])

    with tab_overview:
        st.subheader("模型安全评分")
        redteam = api_get("/redteam/summary")
        summary_df = pd.DataFrame(redteam["summary"])
        result_df = pd.DataFrame(redteam["results"])
        st.dataframe(summary_df, use_container_width=True, hide_index=True)

        st.subheader("红队样本结果")
        categories = ["全部"] + sorted(result_df["category"].unique().tolist())
        category = st.selectbox("攻击类别", categories)
        filtered = result_df if category == "全部" else result_df[result_df["category"] == category]
        st.dataframe(filtered, use_container_width=True, hide_index=True)

    with tab_test:
        left, right = st.columns(2)
        with left:
            st.subheader("输入过滤器")
            prompt = st.text_area("Prompt", height=160, key="prompt_filter")
            if st.button("检查输入", use_container_width=True):
                result = api_post("/filter", {"prompt": prompt})
                st.json(result)

        with right:
            st.subheader("输出审核器")
            output_text = st.text_area("模型输出", height=160, key="output_audit")
            if st.button("审核输出", use_container_width=True):
                result = api_post("/audit", {"prompt": output_text})
                st.json(result)

    with tab_logs:
        st.subheader("最近 100 条请求")
        query = st.text_input("查询 Prompt / 原因")
        logs = api_get("/logs", limit=100, q=query)["logs"]
        logs_df = pd.DataFrame(logs)
        st.dataframe(logs_df, use_container_width=True, hide_index=True)
        export_url = f"{BACKEND_URL}/logs/export?limit=100&q={query}"
        st.link_button("导出 CSV", export_url, use_container_width=False)

    with tab_rules:
        st.subheader("黑名单")
        blacklist = api_get("/blacklist")["blacklist"]
        st.write(", ".join(blacklist))

        new_word = st.text_input("新增黑名单关键字")
        if st.button("添加关键字"):
            st.json(api_post("/blacklist", {"word": new_word}))

        st.subheader("红队模板")
        templates = api_get("/templates")["templates"]
        st.dataframe(pd.DataFrame(templates), use_container_width=True, hide_index=True)

        new_template = st.text_area("新增红队模板", height=100)
        new_category = st.text_input("模板类别", value="Custom")
        if st.button("添加模板"):
            st.json(api_post("/template", {"prompt": new_template, "category": new_category}))

except requests.RequestException as exc:
    st.error(f"无法连接后端：{exc}")
    st.info(f"当前 BACKEND_URL={BACKEND_URL}")
