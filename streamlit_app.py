import streamlit as st
import pandas as pd
from playwright.sync_api import sync_playwright
import time

# Pagina instellingen
st.set_page_config(page_title="Bol Review Checker", page_icon="🛡️")

st.title("🛡️ Bol.com Review Fraude Scanner")
st.markdown("""
Vul hieronder de URL's in van de producten die je wilt vergelijken. 
De tool zoekt naar **dezelfde namen** die bij verschillende producten van deze verkoper terugkomen.
""")

# Inputveld
urls_input = st.text_area("Plak hier de Bol.com URL's (één per regel):", placeholder="https://www.bol.com/nl/nl/p/...")

if st.button("Start Analyse 🔍"):
    urls = [u.strip() for u in urls_input.split('\n') if u.strip()]
    
    if not urls:
        st.error(" Voer aub minimaal één URL in.")
    else:
        results = []
        progress = st.progress(0)
        
        with sync_playwright() as p:
            # We gebruiken een 'stealth' instelling om minder op te vallen
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
            page = context.new_page()

            for idx, url in enumerate(urls):
                st.info(f"Bezig met ophalen van product {idx+1}...")
                try:
                    page.goto(url, wait_until="domcontentloaded")
                    time.sleep(2) # Menselijke vertraging
                    
                    # Haal producttitel op
                    title = page.title().split("|")[0]
                    
                    # Zoek review blokken
                    review_elements = page.query_selector_all('[data-test="review"]')
                    
                    for row in review_elements:
                        name_el = row.query_selector('.review__metadata-name')
                        name = name_el.inner_text() if name_el else "Anoniem"
                        
                        ver_el = row.query_selector('text="Geverifieerde aankoop"')
                        is_verified = "JA" if ver_el else "NEE"
                        
                        results.append({
                            "Product": title.strip(),
                            "Reviewer": name.strip(),
                            "Geverifieerd": is_verified,
                            "Bron": url
                        })
                except Exception as e:
                    st.error(f"Fout bij {url}: {e}")
                
                progress.progress((idx + 1) / len(urls))
            
            browser.close()

        if results:
            df = pd.DataFrame(results)
            
            # Analyse: Zoek dubbele namen (exclusief 'Anoniem' of 'Klant')
            filter_names = ["Anoniem", "Klant", "Bol.com klant", "Een bol.com klant"]
            suspicious = df[df.duplicated('Reviewer', keep=False) & ~df['Reviewer'].isin(filter_names)]
            
            st.divider()
            
            if not suspicious.empty:
                st.warning(f"⚠️ **Verdachte activiteit gevonden!** Er zijn {len(suspicious['Reviewer'].unique())} personen die reviews hebben achtergelaten op meerdere van deze producten.")
                st.subheader("Overzicht van overlappende reviewers:")
                st.dataframe(suspicious.sort_values("Reviewer"))
            else:
                st.success("✅ Geen overlappende reviewers gevonden in deze selectie.")

            st.subheader("Alle verzamelde data")
            st.dataframe(df)
