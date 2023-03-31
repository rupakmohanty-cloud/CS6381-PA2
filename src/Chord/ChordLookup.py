import hashlib
import math
from _hashlib import HASH

from .hashgen import hashgen
from .constants import *

class ChordLookup:
    def __init__(self, current_node, finger_table):
        self.current_node = current_node
        self.finger_table = finger_table
        self.data = {}
        self.successor_node = finger_table[0][1]

    def find_successor(self, key) -> {}:
        if self.current_node.get(HASH) == key:
            return self.current_node

        if self.successor_node.get(HASH) == self.current_node.get(HASH):
            return self.current_node

        if self.current_node.get(HASH) < key <= self.successor_node.get(HASH):
            return self.successor_node

        node = self.__closest_preceding_node(key)
        if node.get(HASH) == self.current_node.get(HASH):
            return self.successor_node

        return node.find_successor(key)

    def __closest_preceding_node(self, key):
        for i in range(len(self.finger_table) - 1, -1, -1):
            if self.finger_table[i][1].get(HASH) > self.current_node.get(HASH) and self.finger_table[i][1].get(HASH) < key:
                return self.finger_table[i][1]
        return self.current_node

     
