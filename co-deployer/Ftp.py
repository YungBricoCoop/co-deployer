import os
import sys
import ftplib
from rich import print

class Ftp:
	config = None
	ftp = None

	def __init__(self, config):
		self.config = config
		self.ftp = None

	def __del__(self):
		if self.ftp: self.disconnect()

	
	def _connect(self):
		"""
		Connects to the FTP server
		"""
		config = self.config
		try:
			ftp = ftplib.FTP()
			ftp.connect(config.get("hostname"), config.get("port"))
			ftp.login(config.get("username"), config.get("password"))
			self.ftp = ftp
		except Exception as e:
			print("[bold red]FTP Error[/bold red] :", e)
			self.ftp = None
			sys.exit(1)
	
	def disconnect(self):
		"""
		Disconnects from the FTP server
		"""
		self.ftp.close()
		self.ftp = None
	
	def upload(self, local_dir, remote_dir):
		"""
		Uplaods a local directory to the FTP server
		"""

		if remote_dir and not self._remote_dir_exists_ftp(remote_dir):
			self.ftp.mkd(remote_dir)
		
		for item in os.listdir(local_dir):
			local_path = os.path.join(local_dir, item)
			remote_path = os.path.join(remote_dir, item)
			remote_path = remote_path.replace("\\", "/")
			if os.path.isfile(local_path):
				name = os.path.basename(local_path)
				with open(local_path, 'rb') as f:
					try:
						self.ftp.storbinary('STOR ' + remote_path, f)
						print(f"[bold green]Uploaded[/bold green] : {name}")
					except Exception as e:
						print(f"[bold red]Error[/bold red] uploading file {name}: {e}")
			elif os.path.isdir(local_path):
				name = os.path.basename(local_path)
				try:
					self.ftp.mkd(remote_path)
					print(f"[bold green]Created folder[/bold green] : {name}")
				except Exception as e:
					print(f"[bold red]Error[/bold red] creating folder {remote_path}: {e}")
				self.upload(local_path, remote_path)

	def _remote_dir_exists_ftp(self, remote_dir):
		try:
			self.ftp.cwd(remote_dir)
			self.ftp.cwd('..') 
			return True
		except ftplib.error_perm:
			return False
