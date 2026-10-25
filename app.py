import streamlit as st
import cv2
import numpy as np
import pytesseract
import zipfile
import io
import os

# Путь к исполняемому файлу Tesseract (оставляем без изменений)
pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'

st.set_page_config(page_title="Majestic RP Сортировщик EMS", page_icon="📸")

st.title("📸 Сортировщик скриншотов Majestic RP (EMS)")
st.write("Загрузите скриншоты, и сайт автоматически разложит их по папкам внутри ZIP-архива.")

# Сверхточный список ключевых слов, ориентированный на всплывающие уведомления
FOLDERS = {
    "Мед_Справки": ["выдали", "справк", "справ", "псих", "физ", "спра", "ъыдали"],
    "Лечение": ["вылечили", "вылеч", "лече", "лечи", "таблет", "табл", "лечеви"],
    "Реанимация": ["реанимировали", "реаним", "реани", "спасение", "спасен", "игрока"],
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
        
        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
            for idx, uploaded_file in enumerate(uploaded_files):
                status_text.text(f"Обработка: {uploaded_file.name} ({idx+1}/{len(uploaded_files)})")
                
                # Читаем файл в память один раз (оптимизация ввода-вывода)
                file_bytes_data = uploaded_file.read()
                file_bytes = np.asarray(bytearray(file_bytes_data), dtype=np.uint8)
                img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
                
                if img is not None:
                    h, w, _ = img.shape
                    
                    # Срез нижней области экрана, где всплывают уведомления плашек
                    crop_center_bottom = img[int(h*0.65):int(h*0.96), int(w*0.35):int(w*0.65)]
                    
                    # Увеличение картинки в 3 раза (чтобы Tesseract лучше видел мелкий шрифт плашек)
                    crop_large = cv2.resize(crop_center_bottom, (0, 0), fx=3.0, fy=3.0, interpolation=cv2.INTER_LINEAR)
                    
                    # Цветовой фильтр: выделяем белый цвет букв. 
                    # Порог снижен до 180, чтобы буквы оставались жирными и читаемыми
                    lower_white = np.array([180, 180, 180], dtype=np.uint8)
                    upper_white = np.array([255, 255, 255], dtype=np.uint8)
                    thresh = cv2.inRange(crop_large, lower_white, upper_white)
                    
                    # Инвертируем маску (делаем текст черным на белом фоне)
                    thresh_inverted = cv2.bitwise_not(thresh)
                    
                    # Настройка Tesseract: 
                    # PSM 7 — читать как одну строку текста (идеально для уведомлений)
                    # Whitelist — разрешаем только русские буквы, цифры, пробел и знаки ID/денег
                    custom_config = (
                        r'--oem 3 --psm 7 '
                        r'-c tessedit_char_whitelist=абвгдеёжзийклмнопрстуфхцчшщъыьэюяАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ0123456789#$ '
                    )
                    
                    # Распознаем строго русский текст, убирая английский «мусор»
                    text = pytesseract.image_to_string(thresh_inverted, lang='rus', config=custom_config).lower()
                    
                    target_folder = "Другое"
                    for folder, keywords in FOLDERS.items():
                        if any(keyword in text for keyword in keywords):
                            target_folder = folder
                            break
                    
                    if target_folder == "Другое":
                        clean_text = " ".join(text.split())
                        debug_logs.append(f"**Файл:** {uploaded_file.name} | **Робот прочитал:** `{clean_text}`")
                    
                    # Сохраняем файл в ZIP архив в соответствующую папку
                    zip_file.writestr(os.path.join(target_folder, uploaded_file.name), file_bytes_data)
                
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
