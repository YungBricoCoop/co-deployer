import sys
import json
import paramiko
import ftplib
from argparse import ArgumentParser
from rich import print

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
			return config
	except FileNotFoundError:
		print(f"File {CONFIG_FILE} not found.")
		sys.exit(1)
	except json.decoder.JSONDecodeError:
		print(f"Invalid JSON in file {CONFIG_FILE}.")
		sys.exit(1)

def validate_hosts(config):
	"""
	This function validates the hosts in the configuration
	:param config: the configuration as a dictionary
	:return: True if the hosts are valid, False otherwise
	"""
	required_fields = ["name", "host"]
	user_fields = ["user", "ftp_user", "ssh_user"]
	password_fields = ["password", "ftp_password", "ssh_password"]

	valid = True
	
	for host in config["hosts"]:
		# check if the required fields are present
		is_required_field_missing = any([field not in host for field in required_fields])
		if is_required_field_missing: print(f"Missing required field : {', '.join(required_fields)}")
		
		# check if one of the user fields is present
		is_user_field_missing = not any([field in host for field in user_fields])
		if is_user_field_missing: print(f"Need at least one user field : {', '.join(user_fields)}")
		
		# check if one of the password fields is present
		is_password_field_missing = not any([field in host for field in password_fields])
		if is_password_field_missing: print(f"Need at least one password field : {', '.join(password_fields)}")

		valid = valid and not is_required_field_missing and not is_user_field_missing and not is_password_field_missing
	
	if not valid:
		print("Invalid hosts configuration.")
		sys.exit(1)
	
	return config["hosts"]

def validate_deployments(config):
	"""
	This function validates the deployments in the configuration
	:param config: the configuration as a dictionary
	:return: True if the deployments are valid, False otherwise
	"""
	required_fields = ["name", "host", "arg", "protocol"]
	protocol_fields = ["ftp", "sftp", "ssh"]
	files_cmd_fields = ["files", "cmd"]
	
	valid = True
	
	for deployment in config["deployments"]:
		# check if the required fields are present
		is_required_field_missing = any([field not in deployment for field in required_fields])
		if is_required_field_missing: print(f"Missing required field : {', '.join(required_fields)}")
		
		# check if the protocol is valid
		protocol = deployment.get("protocol")
		is_protocol_field_invalid = protocol not in protocol_fields
		if is_protocol_field_invalid: print(f"Invalid protocol ({protocol}) : {', '.join(protocol_fields)}")

		is_files_or_cmd_missing = not any([field in deployment for field in files_cmd_fields])
		if is_files_or_cmd_missing: print(f"Need at least one of the following fields : {', '.join(files_cmd_fields)}")

		host = [host for host in config["hosts"] if host["name"] == deployment["host"]]
		if not host or not len(hosts): print(f"Host {deployment['host']} not found.")
		else: host = host[0]
		deployment["host"] = host

		valid = valid and not is_required_field_missing and not is_protocol_field_invalid and not is_files_or_cmd_missing and host
	
	if not valid:
		print("Invalid deployments configuration.")
		sys.exit(1)

	return config["deployments"]

def parse_arguments(deployments):
	"""
	This function parses the command line arguments

	Parameters:
		deployments (list): the list of deployments

	:return: the arguments as a dictionary
	"""
	parser = ArgumentParser()
	for deployment in deployments:
		parser.add_argument(deployment["arg"], f"--{deployment['name']}", help=f"Execute the deployment {deployment['name']}", action="store_true")
	
	# only get the arguments that are present
	arguments = [x for x in  vars(parser.parse_args()) if vars(parser.parse_args())[x]]
	
	return arguments

def deploy_all(deployments, arguments):
	"""
	This function deploys all the deployments that are present in the arguments

	Parameters:
		deployments (list): the list of deployments
		arguments (list): the list of arguments
	"""
	deployments = [deployment for deployment in deployments if deployment["name"] in arguments]
	for deployment in deployments:
		deploy(deployment)

def deploy(deployment):
	"""
	This function deploys using the specified deployment settings

	Parameters:
		deployment (dict): the deployment settings
	
	"""
	host = deployment["host"]
	hostname = host.get("host")

	ftp_user = host.get("ftp_user") or host.get("user")
	ftp_password = host.get("ftp_password") or host.get("password")
	ftp_port = host.get("ftp_port") or 21

	sfpt_user = host.get("sfpt_user") or host.get("user")
	sfpt_password = host.get("sfpt_password") or host.get("password")
	sfpt_port = host.get("sfpt_port") or 22

	ssh_user = host.get("ssh_user") or host.get("user")
	ssh_password = host.get("ssh_password") or host.get("password")
	ssh_port = host.get("ssh_port") or 22

	protocol = deployment.get("protocol")
	
	cmd = deployment.get("cmd")
	cmd_before_transfer = deployment.get("cmd_before_transfer")
	cmd_after_transfer = deployment.get("cmd_after_transfer")
	

	# define connection
	ssh = None
	ftp = None
	sftp = None

	if protocol == "ssh" or (cmd_before_transfer or cmd_after_transfer):
		ssh = ssh_connect(hostname, ssh_user, ssh_password, ssh_port)
		if cmd_before_transfer: print(f"SSH command result : {ssh_execute(ssh, cmd_before_transfer)}")
		if cmd : print(f"SSH command result : {ssh_execute(ssh, cmd)}")
	
	if protocol == "ftp":
		ftp = ftp_connect(hostname, ftp_user, ftp_password, ftp_port)
	
	if protocol == "sftp":
		sftp = sftp_connect(hostname, sfpt_user, sfpt_password, sfpt_port)
	
def ssh_connect(hostname, ssh_user, ssh_password, ssh_port):
	"""
	This function connects to the SSH server

	Parameters:
		ssh_user (str): the SSH user
		ssh_password (str): the SSH password
		ssh_port (int): the SSH port

	:return: the SSH client
	"""
	try:
		ssh = paramiko.SSHClient()
		ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
		ssh.connect(hostname, username=ssh_user, password=ssh_password, port=ssh_port)
	except Exception as e:
		print("[bold red]SSH Error[/bold red] :", e)
		sys.exit(1)
	return ssh

def ftp_connect(hostname, ftp_user, ftp_password, ftp_port):
	"""
	This function connects to the FTP server

	Parameters:
		hostname (str): the hostname
		ftp_user (str): the FTP user
		ftp_password (str): the FTP password
		ftp_port (int): the FTP port

	:return: the FTP client
	"""
	try:
		ftp = ftplib.FTP()
		ftp.connect(hostname, ftp_port)
		ftp.login(ftp_user, ftp_password)
	except Exception as e:
		print("[bold red]FTP Error[/bold red] :", e)
		sys.exit(1)
	return ftp

def sftp_connect(hostname, sfpt_user, sfpt_password, sfpt_port):
	"""
	This function connects to the SFTP server

	Parameters:
		hostname (str): the hostname
		sfpt_user (str): the SFTP user
		sfpt_password (str): the SFTP password
		sfpt_port (int): the SFTP port

	:return: the SFTP client
	"""
	try:
		transport = paramiko.Transport((hostname, sfpt_port))
		transport.connect(username=sfpt_user, password=sfpt_password)
		sftp = transport.open_sftp_client()
		return sftp
	except Exception as e:
		print("[bold red]SFTP Error[/bold red] :", e)
		sys.exit(1)

def ssh_execute(ssh, cmd):
	"""
	This function executes a command on the SSH server

	Parameters:
		ssh (SSHClient): the SSH client
		cmd (str): the command to execute

	:return: the output of the command
	"""
	stdin, stdout, stderr = ssh.exec_command(cmd)
	return stdout.read().decode("utf-8")

if __name__ == "__main__":
	config = load_config()
	hosts = validate_hosts(config)
	deployments = validate_deployments(config)
	arguments = parse_arguments(deployments)
	deploy_all(deployments, arguments)