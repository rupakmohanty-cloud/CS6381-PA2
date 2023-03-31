import logging
import os
from .constants import *
from .chordutils import ChordUtils


##################################
# finger_table_gen class
# Author: Rupak Mohanty
# Purpose: Distributed Systems Spring 2023.  This class contains implementation of the finger table needed for 
# the chord algorithm
##################################
class FingerTableGen():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    @staticmethod
    def generate_finger_table(node, successor_list, m) -> []:
        '''Generates the finger table for the given node hash'''
        FingerTableGen.logger.debug(f"finger_table_gen::generate_finger_table for node {node.get(ID)}")
        _finger_table = []

        node_id = node[HASH]
        FingerTableGen.logger.debug(f"finger_table_gen::generate_finger_table - successor_list = {successor_list}")
        for i in range(m):
            start = (node_id + 2 ** i) % 2 ** m
            successor = FingerTableGen.__find_successor(start, successor_list)
            _finger_table.append((start, successor))
        return _finger_table

    @staticmethod
    def __find_successor(key, successor_list):
        '''Find the successor node for the key'''
        FingerTableGen.logger.debug(f"finger_table_gen::find_successor - start")
        FingerTableGen.logger.debug(f"finger_table_gen::find_successor - successor_list - {successor_list}")
        for i in range(len(successor_list)):
            if FingerTableGen.__is_between(key, successor_list[i].get(HASH),
                                           successor_list[(i + 1) % len(successor_list)].get(HASH)):
                return successor_list[i + 1 if i + 1 < len(successor_list) else 0]
        return successor_list[0]

    @staticmethod
    def __is_between(key, start, end):
        '''Determines if the key is between the start and end hash values'''
        if start == end:
            return True
        if start < end:
            return start < key <= end
        else:
            return key > start or key <= end


##################################
#
# Main program
#
###################################
def main():
    try:
        m = 8
        ft_gen = FingerTableGen()

        dht_node_list = ChordUtils.to_sorted_dht_node_list(
            ChordUtils.load_json_data(os.path.join(os.path.dirname(__file__), '..', 'Utils', f'dht{m}.json')))
        for node in dht_node_list:
            finger_table = ft_gen.generate_finger_table(node, dht_node_list, m)
            ChordUtils.print_finger_table(node, finger_table)

        ChordUtils.print_dht_nodes(dht_node_list)

        m = 48
        dht_node_list = ChordUtils.to_sorted_dht_node_list(
            ChordUtils.load_json_data(os.path.join(os.path.dirname(__file__), '..', 'Utils', f'dht{m}.json')))

        for node in dht_node_list:
            finger_table = ft_gen.generate_finger_table(node, dht_node_list, m)
            ChordUtils.print_finger_table(node, finger_table)

        ChordUtils.print_dht_nodes(dht_node_list)

    except Exception as e:
        logging.exception("Exception caught in main - {}".format(e))
        return


###################################
#
# Main entry point
#
###################################
if __name__ == "__main__":
    # set underlying default logging capabilities
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    main()
