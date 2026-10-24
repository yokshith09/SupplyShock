import pytest


@pytest.fixture(autouse=True)
def _clean_dispatch_env(monkeypatch):
    """Tests must not depend on the developer's shell (e.g. DISPATCH_LOCAL_AGENTS left set from a CLI run)."""
    for k in ("DISPATCH_MODE", "DISPATCH_LOCAL_AGENTS", "DEMO_SUPPLIER_INBOX", "RESEND_API_KEY",
              "SMTP_HOST", "SMTP_USER", "SMTP_PASS", "ASI1_API_KEY"):
        monkeypatch.delenv(k, raising=False)
