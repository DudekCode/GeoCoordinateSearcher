# Importy wbudowane
import re
import time
from io import BytesIO
# Importy zewnętrzne
import streamlit as st
import pandas as pd
import pydeck as pdk
import folium
from streamlit.components.v1 import html
# Selenium do automatyzacji przeglądarki
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# === FUNKCJE ===
def get_google_maps_link(address):
    """ Pobiera link do Google Maps na podstawie wpisanego adresu oraz wyciąga poprawny adres wyszukany przez Google Maps. """
    service = Service(ChromeDriverManager().install())
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # Uruchomienie w tle (bez okna)
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(service=service, options=options)

    try:
        driver.get("https://www.google.com/maps")
        wait = WebDriverWait(driver, 7)

        # Akceptacja cookies (jeśli się pojawi)
        try:
            accept_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//span[text()="Zaakceptuj wszystko"]')))
            accept_button.click()
            time.sleep(random.uniform(2, 5)) 
        except Exception:
            pass  # Jeśli nie ma przycisku, idziemy dalej

        # Wpisanie adresu w pole wyszukiwania
        search_box = wait.until(EC.element_to_be_clickable((By.ID, "searchboxinput")))
        search_box.clear()
        search_box.send_keys(address)
        search_box.send_keys(Keys.RETURN)

        time.sleep(5)  # Czekamy na załadowanie wyników

        # Pobieranie linku do mapy
        map_link = driver.current_url

        # Wyciąganie adresu z wyników wyszukiwania (element <span class="DkEaL">)
        try:
            address_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'span.DkEaL')))
            search_name = address_element.text

            # Sprawdzanie, czy wynik jest zbyt ogólny
            if "Warszawa" in search_name or "dzielnica" in search_name or len(search_name.split(',')) > 2:
                search_name = "Nazwa jest zbyt ogólna, aby jednoznacznie zidentyfikować lokalizację."
        except Exception:
            search_name = "Brak dokładnego adresu"

    except Exception as e:
        map_link = f"Błąd: {e}"
        search_name = "Błąd przy wyszukiwaniu"

    finally:
        driver.quit()

    return map_link, search_name

def extract_coordinates(map_link):
    """ Wyciąga współrzędne geograficzne z linku Google Maps. """
    match = re.search(r'@([-0-9.]+),([-0-9.]+)', map_link)
    if match:
        return float(match.group(1)), float(match.group(2))
    return None, None

def is_valid_address(address):
    """ Sprawdza, czy adres zawiera przynajmniej jedną literę (aby uniknąć wpisywania samych cyfr). """
    return bool(re.search(r'[a-zA-ZąćęłńóśźżĄĆĘŁŃÓŚŹŻ]', address))

# Funkcja do tworzenia mapy Folium z czerwonymi znacznikami
def create_folium_map(locations):
    # Tworzenie mapy na współrzędnych środkowych
    m = folium.Map(location=[locations[0]['lat'], locations[0]['lon']], zoom_start=12)   
    # Dodawanie markerów na mapie z czerwonym kolorem
    for loc in locations:
        folium.Marker(
            [loc['lat'], loc['lon']],
            popup=loc.get('address', 'Brak adresu'),
            icon=folium.Icon(color='red') 
        ).add_to(m)   
    # Zwracanie mapy jako obiekt HTML
    return m._repr_html_()



# === STREAMLIT UI ===
# Dodanie grafiki i znaku

st.image("impel.jpg", use_container_width=True)
st.markdown(
    """
    <div style="text-align: center; font-size: 8px; margin-bottom: 10px;">
        <p>© Impel Group. Wszystkie prawa zastrzeżone.</p>
    </div>
    """, unsafe_allow_html=True
)

st.markdown(
    "<h1 style='text-align: center; color: currentColor;'>🌍 Wyszukiwarka współrzędnych geograficznych</h1>",
    unsafe_allow_html=True)

# Nagłówek h5
st.markdown('<h5 style="text-align: center; color: currentColor;">🡇 Wpisz adresy poniżej (każdy adres musi być w osobnej linijce) 🡇</h5>', unsafe_allow_html=True)

st.markdown(
    """
    <style>
        /* Stylizacja dla textarea w Streamlit */
        .stTextArea textarea {
            background-color: #fcfcfc !important; /* Jasnoszare tło */
            color: solid #000000 !important;  /* Czarny tekst */
            border-radius: 10px;  /* Zaokrąglenie rogów */
            border: 2px solid #6f6f6f;  /* Szara ramka */
            padding: 10px;  /* Dodatkowy padding */
            font-size: 16px;  /* Większy rozmiar czcionki */
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);  /* Lekki cień */
            resize: vertical;  /* Tylko pionowa możliwość zmiany rozmiaru */
            caret-color: black;  /* Kolor kursora */
        }

        /* Stylizacja placeholdera */
        .stTextArea textarea::placeholder {
            color: #6f6f6f !important; /* Szary placeholder */
            opacity: 1; /* Upewnij się, że jest widoczny */
        }
    </style>
    """, unsafe_allow_html=True
)


# Pole do wpisywania adresów
addresses_input = st.text_area("**ADRESY:**", placeholder="Wpisz adresy tutaj, jeden pod drugim...")

# Lista na dane do tabeli
table_data = []

# Sprawdzenie poprawności wpisanych adresów
valid_addresses = []
invalid_addresses = []

if addresses_input.strip():
    addresses = addresses_input.strip().split("\n")
    for address in addresses:
        if is_valid_address(address):
            valid_addresses.append(address)
        else:
            invalid_addresses.append(address)

# Wyświetlenie ostrzeżenia, jeśli są nieprawidłowe adresy
if invalid_addresses:
    st.warning(f"🚨 Poniższe adresy są niepoprawne (muszą zawierać przynajmniej jedną literę):\n\n{', '.join(invalid_addresses)} 🚨")

# Lista do przechowywania współrzędnych
locations = []

# Przycisk "Szukaj" ze stylizacją
st.markdown(
    """
    <style>
        /* Styl podstawowy dla przycisku */
        .stButton > button {
            color: black !important;
            background-color: #f0f0f0 !important; /* Szare tło */
            border: 2px solid #6f6f6f !important; /* Szara ramka */
            border-radius: 10px !important;  /* Zaokrąglenie rogów */
            box-sizing: border-box !important;
            cursor: pointer !important;
            text-transform: uppercase !important; /* Wielkie litery */
            transition: all 0.3s ease-in-out !important;
            user-select: none !important; /* Zapobiega zaznaczaniu tekstu */
        }
        /* Efekt hover (najechanie kursorem) */
        .stButton > button:hover {
            background-color: #d0d0d0 !important; /* Ciemniejszy szary po najechaniu */
            border-color: #333 !important; /* Ciemniejsza ramka */
        }     
        /* Efekt focus (zaznaczenie przycisku) */
        .stButton > button:focus {
            box-shadow: 0 0 5px 2px rgba(51, 51, 51, 0.6) !important;
            outline: none !important;
        }
        /* Efekt active (kliknięcie) */
        .stButton > button:active {
            border: 2px solid red  !important; /* Szara ramka */
            transform: scale(0.95) !important; /* Minimalne zmniejszenie przy kliknięciu */
        }
    </style>
    """,
    unsafe_allow_html=True
)


# Przycisk "Szukaj" jest aktywowany tylko, gdy są poprawne adresy
if valid_addresses:
    # Tworzymy układ z przyciskiem i miejscem na napis
    col1, col2 = st.columns([1, 5])

    with col1:
        # Kliknięcie "SZUKAJ" resetuje dane
        if st.button("SZUKAJ"):
            st.session_state['search_triggered'] = True
            st.session_state['data_processed'] = False  # Flaga przetworzenia danych

    # Dodanie miejsca na migający napis obok przycisku
    with col2:
        placeholder = st.empty()

    # Przetwarzanie danych tylko po kliknięciu "SZUKAJ"
    if st.session_state.get('search_triggered', False) and not st.session_state.get('data_processed', False):
        # Migający napis "Przetwarzanie danych..."
        for i in range(10):
            color = 'red' if i % 2 == 0 else 'black'
            placeholder.markdown(f"<p style='color: {color}; font-weight: bold;'>🔄 Przetwarzanie danych...</p>", unsafe_allow_html=True)
            time.sleep(1)
        placeholder.empty()

        # Czyścimy poprzednie wyniki
        st.session_state.results = []

        # Liczba adresów do przetworzenia
        total_addresses = len(valid_addresses)

        # Przetwarzanie danych
        table_data = []
        locations = []

        for index, address in enumerate(valid_addresses, start=1):
            result_link, search_name = get_google_maps_link(address)
            latitude, longitude = extract_coordinates(result_link)

            # Dodanie do tabeli
            if latitude and longitude:
                table_data.append({
                    "Adres": address,
                    "Wyszukany adres": search_name,
                    "Latitude": latitude,
                    "Longitude": longitude,
                    "Link": result_link
                })

                # Dodajemy do mapy
                locations.append({'lat': latitude, 'lon': longitude, 'address': search_name})  

            else:
                st.warning("❌ Nie udało się znaleźć współrzędnych.")

        # ✅ Usuwamy napis "Przetwarzanie danych..."
        placeholder.empty()

        # Zapisujemy dane w sesji, by nie znikały po pobraniu
        st.session_state['table_data'] = table_data
        st.session_state['locations'] = locations
        st.session_state['data_processed'] = True

    # ✅ Wyświetlamy tabelę tylko jeśli są dane
    if st.session_state.get('data_processed', False):
        table_data = st.session_state['table_data']
        locations = st.session_state['locations']

        if table_data:
            df_table = pd.DataFrame(table_data)

            # Ustawienie precyzji na 8 miejsc po przecinku
            df_table["Latitude"] = df_table["Latitude"].astype(float).map('{:.8f}'.format)
            df_table["Longitude"] = df_table["Longitude"].astype(float).map('{:.8f}'.format)

            # Wyświetlenie tabeli
            st.markdown("<h4 style='text-align: left; border-bottom: 2px solid #6f6f6f; padding-bottom: 5px;'>📋 Tabela z wynikami (można skopiować lub pobrać jako Excel)</h4>", unsafe_allow_html=True)
            st.data_editor(df_table, hide_index=True, width=1000)

            # 📥 Dodanie przycisku pobrania pliku Excel
            output = BytesIO()
            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                df_table.to_excel(writer, sheet_name="Wspolrzedne_geograficzne", index=False)
            output.seek(0)

            st.markdown("""
            <style>
            /* Styl podstawowy dla przycisku */
            .stDownloadButton > button {
                color: black !important;
                background-color: #f0f0f0 !important; /* Szare tło */
                border: 2px solid #6f6f6f !important; /* Szara ramka */
                border-radius: 10px !important;  /* Zaokrąglenie rogów */
                box-sizing: border-box !important;
                cursor: pointer !important;
            }
            </style>
        """, unsafe_allow_html=True)
            
            # Przycisk pobrania Excela (bez resetu danych)
            st.download_button(
                label="📥 Pobierz plik Excel",
                data=output,
                file_name="Wspolrzedne_geograficzne.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="excel_download"
            )

        # ✅ Wyświetlamy mapę jako drugą
        if locations:
            st.markdown("<h4 style='text-align: left; border-bottom: 2px solid #6f6f6f; padding-bottom: 5px;'>🗺️ Mapa z zaznaczonymi punktami:</h4>", unsafe_allow_html=True)
            map_html = create_folium_map(locations)
            html(map_html, height=500)

        # ✅ Na końcu wyświetlamy szczegółowe wyniki (przywrócona oryginalna struktura)
        if table_data:
            st.markdown("<h4 style='text-align: left; border-bottom: 2px solid #6f6f6f; padding-bottom: 5px;'>📊 Wyniki:</h4>", unsafe_allow_html=True)

            for record in table_data:
                st.markdown(
                    f"""
                    <div style="display: flex; gap: 20px; align-items: center; margin-bottom: 5px;">
                        <p style="font-size: 14px; font-weight: bold; margin: 0;">🗺️ Adres: {record['Adres']}</p>
                        <p style="font-size: 14px; font-weight: bold; margin: 0;">🔎 Wyszukany adres: {record['Wyszukany adres']}</p>
                    </div>
                    <div style="display: flex; gap: 20px; margin-top: 5px; align-items: center;">
                        <p style="font-size: 14px; font-weight: bold; margin: 0;">
                            🌍 Link: <a href="{record['Link']}" target="_blank">Google Maps</a>
                        </p>
                        <p style="font-size: 14px; font-weight: bold; margin: 0; margin-left: 20px;">📍 {record['Latitude']}, {record['Longitude']}</p>
                    </div>
                    <hr style="border: 1px solid #6f6f6f; margin: 10px 0;">
                    """,
                    unsafe_allow_html=True
                )


else:
    st.button("Szukaj", disabled=True)













