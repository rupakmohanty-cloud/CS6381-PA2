###############################################
#
# Author: Aniruddha Gokhale
# Vanderbilt University
#
# Purpose: Skeleton/Starter code for the discovery middleware code
#
# Created: Spring 2023
#
###############################################

# Designing the logic is left as an exercise for the student.
#
# The discovery service is a server. So at the middleware level, we will maintain
# a REP socket binding it to the port on which we expect to receive requests.
#
# There will be a forever event loop waiting for requests. Each request will be parsed
# and the application logic asked to handle the request. To that end, an upcall will need
# to be made to the application logic.


###############################################
#
# Author: Elena McQuay
# Vanderbilt University
#
# Purpose: Implementation code for the discovery middleware code
#
# Created: Distributed Systems Spring 2023
#
###############################################

# import the needed packages
import os  # for OS functions
import sys  # for syspath and system exception
import time  # for sleep
import logging  # for logging. Use it in place of print statements.
import zmq  # ZMQ sockets
import traceback

# import serialization logic
from CS6381_MW import discovery_pb2

from Chord.fingertablegen import FingerTableGen
from Chord.chordutils import ChordUtils
from Chord.constants import *
from Chord.hashgen import hashgen

# from CS6381_MW import topic_pb2  # you will need this eventually

# import any other packages you need.

##################################
# DiscoveryMW Middleware class
##################################
class DiscoveryMW():

    ########################################
    # constructor
    ########################################
    def __init__(self, logger):
        self.logger = logger  # internal logger for print statements
        self.router_socket = None
        self.dealer_sockets_dict = {}
        self.poller = None  # used to wait on incoming replies
        self.addr = None  # our advertised IP address
        self.port = None  # port num where we are going to publish our topics
        self.upcall_obj = None  # handle to appln obj to handle appln-specific data
        self.handle_events = True  # in general we keep going thru the event loop
        self.json_file = None
        self.finger_table = None
        self.dht_nodes = None
        self.num_ft_entries = None
        self.dht_info = None
        self.dht_sockets_dic = {}
    ########################################
    # configure/initialize
    ########################################
    def configure(self, args, dht_info, num_ft_entries, finger_table:[]):
        ''' Initialize the object '''

        try:
            # Here we initialize any internal variables
            self.logger.info("DiscoveryMW::configure")

            # First retrieve our advertised IP addr and the publication port num
            self.port = args.port
            self.addr = args.addr
            self.dht_info  = dht_info
            self.num_ft_entries = num_ft_entries
            self.finger_table = finger_table

            # Next get the ZMQ context
            self.logger.debug("DiscoveryMW::configure - obtain ZMQ context")
            context = zmq.Context()  # returns a singleton object

            # get the ZMQ poller object
            self.logger.debug("DiscoveryMW::configure - obtain the poller")
            self.poller = zmq.Poller()

            # Set up the ROUTER socket as a front-end
            self.logger.debug("DiscoveryMW::configure - setting up Router")

            self.router_socket = context.socket(zmq.ROUTER)
            self.router_socket.identity = str(self.dht_info.get(ID)).encode()
            self.poller.register(self.router_socket, zmq.POLLIN)
            bind_str = "tcp://*:" + str(args.port)
            self.logger.debug("bind_str = {}".format(bind_str))
            self.router_socket.bind(bind_str)

            # create a dealer for successor in the finger table.
            self.logger.debug("DiscoveryMW::configure - setting up Dealer")

            # Establish dealer connections only for unique successors
            # Extract the dictionary items from the original_list portion of the tuples
            original_list = [d for _, d in finger_table]

            # Create a set of tuples containing the dictionary items
            tuple_set = set(tuple(sorted(d.items())) for d in original_list)

            # Convert the tuples back to dictionaries
            unique_successors = [dict(t) for t in tuple_set]

            for successor in unique_successors:
                self.logger.info(f"DiscoveryMW::configure successor- {successor}")
                dealer_socket = context.socket(zmq.DEALER)
                dealer_socket.identity = self.router_socket.identity
                conn_str = f"tcp://{successor.get(IP)}:{successor.get(PORT)}"
                dealer_socket.connect(conn_str)
                self.dealer_sockets_dict[successor.get(ID)] = dealer_socket
                self.logger.info(f"DiscoveryMW::configure - adding dealer for {successor.get(ID)} with connection {conn_str}")

            self.logger.info("DiscoveryMW::configure completed")

        except Exception as e:
            raise e

    #################################################################
    # run the event loop where we expect to receive incoming requests
    # WHERE [WHICH DHT NODE] TO RECIEVE INCOMING REQUEST
    #################################################################
    def event_loop(self, timeout=None):

        try:
            self.logger.info("DiscoveryMW::event_loop - run the event loop")

            # we are using a class variable called "handle_events" which is set to
            # True but can be set out of band to False in order to exit this forever
            # loop
            while self.handle_events:  # it starts with a True value
                # poll for events. We give it an infinite timeout.
                # The return value is a socket to event mask mapping
                events = dict(self.poller.poll(timeout=timeout))

                # Unlike the previous starter code, here we are never returning from
                # the event loop but handle everything in the same locus of control
                # Notice, also that after handling the event, we retrieve a new value
                # for timeout which is used in the next iteration of the poll

                # check if a timeout has occurred. We know this is the case when
                # the event mask is empty
                if not events:
                    # timeout has occurred so it is time for us to make appln-level
                    # method invocation. Make an upcall to the generic "invoke_operation"
                    # which takes action depending on what state the application
                    # object is in.
                    timeout = self.upcall_obj.invoke_operation()

                elif self.router_socket in events:
                    self.logger.info("DiscoveryMW::event_loop - router received event")
                    timeout = self.handle_request()
                elif self.dealer_sockets_dict in events:
                    self.logger.info("DiscoveryMW::event_loop - dealer received event")
                    # If a message is received on the backend socket, route it back to the frontend socket

                    # message = backend.recv_multipart()
                    self.router_socket.send_multipart(message)
                else:
                    raise Exception("Unknown event after poll")

            self.logger.info("DiscoveryMW::event_loop - out of the event loop")
        except Exception as e:
            raise e

    #################################################################
    # handle an incoming request
    #################################################################
    def find_successor(self, key) -> {}:
        self.logger.info(f"DiscoveryMW::find_successor - start key {key}")
        # self.logger.info(f"DiscoveryMW::find_successor - fingle_table: {self.finger_table}")
        if self.dht_info.get(HASH) == key:
            self.logger.info(f"DiscoveryMW::find_successor - successor: {self.dht_info}")
            return self.dht_info

        if self.finger_table[0][1].get(HASH) == self.dht_info.get(ID):
            self.logger.info(f"DiscoveryMW::find_successor - successor: {self.dht_info}")
            return self.dht_info

        if self.dht_info.get(HASH)  < key <= self.finger_table[0][1].get(HASH):
            self.logger.info(f"DiscoveryMW::find_successor - successor: {self.finger_table[0][1]}")
            return self.finger_table[0][1]

        return self.__closest_preceding_node(key)

    def __closest_preceding_node(self, key):
        '''Determines who is the closest successor based on the finger table'''

        self.logger.info(f"DiscoveryMW::__closest_preceding_node - start key {key}")
        for i in range(len(self.finger_table) - 1, -1, -1):
            if self.finger_table[i][1].get(HASH) > self.dht_info.get(HASH) and self.finger_table[i][1].get(HASH)  < key:
                self.logger.info(f"DiscoveryMW::__closest_preceding_node - successor: {self.finger_table[i][1]}")
                return self.finger_table[i][1]

        self.logger.info(f"DiscoveryMW::find_successor - successor: {self.dht_info}")
        return self.dht_info

    def handle_request(self):

        try:
            self.logger.info("DiscoveryMW::handle_request")

            # let us first receive all the bytes
            rcv_parts = self.router_socket.recv_multipart()
            self.logger.info(f"DiscoveryMW::handle_request - register - rcv_parts: {rcv_parts}")
            prv_nodes = []

            bytesRcvd = rcv_parts[len(rcv_parts) - 1]
            self.logger.info(f"DiscoveryMW::handle_request - register - bytesRcvd: {bytesRcvd}")

            # now use protobuf to deserialize the bytes
            # The way to do this is to first allocate the space for the
            # message we expect, here DiscoveryReq and then parse
            # the incoming bytes and populate this structure (via protobuf code)
            disc_req = discovery_pb2.DiscoveryReq()
            disc_req.ParseFromString(bytesRcvd)

            # demultiplex the message based on the message type but let the application
            # object handle the contents as it is best positioned to do so. See how we make
            # the upcall on the application object by using the saved handle to the appln object.
            #
            # Note also that we expect the return value to be the desired timeout to use
            # in the next iteration of the poll.
            if (disc_req.msg_type == discovery_pb2.TYPE_REGISTER):


                # register on the node according to the role
                # CREATE A HASH VALUE OF THE NODE
                req_hash = hashgen(self.num_ft_entries, str(disc_req.register_req.role))

                # get the appropriate successor
                successor = self.find_successor(req_hash)

                # if this is the correct service to handle the request, else pass it on
                if successor.get(ID) == self.dht_info.get(ID):
                    self.upcall_obj.register_request(disc_req.register_req)

                    # Build a RegisterResp message
                    self.logger.debug ("DiscoveryMW::register - populate the nested register resp")
                    register_resp = discovery_pb2.RegisterResp()  # allocate
                    register_resp.status = discovery_pb2.STATUS_SUCCESS  # registration successful
                    self.logger.debug ("DiscoveryMW::register - done populating nested RegisterResp")

                    # Finally, build the outer layer DiscoveryResp Message
                    self.logger.debug ("DiscoveryMW::register - build the outer DiscoveryReq message")
                    disc_resp = discovery_pb2.DiscoveryResp()  # allocate
                    disc_resp.msg_type = discovery_pb2.TYPE_REGISTER  # set message type
                    # It was observed that we cannot directly assign the nested field here.
                    # A way around is to use the CopyFrom method as shown
                    disc_resp.register_resp.CopyFrom(register_resp)
                    self.logger.debug ("DiscoveryMW::register - done building the outer message")

                    # now let us stringify the buffer and print it. This is actually a sequence of bytes and not
                    # a real string
                    buf2send = disc_resp.SerializeToString ()
                    self.logger.debug ("Stringified serialized buf = {}".format (buf2send))

                    # now send this to our discovery service
                    self.logger.debug ("DiscoveryMW::register - send stringified buffer to client")

                    if len(rcv_parts) > 2:
                        prev_sender = rcv_parts.pop(0)

                    rcv_parts[len(rcv_parts)-1] = buf2send
                        # We are back at the original dht node, send response back to the client.
                    self.logger.info(f"DiscoveryMW::register - sending {rcv_parts}")
                    self.router_socket.send_multipart(rcv_parts)  # we use the "send" method of ZMQ that sends the bytes

                    # now go to our event loop to receive more requests
                    self.logger.info ("DiscoveryMW::register - sent register response and now wait for more incoming msgs")
                else:
                    # forward to successor node
                    self.__forward_find_successor(successor, rcv_parts)

                return 0
            elif (disc_req.msg_type == discovery_pb2.TYPE_ISREADY):
                # this is a response to is ready request
                ready = self.upcall_obj.isready_request(disc_req.isready_req)

                # Build a RegisterResp message
                self.logger.debug ("DiscoveryMW::isready - populate the nested IsReadyResp resp")
                isready_resp = discovery_pb2.IsReadyResp()  # allocate

                if ready:
                    isready_resp.status = 1  # ready
                else:
                    isready_resp.status = 0  # not ready

                self.logger.debug ("DiscoveryMW::isready - done populating nested RegisterResp")

                # Finally, build the outer layer DiscoveryResp Message
                self.logger.debug ("DiscoveryMW::isready - build the outer DiscoveryReq message")
                disc_resp = discovery_pb2.DiscoveryResp()  # allocate
                disc_resp.msg_type = discovery_pb2.TYPE_ISREADY  # set message type
                # It was observed that we cannot directly assign the nested field here.
                # A way around is to use the CopyFrom method as shown
                disc_resp.isready_resp.CopyFrom(isready_resp)
                self.logger.debug ("DiscoveryMW::isready - done building the outer message")

                # now let us stringify the buffer and print it. This is actually a sequence of bytes and not
                # a real string
                buf2send = disc_resp.SerializeToString ()
                self.logger.debug ("Stringified serialized buf = {}".format (buf2send))

                # now send this to our discovery service
                self.logger.debug ("DiscoveryMW::isready - send stringified buffer to client")
                self.router_socket.send (buf2send)  # we use the "send" method of ZMQ that sends the bytes

                # now go to our event loop to receive more requests
                self.logger.info ("DiscoveryMW::isready - sent isready response and now wait for more incoming msgs")
                return 0
            elif (disc_req.msg_type == discovery_pb2.TYPE_LOOKUP_PUB_BY_TOPIC):

                try:
                    pub_list = self.upcall_obj.lookup_pubs_topic_request(disc_req.lookup_req)

                    # Build a LookupPubByTopicResp message
                    self.logger.debug ("DiscoveryMW::lookup - populate the nested LookupPubByTopicResp resp")
                    lookup_resp = discovery_pb2.LookupPubByTopicResp()  # allocate
                    self.logger.debug(pub_list)

                    lookup_resp.pubs.extend(pub_list)

                    self.logger.debug ("DiscoveryMW::lookup - done populating LookupPubByTopicResp")

                    # Finally, build the outer layer DiscoveryResp Message
                    self.logger.debug ("DiscoveryMW::lookup - build the outer DiscoveryReq message")
                    disc_resp = discovery_pb2.DiscoveryResp()  # allocate
                    disc_resp.msg_type = discovery_pb2.TYPE_LOOKUP_PUB_BY_TOPIC  # set message type
                    disc_resp.lookup_resp.CopyFrom(lookup_resp)
                    self.logger.debug ("DiscoveryMW::lookup - done building the outer message")

                    # now let us stringify the buffer and print it. This is actually a sequence of bytes and not
                    # a real string
                    buf2send = disc_resp.SerializeToString ()
                    self.logger.debug ("Stringified serialized buf = {}".format (buf2send))

                    # now send this to our discovery service
                    self.logger.debug ("DiscoveryMW::lookup - send stringified buffer to client")
                    self.router_socket.send (buf2send)  # we use the "send" method of ZMQ that sends the bytes

                    # now go to our event loop to receive more requests
                    self.logger.info ("DiscoveryMW::lookup - sent lookup response and now wait for more incoming msgs")
                    return 0
                except Exception:
                    self.logger.debug (traceback.print_exc())
            elif (disc_req.msg_type == discovery_pb2.TYPE_LOOKUP_ALL_PUBS):
                try:
                    pub_list = self.upcall_obj.lookup_all_pubs()

                    # Build a LookupPubByTopicResp message
                    self.logger.debug ("DiscoveryMW::lookup - populate the nested LookupPubByTopicResp resp")
                    lookup_resp = discovery_pb2.LookupPubByTopicResp()  # allocate
                    self.logger.debug(pub_list)

                    lookup_resp.pubs.extend(pub_list)
                    # for index, item in enumerate(pub_list):
                    #     lookup_resp.pubs.append(item)

                    # lookup_resp.pubs[:] = pub_list
                    self.logger.debug ("DiscoveryMW::lookup - done populating LookupPubByTopicResp")

                    # Finally, build the outer layer DiscoveryResp Message
                    self.logger.debug ("DiscoveryMW::lookup - build the outer DiscoveryReq message")
                    disc_resp = discovery_pb2.DiscoveryResp()  # allocate
                    disc_resp.msg_type = discovery_pb2.TYPE_LOOKUP_ALL_PUBS  # set message type
                    disc_resp.lookup_resp.CopyFrom(lookup_resp)
                    self.logger.debug ("DiscoveryMW::lookup - done building the outer message")

                    # now let us stringify the buffer and print it. This is actually a sequence of bytes and not
                    # a real string
                    buf2send = disc_resp.SerializeToString ()
                    self.logger.debug ("Stringified serialized buf = {}".format (buf2send))

                    # now send this to our discovery service
                    self.logger.debug ("DiscoveryMW::lookup - send stringified buffer to client")
                    self.router_socket.send (buf2send)  # we use the "send" method of ZMQ that sends the bytes

                    # now go to our event loop to receive more requests
                    self.logger.info ("DiscoveryMW::lookup - sent lookup response and now wait for more incoming msgs")
                    return 0
                except Exception:
                    self.logger.debug (traceback.print_exc())

            else:  # anything else is unrecognizable by this object
                # raise an exception here
                raise ValueError("Unrecognized request message")

            return 0

        except Exception as e:
            raise e

    def handle_response(self):

        self.logger.info("DiscoveryMW::handle_response")

        # let us first receive all the bytes
        rcv_msg = self.router_socket.recv_multipart()

        if len(rcv_msg) > 2:
            self.router_socket.send_multipart(rcv_msg.pop(0))
        else:
            self.router_socket.send_multipart(rcv_msg.pop(0))


    def __forward_find_successor(self, successor_info:{}, message:[]):
        '''Forwards the request to the appropriate successor node'''
        successor_socket = self.dealer_sockets_dict.get(successor_info.get(ID))

        # message.insert(0, self.dht_info.get(HASH))
        successor_socket.send_multipart(message)



    ########################################
    # set upcall handle
    #
    # here we save a pointer (handle) to the application object
    ########################################
    def set_upcall_handle(self, upcall_obj):
        """ set upcall handle """
        self.upcall_obj = upcall_obj

    ########################################
    # disable event loop
    #
    # here we just make the variable go false so that when the event loop
    # is running, the while condition will fail and the event loop will terminate.
    ########################################
    def disable_event_loop(self):
        """ disable event loop """
        self.handle_events = False
