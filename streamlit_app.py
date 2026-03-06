import streamlit as st
import pandas as pd
from playwright.sync_api import sync_playwright
import time
import random

# Pagina instellingen
st.set_page_config(page_title="Bol Review Checker", page_icon="🛡️")

st.title("🛡️ Bol.com Review Fraude Scanner")
st.markdown("""
Vul de URL's van de producten in. De tool probeert de reviews op te halen en zoekt naar overlappende namen.
*Let op: Gebruik maximaal 3-5 URL's per keer om blokkades te voorkomen.*
""")

# Inputveld
urls_input = st.text_area("Plak hier de Bol.com URL's (één per regel):", height=150)

if st.button("Start Analyse 🔍"):
    urls = [u.strip() for u in urls_input.split('\n') if u.strip()]
    
    if not urls:
        st.error("Voer aub minimaal één URL in.")
    else:
        results = []
        progress = st.progress(0)
        
        with sync_playwright() as p:
            # Launch browser met stealth instellingen
            browser = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
            
            # Gebruik een realistische User Agent van een normale computer
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                viewport={'width': 1920, 'height': 1080}
            )
            page = context.new_page()

            for idx, url in enumerate(urls):
                st.info(f"Bezig met product {idx+1}: {url[:50]}...")
                try:
                    # Ga naar de pagina en wacht tot de basis geladen is
                    page.goto(url, wait_until="domcontentloaded", timeout=60000)
                    
                    # Menselijke interactie simuleren: even wachten en scrollen
                    time.sleep(random.uniform(3, 6))
                    page.evaluate("window.scrollTo(0, 800)")
                    time.sleep(2)
                    
                    # Haal producttitel op
                    title = page.title().split("|")[0].strip()
                    
                    # Zoek naar de review sectie. Bol laadt deze vaak lui (lazy loading)
                    # We proberen de namen en de verificatie-labels te pakken
                    review_elements = page.query_selector_all('[data-test="review"]')
                    
                    if not review_elements:
                        st.warning(f"Geen reviews zichtbaar voor {title}. Mogelijk blokkeert Bol de toegang of zijn er geen reviews.")
                    
                    for row in review_elements:
                        name_el = row.query_selector('.review__metadata-name')
                        name = name_el.inner_text() if name_el else "Anoniem"
                        
                        ver_el = row.query_selector('text="Geverifieerde aankoop"')
                        is_verified = "✅ JA" if ver_el else "❌ NEE"
                        
                        results.append({
                            "Product": title,
                            "Reviewer": name.strip(),
                            "Geverifieerd": is_verified,
                            "Bron": url
                        })
                except Exception as e:
                    st.error(f"Fout bij ophalen van data: {e}")
                
                progress.progress((idx + 1) / len(urls))
            
            browser.close()

        if results:
            df = pd.DataFrame(results)
            
            # Filter voor de analyse (negeer algemene namen)
            filter_names = ["Anoniem", "Klant", "Bol.com klant", "Een bol.com klant", "Onbekend"]
            suspicious = df[df.duplicated('Reviewer', keep=False) & ~df['Reviewer'].isin(filter_names)]
            
            st.divider()
            
            if not suspicious.empty:
                st.warning(f"⚠️ **Verdachte activiteit gevonden!**")
                st.write("De volgende namen komen bij meerdere producten voor:")
                # We tonen een overzichtelijke tabel van de dubbelingen
                st.table(suspicious.sort_values("Reviewer"))
            else:
                st.success("✅ Geen overlappende reviewers gevonden tussen deze producten.")

            st.subheader("Alle gevonden reviews")
            st.dataframe(df)
            
            # Export functie
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("Download resultaten als CSV", csv, "bol_reviews.csv", "text/csv")
        else:
            st.error("Er is geen data verzameld. Controleer of de URL's correct zijn en probeer het nogmaals.")
