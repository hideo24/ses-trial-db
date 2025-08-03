import streamlit as st
import openai
from datetime import datetime
import fitz  # PyMuPDF for PDF
from docx import Document
from openai import OpenAI


# ----------------------
# Helper functions
# ----------------------
def extract_text_from_pdf(pdf_file):
    doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
    text = "".join([page.get_text() for page in doc])
    return text

def extract_text_from_docx(docx_file):
    doc = Document(docx_file)
    return "\n".join([p.text for p in doc.paragraphs])

def extract_text(file) -> str:
    """アップロードされたファイルからテキストを抽出"""
    fname = file.name.lower()
    if fname.endswith(".pdf"):
        return extract_text_from_pdf(file)
    elif fname.endswith(".docx"):
        return extract_text_from_docx(file)
    elif fname.endswith(".txt"):
        return file.read().decode("utf-8")
    else:
        st.error("PDF, DOCX, TXTのみ対応しています。")
        st.stop()


def build_prompt(case_no, client, project, bp, candidate_info, doc_text):
    """ChatGPTに送る評価用プロンプトを組み立て"""
    prompt = (f"以下のSES案件({case_no})に対して、人材候補を100点満点で評価してください。"  
              f"\n要件: {project}\nクライアント: {client}\nBP: {bp}\n"  
              f"候補者情報: {candidate_info}\n"  
              f"経歴書内容: {doc_text}\n"  
              "\n出力形式を以下にしてください:\n"  
              "点数: ◯◯点\n評価コメント: ●●●\n提案文: ○○○")
    return prompt


def parse_response(resp_text):
    """ChatGPTの応答から点数・コメント・提案文を抽出"""
    lines = [l.strip() for l in resp_text.splitlines() if l.strip()]
    score = None
    comment = []
    proposal = []
    for line in lines:
        if line.startswith("点数:"):
            score = line.split("点数:")[-1].strip()
        elif line.startswith("評価コメント:"):
            comment.append(line.replace("評価コメント:", "").strip())
        elif line.startswith("提案文:"):
            proposal.append(line.replace("提案文:", "").strip())
    return score, "\n".join(comment), "\n".join(proposal)


# ----------------------
# Streamlit UI
# ----------------------
st.set_page_config(page_title="SES提案評価ツール v0")
st.title("SES提案評価ツール v0")

# 入力フォーム
with st.form(key="input_form"):
    case_no = st.text_input("案件No.")
    client = st.text_input("クライアント名")
    project = st.text_input("案件名")
    bp = st.text_input("BP")
    candidate_info = st.text_area("候補者情報 (スキル・経験など)")
    uploaded_file = st.file_uploader("書類アップロード (PDF/DOCX/TXT)", type=["pdf", "docx", "txt"] )
    run = st.form_submit_button("評価実行")

# 評価実行
if run:
    if not all([case_no, client, project, bp, candidate_info, uploaded_file]):
        st.error("すべての項目を入力・アップロードしてください。")
    else:
        with st.spinner("評価中... \nこの処理には数秒かかります"):
            # ファイル解析
            doc_text = extract_text(uploaded_file)
            # プロンプト組み立て
            prompt = build_prompt(case_no, client, project, bp, candidate_info, doc_text)
            # ChatGPT API呼び出し
            client = OpenAI()  # ← 自動でAPIキーを読み込む（Secrets or 環境変数）

            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )

            resp_text = response.choices[0].message.content
            # レスポンス解析
            score, comment, proposal = parse_response(resp_text)

        # 結果表示
        st.success(f"評価結果 (案件No: {case_no})")
        st.markdown(f"**点数:** {score}")
        st.markdown("**評価コメント:**")
        st.write(comment)
        st.markdown("**提案文:**")
        st.write(proposal)

        # TODO: Google Sheets連携で自動追記 (次ステップ)
