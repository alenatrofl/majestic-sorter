import streamlit as st
import cv2
import numpy as np
import pytesseract
import zipfile
import io
import os

# Настройка Tesseract для Linux/Docker
if os.path.exists('/usr/bin/tesseract'):
    pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'

st.set_page_config(page_title="Majestic RP Сортировщик EMS", page_icon="📸")

st.title("📸 Сортировщик скриншотов Majestic RP (EMS)")
st.write("Загрузите скриншоты, и сайт автоматически разложит их по папкам внутри ZIP-архива.")

# Переключатель уведомлений в сайдбаре
disable_notifications = st.sidebar.checkbox("Отключить уведомления и эффекты", value=False)

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
        zip_buffer.seek(0)
        
        # --- Полностью скрытые эффекты через JavaScript ---
        if not disable_notifications:
            audio_source = "https://soundboard.com"
            
            disco_js_html = f"""
            <script>
                function startDanceParty() {{
                    const mainDoc = window.parent.document;
                    
                    // 1. Создаем фоновую светомузыку
                    if (!mainDoc.getElementById('disco-party-overlay')) {{
                        const overlay = mainDoc.createElement('div');
                        overlay.id = 'disco-party-overlay';
                        overlay.style.position = 'fixed';
                        overlay.style.top = '0';
                        overlay.style.left = '0';
                        overlay.style.width = '100vw';
                        overlay.style.height = '100vh';
                        overlay.style.pointerEvents = 'none';
                        overlay.style.zIndex = '99999';
                        overlay.style.opacity = '0.22';
                        
                        const style = mainDoc.createElement('style');
                        style.innerHTML = `
                            @keyframes discoFlash {{
                                0% {{ background-color: #ff00ff; }}
                                25% {{ background-color: #00ffff; }}
                                50% {{ background-color: #ffff00; }}
                                75% {{ background-color: #00ff00; }}
                                100% {{ background-color: #ff0000; }}
                            }}
                        `;
                        mainDoc.head.appendChild(style);
                        overlay.style.animation = 'discoFlash 0.35s infinite alternate';
                        mainDoc.body.appendChild(overlay);
                        
                        // Удаляем мигание через 8 секунд
                        setTimeout(() => {{ overlay.remove(); }}, 8000);
                    }}
                    
                    // 2. Создаем и запускаем скрытый аудиопоток
                    const audio = new Audio('{audio_source}');
                    audio.volume = 0.4;
                    audio.play().catch(err => console.log("Браузер заблокировал звук:", err));
                }}
                
                startDanceParty();
            </script>
            """
            # Компактный вызов без отображения каких-либо элементов интерфейса
            st.components.v1.html(disco_js_html, height=0, width=0)
            st.toast("🎉 Сортировка окончена! ТАНЦУЮТ ВСЕ!", icon="🕺")
        
        # Кнопка скачивания архива
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
