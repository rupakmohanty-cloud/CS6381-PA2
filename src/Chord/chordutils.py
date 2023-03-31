import json
from .constants import *
from .hashgen import hashgen
import logging


##################################
# finger_table_gen class
# Author: Rupak Mohanty
# Purpose: Distributed Systems Spring 2023.
# This class contains several utility functions for the chord implementation
##################################
class ChordUtils:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    @staticmethod
    def load_json_data(json_path) -> {}:
        """Loads the json file and returns the json"""
        ChordUtils.logger.debug(f"chord_utils::load_json_data - file = {json_path}")
        data = {}
        try:
            # Opening JSON
            f = open(json_path)

            # returns JSON object as a dictionary
            data = json.load(f)
            ChordUtils.logger.debug(f"chord_utils::load_json_data - data: {data}")
        except Exception as e:
            ChordUtils.logger.exception(e)
        return data

    @staticmethod
    def to_sorted_dht_node_list(dht_json: object) -> []:
        """Takes the dht list from json and sort it by hash value."""

        ChordUtils.logger.debug("chord_utils::to_sorted_dht_node_list - retrieved dht list")
        sorted_dht_nodes = []
        if dht_json is not None:
            dht_nodes = dht_json.get(DHT)
            ChordUtils.logger.debug(f"Nodes: {dht_nodes}")
            # Sort the dht table by hash values
            sorted_dht_nodes = sorted(dht_nodes, key=lambda x: x["hash"])

        ChordUtils.logger.debug(f"chord_utils::to_sorted_dht_node_list - sorted dht list: {sorted_dht_nodes}")
        return sorted_dht_nodes

    @staticmethod
    def print_finger_table(node, finger_table):
        """ Pretty print Finger Table"""

        try:
            ChordUtils.logger.info("*" * 50)
            ChordUtils.logger.info(f"Finger Table for Node: {node.get(ID)}, {node.get(HASH)}")
            ChordUtils.logger.info("-" * 50)
            ChordUtils.logger.info("{:<5}  {:<20}  {:<10}".format("Index", "Start", "Successor"))
            ChordUtils.logger.info("{:<5}{:<1}{:<20}{:<1}{:<10}".format("-" * 5, "+", "-" * 20, "+", "-" * 10))
            for i, tuple in enumerate(finger_table):
                ChordUtils.logger.info("{:<5}  {:<20}  {:<10}".format(i, tuple[0], tuple[1].get(ID)))
            ChordUtils.logger.info("*" * 50)

        except Exception as e:
            raise e

    @staticmethod
    def print_dht_nodes(node_list):
        """ Pretty print DHT node dictionary list"""

        try:
            ChordUtils.logger.info("*" * 60)
            ChordUtils.logger.info(f"{'DHT Nodes':^{60}}")
            ChordUtils.logger.info("-" * 60)
            ChordUtils.logger.info(f"{'ID':<{8}} {'Hash':<{20}} {'IP':<{10}} {'Port':<{6}} {'Host':<{8}}")
            ChordUtils.logger.info(
                "{:<8}{:<1}{:<20}{:<1}{:<10}{:<1}{:<6}{:<1}{:<8}".format("-" * 8, "+", "-" * 20, "+", "-" * 10, "+",
                                                                         "-" * 6, "+", "-" * 12))
            for i, dict in enumerate(node_list):
                ChordUtils.logger.info(
                    "{:<8} {:<20} {:<10} {:<6} {:<8}".format(dict[ID], dict[HASH],
                                                             dict[IP], dict[PORT],
                                                             dict[HOST]))
            ChordUtils.logger.info("*" * 60)

        except Exception as e:
            raise e

    @staticmethod
    def registration_node_hash(bits: int) -> int:
        return hashgen(bits, 'Catch the Tea Pot')
