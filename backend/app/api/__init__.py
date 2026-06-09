"""API router package."""

_ROUTER_MODULES = {
    "auth_router": "auth",
    "chat_router": "chat",
    "resume_router": "resume",
    "recording_router": "recording",
    "question_router": "question",
    "admin_router": "admin",
    "profile_router": "profile",
    "interview_router": "interview",
}


def __getattr__(name: str):
    if name not in _ROUTER_MODULES:
        raise AttributeError(name)

    from importlib import import_module

    module = import_module(f"app.api.{_ROUTER_MODULES[name]}")
    router = module.router
    globals()[name] = router
    return router


__all__ = [
    "auth_router",
    "chat_router",
    "resume_router",
    "recording_router",
    "question_router",
    "admin_router",
    "profile_router",
    "interview_router",
]
