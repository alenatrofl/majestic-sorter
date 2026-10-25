import streamlit as st
import cv2
import numpy as np
import pytesseract
import zipfile
import io
import os

pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'

st.set_page_config(page_title="Majestic RP Сортировщик EMS PRO", page_icon="📸")

st.title("📸 Сортировщик скриншотов Majestic RP (EMS PRO)")
st.write("Загрузите скриншоты, и сайт разложит их по папкам внутри ZIP-архива.")

# Самые надежные маркеры, очищенные от мусора
FOLDERS = {
    "Мед_Справки": ["справк", "справ", "псих", "физ"],
    "Лечение": ["вылеч", "лечен", "лече"],
    "Реанимация": ["реаним", "реани", "спасен", "спасени"],
    "Вакцинация": ["вакцин", "привив", "вакци"]
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
        
        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
            for idx, uploaded_file in enumerate(uploaded_files):
                status_text.text(f"Обработка: {uploaded_file.name} ({idx+1}/{len(uploaded_files)})")
                
                file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
                img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
                
                if img is not None:
                    h, w, _ = img.shape
                    
                    # ИДЕАЛЬНЫЙ СРЕЗ: 
                    # Берём по высоте от 65% до 96% (чтобы не цеплять самый низ экрана)
                    # По ширине строго по центру: от 35% до 65% (полностью отсекаем чат, карту и бинды справа!)
                    crop_center_bottom = img[int(h*0.65):int(h*0.96), int(w*0.35):int(w*0.65)]
                    
                    # Переводим в серое и увеличиваем
                    gray = cv2.cvtColor(crop_center_bottom, cv2.COLOR_BGR2GRAY)
                    gray_large = cv2.resize(gray, (0, 0), fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
                    
                    # Делаем жесткий контраст (белые буквы на чистом черном фоне)
                    _, thresh = cv2.threshold(gray_large, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                    
                    # Распознавание текста
                    custom_config = r'--oem 3 --psm 6'
                    text = pytesseract.image_to_string(thresh, lang='rus+eng', config=custom_config).lower()
                    
                    target_folder = "Другое"
                    for folder, keywords in FOLDERS.items():
                        if any(keyword in text for keyword in keywords):
                            target_folder = folder
                            break
                    
                    if target_folder == "Другое":
                        debug_logs.append(f"**Файл:** {uploaded_file.name} | **Робот прочитал:** `{text.strip()}`")
                    
                    uploaded_file.seek(0)
                    zip_file.writestr(os.path.join(target_folder, uploaded_file.name), uploaded_file.read())
                
                progress_bar.progress((idx + 1) / len(uploaded_files))
        
        status_text.text("✅ Сортировка успешно завершена!")
        
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
