# imports
from argparse import ArgumentParser

# modules
import Config
import Deploy

if __name__ == "__main__":
	# load and build config
	config = Config.Config()
	# get the deployment list from the given arguments
	to_deploy = config.get_arguments()
	# create the worker
	deploy = Deploy.Deploy(to_deploy)
	# deploy the list
	deploy.deploy_all()