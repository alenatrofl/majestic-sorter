import streamlit as st
import cv2
import numpy as np
import pytesseract
import zipfile
import io
import os

pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'

st.set_page_config(page_title="Majestic RP Сортировщик PRO", page_icon="📸")

st.title("📸 Сортировщик скриншотов Majestic RP (PRO)")
st.write("Загрузите скриншоты, и сайт разложит их по папкам внутри ZIP-архива.")

# Ультра-гибкие ключи. Ищем даже по обрывкам слов на случай опечаток OCR
FOLDERS = {
    "Лечение": ["вылеч", "лечен", "лече", "здрав", "здоров"],
    "Мед_Справки": ["справк", "справ", "псих", "физ"],
    "Мед_Карты": ["карт", "медкарт", "мед.карт"],
    "Реанимация": ["реаним", "реани", "спасен", "игрок"],
    "Вакцинация": ["вакцин", "привив", "вакци"]
}

uploaded_files = st.file_uploader("Перетащите скриншоты сюда", 
                                  type=["png", "jpg", "jpeg"], 
                                  accept_multiple_files=True)

# Галочка для отладки, если захочется посмотреть, что видит робот
show_debug = st.checkbox("Показать распознанный текст для папки 'Другое' (для поиска ошибок)")

if uploaded_files:
    if st.button("🚀 Начать сортировку"):
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
                    
                    # Берем нижние 30% экрана, чтобы точно поймать плашки, если их вылезло много в ряд
                    crop_bottom = img[int(h*0.70):int(h*0.98), 0:w]
                    
                    # Переводим в серое изображение
                    gray = cv2.cvtColor(crop_bottom, cv2.COLOR_BGR2GRAY)
                    
                    # Увеличиваем размер зоны в 1.5 раза для лучшей читаемости мелкого шрифта
                    gray_large = cv2.resize(gray, (0, 0), fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)
                    
                    # Продвинутый фильтр: делаем текст белым, а фон абсолютно черным (убирает шумы игры)
                    thresh = cv2.threshold(gray_large, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
                    
                    # Читаем текст с тонкой настройкой движка (--psm 6 считает зону как единый блок текста)
                    custom_config = r'--oem 3 --psm 6'
                    text = pytesseract.image_to_string(thresh, lang='rus+eng', config=custom_config).lower()
                    
                    target_folder = "Другое"
                    for folder, keywords in FOLDERS.items():
                        if any(keyword in text for keyword in keywords):
                            target_folder = folder
                            break
                    
                    if target_folder == "Другое":
                        debug_logs.append(f"**Файл:** {uploaded_file.name} | **Робот прочитал:** `{text.strip()}`")
                    
                    # Сохраняем оригинал
                    archive_path = os.path.join(target_folder, uploaded_file.name)
                    uploaded_file.seek(0)
                    zip_file.writestr(archive_path, uploaded_file.read())
                
                progress_bar.progress((idx + 1) / len(uploaded_files))
        
        status_text.text("✅ Сортировка завершена!")
        
        st.download_button(
            label="📥 Скачать готовый архив (ZIP)",
            data=zip_buffer.getvalue(),
            file_name="sorted_screenshots.zip",
            mime="application/zip"
        )
        
        # Выводим логи отладки, если включена галочка
        if show_debug and debug_logs:
            st.write("---")
            st.subheader("🔍 Анализ нераспознанных файлов:")
            for log in debug_logs:
                st.markdown(log)
