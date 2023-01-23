# modules
from modules.Config import Config
from modules.Deploy import Deploy

if __name__ == "__main__":
	# load and build config
	config = Config()
	# get the deployment list from the given arguments
	to_deploy = config.get_arguments()
	# create the worker
	deploy = Deploy(to_deploy)
	# deploy the list
	deploy.deploy_all()