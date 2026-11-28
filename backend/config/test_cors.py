from django.test import Client, SimpleTestCase, override_settings


FIRST_ORIGIN = "http://localhost:5173"
SECOND_ORIGIN = "https://nexamind-frontend.example"
REJECTED_ORIGIN = "https://untrusted.example"
TEST_ENDPOINT = "/__cors_test_endpoint__/"


@override_settings(
    ALLOWED_HOSTS=["testserver"],
    CORS_ALLOWED_ORIGINS=[FIRST_ORIGIN, SECOND_ORIGIN],
    CORS_ALLOW_CREDENTIALS=False,
)
class CorsMiddlewareTests(SimpleTestCase):
    def setUp(self):
        self.client = Client()

    def test_all_configured_origins_are_allowed(self):
        for origin in (FIRST_ORIGIN, SECOND_ORIGIN):
            with self.subTest(origin=origin):
                response = self.client.get(
                    TEST_ENDPOINT,
                    HTTP_ORIGIN=origin,
                )

                self.assertEqual(
                    response.headers.get("Access-Control-Allow-Origin"),
                    origin,
                )

    def test_unconfigured_origin_is_rejected(self):
        response = self.client.get(
            TEST_ENDPOINT,
            HTTP_ORIGIN=REJECTED_ORIGIN,
        )

        self.assertNotIn(
            "Access-Control-Allow-Origin",
            response.headers,
        )

    def test_preflight_allows_generation_request_headers(self):
        response = self.client.options(
            TEST_ENDPOINT,
            HTTP_ORIGIN=FIRST_ORIGIN,
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS=(
                "authorization, content-type, idempotency-key"
            ),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers.get("Access-Control-Allow-Origin"),
            FIRST_ORIGIN,
        )

        allowed_headers = {
            header.strip().lower()
            for header in response.headers.get(
                "Access-Control-Allow-Headers",
                "",
            ).split(",")
        }

        for header in ("authorization", "content-type", "idempotency-key"):
            with self.subTest(header=header):
                self.assertIn(header, allowed_headers)

        allowed_methods = {
            method.strip().upper()
            for method in response.headers.get(
                "Access-Control-Allow-Methods",
                "",
            ).split(",")
        }
        self.assertIn("POST", allowed_methods)

    def test_credentials_are_not_enabled(self):
        response = self.client.get(
            TEST_ENDPOINT,
            HTTP_ORIGIN=FIRST_ORIGIN,
        )

        self.assertNotEqual(
            response.headers.get("Access-Control-Allow-Credentials"),
            "true",
        )
