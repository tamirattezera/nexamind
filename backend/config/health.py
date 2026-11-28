from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.db import connection
from django.http import JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def live(request):
    """Report whether the Django application process can respond."""
    return JsonResponse({"status": "ok"})


@require_GET
def ready(request):
    """Report whether the database and configured cache are reachable."""
    try:
        with transaction.atomic(using="default"):
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT set_config('statement_timeout', %s, true)",
                    [f"{settings.HEALTH_CHECK_DB_STATEMENT_TIMEOUT_MS}ms"],
                )
                cursor.execute("SELECT 1")
                cursor.fetchone()

        cache.get("nexamind:health-check")
    except Exception:
        return JsonResponse(
            {"status": "unavailable"},
            status=503,
        )

    return JsonResponse({"status": "ok"})
