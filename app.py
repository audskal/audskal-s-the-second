import streamlit as st
import google.generativeai as genai
import PyPDF2
import os
import glob
from docx import Document
from io import BytesIO
import urllib.parse
from bs4 import BeautifulSoup  # 💡 HTML에서 순수 텍스트만 추출하기 위해 추가됨

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
        "💡 특이사항 및 희망 전공 (예: 전기전자공학 진학 희망)", 
        height=70
    )
    
    default_book_link = "file:///D:/%EC%9B%90%EB%93%9C%EB%9D%BC%EC%9D%B4%EB%B8%8C/OneDrive%20-%20%EC%9A%B8%EC%82%B0%EA%B4%91%EC%97%AD%EC%8B%9C%EA%B5%90%EC%9C%A1%EC%B2%AD/%EB%AC%B8%EC%84%9C/%EC%B9%B4%EC%B9%B4%EC%98%A4%ED%86%A1%20%EB%B0%9B%EC%9D%80%20%ED%8C%8C%EC%9D%BC/%EB%AF%B8%EB%9E%98%EB%A5%BC%20%EC%97%AC%EB%8A%94%20%EC%84%9C%EC%9E%AC(%EB%82%B4%EC%9D%BC%EA%B5%90%EC%9C%A1%20%EA%B6%8C%EC%9E%A5%EB%8F%84%EC%84%9C%20%EA%B4%80%EB%A0%A8%20%EA%B8%B0%EC%82%AC%20%EA%B2%80%EC%83%89-%EC%8B%A0%EC%84%A0%EC%97%AC%EA%B3%A0%20%EC%9E%84%EC%A2%85%EC%9A%B0).html"
    
    book_reference = st.text_input(
        "🔗 추천 도서 참고 링크 또는 목록 (선택)", 
        value=default_book_link,
        placeholder="도서 링크 또는 목록 입력"
    )
    
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
            
            # --- 💡 [핵심 수정 부분] HTML 태그를 제거하고 순수 텍스트만 추출 ---
            status_box.info("📚 [도서 연동] 추천 도서 목록을 정제하는 중입니다...")
            actual_book_data = book_reference
            
            if book_reference.startswith("file:///"):
                try:
                    local_path = urllib.parse.unquote(book_reference.replace("file:///", ""))
                    if os.path.exists(local_path):
                        with open(local_path, "r", encoding="utf-8", errors='ignore') as f:
                            raw_html = f.read()
                            # BeautifulSoup을 사용하여 HTML 태그를 모두 벗겨내고 텍스트만 추출
                            soup = BeautifulSoup(raw_html, 'html.parser')
                            actual_book_data = soup.get_text(separator=' ', strip=True)
                    else:
                        actual_book_data = "제공된 파일 없음."
                except Exception as e:
                    actual_book_data = "제공된 파일 없음."

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
            
            status_box.success(f"🤖 [진행상황 4/4] 분석을 시작합니다...")
            model = genai.GenerativeModel(best_model_name)
            
            # --- 💡 [프롬프트 강화] 도서 추천 시 절대 지어내지 말 것을 강력히 지시 ---
            prompt = f"""
            당신은 20년 경력의 대한민국 최고 수석 진학 상담 교사입니다.

            🚨 [절대 엄수 - 팩트 체크 및 소설 작성 금지 규칙!] 🚨
            1. 학생부 팩트 기반: 업로드된 내용에 없는 과목이나 활동은 지어내지 마세요.
            2. 학년별 기록 부재 지적 금지: 3학년 기록 부재 등을 단점으로 지적하지 마세요.
            3. [매우 중요] 도서 추천 규칙: 
               - 반드시 아래 제공된 [추천 도서 참고 자료]의 텍스트 안에 '실제로 존재하는 책 제목과 저자'만 추출해서 추천하세요.
               - 자료 안에 적합한 책이 없다면, 억지로 가짜 책을 지어내지 말고 차라리 "제공된 목록에서 적합한 도서를 찾을 수 없습니다"라고 출력하세요. 임의로 책 제목과 저자를 창작(할루시네이션)하는 행위를 엄격히 금지합니다.

            [담당 교사의 특별 지시사항 및 희망 전공]
            {teacher_context if teacher_context else "특별한 지시사항 없음."}
            
            [추천 도서 참고 자료 (추출된 순수 텍스트)]
            {actual_book_data}

            [대학 평가 기준 자료 (범용 벤치마크용)]
            {reference_text}

            [업로드된 학생의 생기부 내용 (100% 팩트)]
            {student_data_text}

            위의 규칙을 완벽히 지켜서, 학생의 실제 데이터만을 바탕으로 아래 5가지 양식에 맞추어 답변해 주세요.
            ### 1. 전공 적합성 및 주요 경쟁력
            ### 2. 범용 평가 기준에 비추어 볼 때 보완이 필요한 약점
            ### 3. 추천 심화 탐구 주제 및 면접 예상 질문 3가지
            ### 4. 종합 의견 및 향후 발전 방향
            ### 5. 맞춤형 추천 도서 및 연계 활동 제안 (반드시 [추천 도서 참고 자료] 내에 명시된 실제 도서명과 저자만 사용할 것)
            """
            
            response = model.generate_content(prompt)
            
            status_box.success("✅ [분석 완료!] 초고속 심층 분석이 완료되었습니다. 결과물을 확인해 주세요!")
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
    🏫 학교생활기록부 분석 시스템 v4.2<br>
    만든이: <b>신선여자고등학교 김명남</b>
</div>
""", unsafe_allow_html=True)
