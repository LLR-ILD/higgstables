"""The default logger for the application."""
import logging

FORMAT = "[%(levelname)s-%(name)s] %(message)s"
logging.basicConfig(format=FORMAT)
logger = logging.getLogger("higgstables")
logger.setLevel(logging.INFO)
logger.setLevel(logging.DEBUG)
