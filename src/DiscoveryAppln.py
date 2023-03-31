###############################################
#
# Author: Aniruddha Gokhale
# Vanderbilt University
#
# Purpose: Skeleton/Starter code for the Discovery application
#
# Created: Spring 2023
#
###############################################


# This is left as an exercise for the student.  The Discovery service is a server
# and hence only responds to requests. It should be able to handle the register,
# is_ready, the different variants of the lookup methods. etc.
#
# The key steps for the discovery application are
# (1) parse command line and configure application level parameters. One
# of the parameters should be the total number of publishers and subscribers
# in the system.
# (2) obtain the discovery middleware object and configure it.
# (3) since we are a server, we always handle events in an infinite event loop.
# See publisher code to see how the event loop is written. Accordingly, when a
# message arrives, the middleware object parses the message and determines
# what method was invoked and then hands it to the application logic to handle it
# (4) Some data structure or in-memory database etc will need to be used to save
# the registrations.
# (5) When all the publishers and subscribers in the system have registered with us,
# then we are in a ready state and will respond with a true to is_ready method. Until then
# it will be false.

import argparse  # for argument parsing
import logging  # for logging. Use it in place of print statements.
from enum import Enum
import configparser  # for configuration parsing
# from Chord import constants
# from Chord import fingertablegen
import os
# Import our topic selector. Feel free to use alternate way to
# get your topics of interest

# Now import our CS6381 Middleware
from CS6381_MW.DiscoveryMW import DiscoveryMW

# We also need the message formats to handle incoming responses.
from CS6381_MW import discovery_pb2
from Chord.fingertablegen import FingerTableGen
from Chord.chordutils import ChordUtils
from Chord.constants import *
from Chord.hashgen import hashgen

##################################
# DiscoveryAppln class
# Author: Elena McQuay
# Purpose: Distributed Systems Spring 2023
##################################
class DiscoveryAppln():
    # these are the states through which our discovery appln object goes thru.
    # We maintain the state so we know where we are in the lifecycle and then
    # take decisions accordingly
    class State(Enum):
        INITIALIZE = 0,
        CONFIGURE = 1,
        REGISTERING = 2

    ########################################
    # constructor
    ########################################
    def __init__(self, logger):
        self.state = self.State.INITIALIZE  # state that are we in
        self.name = None  # our name (some unique name)
        self.mw_obj = None  # handle to the underlying Middleware object
        self.logger = logger  # internal logger for print statements
        self.num_pubs = None  # the number of publishers expected before the service is ready
        self.num_subs = None  # the number of subscribers expected before the service is ready
        self.pub_dict = None  # Dictionary to contain the number of publishers registered
        self.sub_dict = None  # Dictionary to contain the number of subscribers registered
        self.broker = None
        self.dissemination = None  # direct or via broker
        self.json_file = None
        self.finger_table = None
        self.dht_nodes = None
        self.num_ft_entries = None
        self.dht_info = None

    ########################################
    # configure/initialize
    ########################################
    def configure(self, args):
        ''' Initialize the object '''

        try:
            # Initialize internal variables
            self.logger.info("DiscoveryAppln::configure")

            # set our current state to CONFIGURE state
            self.state = self.State.CONFIGURE

            # initialize our variables
            self.name = args.name  # our name
            self.num_pubs = args.num_pubs  # num of publishers expected
            self.num_subs = args.num_subs  # num of subscribers expected
            self.pub_dict = {}
            self.sub_dict = {}

            # chord configs
            self.dht_nodes = ChordUtils.to_sorted_dht_node_list(
                ChordUtils.load_json_data(os.path.join(os.path.dirname(__file__), 'Utils', args.json_file)))
            self.num_ft_entries = 48

            # Find the DHT information for this node
            # Iterate over the list of dictionaries
            for item in self.dht_nodes:
                # Check if the value associated with the key 'ID' in the dictionary is equal to self.name
                if item.get(ID) == self.name:
                    # Set dht_info to the matching dictionary item
                    self.dht_info = item
                    # Exit the loop since we have found the first matching item
                    break

            if self.json_file is not None and self.dht_info is None:
                raise ValueError(f"Cannot fild DHT Node information for Node: {self.name}")

            self.finger_table = FingerTableGen.generate_finger_table(self.dht_info, self.dht_nodes, self.num_ft_entries)

            # Now, get the configuration object
            self.logger.debug("DiscoveryAppln::configure - parsing config.ini")
            config = configparser.ConfigParser()
            config.read(args.config)

            self.dissemination = config["Dissemination"]["Strategy"]

            # Now setup up our underlying middleware object to which we delegate
            # everything
            self.logger.debug("DiscoveryAppln::configure - initialize the middleware object")
            self.mw_obj = DiscoveryMW(self.logger)
            self.mw_obj.configure(args, self.dht_info, self.num_ft_entries, self.finger_table)

            self.logger.info("DiscoveryAppln::configure - configuration complete")

        except Exception as e:
            raise e

    def is_broker_dissemination(self):
        if self.dissemination == "Broker":
            return True
        else:
            return False

    ########################################
    # driver program
    ########################################
    def driver(self):
        ''' Driver program '''

        try:
            self.logger.info("DiscoveryAppln::driver")

            # dump our contents (debugging purposes)
            self.dump()

            # First ask our middleware to keep a handle to us to make upcalls.
            # This is related to upcalls. By passing a pointer to ourselves, the
            # middleware will keep track of it and any time something must
            # be handled by the application level, invoke an upcall.
            self.logger.debug("DiscoveryAppln::driver - upcall handle")
            self.mw_obj.set_upcall_handle(self)

            # the next thing we should be doing is to determine if the discovery
            # service is ready. But because we are simply delegating everything to an event loop
            # that will call us back, we will need to know when we get called back as to
            # what should be our next set of actions.  Hence, as a hint, we set our state
            # accordingly so that when we are out of the event loop, we know what
            # operation is to be performed.  In this case we should be accepting incoming registrations.
            self.state = self.State.REGISTERING

            # Now simply let the underlying middleware object enter the event loop
            # to handle events. However, a trick we play here is that we provide a timeout
            # of zero so that control is immediately sent back to us where we can then
            # register with the discovery service and then pass control back to the event loop
            #
            # As a rule, whenever we expect a reply from remote entity, we set timeout to
            # None or some large value, but if we want to send a request ourselves right away,
            # we set timeout is zero.
            #
            self.mw_obj.event_loop(timeout=0)  # start the event loop
            self.logger.info("DiscoveryAppln::driver completed")

        except Exception as e:
            raise e

    ########################################
    # generic invoke method called as part of upcall
    #
    # This method will get invoked as part of the upcall made
    # by the middleware's event loop after it sees a timeout has
    # occurred.
    ########################################
    def invoke_operation(self):
        ''' Invoke operating depending on state  '''

        try:
            # self.logger.info("DiscoveryAppln::invoke_operation")

            # check what state are we in. If we are in REGISTERING state,
            # we continue to listen for registration requests.
            if (self.state == self.State.REGISTERING):
                # send a register msg to discovery service
                # self.logger.debug("DiscoveryAppln::invoke_operation - listening for registrations")
                return 0
            else:
                raise ValueError("Undefined state of the appln object")

            self.logger.info("DiscoveryAppln::invoke_operation completed")
        except Exception as e:
            raise e

    ########################################
    # handle register request method called as part of upcall
    #
    # As mentioned in class, the middleware object can do the reading
    # from socket and deserialization. But it does not know the semantics
    # of the message and what should be done. So it becomes the job
    # of the application. Hence, this upcall is made to us.
    ########################################
    def register_request(self, reg_req):
        ''' handle register response '''

        self.logger.info("DiscoveryAppln::register_request")
        if (reg_req.role == discovery_pb2.ROLE_BOTH):
            self.logger.debug("registering Broker = {}".format(reg_req.info.id))
            self.logger.debug("registering values = {}".format(reg_req.info))
            self.broker = reg_req
            return 0
        elif reg_req.role == discovery_pb2.ROLE_PUBLISHER:
            self.logger.debug("registering Pub = {}".format(reg_req.info.id))
            self.logger.debug("registering values = {}".format(reg_req.info))
            self.pub_dict[reg_req.info.id] = reg_req
            return 0
        elif reg_req.role == discovery_pb2.ROLE_SUBSCRIBER:
            self.logger.debug("registering Pub = {}".format(reg_req.info.id))
            self.logger.debug("registering values = {}".format(reg_req.info))
            self.sub_dict[reg_req.info.id] = reg_req
            return 0
        else:
            self.logger.debug("DiscoveryAppln::register_request - unknown registration role {}".format(
                reg_req.role))
            raise Exception("Unknown Role for registrant")

    ########################################
    # handle isready request method called as part of upcall
    #
    # Also a part of upcall handled by application logic
    ########################################
    def isready_request(self, isready_req):
        ''' handle isready request '''

        try:
            self.logger.info("DiscoveryAppln::isready_request")

            min_pubs_met = False
            min_subs_met = False
            broker_met = True

            self.logger.debug("registered Pubs = {}".format(len(self.pub_dict)))
            if self.num_pubs <= len(self.pub_dict):
                min_pubs_met = True

            self.logger.debug("registered Subs = {}".format(len(self.sub_dict)))
            if self.num_subs <= len(self.sub_dict):
                min_subs_met = True

            if self.is_broker_dissemination() and self.broker == None:
                broker_met = False

            if min_pubs_met and min_subs_met and broker_met:
                self.logger.info("Discovery Service Ready")
                self.logger.info(f"Pubs: {len(self.pub_dict)}, Subs: {len(self.sub_dict)}")
                return True

            self.logger.info("Discovery Service Not Ready")
            if (self.is_broker_dissemination()):
                self.logger.info(f"Pubs: {len(self.pub_dict)}, Subs: {len(self.sub_dict)}, Broker: {self.broker}")
            else:
                self.logger.info(f"Pubs: {len(self.pub_dict)}, Subs: {len(self.sub_dict)}")

            return False

        except Exception as e:
            raise e

    def lookup_pubs_topic_request(self, lookup_req):
        try:
            self.logger.info("DiscoveryAppln::lookup_pubs_topic_request")

            pubs_matching_topics = []

            if self.is_broker_dissemination():
                self.logger.info("Sending Broker as Pub".format(self.broker))
                return [self.broker.info]
            else:
                self.logger.info("Evaluating {} pubs".format(len(self.pub_dict)))
                for pub in self.pub_dict:
                    # self.logger.debug(x)
                    # self.logger.debug(self.pub_dict[x])

                    self.logger.debug("evaluating pub_dict")
                    self.logger.debug(
                        "DiscoveryAppln::lookup_pubs_topic_request evaluating pub: {}".format(self.pub_dict[pub]))
                    if any(x in lookup_req.topiclist for x in self.pub_dict[pub].topiclist):
                        self.logger.debug(
                            f"DiscoveryAppln::lookup_pubs_topic_request appending pub: {self.pub_dict[pub]}")
                        pubs_matching_topics.append(self.pub_dict[pub].info)

                self.logger.info("DiscoveryAppln::lookup_pubs_topic_request found {} pubs for topic".format(
                    len(pubs_matching_topics)))
                return pubs_matching_topics

        except Exception as e:
            raise e

    def lookup_all_pubs(self):
        try:
            self.logger.debug("DiscoveryAppln::lookup_all_pubs")
            pubs_matching_topics = []

            for pub in self.pub_dict:
                pubs_matching_topics.append(self.pub_dict[pub].info)

            self.logger.debug("DiscoveryAppln::lookup_all_pubs complete")
            return pubs_matching_topics
        except Exception as e:
            raise e

    ########################################
    # dump the contents of the object
    ########################################
    def dump(self):
        ''' Pretty print '''

        try:
            self.logger.info("**********************************")
            self.logger.info("DiscoveryAppln::dump")
            self.logger.info("------------------------------")
            self.logger.info("     Name: {}".format(self.name))
            self.logger.info("     Num Publishers: {}".format(self.num_pubs))
            self.logger.info("     Num Subscribers: : {}".format(self.num_subs))
            self.logger.info("**********************************")

            if self.dht_info is not None:
                ChordUtils.print_finger_table(self.dht_info, self.finger_table)
        except Exception as e:
            raise e


###################################
#
# Parse command line arguments
#
###################################
def parseCmdLineArgs():
    # instantiate a ArgumentParser object
    parser = argparse.ArgumentParser(description="Discovery Application")

    # Now specify all the optional arguments we support
    # At a minimum, you will need a way to specify the IP and port of the lookup
    # service, the role we are playing, what dissemination approach are we
    # using, what is our endpoint (i.e., port where we are going to bind at the
    # ZMQ level)

    parser.add_argument("-n", "--name", default="dis", help="Some name assigned to us.")

    parser.add_argument("-a", "--addr", default="localhost",
                        help="IP addr of this discovery server to advertise (default: localhost)")

    parser.add_argument("-p", "--port", type=int, default=5555,
                        help="Port number on which our underlying discovery service runs, default=5555")

    parser.add_argument("-P", "--num_pubs", type=int, choices=range(1, 10), default=1,
                        help="Number of publishers, currently restricted to max of 9")

    parser.add_argument("-S", "--num_subs", type=int, choices=range(1, 10), default=1,
                        help="Number of subscribers, currently restricted to max of 9")

    parser.add_argument("-c", "--config", default="config.ini", help="configuration file (default: config.ini)")

    parser.add_argument("-l", "--loglevel", type=int, default=logging.INFO,
                        choices=[logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR, logging.CRITICAL],
                        help="logging level, choices 10,20,30,40,50: default 20=logging.INFO")

    parser.add_argument("-j", "--json_file", default="dht48.json",
                        help="JSON file with the database of all DHT nodes, default dht8.json")

    return parser.parse_args()


###################################
#
# Main program
#
###################################
def main():
    try:
        # obtain a system-wide logger and initialize it to debug level to begin with
        logging.info("Main - acquire a child logger and then log messages in the child")
        logger = logging.getLogger("DiscoveryAppln")

        # first parse the arguments
        logger.debug("Main: parse command line arguments")
        args = parseCmdLineArgs()

        # reset the log level to as specified
        logger.debug("Main: resetting log level to {}".format(args.loglevel))
        logger.setLevel(args.loglevel)
        logger.debug("Main: effective log level is {}".format(logger.getEffectiveLevel()))

        # Obtain a discovery application
        logger.debug("Main: obtain the discovery appln object")
        dis_app = DiscoveryAppln(logger)

        # configure the object
        logger.debug("Main: configure the publisher appln object")
        dis_app.configure(args)

        # now invoke the driver program
        logger.debug("Main: invoke the publisher appln driver")
        dis_app.driver()

    except Exception as e:
        logger.exception("Exception caught in main - {}".format(e))
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
