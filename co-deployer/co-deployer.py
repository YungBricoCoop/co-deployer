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
	"""
	Builds a host dictionary from the config file

	:param config: The config dictionary
	:return: The hosts dictionary
	"""
	hosts = {}
	for h in config["hosts"]:
		hosts[h["name"]] = h
	return hosts

def build_deployments_dict(config, hosts):
	"""
	Builds a deployment dictionary from the config file

	:param config: The config dictionary
	:return: The deployments dictionary
	"""
	deployments = {}
	for d in config["deployments"]:
		if d["host"] not in hosts:
			print(f"[bold red]Host[/bold red]: {d['host']} [bold red]not found in hosts list[/bold red]")
			sys.exit(1)
		d["host"] = hosts[d["host"]]
		deployments[d["arg"]] = d
	
	return deployments

def parse_arguments(deployments):
	"""
	This function parses the command line arguments

	:param deployments: The deployments dictionary

	:return: to_deploy: The given deployments to execute
	"""
	parser = ArgumentParser()
	for d in deployments:
		name = deployments[d]["name"]
		parser.add_argument(d, f"--{d}", help=f"Execute the deployment {name}", action="store_true")
	
	# only return the deployments that are set to true
	to_deploy = [deployments["-"+x] for x,y in vars(parser.parse_args()).items() if y]
	return to_deploy



def ssh_connect(hostname, username, password, port):
	"""
	This function connects to the SSH server

	Parameters:
		username (str): the SSH user
		password (str): the SSH password
		port (int): the SSH port

	:return: the SSH client
	"""
	try:
		ssh = paramiko.SSHClient()
		ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
		ssh.connect(hostname=hostname, username=username, password=password, port=port)
	except Exception as e:
		print("[bold red]SSH Error[/bold red] :", e)
		sys.exit(1)
	return ssh

def ftp_connect(hostname, username, password, port):
	"""
	This function connects to the FTP server

	Parameters:
		hostname (str): the hostname
		username (str): the FTP user
		password (str): the FTP password
		port (int): the FTP port

	:return: the FTP client
	"""
	try:
		ftp = ftplib.FTP()
		ftp.connect(hostname, port)
		ftp.login(username, password)
	except Exception as e:
		print("[bold red]FTP Error[/bold red] :", e)
		sys.exit(1)
	return ftp

def sftp_connect(hostname, username, password, port):
	"""
	This function connects to the SFTP server

	Parameters:
		hostname (str): the hostname
		username (str): the SFTP user
		password (str): the SFTP password
		port (int): the SFTP port

	:return: the SFTP client
	"""
	try:
		transport = paramiko.Transport((hostname, port))
		transport.connect(username=username, password=password)
		sftp = transport.open_sftp_client()
		return sftp
	except Exception as e:
		print("[bold red]SFTP Error[/bold red] :", e)
		sys.exit(1)

def close_connections(ssh, ftp, sftp):
	"""
	This function closes the connections

	Parameters:
		ssh (SSHClient): the SSH client
		ftp (FTP): the FTP client
		sftp (SFTP): the SFTP client
	"""
	try:
		if ssh: 
			ssh.close()
			print("[bold green]Closed connection[/bold green] : SSH")
		if ftp: 
			ftp.close()
			print("[bold green]Closed connection[/bold green] : FTP")
		if sftp: 
			sftp.close()
			print("[bold green]Closed connection[/bold green] : SFTP")

	except Exception as e:
		print("[bold red]Error while closing connection(s)[/bold red] :", e)

if __name__ == "__main__":
	config = load_config()
	validate_config(config)
	hosts = build_hosts_dict(config)
	deployments = build_deployments_dict(config, hosts)
	to_deploy = parse_arguments(deployments)