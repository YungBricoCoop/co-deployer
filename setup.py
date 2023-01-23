from setuptools import setup, find_packages

# read the contents of your README file
from pathlib import Path
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(
    name="co-deployer",
	description="A simple deployment tool for your projects",
    long_description=long_description,
    long_description_content_type='text/markdown',
	author="Elwan Mayencourt",
    version="1.0.4",
    packages=find_packages(),
    install_requires=[
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