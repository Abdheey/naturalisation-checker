import streamlit as st
import requests
from bs4 import BeautifulSoup
import pdfplumber
import pytesseract
from PIL import Image
import io
from fuzzywuzzy import fuzz
from pdf2image import convert_from_bytes

pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"

PDF_BASE_URL = "https://www.legifrance.gouv.fr"

def normaliser_nom(nom):
    return nom.upper().replace("É", "E").replace("È", "E").replace("À", "A")

def chercher_personne(nom, prenom, texte):
    nom = normaliser_nom(nom)
    prenom = normaliser_nom(prenom)
    lignes = texte.split("\n")
    for ligne in lignes:
        if fuzz.partial_ratio(nom, ligne.upper()) > 90 and fuzz.partial_ratio(prenom, ligne.upper()) > 80:
            return ligne
    return None

def extraire_texte_pdf(url):
    r = requests.get(url)
    with pdfplumber.open(io.BytesIO(r.content)) as pdf:
        texte = ""
        for page in pdf.pages:
            texte += page.extract_text() or ""
    return texte

def ocr_pdf(url):
    r = requests.get(url)
    pages = convert_from_bytes(r.content)
    texte = ""
    for img in pages:
        texte += pytesseract.image_to_string(img)
    return texte

def chercher_jo_naturalisation_urls(annee):
    base_url = f"https://www.legifrance.gouv.fr/jorf/jorf-{annee}"
    urls = []
    try:
        r = requests.get(base_url)
        soup = BeautifulSoup(r.text, "html.parser")
        for lien in soup.find_all("a", href=True):
            if "naturalisation" in lien.text.lower() or "décret" in lien.text.lower():
                urls.append(PDF_BASE_URL + lien['href'])
    except:
        pass
    return urls

def verifier(nom, prenom, annee):
    urls = chercher_jo_naturalisation_urls(annee)
    for url in urls:
        try:
            texte = extraire_texte_pdf(url)
            if not texte.strip():
                texte = ocr_pdf(url)
        except:
            continue
        resultat = chercher_personne(nom, prenom, texte)
        if resultat:
            return True, resultat, url
    return False, "", ""

# -------------------- STREAMLIT APP --------------------

st.set_page_config(page_title="Vérification de naturalisation 🇫🇷")

st.title("🔎 Vérification de naturalisation (JO)")

with st.form("verif_form"):
    nom = st.text_input("Nom (ex: Dupont)").strip()
    prenom = st.text_input("Prénom (ex: Jean)").strip()
    annee = st.selectbox("Année de publication", [2025, 2024, 2023, 2022, 2021, 2020])
    submitted = st.form_submit_button("Vérifier")

if submitted:
    if not nom or not prenom:
        st.warning("Veuillez entrer un nom et un prénom.")
    else:
        with st.spinner("Recherche en cours dans le Journal Officiel..."):
            trouve, ligne, url = verifier(nom, prenom, annee)
        if trouve:
            st.success("✅ Personne trouvée dans un décret de naturalisation !")
            st.markdown(f"**Extrait trouvé :**\n```\n{ligne}\n```")
            st.markdown(f"[📄 Voir le Journal Officiel]({url})")
        else:
            st.error("❌ Personne non trouvée dans les documents analysés.")
