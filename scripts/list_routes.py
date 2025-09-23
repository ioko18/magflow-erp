from app.main import create_app

app = create_app()


def list_routes():
    print("\nRegistered routes:")
    print("-" * 80)
    for route in app.routes:
        if hasattr(route, "path"):
            print(
                f"{route.path} - {route.methods if hasattr(route, 'methods') else 'N/A'}"
            )


if __name__ == "__main__":
    list_routes()
