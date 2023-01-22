# imports
import os
import sys
import json
import shutil
import uuid
import subprocess
import tempfile
import ftplib
import Config
from argparse import ArgumentParser

# third party imports

import paramiko
from jsonschema import validate, ValidationError
from rich import print
from rich.progress import track

def ssh_connect(config):
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
		ssh.connect(hostname=config.get("hostname"), username=config.get("username"), password=config.get("password"), port=config.get("port"))
	except Exception as e:
		print("[bold red]SSH Error[/bold red] :", e)
		sys.exit(1)
	return ssh

def ftp_connect(config):
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
		ftp.connect(config.get("hostname"), config.get("port"))
		ftp.login(config.get("username"), config.get("password"))
	except Exception as e:
		print("[bold red]FTP Error[/bold red] :", e)
		sys.exit(1)
	return ftp

def sftp_connect(config):
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
		transport = paramiko.Transport((config.get("hostname"), config.get("port")))
		transport.connect(username=config.get("username"), password=config.get("password"))
		sftp = transport.open_sftp_client()
		return sftp
	except Exception as e:
		print("[bold red]SFTP Error[/bold red] :", e)
		sys.exit(1)

def close_connections(opened_connections):
	"""
	This function closes the connections

	Parameters:
		opened_connections (dict): the opened connections
	"""

	ssh = opened_connections.get("ssh")
	ftp = opened_connections.get("ftp")
	sftp = opened_connections.get("sftp")
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

def build_protocol_dict(host, protocol):
	protocol_dict = host.get(protocol) or {}
	ssh_port, sftp_port, ftp_port,  = 22, 22, 21
	port = protocol_dict.get("port") or host.get("port") or ssh_port if protocol == "ssh" else sftp_port if protocol == "sftp" else ftp_port
	return {
		"hostname": protocol_dict.get("hostname") or host.get("hostname"),
		"username": protocol_dict.get("username") or host.get("username"),
		"password": protocol_dict.get("password") or host.get("password"),
		"port":  port
	}

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

def execute(cmd):
	"""
	This function executes a command

	Parameters:
		cmd (str): the command to execute

	:return: the output of the command
	"""
	result = ""
	try:
		result = subprocess.check_output(cmd, shell=True).decode("utf-8")
	except Exception as e:
		print("[bold red]Error while executing command[/bold red] :", e)
	return result


def deploy(deployment):

	# deployment variables
	name = deployment.get("name")
	protocol = deployment.get("protocol")
	local_path = deployment.get("local_path", ".")
	remote_path = deployment.get("remote_path", "/")
	exclude = deployment.get("exclude", [])
	cmd = deployment.get("cmd", "") or {}

	# host variables
	host = deployment.get("host")
	
	print(f"[bold green]Deploying[/bold green] : {name}")

	# create temporary directory
	tmp_dir = create_tmp_file_structure(local_path, exclude)

	# build the protocol configs
	ssh = build_protocol_dict(host, "ssh")
	ftp = build_protocol_dict(host, "ftp")
	sftp = build_protocol_dict(host, "sftp")

	# opened connections
	opened_connections =  {
		"ssh": False,
		"ftp": False,
		"sftp": False
	}

	# create connections	
	if cmd.get("ssh_before") or cmd.get("ssh_after"):
		ssh = ssh_connect(ssh)
		opened_connections["ssh"] = ssh
	
	if protocol == "sftp":
		sftp = sftp_connect(sftp)
		opened_connections["sftp"] = sftp

	if protocol == "ftp":
		ftp = ftp_connect(ftp)
		opened_connections["ftp"] = ftp
	
	# execute the commands before the deployment
	if cmd.get("before"):
		result = execute(cmd.get("before"))
		print(f"[bold cyan][BEFORE CMD OUT][/bold cyan] : {result}")
	
	if cmd.get("ssh_before"):
		result = ssh_execute(ssh, cmd.get("ssh_before"))
		print(f"[bold cyan][BEFORE CMD OUT][/bold cyan] : {result}")
	
	# deploy
	if protocol == "sftp":
		print("[bold cyan][SFTP][/bold cyan] Deploying[FTP]...")
		sftp_upload(sftp, tmp_dir, remote_path)
		print("[bold green][SFTP]Successfully deployed[/bold green]")
	
	if protocol == "ftp":
		print("[bold cyan][FTP][/bold cyan] Deploying...")
		ftp_upload(ftp, tmp_dir, remote_path)
		print("[bold cyan][FTP][/bold cyan] Successfully deployed")
	
	# execute the commands after the deployment
	if cmd.get("after"):
		result = execute(cmd.get("after"))
		print(f"[bold cyan][AFTER CMD OUT][/bold cyan] : {result}")

	if cmd.get("ssh_after"):
		result = ssh_execute(ssh, cmd.get("ssh_after"))
		print(f"[bold cyan][AFTER SSH CMD OUT][/bold cyan] : {result}")
	
	close_connections(opened_connections)
	remove_tmp_dir(tmp_dir)

def sftp_upload(sftp, local_dir, remote_dir):
	if remote_dir and not remote_dir_exists_sftp(sftp, remote_dir):
		sftp.mkdir(remote_dir)
		
	for item in os.listdir(local_dir):
		local_path = os.path.join(local_dir, item)
		remote_path = os.path.join(remote_dir, item)
		remote_path = remote_path.replace("\\", "/")
		if os.path.isfile(local_path):
			name = os.path.basename(local_path)
			try:
				sftp.put(local_path, remote_path)
				print(f"[bold green]Uploaded[/bold green] : {name}")
			except Exception as e:
				print(f"[bold red]Error[/bold red] uploading file {name}: {e}")
		elif os.path.isdir(local_path):
			name = os.path.basename(local_path)
			try:
				sftp.mkdir(remote_path)
				print(f"[bold green]Created folder[/bold green] : {name}")
			except Exception as e:
				print(f"[bold red]Error[/bold red] creating folder {remote_path}: {e}")
			sftp_upload(sftp, local_path, remote_path)
			
def remote_dir_exists_sftp(sftp, remote_dir):
	try:
		sftp.stat(remote_dir)
		return True
	except IOError:
		return False

def ftp_upload(ftp, local_dir, remote_dir):
	if remote_dir and not remote_dir_exists_ftp(ftp, remote_dir):
		ftp.mkd(remote_dir)
	
	for item in os.listdir(local_dir):
		local_path = os.path.join(local_dir, item)
		remote_path = os.path.join(remote_dir, item)
		remote_path = remote_path.replace("\\", "/")
		if os.path.isfile(local_path):
			name = os.path.basename(local_path)
			with open(local_path, 'rb') as f:
				try:
					ftp.storbinary('STOR ' + remote_path, f)
					print(f"[bold green]Uploaded[/bold green] : {name}")
				except Exception as e:
					print(f"[bold red]Error[/bold red] uploading file {name}: {e}")
		elif os.path.isdir(local_path):
			name = os.path.basename(local_path)
			try:
				ftp.mkd(remote_path)
				print(f"[bold green]Created folder[/bold green] : {name}")
			except Exception as e:
				print(f"[bold red]Error[/bold red] creating folder {remote_path}: {e}")
			ftp_upload(ftp, local_path, remote_path)

def remote_dir_exists_ftp(ftp, remote_dir):
    try:
        ftp.cwd(remote_dir)
        ftp.cwd('..') 
        return True
    except ftplib.error_perm:
        return False

def create_tmp_file_structure(localpath = ".", exclude = []):
	# create a temporary directory
	tmp_dir = os.path.join(tempfile.gettempdir(), str(uuid.uuid4()))
	
	# copy the local directory to the temporary directory
	try:
		shutil.copytree(localpath, tmp_dir)
	except Exception as e:
		print(f"[bold red]Error[/bold red] creating temporary directory: {e}")
		sys.exit(1)
	
	# remove the excluded files and folders
	for item in track(exclude, description = "Removing excluded files and folders..."):
		item_path = os.path.join(tmp_dir, item)
		if os.path.isfile(item_path):
			os.remove(item_path)
		elif os.path.isdir(item_path):
			shutil.rmtree(item_path)
	
	# return the temporary directory
	return tmp_dir

def remove_tmp_dir(tmp_dir):
	"""
	This function removes the tmp directory

	Parameters:
		tmp_dir (str): the tmp directory
	"""
	try:
		shutil.rmtree(tmp_dir)
		print(f"[bold green]Removed[/bold green] : Temp directory")
	except Exception as e:
		print("[bold red]Error while removing tmp directory[/bold red] :", e)

if __name__ == "__main__":
	# create workers
	config = Config.Config()
	to_deploy = config.get_arguments()
	for d in to_deploy: 
		deploy(d)