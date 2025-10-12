#!/usr/bin/env python3
"""
eMAG Marketplace Product Fetcher

Acest script extrage și afișează informații despre produse din contul tău eMAG Marketplace.

Pentru a rula acest script, asigură-te că:
1. IP-ul tău este în whitelist în contul de vânzător eMAG
2. Ai instalat toate dependențele necesare (requests)
"""

import json
from datetime import datetime

import requests

# Configurare
API_URL = "https://marketplace-api.emag.ro/api-3"
CREDENTIALS = {
    "username": "galactronice@yahoo.com",
    "password": "NB1WXDm"  # În producție, folosește variabile de mediu pentru parole
}

# Obține adresa IP publică
def get_public_ip():
    try:
        response = requests.get('https://api.ipify.org?format=json', timeout=5)
        return response.json().get('ip', 'Necunoscut')
    except:
        return 'Nu s-a putut determina'

def get_products(page=1, per_page=5):
    """Extrage produse de la API-ul eMAG"""
    url = f"{API_URL}/product_offer/read"
    data = {"data": {"currentPage": page, "itemsPerPage": per_page}}

    # Afișează informații despre conexiune
    print("\n" + "="*50)
    print("🔍 Încerc să mă conectez la eMAG Marketplace...")
    print(f"🌐 URL API: {url}")
    print(f"👤 Nume utilizator: {CREDENTIALS['username']}")
    print(f"🌍 IP public: {get_public_ip()}")
    print("="*50 + "\n")

    try:
        # Adaugă headere suplimentare pentru a prevenii problemele cu CORS
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }

        # Rulează cererea cu mai multe detalii de depanare
        response = requests.post(
            url,
            auth=(CREDENTIALS["username"], CREDENTIALS["password"]),
            headers=headers,
            json=data,
            timeout=30
        )

        # Afișează răspunsul HTTP
        print(f"📡 Status răspuns: {response.status_code}")
        print(f"🔑 Headere răspuns: {dict(response.headers)}")

        # Încearcă să parsezi răspunsul JSON
        try:
            response_data = response.json()
            print("\n📄 Răspuns API:", json.dumps(response_data, indent=2, ensure_ascii=False, sort_keys=True))

            if response_data.get("isError"):
                error_msg = response_data.get('messages', ['Eroare necunoscută'])
                if isinstance(error_msg, list):
                    error_msg = "; ".join(str(m) for m in error_msg)
                print(f"\n❌ Eroare API: {error_msg}")

                # Sugestii pentru erori specifice
                if "Invalid vendor ip" in str(error_msg):
                    print("\n⚠️  ATENȚIE: IP-ul tău nu este în whitelist!")
                    print("Pentru a rezolva această problemă:")
                    print("1. Intră în contul tău de vânzător eMAG")
                    print("2. Mergi la Setări > Acces API")
                    print(f"3. Adaugă următorul IP în lista de adrese permise: {get_public_ip()}")
                    print("4. Salvează modificările și încearcă din nou")

                return []

        except ValueError as e:
            print(f"❌ Invalid JSON response: {e}")
            print(f"Raw response: {response.text[:500]}...")  # Print first 500 chars of response
            return []

    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response status: {e.response.status_code}")
            print(f"Response content: {e.response.text[:500]}...")
        return []
    except Exception as e:
        print(f"❌ Unexpected error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return []

def get_validation_status(status_code):
    """Returnează descrierea stării de validare"""
    status_mapping = {
        0: "Draft",
        1: "În validare eMAG",
        2: "În așteptarea validării brandului",
        3: "În așteptarea aprobării EAN",
        4: "Documentație în așteptarea validării",
        5: "Brand respins",
        6: "EAN respins",
        8: "Documentație respinsă",
        9: "Documentație aprobată",
        10: "Blocat",
        11: "Actualizare în așteptarea aprobării",
        12: "Actualizare respinsă"
    }
    return status_mapping.get(status_code, f"Status necunoscut ({status_code})")

def display_products(products):
    """Afișează informații detaliate despre produse"""
    for i, product in enumerate(products, 1):
        print(f"\n{'='*60}")
        print(f"📦 PRODUS {i}: {product.get('name')}")
        print(f"{'='*60}")

        # Informații de bază
        print("\n🔹 INFORMATII DE BAZA")
        print(f"  ID: {product.get('id')}")
        print(f"  Brand: {product.get('brand')}")
        print(f"  Cod produs: {product.get('part_number')}")
        print(f"  Categorie ID: {product.get('category_id')}")

        # Stoc și preț
        print("\n💰 PRET SI STOC")
        print(f"  Preț de vânzare: {product.get('sale_price')} {product.get('currency', 'RON')}")
        print(f"  Preț recomandat: {product.get('recommended_price')} {product.get('currency', 'RON')}")
        print(f"  Stoc disponibil: {product.get('general_stock', 0)} bucăți")
        print(f"  Stoc estimat: {product.get('estimated_stock', 0)} bucăți")

        # 1. Statutul ofertei și validare
        print("\n✅ STATUT OFERTA")
        print(f"  Status: {'Activ' if product.get('status') == 1 else 'Inactiv'}")

        # 2. Statusul validării documentației
        validation_status = product.get('validation_status', [{}])[0] if product.get('validation_status') else {}
        print(f"  Status validare: {get_validation_status(validation_status.get('value'))}")
        if validation_status.get('errors'):
            print(f"  Erori validare: {', '.join(validation_status['errors'])}")

        # 3. Statutul traducerii (pentru produsele traduse)
        if 'translation_validation_status' in product:
            trans_status = product['translation_validation_status'][0] if product['translation_validation_status'] else {}
            print(f"  Status traducere: {get_validation_status(trans_status.get('value'))}")

        # 4. Statutul ofertei (vandabil/nu)
        offer_status = product.get('offer_validation_status', {})
        if isinstance(offer_status, list) and offer_status:
            offer_status = offer_status[0]
        print(f"  Statut ofertă: {'Vandabil' if offer_status.get('value') == 1 else 'Nevandabil'}")
        if 'description' in offer_status:
            print(f"  Detalii: {offer_status['description']}")

        # 5. Competiție și prețuri
        print("\n🏆 COMPETITIE")
        print(f"  Număr oferte concurenți: {product.get('number_of_offers', 0)}")
        print(f"  Cel mai bun preț pe eMAG: {product.get('best_offer_sale_price')} {product.get('currency', 'RON')}")

        # 6. Poze și documentație
        print("\n📸 RESURSE")
        print(f"  Imagini disponibile: {len(product.get('images', []))}")
        if product.get('images') and len(product['images']) > 0:
            print(f"  Exemplu imagine: {product['images'][0].get('url', 'N/A')}")

        # 7. Garantie și alte detalii
        print("\nℹ️  ALTE DETALII")
        print(f"  Garantie: {product.get('warranty', 'Nespecificat')} luni")
        print(f"  EAN-uri: {', '.join(product.get('ean', [])) or 'N/A'}")

        # 8. Statistici suplimentare
        if 'genius_eligibility' in product:
            genius_types = {1: 'Full', 2: 'EasyBox', 3: 'HD'}
            genius_type = genius_types.get(product.get('genius_eligibility_type', 0), 'Nespecificat')
            print(f"  Eligibil Genius: {'Da' if product.get('genius_eligibility') == 1 else 'Nu'} ({genius_type})")

        print(f"\n{'='*60}")

def save_to_json(products):
    """Save products to JSON file"""
    filename = f"emag_products_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(products, f, indent=2, ensure_ascii=False)
        print(f"\n✅ Products saved to {filename}")
    except Exception as e:
        print(f"\n❌ Error saving file: {e}")

def main():
    print("🔍 Se preiau produsele din contul eMAG...")
    result = get_products(per_page=5)

    # Verifică dacă am primit un răspuns valid de la API
    if not result or not isinstance(result, list):
        print("❌ Nu s-au putut prelua produsele. Verifică conexiunea la internet sau datele de autentificare.")
        return

    # Afișează numărul de produse găsite
    print(f"\n✅ S-au găsit {len(result)} produse în contul tău eMAG")

    # Afișează fiecare produs în format lizibil
    for i, product in enumerate(result, 1):
        print(f"\n{'='*80}")
        print(f"📦 PRODUS {i}: {product.get('name', 'Necunoscut')}")
        print(f"{'='*80}")

        # Informații de bază
        print("\n🔹 INFORMATII DE BAZA")
        print(f"  ID: {product.get('id', 'N/A')}")
        print(f"  Brand: {product.get('brand', 'N/A')}")
        print(f"  Cod produs: {product.get('part_number', 'N/A')}")
        print(f"  Categorie ID: {product.get('category_id', 'N/A')}")

        # Prețuri și stoc
        print("\n💰 PRETURI SI STOC")
        print(f"  Preț de vânzare: {product.get('sale_price', 'N/A')} {product.get('currency', 'RON')}")
        print(f"  Preț recomandat: {product.get('recommended_price', 'N/A')} {product.get('currency', 'RON')}")
        print(f"  Stoc disponibil: {product.get('general_stock', 0)} bucăți")
        print(f"  Stoc estimat: {product.get('estimated_stock', 0)} bucăți")

        # Statut ofertă
        print("\n✅ STATUT OFERTA")
        print(f"  Status: {'Activ' if product.get('status') == 1 else 'Inactiv'}")

        # Validare documentație
        validation = product.get('validation_status', [{}])[0] if isinstance(product.get('validation_status'), list) else {}
        print(f"  Status validare: {validation.get('description', 'Necunoscut')}")

        # Statut ofertă (vandabil/nevandabil)
        offer_status = product.get('offer_validation_status', {})
        if isinstance(offer_status, list) and offer_status:
            offer_status = offer_status[0]
        print(f"  Statut ofertă: {offer_status.get('description', 'Necunoscut')}")

        # Competiție
        print("\n🏆 COMPETITIE")
        print(f"  Număr oferte concurenți: {product.get('number_of_offers', 0)}")
        print(f"  Cel mai bun preț pe eMAG: {product.get('best_offer_sale_price', 'N/A')} {product.get('currency', 'RON')}")

        # Resurse
        print("\n📸 RESURSE")
        images = product.get('images', [])
        print(f"  Imagini disponibile: {len(images)}")
        if images:
            print(f"  Exemplu imagine: {images[0].get('url', 'N/A')}")

        # Alte detalii
        print("\nℹ️  ALTE DETALII")
        print(f"  Garantie: {product.get('warranty', 'Nespecificat')} luni")
        print(f"  EAN-uri: {', '.join(product.get('ean', [])) or 'N/A'}")

        # Noi câmpuri adăugate
        print("\n🏷️  DETALII SUPLIMENTARE")
        print(f"  Poziție în clasament 'Adaugă în coș': {product.get('buy_button_rank', 'N/A')}")
        print(f"  Număr total vânzători: {product.get('number_of_offers', 0)}")
        print(f"  Prețul cel mai bun pe eMAG: {product.get('best_offer_sale_price', 'N/A')} {product.get('currency', 'RON')}")

        # Detalii Genius
        genius_type = {1: 'Full', 2: 'EasyBox', 3: 'HD'}.get(product.get('genius_eligibility_type', 0), 'Nespecificat')
        print(f"  Eligibilitate Genius: {'Da' if product.get('genius_eligibility') else 'Nu'}{f' ({genius_type})' if product.get('genius_eligibility') else ''}")

        # Drepturi de modificare
        ownership = product.get('ownership')
        print(f"  Drepturi de modificare: {'Da' if ownership == 1 else 'Nu'}")

        # Starea traducerii
        translation_status = product.get('translation_validation_status', [{}])[0] if isinstance(product.get('translation_validation_status'), list) else {}
        print(f"  Stare traducere: {translation_status.get('description', 'Necunoscut')}")

        # Detalii stocare
        handling_time = product.get('handling_time')
        if handling_time and isinstance(handling_time, list) and len(handling_time) > 0:
            print(f"  Timp de procesare: {handling_time[0].get('value', 'N/A')} zile")

    # Salvare în fișier JSON dacă se dorește
    save = input("\n💾 Dorești să salvezi aceste date într-un fișier JSON? (d/n): ").lower()
    if save == 'd':
        save_to_json(result)
        print("✅ Datele au fost salvate cu succes!")

if __name__ == "__main__":
    main()
