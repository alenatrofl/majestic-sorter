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

# --- СТИЛЬНЫЙ И ЧИСТЫЙ CSS (СВЕТЛАЯ ТЕМА В СТИЛЕ MAJESTIC RP) ---
st.markdown("""
    <style>
    /* Базовые настройки приложения (чистый светлый фон) */
    .stApp {
        background-color: #f8fafc;
        color: #1e293b;
    }
    
    /* Красивый и аккуратный заголовок */
    .main-title {
        font-size: 2.4rem !important;
        font-weight: 700;
        color: #5932a6; /* Фирменный фиолетовый цвет Majestic */
        text-align: center;
        margin-bottom: 0.2rem;
    }
    
    .sub-title {
        text-align: center;
        color: #64748b;
        font-size: 1rem;
        margin-bottom: 1.5rem;
    }

    /* Стилизация всех стандартных кнопок */
    div.stButton > button {
        border-radius: 8px !important;
        font-weight: 500 !important;
        border: 1px solid #cbd5e1 !important;
        background-color: #ffffff !important;
        color: #334155 !important;
        transition: all 0.2s ease !important;
    }
    div.stButton > button:hover {
        border-color: #5932a6 !important;
        color: #5932a6 !important;
    }

    # 🔥 Особый стиль для главной кнопки запуска (Кнопка "Начать проверку")
    div.stButton > button[key="start_btn"] {
        background-color: #5932a6 !important;
        color: #ffffff !important;
        border: none !important;
        font-weight: 600 !important;
        font-size: 1.05rem !important;
        width: 100% !important;
        padding: 0.5rem 0 !important;
        box-shadow: 0 2px 4px rgba(89, 50, 166, 0.15) !important;
    }
    div.stButton > button[key="start_btn"]:hover {
        background-color: #4c2893 !important;
        box-shadow: 0 4px 8px rgba(89, 50, 166, 0.25) !important;
    }

    # Стиль для кнопки скачивания архива
    div.stDownloadButton > button {
        background-color: #10b981 !important;
        color: #ffffff !important;
        border: none !important;
        font-weight: 600 !important;
        width: 100% !important;
    }
    div.stDownloadButton > button:hover {
        background-color: #059669 !important;
    }
    
    /* Аккуратные рамки вокруг блоков */
    .stFileUploader, .stCheckbox {
        background-color: #ffffff;
        padding: 1.2rem;
        border-radius: 10px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.02);
    }
    </style>
""", unsafe_allow_html=True)

# Заголовки сайта
st.markdown('<h1 class="main-title">🚑 Majestic RP | Сортировщик EMS</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">Автоматическая сортировка скриншотов медицинских отчетов</p>', unsafe_allow_html=True)

# Инициализация состояний звука
if "play_sound" not in st.session_state:
    st.session_state.play_sound = True
if "upload_sound_triggered" not in st.session_state:
    st.session_state.upload_sound_triggered = False

# Кнопка звука (теперь она выглядит аккуратно и текст отлично читается)
col1, col2, col3 = st.columns([1, 1.2, 1])
with col2:
    if st.session_state.play_sound:
        if st.button("🔊 Уведомления: ВКЛ", use_container_width=True):
            st.session_state.play_sound = False
            st.rerun()
    else:
        if st.button("🔇 Уведомления: ВЫКЛ", use_container_width=True):
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

show_debug = st.checkbox("🔍 Показать распознанный текст для папки 'Другое' (для поиска ошибок)")

if uploaded_files:
    # --- ЗВУК ПРИ ПОЯВЛЕНИИ КНОПКИ (ИЗ ПАПКИ sounds_start) ---
    if st.session_state.play_sound and not st.session_state.upload_sound_triggered:
        play_random_sound_from_dir("sounds_start")
        st.session_state.upload_sound_triggered = True  
    # --------------------------------------------------------

    st.write("") # Небольшой отступ
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
