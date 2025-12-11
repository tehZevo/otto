from setuptools import setup, find_packages

setup(
    name="otto",
    version="0.1.0",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "otto=otto:main",
        ],
    },
    install_requires=[
        "openai>=1.30.0",
        "fastmcp>=0.1.0",
        "PyYAML>=5.4.0",
    ]
)
