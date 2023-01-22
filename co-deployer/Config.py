import sys
import json
from argparse import ArgumentParser
from jsonschema import validate, ValidationError
from rich import print

class Config:
	CONFIG_FILE = "deploy.config.json"
	config = {}
	schema = {"type": "object",
		"properties": {
			"hosts" : {
				"type": "array",
				"minItems" : 1,
				"items": {
					"type": "object",
					"properties": {
						"name" : { "type": "string" },
						"hostname" : { "type": "string" },
						"username" : { "type": "string" },
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
					"required": ["name", "hostname"],
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
						"protocol" : { "type": "string" , "enum": ["ftp", "sftp"] },

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
		"additionalProperties" : False}
	
	def __init__(self):
		self._load_config()
		self._validate()
		self._build_hosts_dict()
		self._build_deployments_dict()
	
	def _load_config(self):
		"""
		Loads and set the config file
		"""
		try:
			with open(self.CONFIG_FILE, "r") as f:
				self.config = json.loads(f.read())
		except FileNotFoundError:
			print(f"{self.CONFIG_FILE} [bold red]not found[/bold red]")
			sys.exit(1)
		except json.decoder.JSONDecodeError:
			print(f"{self.CONFIG_FILE} [bold red]is not a valid JSON file[/bold red]")
			sys.exit(1)
	
	def _validate(self):
		try:
			validate(instance=self.config, schema=self.schema)
		except ValidationError as e:
			print(f"{self.CONFIG_FILE} [bold red]is invalid[/bold red] : {e}")
			sys.exit(1)

	def _build_hosts_dict(self):
		"""
		Builds a host dictionary from the config file
		"""
		hosts = {}
		for h in self.config["hosts"]:
			h["ssh"] = self._build_host_protocols_dict(h, "ssh")
			h["sftp"] = self._build_host_protocols_dict(h, "sftp")
			h["ftp"] = self._build_host_protocols_dict(h, "ftp")
			hosts[h["name"]] = h
		
		self.config["hosts"] = hosts

	def _build_host_protocols_dict(self, host, protocol):
		protocol_dict = host.get(protocol) or {}
		ssh_port, sftp_port, ftp_port,  = 22, 22, 21
		port = protocol_dict.get("port") or host.get("port") or ssh_port if protocol == "ssh" else sftp_port if protocol == "sftp" else ftp_port
		return {
			"hostname": protocol_dict.get("hostname") or host.get("hostname"),
			"username": protocol_dict.get("username") or host.get("username"),
			"password": protocol_dict.get("password") or host.get("password"),
			"port":  port
		}

	def _build_deployments_dict(self):
		"""
		Builds a deployment dictionary from the config file
		"""

		deployments = {}
		hosts = self.config["hosts"]
		for d in self.config["deployments"]:
			if d["host"] not in hosts:
				print(f"[bold red]Host[/bold red]: {d['host']} [bold red]not found in hosts list[/bold red]")
				sys.exit(1)
			d["host"] = hosts[d["host"]]
			deployments[d["arg"]] = d
		
		self.config["deployments"] = deployments

	def get_arguments(self):
		"""
		This function build and parses the command line arguments

		Returns:
			list: A list of deployment to execute
		"""
		deployments = self.config.get("deployments")
		parser = ArgumentParser()
		for d in deployments:
			name = deployments[d]["name"]
			arg = deployments[d]["arg"]
			parser.add_argument(arg, f"--{arg}", help=f"Execute the deployment {name}", action="store_true")
		
		# only return the deployments that are set to true
		arguments = [deployments["-"+x] for x,y in vars(parser.parse_args()).items() if y]
		return arguments