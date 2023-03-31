###############################################
#
# Author: Aniruddha Gokhale
# Vanderbilt University
#
# Purpose: Skeleton/Starter code for the Broker application
#
# Created: Spring 2023
#
###############################################


# This is left as an exercise for the student.  The Broker is involved only when
# the dissemination strategy is via the broker.
#
# A broker is an intermediary; thus it plays both the publisher and subscriber roles
# but in the form of a proxy. For instance, it serves as the single subscriber to
# all publishers. On the other hand, it serves as the single publisher to all the subscribers.

import time   # for sleep
import argparse # for argument parsing
import configparser # for configuration parsing
import logging # for logging. Use it in place of print statements.
from threading import Thread
from topic_selector import TopicSelector

# Now import our CS6381 Middleware
from CS6381_MW.BrokerMW import BrokerMW
# We also need the message formats to handle incoming responses.
from CS6381_MW import discovery_pb2

# import any other packages you need.
from enum import Enum  # for an enumeration we are using to describe what state we are in
from Chord.chordutils import ChordUtils
from Chord.constants import *


##################################
#       BrokerAppln class
##################################
class BrokerAppln ():

    class State (Enum):
        INITIALIZE = 0,
        CONFIGURE = 1,
        REGISTER = 2,
        ISREADY = 3,
        LOOKUP_PUBS =4,
        CONSUME = 5,
        COMPLETED = 6

    ########################################
    # constructor
    ########################################
    def __init__ (self, logger):
        self.state = self.State.INITIALIZE # state that are we in
        self.name = None # our name (some unique name)
        self.port = None
        self.topiclist = None # the different topics that we publish on
        self.iters = None   # number of iterations of publication
        self.frequency = None # rate at which dissemination takes place
        self.lookup = None # one of the diff ways we do lookup
        self.dissemination = None # direct or via broker
        self.mw_obj = None # handle to the underlying Middleware object
        self.logger = logger  # internal logger for print statements

    ########################################
    # configure/initialize
    ########################################
    def configure (self, args):
        ''' Initialize the object '''

        try:
            # Here we initialize any internal variables
            self.logger.info ("BrokerAppln::configure")

            # set our current state to CONFIGURE state
            self.state = self.State.CONFIGURE

            # initialize our variables
            self.name = args.name # our name
            self.iters = args.iters  # num of iterations
            self.frequency = args.frequency # frequency with which topics are disseminated
            self.port = args.port

            # Choose a discovery node.  Start with the first one to make sure things are wired properly.
            dht_nodes = ChordUtils.to_sorted_dht_node_list(
                ChordUtils.load_json_data(os.path.join(os.path.dirname(__file__), 'Utils', args.json_file)))
            discover_node = dht_nodes[0]
            args.discovery = f"{discover_node.get(IP)}:{discover_node.get(PORT)}"
            self.logger.info(f"BrokerAppln::configure - discovery set to {discover_node} - {args.discovery}")

            # Now, get the configuration object
            try:
                self.logger.debug ("BrokerAppln::configure - parsing config.ini")
                config = configparser.ConfigParser ()
                self.logger.debug ("BrokerAppln::configure - config args {}".format(args.config))
                config.read (args.config)
                self.logger.debug ("BrokerAppln::configure - config sections {}".format(config.sections()))
                self.logger.debug ("BrokerAppln::configure - config.ini lookup")
                self.lookup = config["Discovery"]["Strategy"]
                self.logger.debug ("BrokerAppln::configure - config.ini dissemination")
                self.dissemination = config["Dissemination"]["Strategy"]
            except Exception as e:
                self.logger.exception ("BrokerAppln::configure - Trace {}".format(e))

            # Now get our topic list of interest
            self.logger.debug ("BrokerAppln::configure - selecting our topic list")
            ts = TopicSelector ()
            self.topiclist = ts.interest (len(ts.topiclist))  # let topic selector give us the desired num of topics

            # Now setup up our underlying middleware object to which we delegate
            # everything
            self.logger.debug ("BrokerAppln::configure - initialize the middleware object")
            self.mw_obj = BrokerMW (self.logger)
            self.mw_obj.configure (args) # pass remainder of the args to the m/w object

            self.logger.info ("BrokerAppln::configure - configuration complete")

        except Exception as e:
            raise e

    ########################################
    # driver program
    ########################################
    def driver (self):
        ''' Driver program '''

        try:
            self.logger.info ("BrokerAppln::driver")

            # dump our contents (debugging purposes)
            self.dump ()

            self.logger.debug ("BrokerAppln::driver - upcall handle")
            self.mw_obj.set_upcall_handle (self)


            self.logger.info ("BrokerAppln::driver - lookup = {}".format(self.dissemination))
            if self.dissemination == "Direct":
                self.logger.info ("BrokerAppln::driver - Exiting on Direct lookup")
                self.state = self.State.COMPLETED
            else:
                self.state = self.State.REGISTER

            self.mw_obj.event_loop (timeout=0)  # start the event loop

            self.logger.info ("BrokerAppln::driver completed")

        except Exception as e:
            raise e


    def invoke_operation (self):
        ''' Invoke operating depending on state  '''

        try:
            self.logger.info ("BrokerAppln::invoke_operation")
    
            if (self.state == self.State.REGISTER):
                # send a register msg to discovery service
                self.logger.debug ("BrokerAppln::invoke_operation - register with the discovery service")
                self.mw_obj.register (self.name, self.topiclist)
    
                return None
    
            elif (self.state == self.State.ISREADY):

                self.logger.debug ("BrokerAppln::invoke_operation - check if are ready to go")
                self.mw_obj.is_ready ()  # send the is_ready? request
    
                return None

            elif (self.state == self.State.LOOKUP_PUBS):
                self.logger.debug ("SubscriberAppln::invoke_operation - check for publishers to interested topics")
                self.mw_obj.lookup_pubs(self.topiclist)
                return None

            elif (self.state == self.State.CONSUME):
                for i in range (500):
                    t = Thread(target=self.mw_obj.consume, args=())
                    t.start()
                    t.join(timeout=20)

                self.state = self.State.COMPLETED
                return 0

            elif (self.state == self.State.COMPLETED):
    
                # we are done. Time to break the event loop. So we created this special method on the
                # middleware object to kill its event loop
                self.mw_obj.disable_event_loop ()
                return None
    
            else:
                raise ValueError ("Undefined state of the appln object")
    
            self.logger.info ("BrokerAppln::invoke_operation completed")
        except Exception as e:
            raise e

    def register_response (self, reg_resp):
        ''' handle register response '''

        try:
            self.logger.info ("BrokerAppln::register_response")
            if (reg_resp.status == discovery_pb2.STATUS_SUCCESS):
                self.logger.debug ("BrokerAppln::register_response - registration is a success")
    
                # set our next state to isready so that we can then send the isready message right away
                self.state = self.State.ISREADY
                return 0
    
            else:
                self.logger.debug ("BrokerAppln::register_response - registration is a failure with reason {}".format (response.reason))
                raise ValueError ("Publisher needs to have unique id")
    
        except Exception as e:
            raise e
    
        ########################################
        # handle isready response method called as part of upcall
        #
        # Also a part of upcall handled by application logic
        ########################################
    def isready_response (self, isready_resp):
        ''' handle isready response '''
    
        try:
            self.logger.info ("BrokerAppln::isready_response")
    
            # Notice how we get that loop effect with the sleep (10)
            # by an interaction between the event loop and these
            # upcall methods.
            if not isready_resp.status:
                # discovery service is not ready yet
                self.logger.debug ("BrokerAppln::driver - Not ready yet; check again")
                time.sleep (10)  # sleep between calls so that we don't make excessive calls
    
            else:
                self.state = self.State.LOOKUP_PUBS
    
            # return timeout of 0 so event loop calls us back in the invoke_operation
            # method, where we take action based on what state we are in.
            return 0
    
        except Exception as e:
            raise e

    def lookup_all_pubs_response (self, lookup_resp):
        try:
            self.logger.info ("SubscriberAppln::lookup_all_pubs_response")

            self.mw_obj.subscribe(self.topiclist, lookup_resp.pubs)

            self.state = self.State.CONSUME

            # return timeout of 0 so event loop calls us back in the invoke_operation
            # method, where we take action based on what state we are in.
            return 0

        except Exception as e:
            raise e

    def dump (self):
        ''' Pretty print '''

        try:
            self.logger.info ("**********************************")
            self.logger.info ("BrokerAppln::dump")
            self.logger.info ("------------------------------")
            self.logger.info ("     Name: {}".format (self.name))
            self.logger.info ("     Port: {}".format (self.port))
            self.logger.info ("     Lookup: {}".format (self.lookup))
            self.logger.info ("     Dissemination: {}".format (self.dissemination))
            self.logger.info ("     TopicList: {}".format (self.topiclist))
            self.logger.info ("     Iterations: {}".format (self.iters))
            self.logger.info ("     Frequency: {}".format (self.frequency))
            self.logger.info ("**********************************")
    
        except Exception as e:
            raise e


###################################
#
# Parse command line arguments
#
###################################
def parseCmdLineArgs():
    # instantiate a ArgumentParser object
    parser = argparse.ArgumentParser(description="Subscriber Application")

    # Now specify all the optional arguments we support
    # At a minimum, you will need a way to specify the IP and port of the lookup
    # service, the role we are playing, what dissemination approach are we
    # using, what is our endpoint (i.e., port where we are going to bind at the
    # ZMQ level)

    parser.add_argument("-n", "--name", default="broker", help="Some name assigned to us. Keep it unique per broker")

    parser.add_argument("-a", "--addr", default="localhost",
                        help="IP addr of this broker to advertise (default: localhost)")

    parser.add_argument("-p", "--port", type=int, default=5588,
                        help="Port number on which our underlying publisher ZMQ service runs, default=5588")

    parser.add_argument("-d", "--discovery", default="localhost:5555",
                        help="IP Addr:Port combo for the discovery service, default localhost:5555")

    parser.add_argument("-c", "--config", default="config.ini", help="configuration file (default: config.ini)")

    parser.add_argument ("-f", "--frequency", type=int,default=1, help="Rate at which topics disseminated: default once a second - use integers")

    parser.add_argument ("-i", "--iters", type=int, default=1000, help="number of publication iterations (default: 1000)")

    parser.add_argument("-l", "--loglevel", type=int, default=logging.INFO,
                        choices=[logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR, logging.CRITICAL],
                        help="logging level, choices 10,20,30,40,50: default 20=logging.INFO")

    parser.add_argument ("-j", "--json_file", default="dht8.json",
                         help="JSON file with the database of all DHT nodes, default dht8.json")

    return parser.parse_args()


###################################
#
# Main program
#
###################################
def main():
    try:
        # obtain a system wide logger and initialize it to debug level to begin with
        logging.info("Main - acquire a child logger and then log messages in the child")
        logger = logging.getLogger("BrokerAppln")

        # first parse the arguments
        logger.debug("Main: parse command line arguments")
        args = parseCmdLineArgs()

        # reset the log level to as specified
        logger.debug("Main: resetting log level to {}".format(args.loglevel))
        logger.setLevel(args.loglevel)
        logger.debug("Main: effective log level is {}".format(logger.getEffectiveLevel()))

        # Obtain a publisher application
        logger.debug("Main: obtain the broker appln object")
        pub_app = BrokerAppln(logger)

        # configure the object
        logger.debug("Main: configure the broker appln object")
        pub_app.configure(args)

        # now invoke the driver program
        logger.debug("Main: invoke the broker appln driver")
        pub_app.driver()

    except Exception as e:
        logger.error("Exception caught in main - {}".format(e))
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
