import os
import sys
import paramiko
from rich import print

class Sftp:
	config = None
	sftp = None

	def __init__(self, config):
		self.config = config
		self.sftp = None

	def __del__(self):
		if self.sftp: self.disconnect()

	
	def _connect(self):
		"""
		Connects to the SFTP server
		"""
		config = self.config
		try:
			transport = paramiko.Transport((config.get("hostname"), config.get("port")))
			transport.connect(username=config.get("username"), password=config.get("password"))
			sftp = transport.open_sftp_client()
			return sftp
		except Exception as e:
			print("[bold red]SFTP Error[/bold red] :", e)
			sys.exit(1)
	
	def disconnect(self):
		"""
		Disconnects from the FTP server
		"""
		self.sftp.close()
		self.sftp = None
	
	def upload(self, local_dir, remote_dir):
		if remote_dir and not self.remote_dir_exists(self.sftp, remote_dir):
			self.sftp.mkdir(remote_dir)
			
		for item in os.listdir(local_dir):
			local_path = os.path.join(local_dir, item)
			remote_path = os.path.join(remote_dir, item)
			remote_path = remote_path.replace("\\", "/")
			if os.path.isfile(local_path):
				name = os.path.basename(local_path)
				try:
					self.sftp.put(local_path, remote_path)
					print(f"[bold green]Uploaded[/bold green] : {name}")
				except Exception as e:
					print(f"[bold red]Error[/bold red] uploading file {name}: {e}")
			elif os.path.isdir(local_path):
				name = os.path.basename(local_path)
				try:
					self.sftp.mkdir(remote_path)
					print(f"[bold green]Created folder[/bold green] : {name}")
				except Exception as e:
					print(f"[bold red]Error[/bold red] creating folder {remote_path}: {e}")
				self.upload(local_path, remote_path)
				
	def remote_dir_exists(sftp, remote_dir):
		try:
			sftp.stat(remote_dir)
			return True
		except IOError:
			return False
