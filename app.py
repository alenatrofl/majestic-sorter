import streamlit as st
import cv2
import numpy as np
import pytesseract
import zipfile
import io
import os
import random
import base64  # <--- Добавили для скрытого воспроизведения звука

# Указывайте путь к tesseract, только если вы точно уверены, что он там (для Linux/Docker)
if os.path.exists('/usr/bin/tesseract'):
    pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'

st.set_page_config(page_title="Majestic RP Сортировщик EMS", page_icon="📸")

st.title("📸 Сортировщик скриншотов Majestic RP (EMS)")
st.write("Загрузите скриншоты, и сайт автоматически разложит их по папкам внутри ZIP-архива.")

# --- БЛОК УПРАВЛЕНИЯ ЗВУКОМ ---
if "play_sound" not in st.session_state:
    st.session_state.play_sound = True  # По умолчанию звук включен

# Кнопка-переключатель звука
if st.session_state.play_sound:
    if st.button("🔊 Уведомления: ВКЛ (Нажмите, чтобы заглушить)"):
        st.session_state.play_sound = False
        st.rerun()
else:
    if st.button("🔇 Уведомления: ВЫКЛ (Нажмите, чтобы включить)"):
        st.session_state.play_sound = True
        st.rerun()
# ------------------------------

# Сверхточный список ключевых слов
FOLDERS = {
    "Мед_Справки": ["выдали", "справк", "справ", "псих", "физ", "спра", "спран"],
    "Лечение": ["вылечили", "вылеч", "лече", "лечи", "таблет","лечеви"],
    "Реанимация": ["реанимировали", "реаним", "реани", "спасение", "спасен"],
    "Вакцинация": ["вакцинировали", "вакцин", "вакци", "привив", "ваки"]
}

uploaded_files = st.file_uploader("Перетащите скриншоты сюда", 
                                  type=["png", "jpg", "jpeg"], 
                                  accept_multiple_files=True)

show_debug = st.checkbox("Показать распознанный текст для папки 'Другое' (для поиска ошибок)")

if uploaded_files:
    if st.button("🚀 Начать точную сортировку"):
        zip_buffer = io.BytesIO()
        progress_bar = st.progress(0)
        status_text = st.empty()
        debug_logs = []
        
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED, allowZip64=True) as zip_file:
            for idx, uploaded_file in enumerate(uploaded_files):
                status_text.text(f"Обработка: {uploaded_file.name} ({idx+1}/{len(uploaded_files)})")
                
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
        
        status_text.text("✅ Сортировка успешно завершена!")
        
        # --- СКРЫТОЕ ПРОИГРЫВАНИЕ СЛУЧАЙНОГО ЗВУКА ---
        if st.session_state.play_sound:
            SOUNDS_DIR = "sounds"
            if os.path.exists(SOUNDS_DIR):
                sound_files = [f for f in os.listdir(SOUNDS_DIR) if f.endswith(('.mp3', '.wav', '.ogg'))]
                if sound_files:
                    random_sound = random.choice(sound_files)
                    sound_path = os.path.join(SOUNDS_DIR, random_sound)
                    
                    # Кодируем аудио в base64 для незаметной вставки в HTML
                    with open(sound_path, "rb") as f:
                        audio_bytes = f.read()
                    audio_base64 = base64.b64encode(audio_bytes).decode()
                    format_ext = random_sound.split('.')[-1]
                    
                    # Встраиваем скрытый аудио-тег с автозапуском
                    audio_html = f"""
                        <audio autoplay style="display:none;">
                            <source src="data:audio/{format_ext};base64,{audio_base64}" type="audio/{format_ext}">
                        </audio>
                    """
                    st.markdown(audio_html, unsafe_allow_html=True)
        # ----------------------------------------------
        
        zip_buffer.seek(0)
        
        st.download_button(
            label="📥 Скачать готовый архив (ZIP)",
            data=zip_buffer.getvalue(),
            file_name="sorted_screenshots.zip",
            mime="application/zip"
        )
        
        if show_debug and debug_logs:
            st.write("---")
            st.subheader("🔍 Анализ нераспознанных файлов:")
            for log in debug_logs:
                st.markdown(log)
