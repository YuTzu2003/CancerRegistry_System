"""Survival report module.

The blueprint is imported lazily so model and parser users do not pull in route
dependencies while running unit tests.
"""


def __getattr__(name):
    if name == "survival_report_bp":
        from .routes import survival_report_bp

        return survival_report_bp
    raise AttributeError(name)


__all__ = ["survival_report_bp"]
