import streamlit as st
import google.generativeai as genai
import PyPDF2
import os
import glob
from docx import Document
from io import BytesIO

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
    st.subheader("2. 학생부 분석을 위한 특이사항 추가 입력")
    teacher_context = st.text_area(
        "예: '전기, 전자 공학 계열로 진학을 희망하는 학생이야. 이 점 고려해서 분석해줘'", 
        height=150
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
                raise Exception("업로드하신 PDF 파일에서 글씨를 읽을 수 없습니다! (이미지 스캔본이거나 나이스 보안파일입니다). PDF 대신 왼쪽 빈칸에 생기부 내용을 직접 마우스로 긁어서 붙여넣어 주세요.")
            
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
            
            status_box.success(f"🤖 [진행상황 4/4] AI 엔진('{best_model_name}') 장착 완료! 객관적 경쟁력 분석을 시작합니다...")
            model = genai.GenerativeModel(best_model_name)
            
            # --- [수정된 마법의 프롬프트: 범용적 벤치마킹 적용] ---
            prompt = f"""
            당신은 20년 경력의 대한민국 최고 수석 진학 상담 교사입니다.
            아래에 제공된 [대학 평가 기준 자료]는 훌륭한 학생부를 판단하기 위한 '참고용 범용 벤치마크(기준점)'입니다.
            이 기준점들에 비추어 보았을 때, [업로드된 학생의 생기부 내용]이 가진 객관적인 경쟁력과 역량 수준을 날카롭게 분석해 주세요.

            🚨 [주의: 특정 대학 편향 금지] 🚨
            - 특정 대학교에 지원한다는 가정하에 작성하지 마세요. 
            - 평가 기준 자료에 등장하는 특정 대학교 이름이나 '목표 대학'이라는 단어를 억지로 출력하지 마세요. 
            - 오직 '상위권 대학들이 공통으로 요구하는 역량'을 잣대로 삼아, 이 학생부 자체가 가진 경쟁력과 전공 적합성에만 집중하세요.

            🚨 [절대 엄수 - 팩트 체크 및 소설 작성 금지 규칙!] 🚨
            1. 팩트 기반 작성 (할루시네이션 절대 금지): 
               - 반드시 [업로드된 학생의 생기부 내용]에 '실제로 적혀있는 학년'과 '실제로 한 활동'만 가지고 분석하세요.
               - 생기부에 없는 내용, 학년, 과목명, 활동명은 단 한 글자도 지어내면 안 됩니다.
            2. 예시 내용 복사 금지: 
               - 아래의 [작성 예시]는 구조와 문체를 보여주기 위함입니다. 빈칸에 반드시 학생의 '실제 데이터'만 채워 넣으세요.

            🚨 [형식 및 문체 규칙] 🚨
            1. 압축 서술: 사소한 활동은 버리고, 테마별로 가장 강력한 활동 단 2~3개만 엄선하여 3~4문장으로 압축할 것.
            2. 이중 출처 표기:
               - 문단 시작: 핵심 출처를 묶어서 `**[1학년 진로, 2학년 물리]** ` 형태로 표기.
               - 문장 끝: 해당 활동의 개별 출처를 `[1학년 진로]` 형태로 꼬리표 달기.
            3. 전 구간 개조식 어미 사용: 
               - 모든 문장의 끝은 '~함', '~임', '~됨', '~판단됨', '~요망됨' 으로 끝낼 것. ('~다', '~합니다' 절대 금지)

            💡 [형식 참고용 작성 예시]
            ### 1. 전공 적합성 및 주요 강점
            ■ (학생의 데이터 기반 핵심 테마 소제목)
            **[O학년 OO활동, O학년 OO과목]** 학생은 (학생의 실제 호기심이나 역량 요약) 모습이 돋보임. O학년 때 (실제 활동 1)에 참여하여 (배운 점 1)을 학습함 [O학년 OO활동]. O학년 행사에서는 (실제 활동 2)를 탐구하고 (배운 점 2) 능력을 향상함 [O학년 OO과목]. 

            [담당 교사의 특별 지시사항]
            {teacher_context if teacher_context else "특별한 지시사항 없음."}

            [대학 평가 기준 자료 (범용 벤치마크용)]
            {reference_text}

            [업로드된 학생의 생기부 내용 (100% 팩트)]
            {student_data_text}

            위의 규칙을 완벽히 지켜서, 학생의 실제 데이터만을 바탕으로 아래 4가지 양식에 맞추어 답변해 주세요.
            ### 1. 전공 적합성 및 주요 경쟁력 (테마별 소제목 작성, 테마당 3~4문장 압축, 이중 출처 표기)
            ### 2. 범용 평가 기준에 비추어 볼 때 보완이 필요한 약점 (실제 데이터 기반 압축 서술, 이중 출처 표기)
            ### 3. 추천 심화 탐구 주제 및 면접 예상 질문 3가지
            ### 4. 종합 의견 및 향후 발전 방향 (구체적인 액션 플랜과 최종 코멘트 포함, 개조식 마무리)
            """
            
            response = model.generate_content(prompt)
            
            status_box.success("✅ [분석 완료!] 초고속 심층 분석이 완료되었습니다. 결과물을 확인해 주세요!")
            st.write(response.text)
            
            word_file = create_word_file(response.text)
            st.download_button(
                label="📥 분석 결과 워드(Word) 파일로 다운로드",
                data=word_file,
                file_name="생기부_분석결과.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
            
        except Exception as e:
            status_box.error(f"오류가 발생했습니다: {e}")
            

