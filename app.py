import streamlit as st
import cv2
import numpy as np
import pytesseract
import zipfile
import io
import os
import random
import base64

# Универсальная функция для скрытого воспроизведения звука из указанной папки
def play_random_sound_from_dir(directory_name):
    if os.path.exists(directory_name):
        sound_files = [f for f in os.listdir(directory_name) if f.endswith(('.mp3', '.wav', '.ogg'))]
        if sound_files:
            random_sound = random.choice(sound_files)
            sound_path = os.path.join(directory_name, random_sound)
            
            with open(sound_path, "rb") as f:
                audio_bytes = f.read()
            audio_base64 = base64.b64encode(audio_bytes).decode()
            format_ext = random_sound.split('.')[-1]
            
            audio_html = f"""
                <audio autoplay style="display:none;">
                    <source src="data:audio/{format_ext};base64,{audio_base64}" type="audio/{format_ext}">
                </audio>
            """
            st.markdown(audio_html, unsafe_allow_html=True)

# Указывайте путь к tesseract, только если вы точно уверены, что он там (для Linux/Docker)
if os.path.exists('/usr/bin/tesseract'):
    pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'

# Конфигурация страницы
st.set_page_config(page_title="Majestic RP Сортировщик EMS", page_icon="🚑", layout="centered")

# --- БЛОК КАСТОМНОГО CSS ДЛЯ КРАСОЧНОГО ДИЗАЙНА ---
st.markdown("""
    <style>
    /* Настройка главного фона и шрифтов */
    .stApp {
        background: linear-gradient(135deg, #111827 0%, #1f2937 100%);
        color: #f3f4f6;
    }
    
    /* Красивый заголовок с градиентом */
    .main-title {
        font-size: 2.8rem !important;
        font-weight: 800;
        background: linear-gradient(90deg, #ef4444, #3b82f6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    
    .sub-title {
        text-align: center;
        color: #9ca3af;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }

    /* Стилизация ВСЕХ кнопок в приложении */
    div.stButton > button {
        border-radius: 12px !important;
        padding: 0.6rem 1.5rem !important;
        font-weight: 600 !important;
        transition: all 0.3s ease-index !important;
        border: none !important;
    }

    /* Особый стиль для главной кнопки запуска проверки */
    div.stButton > button[key="start_btn"] {
        background: linear-gradient(90deg, #ff416c, #ff4b2b) !important;
        color: white !important;
        font-size: 1.2rem !important;
        width: 100% !important;
        box-shadow: 0 4px 15px rgba(255, 65, 108, 0.4) !important;
    }
    div.stButton > button[key="start_btn"]:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(255, 65, 108, 0.6) !important;
    }

    /* Стиль кнопки скачивания архива */
    div.stDownloadButton > button {
        background: linear-gradient(90deg, #11998e, #38ef7d) !important;
        color: white !important;
        border-radius: 12px !important;
        width: 100% !important;
        font-size: 1.1rem !important;
        box-shadow: 0 4px 15px rgba(56, 239, 125, 0.4) !important;
    }
    
    /* Кастомные контейнеры (Glassmorphism effect) */
    .css-1r6slb0, .stCheckbox, .stFileUploader {
        background: rgba(255, 255, 255, 0.05);
        padding: 1.5rem;
        border-radius: 16px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(8px);
        margin-bottom: 1rem;
    }
    </style>
""", unsafe_allow_html=True)

# Использование кастомных заголовков вместо стандартных st.title
st.markdown('<h1 class="main-title">🚑 Majestic RP | Сортировщик EMS</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">Профессиональная автоматическая сортировка скриншотов медицинских отчетов</p>', unsafe_allow_html=True)

# Инициализация состояний звука
if "play_sound" not in st.session_state:
    st.session_state.play_sound = True
if "upload_sound_triggered" not in st.session_state:
    st.session_state.upload_sound_triggered = False

# Кнопка-переключатель звука (сделаем её аккуратной сверху)
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if st.session_state.play_sound:
        if st.button("🔊 Звук: ВКЛ", use_container_width=True):
            st.session_state.play_sound = False
            st.rerun()
    else:
        if st.button("🔇 Звук: ВЫКЛ", use_container_width=True):
            st.session_state.play_sound = True
            st.rerun()

st.write("---")

# Сверхточный список ключевых слов
FOLDERS = {
    "Мед_Справки": ["выдали", "справк", "справ", "псих", "физ", "спра", "спран"],
    "Лечение": ["вылечили", "вылеч", "лече", "лечи", "таблет","лечеви"],
    "Реанимация": ["реанимировали", "реаним", "реани", "спасение", "спасен"],
    "Вакцинация": ["вакцинировали", "вакцин", "вакци", "привив", "ваки"]
}

uploaded_files = st.file_uploader("Перетащите файлы скриншотов сюда", 
                                  type=["png", "jpg", "jpeg"], 
                                  accept_multiple_files=True)

show_debug = st.checkbox("🔍 Показать распознанный текст для папки 'Другое' (дебаг)")

if uploaded_files:
    # --- ЗВУК ПРИ ПОЯВЛЕНИИ КНОПКИ (ИЗ ПАПКИ sounds_start) ---
    if st.session_state.play_sound and not st.session_state.upload_sound_triggered:
        play_random_sound_from_dir("sounds_start")
        st.session_state.upload_sound_triggered = True  
    # --------------------------------------------------------

    # Назначаем кнопке уникальный key="start_btn" для применения CSS стилей огненного градиента
    if st.button("🚀 НАЧАТЬ ТОЧНУЮ СОРТИРОВКУ", key="start_btn"):
        zip_buffer = io.BytesIO()
        progress_bar = st.progress(0)
        status_text = st.empty()
        debug_logs = []
        
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED, allowZip64=True) as zip_file:
            for idx, uploaded_file in enumerate(uploaded_files):
                status_text.markdown(f"⏳ **Обработка:** `{uploaded_file.name}` ({idx+1}/{len(uploaded_files)})")
                
                file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
                img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
                
                if img is not None:
                    h, w, _ = img.shape
                    
                    crop_center_bottom = img[int(h*0.65):int(h*0.96), int(w*0.35):int(w*0.65)]
                    
                    gray = cv2.cvtColor(crop_center_bottom, cv2.COLOR_BGR2GRAY)
                    gray_large = cv2.resize(gray, (0, 0), fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
                    _, thresh = cv2.threshold(gray_large, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                    
                    custom_config = r'--oem 3 --psm 6'
                    text = pytesseract.image_to_string(thresh, lang='rus+eng', config=custom_config).lower()
                    
                    target_folder = "Другое"
                    for folder, keywords in FOLDERS.items():
                        if any(keyword in text for keyword in keywords):
                            target_folder = folder
                            break
                    
                    if target_folder == "Другое":
                        clean_text = text.strip().replace('\n', ' ')
                        debug_logs.append(f"**Файл:** {uploaded_file.name} | **Робот прочитал:** `{clean_text}`")
                    
                    uploaded_file.seek(0)
                    zip_file.writestr(os.path.join(target_folder, uploaded_file.name), uploaded_file.read())
                
                progress_bar.progress((idx + 1) / len(uploaded_files))
        
        status_text.markdown("### 🎉 Сортировка успешно завершена!")
        
        # --- ЗВУК ПОСЛЕ ЗАВЕРШЕНИЯ ПРОВЕРКИ (ИЗ ПАПКИ sounds_end) ---
        if st.session_state.play_sound:
            play_random_sound_from_dir("sounds_end")
        # -----------------------------------------------------------
        
        zip_buffer.seek(0)
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.download_button(
            label="📥 СКАЧАТЬ ГОТОВЫЙ АРХИВ (ZIP)",
            data=zip_buffer.getvalue(),
            file_name="sorted_screenshots.zip",
            mime="application/zip"
        )
        
        if show_debug and debug_logs:
            st.write("---")
            st.subheader("🔍 Анализ нераспознанных файлов:")
            for log in debug_logs:
                st.markdown(log)
else:
    st.session_state.upload_sound_triggered = False
