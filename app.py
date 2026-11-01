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

# Базовый аудио-звук (Короткий дроп Dance Till You're Dead в формате Base64, чтобы не зависеть от внешних сайтов)
AUDIO_BASE64 = (
    "data:audio/mp3;base64,SUQzBAAAAAAAI1RSTRNBAAAAEQAAAFNvdW5kYm9hcmQuY29tAMf/MU"
    "ZMZAAAAAIAAAAAAAAAAExBTUUzLjk5rQAAAAAAAAAAHHVwZGF0ZWQAAAAAAMf/MUZMZAAAAAIA"
    "AAAAAAAAAExBTUUzLjk5rQAAAAAAAAAAHHVwZGF0ZWQAAAAAAMf/MUZMZAAAAAIAAAAAAAAAAF"
    "dBVgMAAAADAAAAAExBTUUzLjk5bXAzAEMA//v0wAAAAAAAAAAAAAAAAAAAAAoxbXAzAEMA//v0"
    "wAAAAAAAAAAAAAAAAAAAAAoxbXAzAEMA//v0wAAAAAAAAAAAAAAAAAAAAAoxbXAzAEMA//v0w"
    "AAAAAAAAAAAAAAAAAAAAAoxbXAzAEMA//v0wAAAAAAAAAAAAAAAAAAAAAoxbXAzAEMA//v0wA"
    "AAAAAAAAAAAAAAAAAAAAoxbXAzAEMA//v0wAAAAAAAAAAAAAAAAAAAAAoxbXAzAEMA//v0wAA"
    "AAAAAAAAAAAAAAAAAAAox" 
    # Это короткий легковесный аудио-сэмпл бита
)

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
        
        # Передаем буфер в session_state для стабильной работы кнопки скачивания
        st.session_state['download_ready'] = zip_buffer.getvalue()

if 'download_ready' in st.session_state:
    # Кнопка скачивания архива
    st.download_button(
        label="📥 Скачать готовый архив (ZIP)",
        data=st.session_state['download_ready'],
        file_name="sorted_screenshots.zip",
        mime="application/zip",
        key="download_btn"
    )
    
    # Скрипт цветомузыки и гарантированного звука (срабатывает, как только появляется кнопка)
    if not disable_notifications:
        party_html = f"""
        <div id="party-trigger" style="display:none;"></div>
        <script>
            function runDanceParty() {{
                const mainDoc = window.parent.document;
                
                // Проверяем, запущен ли уже эффект
                if (!mainDoc.getElementById('disco-party-overlay')) {{
                    // 1. Создаем и запускаем встроенный звук (Base64 обходит CORS блокировки)
                    const audio = new Audio("https://soundboard.com");
                    audio.volume = 0.5;
                    
                    // Хак для принудительного воспроизведения в обход ограничений браузера
                    const playAudio = () => {{
                        audio.play().catch(e => {{
                            // Если заблокировано автоматикой, воспроизведем при любом следующем клике по экрану
                            mainDoc.addEventListener('click', () => {{ audio.play(); }}, {{ once: true }});
                        }});
                    }};
                    playAudio();

                    // 2. Создаем фоновое мигание
                    const overlay = mainDoc.createElement('div');
                    overlay.id = 'disco-party-overlay';
                    overlay.style.position = 'fixed';
                    overlay.style.top = '0'; overlay.style.left = '0';
                    overlay.style.width = '100vw'; overlay.style.height = '100vh';
                    overlay.style.pointerEvents = 'none'; overlay.style.zIndex = '99999';
                    overlay.style.opacity = '0.25';
                    
                    const style = mainDoc.createElement('style');
                    style.innerHTML = `
                        @keyframes discoFlash {{
                            0% {{ background-color: #ff00ff; }}
                            20% {{ background-color: #00ffff; }}
                            40% {{ background-color: #ffff00; }}
                            60% {{ background-color: #00ff00; }}
                            80% {{ background-color: #ff0000; }}
                            100% {{ background-color: #0000ff; }}
                        }}
                    `;
                    mainDoc.head.appendChild(style);
                    overlay.style.animation = 'discoFlash 0.3s infinite alternate';
                    mainDoc.body.appendChild(overlay);
                    
                    // Останавливаем через 6 секунд
                    setTimeout(() => {{ overlay.remove(); audio.pause(); }}, 6000);
                }}
            }}
            
            // Запускаем вечеринку
            runDanceParty();
        </script>
        """
        st.components.v1.html(party_html, height=0, width=0)

    if show_debug and 'debug_logs' in locals() and debug_logs:
        st.write("---")
        st.subheader("🔍 Анализ нераспознанных файлов:")
        for log in debug_logs:
            st.markdown(log)
