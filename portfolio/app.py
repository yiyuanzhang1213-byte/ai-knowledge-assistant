"""Portfolio app. Inspired by streamlit/llm-examples file Q&A; new implementation."""
import hashlib
import json
import os
from pathlib import Path
import sys

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from portfolio.core import Retriever, answer, split_document
from portfolio.provider import generate

st.set_page_config(page_title="健身门店知识助手", page_icon="📖", layout="wide")
st.title("健身门店知识助手")
st.caption("查询预约、会员卡与账单规则，查看每条回答的原文依据。")

with st.sidebar:
    st.header("知识库")
    files = st.file_uploader("上传公开规则文档", type=["txt", "md"], accept_multiple_files=True)
    st.caption("仅使用公开资料，请勿上传个人信息。未上传时使用虚拟门店演示规则。")
    mode = st.radio("回答方式", ["原文检索", "AI 整理（需服务配置）"])
    threshold = st.slider("依据匹配要求", .1, .8, .22, .01,
                          help="词项覆盖率阈值，仅用于筛选依据，不代表回答正确概率。")
    st.caption("AI 整理读取服务端 LLM_BASE_URL、LLM_MODEL、LLM_API_KEY。")
    if st.button("清空会话"):
        st.session_state.clear()
        st.rerun()

documents = []
if files:
    if len(files) > 10:
        st.error("每次最多上传 10 个文件。")
        st.stop()
    for file in files:
        if file.size > 600_000:
            st.error(f"{file.name} 超过 600 KB，请缩小文档。")
            st.stop()
        try:
            text = file.getvalue().decode("utf-8-sig")
            documents.append((file.name, text))
        except UnicodeDecodeError:
            st.error(f"{file.name} 请另存为 UTF-8 格式。")
            st.stop()
else:
    documents = [("演示门店规则.md", (Path(__file__).parent / "data/fitness_faq.md").read_text(encoding="utf-8"))]
try:
    chunks = [chunk for source, text in documents for chunk in split_document(source, text)]
except ValueError as exc:
    st.error(str(exc))
    st.stop()
fingerprint = hashlib.sha256(repr(documents).encode()).hexdigest()
if st.session_state.get("fingerprint") != fingerprint:
    st.session_state.update(fingerprint=fingerprint, history=[], feedback={})
retriever = Retriever(chunks)
st.write(f"已载入 {len(documents)} 份文档 · {len(chunks)} 个知识片段")
st.info("试问：课程开始后还能取消预约吗？或：可以查询其他会员的账单吗？")
question = st.chat_input("输入你的问题")
if question:
    if len(question) > 1000:
        st.error("问题请控制在 1000 字符以内。")
    else:
        result = answer(question, retriever, threshold)
        result["mode"] = "原文检索"
        if mode.startswith("AI") and result["status"] == "evidence":
            try:
                if not all(os.environ.get(k) for k in ("LLM_BASE_URL", "LLM_MODEL", "LLM_API_KEY")):
                    raise ValueError("尚未配置 AI 服务，已展示原文依据。")
                result.update(generate(question, result["sources"]))
                result["mode"] = "AI 整理"
            except (ValueError, RuntimeError) as exc:
                result["notice"] = str(exc)
        st.session_state.history.append({"question": question, **result})

for i, item in enumerate(st.session_state.history):
    with st.chat_message("user"):
        st.write(item["question"])
    with st.chat_message("assistant"):
        if item.get("notice"):
            st.warning(item["notice"])
        st.write(item["answer"])
        st.caption(f"{item['mode']} · 检索 {item['latency_ms']:.2f} ms")
        if item.get("usage"):
            st.caption(f"模型用量（服务返回）：{item['usage']}")
        with st.expander("查看原文依据", expanded=False):
            for source in item["sources"]:
                st.markdown(f"**[{source['citation']}] {source['source']} / {source['heading']}**")
                st.write(source["text"])
        feedback = st.radio("这条回答是否有帮助？", ["未评价", "有帮助", "需改进"], horizontal=True, key=f"feedback_{i}")
        st.session_state.feedback[str(i)] = feedback
if st.session_state.history:
    export = {"records": st.session_state.history, "feedback": st.session_state.feedback}
    st.download_button("导出本次问答与反馈", json.dumps(export, ensure_ascii=False, indent=2),
                       "knowledge-feedback.json", "application/json")
