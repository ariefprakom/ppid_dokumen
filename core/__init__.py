# Import admin customization so it applies on startup
try:
    from . import admin  # noqa: F401
except Exception:
    pass
