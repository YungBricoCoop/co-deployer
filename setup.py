from setuptools import setup, find_packages

setup(
    name="co-deployer",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "argparse",
		"rich",
		"ftplib"
		"paramiko"
		"pysftp",
    ],
)