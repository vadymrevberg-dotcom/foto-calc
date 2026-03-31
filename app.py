import streamlit as st
import requests

def send_telegram(message):
    try:
        token = st.secrets["TELEGRAM_TOKEN"]
        chat_id = st.secrets["TELEGRAM_CHAT_ID"]
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
        requests.post(url, json=payload)
    except Exception as e:
        st.error(f"Błąd konfiguracji powiadomień: {e}")

# --- ЛОГИЧЕСКОЕ ЯДРО ---
def calculate_oze_system(power_kwp, inverter, roof_type, battery_option, panel_type):
    # Базовые константы (до получения прайсов от ENKAM)
    BASE_FIXED_COST = 9100  
    VARIABLE_PRICE_PER_KWP = 2200 
    
    # Модификаторы сложности крыши (оценочные нетто PLN)
    ROOF_MODIFIERS = {
        "Blachodachówka": 0,
        "Blacha trapezowa": 0,
        "Dachówka zakładkowa betonowa lub ceramiczna": 500,
        "Dachówka płaska betonowa lub ceramiczna": 800,
        "Dachówka karpiówka": 1078,
        "Papa lub gont bitumiczny": 1200,
        "Dach płaski kryty papą lub membraną": 1500,
        "Instalacja na gruncie": 2000
    }
    
    # Цены на батареи (нетто PLN)
    BATTERY_PRICES = {
        "Bez magazynu": 0,
        "Eitai 10,2 kWh": 6550,
        "Eitai 16 kWh": 9800,
        "Eitai 20,4 kWh": 12500,
        "Eitai 32 kWh": 18500
    }
    
    # Наценка за бренд инвертора
    inverter_premium = 800 if "FoxESS" in inverter else 0
    
    # Наценка за мощность панелей
    panel_premium = 300 if "540 W" in panel_type else 0

    EMS_COST = 2050 if battery_option != "Bez magazynu" else 0
    
    # Расчет PV
    pv_netto = BASE_FIXED_COST + (power_kwp * VARIABLE_PRICE_PER_KWP)
    pv_netto += ROOF_MODIFIERS.get(roof_type, 0)
    pv_netto += inverter_premium + panel_premium
    
    # Скидка за комплексную установку
    bundle_discount = 600 if battery_option != "Bez magazynu" else 0
    
    battery_netto = BATTERY_PRICES.get(battery_option, 0) + EMS_COST
    total_netto = (pv_netto + battery_netto) - bundle_discount
    
    vat_multiplier = 1.08 # VAT 8%
    
    return {
        "pv_brutto": round(pv_netto * vat_multiplier),
        "battery_brutto": round(battery_netto * vat_multiplier),
        "grand_total": round(total_netto * vat_multiplier),
        "tax_relief": round((total_netto * vat_multiplier) * 0.12)
    }

# --- ИНТЕРФЕЙС ---
st.set_page_config(page_title="ENKAM Wycena", layout="centered")

st.markdown("## Wycena Instalacji OZE")
st.markdown("Wypełnij poniższe parametry, aby wygenerować ofertę.")

# Создаем форму. Интерфейс не обновится, пока не будет нажата кнопка submit.
with st.form("calc_form"):
    
    power = st.slider("Moc instalacji fotowoltaicznej (kWp):", min_value=3.0, max_value=20.0, value=5.0, step=0.1)
    
    inverter = st.selectbox("Marka i rodzaj falownika:", [
        "Deye - dobra cena za solidną jakość", 
        "FoxESS - zaawansowane funkcje i niezawodność"
    ])
    
    battery = st.selectbox("Magazyn energii:", [
        "Bez magazynu", 
        "Eitai 10,2 kWh", 
        "Eitai 16 kWh", 
        "Eitai 20,4 kWh", 
        "Eitai 32 kWh"
    ])
    
    panel = st.radio("Typ panela fotowoltaicznego:", [
        "Longi Solar 510 W", 
        "Longi Solar 540 W"
    ])
    
    roof = st.selectbox("Rodzaj pokrycia dachu:", [
        "Blachodachówka",
        "Dachówka zakładkowa betonowa lub ceramiczna",
        "Dachówka płaska betonowa lub ceramiczna",
        "Dachówka karpiówka",
        "Blacha trapezowa",
        "Papa lub gont bitumiczny",
        "Dach płaski kryty papą lub membraną",
        "Instalacja na gruncie"
    ])
    
    # Кнопка отправки формы
    submitted = st.form_submit_button("GENERUJ WYCENĘ", type="primary", use_container_width=True)

# Логика отображения результатов ТОЛЬКО после нажатия кнопки
if submitted:
    results = calculate_oze_system(power, inverter, roof, battery, panel)
    
    st.markdown("---")
    st.markdown("### Podsumowanie Oferty (ceny brutto, z VAT 8%):")
    
    st.write(f"**Cena Instalacji Fotowoltaicznej {power} kWp:** {results['pv_brutto']:,} zł".replace(',', ' '))
    
    if results['battery_brutto'] > 0:
        st.write(f"**Cena Magazynu Energii z systemem EMS:** {results['battery_brutto']:,} zł".replace(',', ' '))
        
    st.markdown(f"#### Razem Instalacja (brutto, z VAT 8%): {results['grand_total']:,} zł".replace(',', ' '))
    
    st.markdown("### Korzyści z Dostępnych Ulg:")
    st.write(f"**Ulga Termomodernizacyjna (dla podatku 12%):** -{results['tax_relief']:,} zł".replace(',', ' '))
    st.success(f"**Koszt końcowy po Ulgach: {results['grand_total'] - results['tax_relief']:,} zł**".replace(',', ' '))
    report = f"""
🚀 *Новый лид из калькулятора!*

📊 *Конфигурация:*
- Мощность: {power} kWp
- Инвертор: {inverter}
- Панели: {panel}
- Крыша: {roof}
- АКБ: {battery}

💰 *Стоимость:*
- Итого: **{results['grand_total']} PLN** (Brutto)
- Ульга: {results['tax_relief']} PLN
    """
    
    send_telegram(report)
    
    st.markdown("### Co Otrzymujesz:")
    st.markdown(f"""
    * Panele fotowoltaiczne: **{panel}** dopasowane do mocy **{power} kWp**.
    * Falownik: **{inverter.split(' - ')[0]}**.
    * Magazyn Energii: **{battery}**.
    * Konstrukcja montażowa dedykowana do: **{roof.lower()}**.
    * Komplet okablowania, zabezpieczeń i elementów uziemienia.
    """)
