# Co-Deployer
Co-Deployer is a tool made to deploy your projects simply and quickly. You can deploy your projects to a server using FTP or SFTP and also you can run commands on the server using SSH.

## Installation
You can install Co-Deployer using composer:
```bash
pip install co-deployer
```

## Usage

To use Co-Deployer you need to create a file named `deploy.config.json` in the root of your project. This file contains the configuration of your hosts and all the deployments you can use.

### Configuration file
The file is structured in two parts: `hosts` and `deployments`.
```json
{
	"hosts": [],
	"deployments": []
}
```

#### Hosts
The hosts are the servers where you want to deploy your project. You can define as many hosts as you want. Each host has a name and the credentials to connect to the server, the credentials can be shared for ftp/sfp and ssh connections or you can define different credentials for each connection type.

Only the `name` and `host` fields are required, the rest are optional.
```json
"hosts" : [{
	"name" : "my_host",
	"host" : "my-host.com",
	"username" : "user",
	"password" : "password",
	"ftp" : {
		"hostname" : "my-ftp-host.com",
		"username" : "my-ftp-user",
		"password" : "very-secure-password",
		"port" : 21
	},
	"sftp" : {
		"hostname" : "my-sftp-host.com",
		"username" : "my-sftp-user",
		"password" : "very-secure-password",
		"port" : 22
	},
	"ssh" : {
		"hostname" : "my-ssh-host.com",
		"username" : "my-ssh-user",
		"password" : "very-secure-password",
		"port" : 22
	}
}]
```

#### Deployments
The deployments are the tasks that you want to run on the server. You can define as many deployments as you want. 

Here 4 fields are required: `name`, `host`, `arg` and `protocol`. The `name` is the name of the deployment, the `host` is the name of the host where you want to deploy, the `arg` is the argument that will trigger the deployment and the `protocol` is the protocol that you want to use to deploy your project. The `protocol` can be `ftp`, `sftp`.  

The `local_path` is the path of the folder that you want to deploy, the `remote_path` is the path of the folder where you want to deploy your project. The `exclude` is an array of files and folders that you want to exclude from the deployment.	

The `cmd` is an object that contains the commands that you want to run on the server. All the fields are optional. The `cmd` is the command that you want to run localy, the `ssh` is the command that you want to run on the server using ssh. The `before` and `after` are the commands that you want to run before and after the deployment. The `ssh_before` and `ssh_after` are the commands that you want to run before and after the deployment using ssh.


```json
"deployments" : [{
	"name" : "react frontend build and deployment",
	"host" : "my_host",
	"arg" : "-fb",
	"protocol" : "sftp",
	
	"local_path" : "",
	"remote_path" : "/var/www/html",
	
	"exclude" : [],
	
	"cmd" : {
		"cmd" : "",
		"ssh" : "",

		"before" : "npm run build",
		"after" : "",
		
		"ssh_before" : "",
		"ssh_after" : "",
	}
}]
```