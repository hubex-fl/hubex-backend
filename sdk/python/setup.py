from setuptools import setup, find_packages

setup(
    name="hubex-agent",
    version="0.1.0",
    description="HUBEX Agent SDK — connect any machine to HUBEX as an agent device",
    packages=find_packages(),
    install_requires=["requests>=2.28.0"],
    extras_require={
        "system": ["psutil>=5.9.0"],
    },
    python_requires=">=3.9",
    entry_points={
        "console_scripts": [
            "hubex-agent=hubex_agent.cli:main",
        ],
    },
)
