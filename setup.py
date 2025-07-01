from setuptools import setup

setup(
    name="django_wrapper",
    version="0.1",
    py_modules=["django_wrapper"],
    entry_points={
        "console_scripts": [
            "django-wrapper = django_wrapper:main",
        ],
    },
)

