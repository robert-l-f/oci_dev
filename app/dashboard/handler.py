import os

import requests
import streamlit as st

st.title("OCI RAG Demo")
st.caption("Ask questions against content ingested into MySQL HeatWave.")

api_url = st.text_input("API function URL", value=os.getenv("RAG_API_URL", ""))
question = st.text_area("Question", value="What does this knowledge base say?")
top_k = st.slider("Top K", min_value=1, max_value=10, value=4)

if st.button("Ask"):
    if not api_url:
        st.error("Provide the API function URL first.")
    else:
        resp = requests.post(api_url, json={"question": question, "top_k": top_k}, timeout=30)
        if resp.ok:
            st.json(resp.json())
        else:
            st.error(f"Request failed: {resp.status_code} {resp.text}")
