import yaml
import logging
from logging import info, warning, critical, debug


def load_yaml_config(config_filename):
    """Load the data structure from the YAML config file."""
    try:
        with open(config_filename, 'r') as stream:
            rawConfig = "".join(stream.readlines())

        parsedConfig = next(yaml.load_all(rawConfig))
    except IOError:
        critical("Could not open {} YAML config file for motor variables")
        raise
    else:
        return parsedConfig


def save_yaml_config(data, config_filename):
    """Load the data structure from the YAML config file."""
    try:
        with open(config_filename, 'w') as stream:
            yaml.dump(data, stream)  # Write a YAML representation of data
    except IOError:
        critical("Could not write {} YAML config file for motor variables".format(config_filename))
        raise

    return


