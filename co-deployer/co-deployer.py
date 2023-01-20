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
from jsonschema import validate, ValidationError
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

def validate_config(config):
	schema = {
		"type": "object",
		"properties": {
			"hosts" : {
				"type": "array",
				"minItems" : 1,
				"items": {
					"type": "object",
					"properties": {
						"name" : { "type": "string" },
						"host" : { "type": "string" },
						"user" : { "type": "string" },
						"password" : { "type": "string" },
						"ftp" : { 
							"type": "object",
							"properties": {
								"username": { "type": "string" },
								"password": { "type": "string" },
								"port": { "type": "integer" },
							},
							"required": ["username", "password"],
							"additionalProperties" : False
						 },
						"sftp" : { 
							"type": "object",
							"properties": {
								"username": { "type": "string" },
								"password": { "type": "string" },
								"port": { "type": "integer" },
							},
							"required": ["username", "password"],
							"additionalProperties" : False
						 },
						"ssh" : { 
							"type": "object",
							"properties": {
								"username": { "type": "string" },
								"password": { "type": "string" },
								"port": { "type": "integer" },
							},
							"required": ["username", "password"],
							"additionalProperties" : False
						 },

					},
					"required": ["name", "host"],
			
					"additionalProperties" : False
				}
			},
			"deployments": {
				"type": "array",
				"minItems" : 1,
				"items": {
					"type": "object",
					"properties": {
						"name" : { "type": "string" },
						"host" : { "type": "string" },
						"arg" : { "type": "string", "pattern": "^-.*$" },
						"protocol" : { "type": "string" , "enum": ["ftp", "sftp", "ssh"] },

						"local_path" : { "type": "string" },
						"remote_path" : { "type": "string" },

						"exclude" : { "type": "array" },

						"cmd" : {
							"type": "object",
							"properties": {
								"before" : { "type": "string" },
								"after" : { "type": "string" },

								"ssh_before" : { "type": "string" },
								"ssh_after" : { "type": "string" },
							},
							"additionalProperties" : False
						}
						
					},
					"required": ["name", "host", "arg", "protocol"],
					"additionalProperties" : False
				}
			}
		},
		"required": ["hosts", "deployments"],
		"additionalProperties" : False
	}
	try:
		validate(instance=config, schema=schema)
		print(f"[bold green]Configuration file[/bold green]: {CONFIG_FILE} [bold green]is valid[/bold green]")
	except ValidationError as e:
		print(f"[bold red]Configuration file[/bold red]: {CONFIG_FILE} [bold red]is not valid[/bold red]")
		print(e)
		sys.exit(1)

def build_hosts_dict(config):
	hosts = {}
	for host in config["hosts"]:
		hosts[host["name"]] = host
	return hosts

def build_deployments_dict(config):
	deployments = {}
	for deployment in config["deployments"]:
		deployments[deployment["arg"]] = deployment
	return deployments

if __name__ == "__main__":
	config = load_config()
	validate_config(config)