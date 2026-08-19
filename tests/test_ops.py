"""
Operational-reliability regressions.

These cover the failure modes that let a real production outage stay invisible:
a container that started happily while every database query failed, and API
paths that returned HTTP 200 HTML instead of an error.
"""
from unittest.mock import patch

from django.test import TestCase, override_settings


@override_settings(ALLOWED_HOSTS=["*"])
class HealthCheckTests(TestCase):
    def test_health_ok_when_database_reachable(self):
        r = self.client.get("/health/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "ok")
        self.assertEqual(r.json()["checks"]["database"], "ok")

    def test_health_reports_degraded_when_database_down(self):
        """A dead database must fail the health check, not pass silently."""
        with patch("django.db.connection.cursor", side_effect=Exception("boom")):
            r = self.client.get("/health/")
        self.assertEqual(r.status_code, 503)
        self.assertEqual(r.json()["status"], "degraded")

    def test_health_never_leaks_connection_details(self):
        with patch("django.db.connection.cursor",
                   side_effect=Exception("password=hunter2 host=db.internal")):
            body = self.client.get("/health/").content.decode()
        self.assertNotIn("hunter2", body)
        self.assertNotIn("db.internal", body)


@override_settings(ALLOWED_HOSTS=["*"])
class ApiRoutingTests(TestCase):
    """Unmatched /api/ paths must 404 — never fall through to the SPA.

    Returning index.html with HTTP 200 for a non-existent endpoint made a
    broken backend look healthy and defeated ordinary uptime checking.
    """

    def test_unknown_api_path_returns_404(self):
        r = self.client.get("/api/definitely-not-a-real-endpoint/")
        self.assertEqual(r.status_code, 404)

    def test_unknown_api_path_does_not_return_spa_html(self):
        r = self.client.get("/api/definitely-not-a-real-endpoint/")
        self.assertNotIn(b"<div id=\"root\">", r.content)

    def test_real_api_endpoint_still_works(self):
        self.assertEqual(self.client.get("/api/features/").status_code, 200)

    def test_frontend_routes_still_serve_the_spa(self):
        for path in ("/", "/feed", "/track/abc123"):
            self.assertEqual(self.client.get(path).status_code, 200,
                             f"SPA route {path} broke")
