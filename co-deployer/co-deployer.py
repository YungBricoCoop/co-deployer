# imports
import os
import sys
import json
import shutil
import uuid
import subprocess
import tempfile
import ftplib
from argparse import ArgumentParser

# third party imports
import paramiko
from rich import print
from rich.progress import track

CONFIG_FILE = "deploy.config.json"

def load_config():
	"""
	This function reads the configuration from a file named 'deploy.config.json'
	:param file_path: the path of the file to read
	:return: the configuration as a dictionary
	"""
	try:
		with open(CONFIG_FILE, "r") as f:
			config = json.loads(f.read())
			print(f"[bold green]Configuration file[/bold green]: {CONFIG_FILE} [bold green]loaded[/bold green]")
			return config
	except FileNotFoundError:
		print(f"[bold red]Configuration not found file[/bold red]: {CONFIG_FILE}")
		sys.exit(1)
	except json.decoder.JSONDecodeError:
		print(f"[bold red]Configuration file[/bold red]: {CONFIG_FILE} [bold red]is not valid JSON[/bold red]")
		sys.exit(1)

if __name__ == "__main__":
	load_config()