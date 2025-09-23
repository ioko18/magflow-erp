import random

from locust import HttpUser, tag, task
from locust.user.wait_time import between


class ApiUser(HttpUser):
    wait_time = between(0.5, 2.5)

    def on_start(self):
        # Login and store the token
        response = self.client.post(
            "/auth/login",
            json={"username": "test@example.com", "password": "test123"},
        )
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}

    @tag("products")
    @task(3)
    def list_products(self):
        # Test product listing with search and pagination
        search_terms = ["laptop", "phone", "monitor", "keyboard", ""]
        cursor = None

        # Make initial request
        params = {"q": random.choice(search_terms), "limit": 20}
        if cursor:
            params["cursor"] = cursor

        with self.client.get(
            "/products",
            params=params,
            headers=self.headers,
            name="/products?q=[search]&cursor=[cursor]",
        ) as response:
            if response.status_code == 200:
                data = response.json()
                cursor = data.get("next_cursor")

    @tag("categories")
    @task(2)
    def list_categories(self):
        # Test category pagination
        cursor = None

        with self.client.get(
            "/categories",
            params={"limit": 10, "cursor": cursor},
            headers=self.headers,
            name="/categories?cursor=[cursor]",
        ) as response:
            if response.status_code == 200:
                data = response.json()
                cursor = data.get("next_cursor")

    @tag("auth")
    @task(1)
    def refresh_token(self):
        # Test token refresh
        self.client.post(
            "/auth/refresh",
            headers={"Authorization": f"Bearer {self.token}"},
            name="/auth/refresh",
        )
