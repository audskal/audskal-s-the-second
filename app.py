import streamlit as st
import google.generativeai as genai
import PyPDF2
import os
import glob
import requests
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
    st.subheader("📚 내장된 기본 평가 기준 파일")
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
    
    student_file = st.file_uploader("📂 학생 생기부 파일 (PDF) 업로드", type=["pdf"], key="student_upload")
    st.markdown("**-- 또는 --**")
    student_text_input = st.text_area("📝 생기부 내용 직접 붙여넣기 (추천)", height=250)

with col2:
    st.subheader("2. 분석 옵션 및 추가 데이터 입력")
    teacher_context = st.text_area(
        "💡 특이사항 및 희망 전공 (예: 경영학과 진학 희망)", 
        height=70
    )
    
    # --- 💡 [유지] 목표 대학 가이드북 업로드 영역 ---
    st.markdown("**🎯 목표 대학 전형 / 전공 가이드북 (선택)**")
    st.info("특정 대학/전공의 인재상과 평가 기준에 맞춘 정밀 분석을 원하시면 해당 대학의 가이드북(PDF)을 업로드하세요.")
    univ_guide_file = st.file_uploader("🏫 대학 가이드북 PDF 업로드", type=["pdf"], key="univ_guide_upload")
    
    # --- 💡 [수정] 도서 추천 영역 (직접 업로드 제거, URL만 유지) ---
    st.markdown("**📚 맞춤형 추천 도서 참고 자료 (선택)**")
    default_url = "https://nojaesu.com/category/DIRECTORY/%EA%B5%90%EA%B3%BC%EC%97%B0%EA%B3%84%26%EC%A0%84%EA%B3%B5%EC%A0%81%ED%95%A9%EC%84%9C%20%EA%B8%B0%EC%82%AC%20%EB%AA%A8%EC%9D%8C"
    book_url = st.text_input("🌐 추천 도서 웹사이트 주소(URL)", value=default_url)
    
    submit_btn = st.button("↵ 🚀 목표 대학 맞춤형 심층 분석 시작", type="primary", use_container_width=True)

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
            status_box.info("⏳ [진행상황 1/5] 내장된 기본 가이드북을 학습하는 중입니다...")
            reference_text = load_reference_pdfs(pdf_files)
            
            # --- 대학 가이드북 텍스트 추출 ---
            univ_guide_text = ""
            if univ_guide_file:
                status_box.info("🏫 [진행상황 2/5] 업로드된 목표 대학 가이드북의 평가 기준을 분석 중입니다...")
                univ_pdf_reader = PyPDF2.PdfReader(univ_guide_file)
                for page in univ_pdf_reader.pages:
                    extracted = page.extract_text()
                    if extracted:
                        univ_guide_text += extracted + "\n"
            else:
                status_box.info("🏫 [진행상황 2/5] 목표 대학 가이드북이 생략되었습니다. 기본 범용 기준으로 진행합니다.")

            status_box.info("⏳ [진행상황 3/5] 학생의 생기부 데이터를 추출하는 중입니다...")
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
                raise Exception("생기부에서 글씨를 읽을 수 없습니다! PDF 대신 빈칸에 직접 붙여넣어 주세요.")
            
            status_box.info("📚 [진행상황 4/5] 추천 도서 목록을 수집하고 정제하는 중입니다...")
            actual_book_data = ""
            
            # URL 웹 크롤링만 유지
            if book_url.strip():
                try:
                    headers = {'User-Agent': 'Mozilla/5.0'}
                    response = requests.get(book_url.strip(), headers=headers)
                    response.raise_for_status() 
                    soup = BeautifulSoup(response.text, 'html.parser')
                    actual_book_data += soup.get_text(separator=' ', strip=True) + "\n\n"
                except Exception as e:
                    st.warning(f"⚠️ 입력하신 링크에 접속할 수 없습니다. (오류 메시지: {e})")
            
            book_instruction = ""
            if actual_book_data.strip():
                book_instruction = "반드시 아래 제공된 [추천 도서 참고 자료]의 텍스트 안에 '실제로 존재하는 책 제목과 저자'만 추출해서 추천하세요. 자료 안에 적합한 책이 없다면 억지로 지어내지 마세요."
            else:
                book_instruction = "별도로 제공된 도서 목록이 없으므로, AI가 자체적으로 학습한 실존하는 전공 적합 우수 도서를 추천해 주세요. (할루시네이션 절대 금지)"

            status_box.warning("🔍 [마무리 준비] 최적의 AI 모델을 탐색하여 분석을 시작합니다...")
            genai.configure(api_key=api_key)
            
            best_model_name = ""
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    best_model_name = m.name.replace("models/", "")
                    if 'flash' in best_model_name or 'pro' in best_model_name:
                        break 
            
            if best_model_name == "":
                raise Exception("사용할 수 있는 AI 모델이 없습니다.")
            
            model = genai.GenerativeModel(best_model_name)
            
            # --- 프롬프트 (기존과 100% 동일) ---
            prompt = f"""
            당신은 20년 경력의 대한민국 최고 수석 진학 상담 교사입니다.

            [담당 교사의 특별 지시사항 및 희망 전공]
            {teacher_context if teacher_context else "특별한 지시사항 없음."}
            
            [추천 도서 참고 자료 (웹사이트 추출 텍스트)]
            {actual_book_data if actual_book_data else "제공된 목록 없음."}

            [기본 범용 대학 평가 기준 자료]
            {reference_text}

            [목표 대학 전형/전공 가이드북 평가 기준 (선택 사항)]
            {univ_guide_text if univ_guide_text else "제공된 목표 대학 가이드북 없음. 기본 범용 평가 기준만 적용할 것."}

            [업로드된 학생의 생기부 내용 (100% 팩트)]
            {student_data_text}

            🚨 [절대 엄수 - 팩트 체크 및 소설 작성 금지 규칙!] 🚨
            1. 학생부 팩트 기반: 업로드된 내용에 없는 과목이나 활동은 지어내지 마세요.
            2. 학년별 기록 부재 지적 금지: 3학년 기록 부재 등을 단점으로 지적하지 마세요.
            3. 도서 추천 규칙: {book_instruction}
            4. 🆕 맞춤형 평가 적용: [목표 대학 전형/전공 가이드북 평가 기준]이 제공되었다면, 해당 대학이 원하는 '인재상'과 '핵심 평가 요소'를 집중적으로 벤치마킹하여 학생부를 분석하세요. 제공되지 않았다면 기본 범용 기준을 따르세요.

            🚨 [절대 엄수 - 출력 형식 및 출처 표기 규칙! (매우 중요)] 🚨
            1. 이중 출처 표기 (필수): 1번과 2번 항목에서 학생부의 내용을 언급할 때는 **반드시** 해당 내용이 몇 학년 어느 영역(과목/활동)에 있는지 출처를 밝혀야 합니다.
               - 문단 시작 시: `■ **[O학년 OO활동, O학년 OO과목]** 핵심 요약` 형태로 표기.
               - 문장 끝 시: 해당 활동의 개별 출처를 문장 끝에 `[O학년 OO활동]` 형태로 꼬리표 달기.
            2. 개조식 어미 사용: 1, 2, 4, 5번 항목의 모든 문장 끝은 '~함', '~임', '~됨', '~판단됨' 등으로 명사형 종결할 것. ('~습니다', '~해요' 절대 금지)

            💡 [형식 참고용 작성 예시]
            ### 1. 전공 적합성 및 주요 경쟁력
            ■ **[1학년 진로활동, 1학년 공통수학]** 정량적 분석 능력과 경제 현상 이해
            학생은 수학적 사고력을 바탕으로 경제 현상을 분석하는 역량이 돋보임. 공통수학 시간에 투자 수익률 모델링을 진행하며 의사결정 도구로 활용함 [1학년 공통수학]. 또한 '경제는 지리다' 독서를 통해 세계 경제 흐름에 대한 시야를 기름 [1학년 진로활동]. (가이드북이 있을 경우: 목표 대학 가이드북에서 강조하는 '융합적 문제해결력'에 매우 부합함.)

            위의 규칙을 완벽히 지켜서, 아래 5가지 양식 및 순서에 맞추어 최종 결과물을 작성해 주세요.
            ### 1. 목표 대학 및 전공 적합성 주요 경쟁력 (반드시 '이중 출처 표기' 및 '개조식' 적용)
            ### 2. 목표 대학(또는 범용) 평가 기준에 비추어 볼 때 보완이 필요한 약점 (반드시 '이중 출처 표기' 및 '개조식' 적용)
            ### 3. 추천 심화 탐구 주제 및 면접 예상 질문 3가지
            ### 4. 맞춤형 추천 도서 및 연계 활동 제안 (반드시 제공된 도서 목록 활용)
            ### 5. 종합 의견 및 향후 발전 방향 (개조식 마무리)
            """
            
            response = model.generate_content(prompt)
            
            status_box.success("✅ [분석 완료!] 대학 가이드북을 반영한 심층 분석이 완료되었습니다. 결과물을 확인해 주세요!")
            st.write(response.text)
            
            word_file = create_word_file(response.text)
            st.download_button(
                label="📥 분석 결과 워드 다운로드",
                data=word_file,
                file_name="생기부_맞춤형_분석결과.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
            
        except Exception as e:
            status_box.error(f"오류가 발생했습니다: {e}")

st.divider()
st.markdown("""
<div style='text-align: center; color: gray; padding: 20px; font-size: 13px;'>
    🏫 학교생활기록부 분석 시스템 v6.1 (불필요한 UI 정리 완료)<br>
    만든이: <b>신선여자고등학교 김명남</b>
</div>
""", unsafe_allow_html=True)
