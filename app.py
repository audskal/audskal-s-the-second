import streamlit as st
import google.generativeai as genai
import PyPDF2
import os
import glob
import requests  # 💡 인터넷 웹페이지 접속을 위해 추가된 모듈
from docx import Document
from io import BytesIO
from bs4 import BeautifulSoup

st.set_page_config(page_title="audskal의 학교생활기록부 분석", layout="wide")
st.title("🏫 객관적이고 체계적인 학생부 분석")
st.markdown("API 키에 맞는 최적의 AI 모델을 자동으로 찾아내어 생기부를 체계적으로 분석합니다.")

@st.cache_data(show_spinner=False)
def load_reference_pdfs(pdf_list):
    text = ""
    for pdf_file in pdf_list:
        with open(pdf_file, "rb") as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
    return text

with st.sidebar:
    st.header("🔑 기본 설정")
    api_key = st.text_input("API 키를 입력하세요", type="password")
    st.markdown("[👉 무료 API 키 발급받기](https://aistudio.google.com/app/apikey)")
    
    st.markdown("---")
    st.subheader("📚 내장된 평가 기준 파일 (참고용)")
    pdf_files = glob.glob("*.pdf")
    if pdf_files:
        for f in pdf_files:
            st.write(f"- {f}")
    else:
        st.error("폴더에 기준 PDF 파일이 없습니다!")

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("1. 학교생활기록부 데이터 입력")
    st.info("💡 나이스(NEIS) 원본 PDF는 보안상 안 읽히는 경우가 많습니다. 가급적 아래 빈칸에 내용을 직접 긁어서 붙여넣으세요!")
    
    student_file = st.file_uploader("📂 학생 생기부 파일 (PDF) 업로드", type=["pdf"])
    st.markdown("**-- 또는 --**")
    student_text_input = st.text_area("📝 생기부 내용 직접 붙여넣기 (추천)", height=250)

with col2:
    st.subheader("2. 학생부 분석을 위한 추가 정보 입력")
    teacher_context = st.text_area(
        "💡 특이사항 및 희망 전공 (예: 경영학과 진학 희망)", 
        height=70
    )
    
    # --- 💡 [핵심 변경] 인터넷 주소(URL) 입력창 추가 ---
    st.markdown("**📚 맞춤형 추천 도서 참고 자료 (선택)**")
    
    default_url = "https://nojaesu.com/category/DIRECTORY/%EA%B5%90%EA%B3%BC%EC%97%B0%EA%B3%84%26%EC%A0%84%EA%B3%B5%EC%A0%81%ED%95%A9%EC%84%9C%20%EA%B8%B0%EC%82%AC%20%EB%AA%A8%EC%9D%8C"
    book_url = st.text_input("🌐 추천 도서 참고 웹사이트 주소(URL)", value=default_url, help="웹사이트의 글씨를 AI가 직접 긁어옵니다.")
    
    with st.expander("파일 업로드 또는 직접 입력 (클릭하여 열기)"):
        book_file = st.file_uploader("🔗 도서 목록 파일 업로드 (HTML, PDF, TXT)", type=["html", "pdf", "txt"])
        book_text_input = st.text_area("또는 텍스트 직접 붙여넣기", height=100)
    
    submit_btn = st.button("↵ 🚀 심층 분석 시작 (클릭)", type="primary", use_container_width=True)

st.markdown("---")

def create_word_file(text):
    doc = Document()
    doc.add_heading('AI 생기부 분석 결과 보고서', 0)
    doc.add_paragraph(text)
    
    file_stream = BytesIO()
    doc.save(file_stream)
    file_stream.seek(0)
    return file_stream

if submit_btn:
    if not api_key:
        st.error("왼쪽에 API 키를 먼저 입력해 주세요!")
    elif not pdf_files:
        st.error("기준이 될 PDF 파일이 폴더에 없습니다!")
    elif not student_file and not student_text_input.strip():
        st.error("학생의 생기부 파일(PDF)을 업로드하거나 텍스트를 직접 붙여넣어 주세요!")
    else:
        status_box = st.empty()
        
        try:
            status_box.info("⏳ [진행상황 1/4] 내장된 가이드북(PDF)을 읽고 암기하는 중입니다...")
            reference_text = load_reference_pdfs(pdf_files)
            
            status_box.info("⏳ [진행상황 2/4] 학생의 생기부 데이터를 추출하는 중입니다...")
            student_data_text = ""
            
            if student_text_input.strip():
                student_data_text = student_text_input
            elif student_file:
                student_pdf_reader = PyPDF2.PdfReader(student_file)
                for page in student_pdf_reader.pages:
                    text = page.extract_text()
                    if text:
                        student_data_text += text + "\n"
            
            if not student_data_text.strip():
                raise Exception("업로드하신 PDF 파일에서 글씨를 읽을 수 없습니다! PDF 대신 빈칸에 직접 붙여넣어 주세요.")
            
            # --- 💡 웹 크롤링 및 파일 텍스트 추출 통합 ---
            status_box.info("📚 [도서 연동] 추천 도서 목록을 수집하고 정제하는 중입니다...")
            actual_book_data = ""
            
            # 1. URL 웹 크롤링 시도
            if book_url.strip():
                try:
                    # 봇 차단 방지용 헤더 추가 (마치 사람이 브라우저로 접속하는 것처럼 위장)
                    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
                    response = requests.get(book_url.strip(), headers=headers)
                    response.raise_for_status() # 접속 실패 시 에러 발생시킴
                    
                    # HTML에서 순수 텍스트만 추출
                    soup = BeautifulSoup(response.text, 'html.parser')
                    actual_book_data += soup.get_text(separator=' ', strip=True) + "\n\n"
                except Exception as e:
                    st.warning(f"⚠️ 입력하신 링크에 접속할 수 없습니다. 보안이 설정된 사이트일 수 있습니다. (오류 메시지: {e})")

            # 2. 텍스트 박스 내용 추가
            if book_text_input.strip():
                actual_book_data += book_text_input + "\n\n"
                
            # 3. 파일 업로드 내용 추가
            if book_file:
                if book_file.name.endswith('.html'):
                    raw_html = book_file.read().decode('utf-8', errors='ignore')
                    soup = BeautifulSoup(raw_html, 'html.parser')
                    actual_book_data += soup.get_text(separator=' ', strip=True) + "\n\n"
                elif book_file.name.endswith('.txt'):
                    actual_book_data += book_file.read().decode('utf-8', errors='ignore') + "\n\n"
                elif book_file.name.endswith('.pdf'):
                    pdf_reader = PyPDF2.PdfReader(book_file)
                    for page in pdf_reader.pages:
                        extracted = page.extract_text()
                        if extracted:
                            actual_book_data += extracted + "\n"
            
            # --- 유연한 프롬프트 세팅 ---
            book_instruction = ""
            if actual_book_data.strip():
                book_instruction = "반드시 아래 제공된 [추천 도서 참고 자료]의 텍스트 안에 '실제로 존재하는 책 제목과 저자'만 추출해서 추천하세요. 자료 안에 적합한 책이 없다면 억지로 지어내지 말고 '제공된 목록에서 적합한 도서를 찾을 수 없습니다'라고 출력하세요."
            else:
                book_instruction = "별도로 제공된 도서 목록이 없으므로, AI가 자체적으로 학습한 실존하는 전공 적합 우수 도서 3권을 추천해 주세요. (가상의 책을 지어내는 할루시네이션 절대 금지)"

            status_box.warning("🔍 [진행상황 3/4] 최적의 구글 AI 모델을 탐색 중입니다...")
            genai.configure(api_key=api_key)
            
            best_model_name = ""
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    best_model_name = m.name.replace("models/", "")
                    if 'flash' in best_model_name or 'pro' in best_model_name:
                        break 
            
            if best_model_name == "":
                raise Exception("사용할 수 있는 AI 모델이 없습니다.")
            
            status_box.success(f"🤖 [진행상황 4/4] 수집된 도서 데이터를 바탕으로 분석을 시작합니다...")
            model = genai.GenerativeModel(best_model_name)
            
            prompt = f"""
            당신은 20년 경력의 대한민국 최고 수석 진학 상담 교사입니다.

            🚨 [절대 엄수 - 팩트 체크 및 소설 작성 금지 규칙!] 🚨
            1. 학생부 팩트 기반: 업로드된 내용에 없는 과목이나 활동은 지어내지 마세요.
            2. 학년별 기록 부재 지적 금지: 3학년 기록 부재 등을 단점으로 지적하지 마세요.
            3. [매우 중요] 도서 추천 규칙: 
               - {book_instruction}

            [담당 교사의 특별 지시사항 및 희망 전공]
            {teacher_context if teacher_context else "특별한 지시사항 없음."}
            
            [추천 도서 참고 자료 (웹사이트 및 파일에서 추출된 텍스트)]
            {actual_book_data if actual_book_data else "제공된 목록 없음."}

            [대학 평가 기준 자료 (범용 벤치마크용)]
            {reference_text}

            [업로드된 학생의 생기부 내용 (100% 팩트)]
            {student_data_text}

            위의 규칙을 완벽히 지켜서, 학생의 실제 데이터만을 바탕으로 아래 5가지 양식에 맞추어 답변해 주세요.
            ### 1. 전공 적합성 및 주요 경쟁력
            ### 2. 범용 평가 기준에 비추어 볼 때 보완이 필요한 약점
            ### 3. 추천 심화 탐구 주제 및 면접 예상 질문 3가지
            ### 4. 종합 의견 및 향후 발전 방향
            ### 5. 맞춤형 추천 도서 및 연계 활동 제안
            """
            
            response = model.generate_content(prompt)
            
            status_box.success("✅ [분석 완료!] 웹 크롤링 및 심층 분석이 완료되었습니다. 결과물을 확인해 주세요!")
            st.write(response.text)
            
            word_file = create_word_file(response.text)
            st.download_button(
                label="📥 분석 결과 워드 다운로드",
                data=word_file,
                file_name="생기부_분석결과.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
            
        except Exception as e:
            status_box.error(f"오류가 발생했습니다: {e}")

st.divider()
st.markdown("""
<div style='text-align: center; color: gray; padding: 20px; font-size: 13px;'>
    🏫 학교생활기록부 분석 시스템 v5.0 (웹사이트 자동 크롤링 기능 탑재)<br>
    만든이: <b>신선여자고등학교 김명남</b>
</div>
""", unsafe_allow_html=True)
