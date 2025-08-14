"""
Setup script for questionnaire-processor package
"""
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="questionnaire-processor",
    version="0.1.0",
    author="DrelliaTech",
    description="A Python application for processing questionnaires from conversation data",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/DrelliaTech/questionnaire-processor",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.9",
    install_requires=requirements,
    extras_require={
        "dev": [
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
            "pytest>=7.2.0",
            "pytest-asyncio>=0.21.0",
            "moto>=4.1.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "questionnaire-processor=main:main",
        ],
    },
)