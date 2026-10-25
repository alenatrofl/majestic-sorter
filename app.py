import streamlit as st
import cv2
import numpy as np
import pytesseract
import zipfile
import io
import os

pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'

st.set_page_config(page_title="Majestic RP Сортировщик", page_icon="📸")

st.title("📸 Сортировщик скриншотов Majestic RP")
st.write("Загрузите скриншоты, и сайт разложит их по папкам внутри ZIP-архива.")

# Максимально гибкие ключевые слова с учетом возможных ошибок чтения букв
FOLDERS = {
    "Лечение": ["вылечил", "вылечи", "лечен", "лече"],
    "Мед_Справки": ["справк", "справку", "о псих", "о физ"],
    "Мед_Карты": ["карт", "медкарт", "мед. карт", "медицинск"],
    "Реанимация": ["реанимир", "реаним", "спасен", "реани"],
    "Вакцинация": ["вакцин", "привив", "вакци"],
    "Другое": []
}

uploaded_files = st.file_uploader("Перетащите скриншоты сюда (можно выбрать сразу много)", 
                                  type=["png", "jpg", "jpeg"], 
                                  accept_multiple_files=True)

if uploaded_files:
    if st.button("🚀 Начать сортировку и собрать архив"):
        zip_buffer = io.BytesIO()
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
            for idx, uploaded_file in enumerate(uploaded_files):
                status_text.text(f"Обработка файла {idx+1} из {len(uploaded_files)}: {uploaded_file.name}")
                
                file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
                img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
                
                if img is not None:
                    h, w, _ = img.shape
                    
                    # Захватываем нижнюю четверть экрана (от 75% до 98% высоты), 
                    # чтобы точно поймать плашки и не зацепить радар/полосу здоровья в самом низу
                    crop_bottom = img[int(h*0.75):int(h*0.98), 0:w]
                    
                    # Улучшаем качество картинки для робота: переводим в черно-белый формат
                    gray = cv2.cvtColor(crop_bottom, cv2.COLOR_BGR2GRAY)
                    
                    # Распознаем текст (ищем и на русском, и на английском)
                    text = pytesseract.image_to_string(gray, lang='rus+eng').lower()
                    
                    target_folder = "Другое"
                    for folder, keywords in FOLDERS.items():
                        if folder == "Другое":
                            continue
                        if any(keyword in text for keyword in keywords):
                            target_folder = folder
                            break
                    
                    archive_path = os.path.join(target_folder, uploaded_file.name)
                    uploaded_file.seek(0)
                    zip_file.writestr(archive_path, uploaded_file.read())
                
                progress_bar.progress((idx + 1) / len(uploaded_files))
        
        status_text.text("✅ Все файлы успешно отсортированы!")
        
        st.download_button(
            label="📥 Скачать готовый архив (ZIP)",
            data=zip_buffer.getvalue(),
            file_name="sorted_screenshots.zip",
            mime="application/zip"
        )
