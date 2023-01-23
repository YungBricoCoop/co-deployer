from setuptools import setup, find_packages

setup(
    name="co-deployer",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "argparse",
		"rich",
		"paramiko",
		"jsonschema"
    ],
	   entry_points={
        "console_scripts": [
            "co-deployer = co_deployer.co_deployer:main",
        ],
    },
)