import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="LLM 安全护栏", layout="wide")
st.title("LLM 安全护栏 Dashboard")

st.header("红队自动化测试结果")
resp = requests.get("http://backend:8000/redteam")
df = pd.DataFrame(resp.json())
st.dataframe(df)

st.header("输入过滤器测试")
prompt = st.text_area("输入Prompt")
if st.button("检查输入"):
    r = requests.post("http://backend:8000/filter", json={"prompt": prompt})
    st.write(r.json())

st.header("输出审核器测试")
out_text = st.text_area("模型输出")
if st.button("审核输出"):
    r = requests.post("http://backend:8000/audit", json={"prompt": out_text})
    st.write(r.json())

st.header("红队模板管理")
new_template = st.text_input("新增模板")
if st.button("添加模板"):
    r = requests.post("http://backend:8000/template", json={"prompt": new_template})
    st.write(r.json())
st.write("现有模板")
r = requests.get("http://backend:8000/templates")
st.write(r.json()["templates"])
