#!/usr/bin/env python3
"""
Test script pentru conectivitatea cu API-ul eMAG real.
"""

import asyncio
import os
from dotenv import load_dotenv
from app.services.emag_api_client import EmagApiClient, EmagApiError


async def test_emag_connection():
    """Testează conectivitatea cu API-ul eMAG pentru ambele conturi."""

    # Încarcă variabilele de mediu
    load_dotenv()

    print("🔍 Testez conectivitatea cu API-ul eMAG...")

    # Test MAIN account
    print("\n📱 Testez contul MAIN...")
    main_username = os.getenv("EMAG_MAIN_USERNAME")
    main_password = os.getenv("EMAG_MAIN_PASSWORD")
    main_base_url = os.getenv(
        "EMAG_MAIN_BASE_URL", "https://marketplace-api.emag.ro/api-3"
    )

    print(f"Username MAIN: {main_username}")
    print(f"Base URL: {main_base_url}")

    try:
        async with EmagApiClient(
            username=main_username,
            password=main_password,
            base_url=main_base_url,
            timeout=30,
        ) as client:
            print("✅ Conexiune stabilită cu contul MAIN")

            # Test apel API pentru produse
            print("📦 Încerc să obțin produsele...")
            products_response = await client.get_products(page=1, items_per_page=5)

            print(f"📊 Răspuns API: {type(products_response)}")
            if isinstance(products_response, dict):
                print(f"🔢 Chei disponibile: {list(products_response.keys())}")

                if "results" in products_response:
                    products = products_response["results"]
                    print(f"✅ Găsite {len(products)} produse în contul MAIN")

                    # Afișează primul produs ca exemplu
                    if products:
                        first_product = products[0]
                        print(f"📱 Primul produs: {first_product.get('name', 'N/A')}")
                        print(f"🏷️  SKU: {first_product.get('part_number', 'N/A')}")
                        print(
                            f"💰 Preț: {first_product.get('price', 'N/A')} {first_product.get('currency', 'RON')}"
                        )
                else:
                    print("⚠️  Nu s-au găsit produse în răspuns")
                    print(f"Răspuns complet: {products_response}")

    except EmagApiError as e:
        print(f"❌ Eroare API eMAG MAIN: {e}")
        print(f"Status code: {e.status_code}")
        print(f"Response: {e.response}")
    except Exception as e:
        print(f"❌ Eroare neașteptată MAIN: {e}")

    print("\n" + "=" * 50)

    # Test FBE account
    print("\n🏪 Testez contul FBE...")
    fbe_username = os.getenv("EMAG_FBE_USERNAME")
    fbe_password = os.getenv("EMAG_FBE_PASSWORD")
    fbe_base_url = os.getenv(
        "EMAG_FBE_BASE_URL", "https://marketplace-api.emag.ro/api-3"
    )

    print(f"Username FBE: {fbe_username}")
    print(f"Base URL: {fbe_base_url}")

    try:
        async with EmagApiClient(
            username=fbe_username,
            password=fbe_password,
            base_url=fbe_base_url,
            timeout=30,
        ) as client:
            print("✅ Conexiune stabilită cu contul FBE")

            # Test apel API pentru produse
            print("📦 Încerc să obțin produsele...")
            products_response = await client.get_products(page=1, items_per_page=5)

            print(f"📊 Răspuns API: {type(products_response)}")
            if isinstance(products_response, dict):
                print(f"🔢 Chei disponibile: {list(products_response.keys())}")

                if "results" in products_response:
                    products = products_response["results"]
                    print(f"✅ Găsite {len(products)} produse în contul FBE")

                    # Afișează primul produs ca exemplu
                    if products:
                        first_product = products[0]
                        print(f"📱 Primul produs: {first_product.get('name', 'N/A')}")
                        print(f"🏷️  SKU: {first_product.get('part_number', 'N/A')}")
                        print(
                            f"💰 Preț: {first_product.get('price', 'N/A')} {first_product.get('currency', 'RON')}"
                        )
                else:
                    print("⚠️  Nu s-au găsit produse în răspuns")
                    print(f"Răspuns complet: {products_response}")

    except EmagApiError as e:
        print(f"❌ Eroare API eMAG FBE: {e}")
        print(f"Status code: {e.status_code}")
        print(f"Response: {e.response}")
    except Exception as e:
        print(f"❌ Eroare neașteptată FBE: {e}")


if __name__ == "__main__":
    asyncio.run(test_emag_connection())
