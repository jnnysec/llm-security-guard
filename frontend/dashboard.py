import streamlit as st
import requests
import pandas as pd

st.title("LLM 安全护栏 Dashboard")

# 红队测试
st.header("红队自动化测试结果")
models = ["Qwen", "Llama", "GLM"]
resp = requests.get("http://backend:8000/redteam")
df = pd.DataFrame(resp.json())
st.dataframe(df)

# 输入过滤器测试
st.header("输入过滤器测试")
prompt = st.text_area("输入Prompt")
if st.button("检查"):
    r = requests.post("http://backend:8000/filter", json={"prompt": prompt})
    st.write(r.json())

# 输出审核器测试
st.header("输出审核器测试")
out_text = st.text_area("模型输出")
if st.button("审核"):
    r = requests.post("http://backend:8000/audit", json={"prompt": out_text})
    st.write(r.json())
