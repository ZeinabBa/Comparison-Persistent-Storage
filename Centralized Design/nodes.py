import random


# used to define failure points by iteration and stage
class Failure:
    def __init__(self, iteration, stage):
        self.iteration = iteration
        self.stage = stage


class App:

    def __init__(self, mips, ram, storage, deployment_time, iterations, app_data, app_num):
        self.mips = mips
        self.ram = ram
        self.storage = storage
        self.deployment_time = deployment_time
        self.execution_time = 0   # this is defined when the App is attached to a Node
        self.iterations = iterations
        self.original_iterations = iterations  # used for catastrophic failure case
        self.app_data = app_data  # quantity of data in kilo bytes
        self.app_num = app_num  # the number of the app which acts as the rds and app_data_array for a Node
        self.deployed = False  # set to true when app is deployed
        self.write_to_cs = 0  # 5 ms delay to write to central storage
        self.read_from_cs = 0  # 5 ms delay to read from central storage
        self.S = 0  # temporary variable in app
        self.failure = None

    # stage t0 of app, returns deployment time in ms if app is not deployed, else 0 ms
    def deploy_app(self):
        if not self.deployed:
            self.deployed = True
            return self.deployment_time
        return 0

    # stage t1, t3 and t5 of app
    def exec_app(self, iteration):
        if not self.deployed:
            return 0

        if iteration >= self.iterations:
            return 0
        self.S += 1
        return self.execution_time

    # stage t2 of app
    # writes data to central storage for this app's index (self.app_num)
    # Returns True of successful, else False
    def write_app(self, iteration):
        if not self.deployed:
            return False

        if iteration >= self.iterations:
            return False

        # update central storage array for this app
        Node.central_array[self.app_num] = self.S
        # TODO add time for this process
        return True

    # stage t4 of app
    # reads data from central storage from some storage
    # Returns True of successful, else False
    def read_external_app(self, iteration):
        if not self.deployed:
            return False

        if iteration >= self.iterations:
            return False
        # TODO add time for this process
        return True

    # adds the point where failure should occur according to iteration and stage
    def set_failure(self, failure):
        self.failure = failure

    # trigger failure if the iteration and stage matches, returns True if failure is invoked
    def invoke_failure(self, iteration, stage):
        if self.failure:
            if iteration == self.failure.iteration and stage == self.failure.stage:
                self.deployed = False
                self.iterations += 1   # add an iteration to compensate for failure
                self.S = 0
                return True
        return False

    # set up to be redeployed after Node failure
    def reset_app(self):
        self.deployed = False
        self.iterations += 1  # add iteration to make up for failure
        self.S = 0

    def zero_app(self):
        self.deployed = False
        self.iterations = self.original_iterations
        self.S = 0

    def add_node_mips(self, node_mips):
        # update execution time... the default execution time is from a table
        #  this is calculated depending on node it's on
        self.execution_time = (self.mips/node_mips)*1000  # execution time in milliseconds


class Node:
    central_array = []   # This holds the centralized array data for the centralized node, now accessible by all nodes
    replica_array = []   # This holds the replica array data
    failure_rate = 0.0
    num_failed_nodes = 0  # Keep track of numbers of failures of each component
    num_failed_apps = 0
    cs_failed = 0     # keep track of whether cs failed, set to 1 if failed
    replica_failed = 0   # keep track of whether replica failed, set to 1 if failed
    random_count = 0

    def __init__(self, mips, ram, storage, bw_start, bw_end, delay_start, delay_end, node_type, cloud_layer):
        self.mips = mips
        self.ram = ram
        self.storage = storage
        self.bw_start = bw_start   # start of the bandwidth range in Mbits per second
        self.bw_end = bw_end  # end of the bandwidth range in Mbits per second
        self.delay_start = delay_start  # start of the delay range in milliseconds
        self.delay_end = delay_end  # end of the delay range in milliseconds

        # self.app_data_array = []  # the app_data_array which gives how much data each app sends on the network
        self.cloud_layer = cloud_layer  # set to true or false.   A cloud layer can't have apps
        self.apps = []  # the set of apps connected to this Node
        # self.sc_deployment_time = 100  # 100 ms
        # self.sc_deployed = False  # set true with the SC is deployed
        self.node_deployed = False
        # self.fetch_from_rds = 0  # 5 ms to fetch data from rds
        self.node_failure = None
        # self.sc_failure = None
        self.node_num = -1  # The number of this node on its layer
        #  New parameters 5/19/23, 7:21 p.m.
        self.node_type = node_type  # defaults to N, but can also be CS (Centralized Storage) or R (Replica)
        # self.central_array = []  # holds the storage for the centralized system, or replica, otherwise unused

    # set this node up for failure at an iteration and stage
    def set_node_failure(self, failure):
        self.node_failure = failure

    # add application if it fits on the node.  Return True if it fits, else False
    def add_app(self, app):

        # Can't add app to Central Storage node nor Replica Node
        if self.node_type == "CS" or self.node_type == "R":
            return False

        # If app fits, reduce node's values to indicate resources remaining.
        if app.mips <= self.mips and app.ram <= self.ram and app.storage <= self.storage:
            self.mips -= app.mips
            self.ram -= app.ram
            self.storage -= app.storage
            self.apps.append(app)
            # add the node mips to application to update its execution time
            app.add_node_mips(self.mips)
            return True
        return False

    # find the maximum number of iterations the apps on this node have
    def get_max_iterations(self):
        max_iterations = 0
        for app in self.apps:
            iter = app.iterations
            if iter > max_iterations:
                max_iterations = iter
        return max_iterations

    # Check if there will be a failure on this node from any element
    def does_failure_exist(self):
        pass
        if self.node_failure:
            return True

        for app in self.apps:
            if app.failure:
                return True
        return False

    def add_failure(self, failure_type, iteration):
        if self.does_failure_exist():
            return 0

        stage = random.randint(1, 5)
        failure = Failure(iteration, stage)
        failure_count = 0
        if failure_type == "node":
            self.set_node_failure(failure)

            failure_count = 1
            for app in self.apps:
                if iteration < app.iterations:
                    failure_count += 1
                    app.set_failure(failure)

        elif failure_type == "app" and len(self.apps) != 0:
            idx = random.randint(0, len(self.apps) - 1)

            app = self.apps[idx]  # .set_failure(failure)
            its = random.randint(0, app.iterations - 1)
            failure = Failure(its, stage)
            app.set_failure(failure)
            failure_count = 1
        return failure_count

    def get_app_count(self):
        return len(self.apps)

    def deploy_node(self):
        if not self.node_deployed:
            self.node_deployed = True
            # since node was not deployed, app must be redeployed
            for app in self.apps:
                app.deployed = False

    # stage t0 of app
    def deploy_app(self):
        tmax = 0
        for app in self.apps:
            t = app.deploy_app()
            if t > tmax:
                tmax = t
        return tmax

    #  returns bandwidth in kilobytes per millisecond
    #  selects from a range after converting to kilobytes per millisecond
    def get_random_bw(self):
        # Convert megabits per second to bytes per second
        #  multiply by 1000000 for mega bits, divide by 1000 for milliseconds, and divide by 8 for bytes
        # for kilobytes per millisecond:
        #  There are bw_start times 1000 kilo bits per second, and divide by 8 for bytes, divide
        #  by 1000 for milliseconds,  the 1000/1000 = 1, so just divide by 8 for bytes
        bw_start = self.bw_start / 8   # convert to kilobytes per millisecond
        bw_end = self.bw_start / 8  # convert to kilobytes per millisecond
        return random.randint(self.bw_start, self.bw_end)

    def get_random_delay(self):
        return random.uniform(self.delay_start, self.delay_end)

    # The app_data_size (message size) in kilobytes of an application on this node
    def link_delay(self, app_data_size):
        latency = self.get_random_delay()
        bw = self.get_random_bw()
        bw_delay = app_data_size/bw
        L = latency + bw_delay   # The link delay
        return L

    # apps write to central storage
    # Stage 2, and returns the link delay
    def apps_write_to_cs(self, iteration, central_storage_node):
        if not self.node_deployed:
            return 0

        tmax = 0
        for app in self.apps:
            if app.deployed:
                # if app data successfully written, compute the link delay time and return it
                if app.write_app(iteration):
                    t = central_storage_node.link_delay(app.app_data)
                    if t > tmax:
                        tmax = t
        return tmax

    # stage t1, t3 and t5 of app
    def apps_execute(self, iteration):
        if not self.node_deployed:
            return 0
        tmax = 0
        for app in self.apps:
            t = app.exec_app(iteration)
            if t > tmax:
                tmax = t
        return tmax

    # apps write to central storage
    # Stage 2 and returns the link delay
    def apps_read_from_cs(self, iteration, central_storage_node):
        if not self.node_deployed:
            return 0

        tmax = 0
        for app in self.apps:
            if app.deployed:
                # if app data successfully written, compute the link delay time and return it
                if app.read_external_app(iteration):
                    t = central_storage_node.link_delay(app.app_data)
                    if t > tmax:
                        tmax = t
        return tmax

    # only applicable to the central storage node
    def update_replica(self, edge_fog_layer, replica_node):
        l = len(Node.central_array)
        i = 0
        tmax = 0

        # go through all nodes of edge_fog_layer
        # replicate and determine link delay
        for node in edge_fog_layer:
            for app in node.apps:
                Node.replica_array[app.app_num] = Node.central_array[app.app_num]
                t = replica_node.link_delay(app.app_data)
                if t > tmax:
                    tmax = t

        return tmax

    # triggers failure for anything that is set to fail according to stage or iteration
    # returns true if failure is invoked
    def invoke_failure(self, iteration, stage):

        layer_name = "edge-fog layer"
        if self.cloud_layer:
            layer_name = "cloud layer"

        if self.node_failure:
            if iteration == self.node_failure.iteration and stage == self.node_failure.stage:
                self.node_deployed = False
                if self.node_type == "CS":
                    Node.cs_failed = 1
                elif self.node_type == "R":
                    Node.replica_failed = 1
                else:
                    Node.num_failed_nodes += 1

                fail_info = f"Node {self.node_num} failed on {layer_name}, iteration={iteration}, stage={stage}\n"

                # make sure all apps fail so that they are redeployed
                for app in self.apps:
                    if iteration < app.iterations:
                        fail_info += f" app {app.app_num} failed\n"
                        app.reset_app()
                        Node.num_failed_apps += 1

                return True, fail_info

        failure_state = False
        fail_info = ""
        for app in self.apps:
            result = app.invoke_failure(iteration, stage)
            if result:
                fail_info += f"App {app.app_num} failed on Node {self.node_num} of {layer_name}, " \
                             f"iteration={iteration}, stage={stage}\n"
                failure_state = True
                Node.num_failed_apps += 1

        return failure_state, fail_info

    # zero the arrays for catastrophic failure case
    # zeros central and replica arrays and all apps
    # everything goes back to the start
    def zero_storage_nodes(self):
        l = len(Node.central_array)
        i = 0
        while i < l:
            Node.central_array[i] = 0
            Node.replica_array[i] = 0
            i += 1

    # used for the catastrophic failure case
    def zero_apps(self):
        for app in self.apps:
            app.zero_app()


