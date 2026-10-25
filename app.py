import streamlit as st
import cv2
import numpy as np
import pytesseract
import zipfile
import io
import os
import requests
import base64

pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'

st.set_page_config(page_title="Majestic RP Сортировщик Yandex AI", page_icon="📸")

st.title("📸 Сортировщик скриншотов Majestic RP (Yandex AI)")
st.write("Сайт автоматически сортирует скриншоты. Ошибки сканера исправляет искусственный интеллект Яндекса.")

# ВШИТЫЕ ДАННЫЕ ВАШЕГО АККАУНТА YANDEX CLOUD
FOLDER_ID = "b1gup39u1sf9n94ui1fj"
YANDEX_KEY = "AQVN1Sp-chxZjkBxH8PllyCcME4HnH-F1Nj-onX3"

FOLDERS = {
    "Мед_Справки": ["выдали", "справк", "справ", "псих", "физ", "спра"],
    "Лечение": ["вылечили", "вылеч", "лече", "лечи", "таблет", "пе о", "пео"],
    "Реанимация": ["реанимировали", "реаним", "реани", "спасение", "спасен"],
    "Вакцинация": ["вакцинировали", "вакцин", "вакци", "привив"]
}

uploaded_files = st.file_uploader("Перетащите скриншоты сюда", 
                                  type=["png", "jpg", "jpeg"], 
                                  accept_multiple_files=True)

show_debug = st.checkbox("Показать отчет о работе Yandex AI (поможет найти ошибки)")

if uploaded_files:
    if st.button("🚀 Начать умную сортировку"):
        zip_buffer = io.BytesIO()
        progress_bar = st.progress(0)
        status_text = st.empty()
        ai_logs = []
        
        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
            for idx, uploaded_file in enumerate(uploaded_files):
                status_text.text(f"Обработка: {uploaded_file.name} ({idx+1}/{len(uploaded_files)})")
                
                file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
                img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
                
                target_folder = "Другое"
                
                if img is not None:
                    h, w, _ = img.shape
                    
                    # Точный срез центральной нижней части экрана
                    crop_center_bottom = img[int(h*0.65):int(h*0.96), int(w*0.35):int(w*0.65)]
                    gray = cv2.cvtColor(crop_center_bottom, BGR2GRAY)
                    gray_large = cv2.resize(gray, (0, 0), fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
                    _, thresh = cv2.threshold(gray_large, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                    
                    custom_config = r'--oem 3 --psm 6'
                    text = pytesseract.image_to_string(thresh, lang='rus', config=custom_config).lower().strip()
                    
                    # 1. Быстрый поиск по чистым ключам
                    for folder, keywords in FOLDERS.items():
                        if any(keyword in text for keyword in keywords):
                            target_folder = folder
                            break
                    
                    # 2. Подстраховка через Яндекс ИИ, если файл летит в "Другое"
                    if target_folder == "Другое":
                        try:
                            _, encoded_img = cv2.imencode('.jpg', crop_center_bottom)
                            base64_image = base64.b64encode(encoded_img).decode('utf-8')
                            
                            url = "https://yandex.net"
                            headers = {
                                "Content-Type": "application/json",
                                "Authorization": f"Api-Key {YANDEX_KEY}"
                            }
                            body = {
                                "folderId": FOLDER_ID,
                                "analyzeSpecs": [{
                                    "content": base64_image,
                                    "features": [{
                                        "type": "TEXT_DETECTION",
                                        "textDetectionConfig": {
                                            "languageCodes": ["rus", "eng"]
                                        }
                                    }]
                                }]
                            }
                            
                            response = requests.post(url, headers=headers, json=body, timeout=10)
                            result = response.json()
                            
                            # Собираем текст от Яндекса
                            records = result['results']['results']['textDetection']['pages']['blocks']
                            ai_text = ""
                            for block in records:
                                for line in block['lines']:
                                    for word in line['words']:
                                        ai_text += word['text'] + " "
                            
                            ai_text = ai_text.lower().strip()
                            
                            # Проверяем текст Яндекса
                            for folder, keywords in FOLDERS.items():
                                if any(keyword in ai_text for keyword in keywords):
                                    target_folder = folder
                                    ai_logs.append(f"🧠 **Yandex AI спас файл** `{uploaded_file.name}` -> распределил в **{target_folder}**")
                                    break
                                    
                            if target_folder == "Другое":
                                ai_logs.append(f"❌ Яндекс ИИ тоже не смог прочесть текст на `{uploaded_file.name}` (Текст: `{ai_text}`)")
                                
                        except Exception as e:
                            ai_logs.append(f"⚠️ Ошибка ИИ на файле `{uploaded_file.name}`: {str(e)}")
                    
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
        
        if show_debug and ai_logs:
            st.write("---")
            st.subheader("🤖 Отчет искусственного интеллекта Yandex:")
            for log in ai_logs:
                st.markdown(log)
