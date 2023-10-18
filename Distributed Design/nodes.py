import random


# used to define failure points by iteration and stage
class Failure:
    def __init__(self, iteration, stage):
        self.iteration = iteration
        self.stage = stage


class App:

    def __init__(self, mips, ram, storage, deployment_time, execution_time, iterations, app_data, app_num):
        self.mips = mips
        self.ram = ram
        self.storage = storage
        self.deployment_time = deployment_time
        self.execution_time = execution_time   # this table value is changed when app is attached to a node
        self.iterations = iterations
        self.app_data = app_data  # quantity of data in kilo bytes
        self.app_num = app_num  # the number of the app which acts as the rds and app_data_array for a Node
        self.deployed = False  # set to true when app is deployed
        self.write_to_rds = 0  # 5 ms delay to write to rds
        self.read_from_rds = 0  # 5 ms delay to read from rds
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
    def write_app(self, rds, iteration):
        if not self.deployed:
            return 0

        if iteration >= self.iterations:
            return 0
        rds[self.app_num] = self.S
        return self.write_to_rds

    # stage t4 of app
    def read_external_app(self, iteration):
        if not self.deployed:
            return 0

        if iteration >= self.iterations:
            return 0
        return self.read_from_rds

    # adds the point where failure should occur according to iteration and stage
    def set_failure(self, failure):
        self.failure = failure

    # trigger failure if the iteration and stage matches, returns True if failure is invoked
    def invoke_failure(self, iteration, stage):
        if self.failure:
            if iteration == self.failure.iteration and stage == self.failure.stage:
                self.deployed = False
                # self.iterations += 1   # add an iteration to compensate for failure
                self.S = 0
                return True
        return False

    # set up to be redeployed after Node failure
    def reset_app(self):
        self.deployed = False
        # self.iterations += 1
        self.S = 0

    def add_node_mips(self, node_mips):
        # update execution time... the default execution time is from a table
        #  this is calculated depending on node it's on

        et = self.execution_time
        self.execution_time = (self.mips/node_mips)*1000  # execution time in milliseconds
        print(f" add_node_mips: old execution_time: {et}, new execution_time {self.execution_time}")



class Node:
    failure_rate = 0.0
    num_failed_nodes = 0  # Keep track of numbers of failures of each component
    num_failed_scs = 0
    num_failed_apps = 0
    random_count = 0

    def __init__(self, mips, ram, storage, bw_start, bw_end, delay_start, delay_end, leader, cloud_layer):
        self.mips = mips
        self.ram = ram
        self.storage = storage
        self.bw_start = bw_start   # start of the bandwidth range in Mbits per second
        self.bw_end = bw_end  # end of the bandwidth range in Mbits per second
        self.delay_start = delay_start  # start of the delay range in milliseconds
        self.delay_end = delay_end  # end of the delay range in milliseconds
        self.leader = leader  # true or false
        self.rds = []   # The rds: replicated data structure array
        self.app_data_array = []  # the app_data_array which gives how much data each app sends on the network
        self.cloud_layer = cloud_layer  # set to true or false.   A cloud layer can't have apps
        self.apps = []  # the set of apps connected to this Node
        self.sc_deployment_time = 100  # 100 ms
        self.sc_deployed = False  # set true with the SC is deployed
        self.node_deployed = False
        self.fetch_from_rds = 0  # 5 ms to fetch data from rds
        self.node_failure = None
        self.sc_failure = None
        self.node_num = -1  # The number of this node on its layer

    def deploy_node(self):
        if not self.node_deployed:
            self.node_deployed = True
            # since node was not deployed, both app and sc must be redeployed
            self.sc_deployed = False
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

    #  stage t0 of SC and Leader
    def deploy_sc(self):
        if self.sc_deployed:
            return 0
        self.sc_deployed = True
        return self.sc_deployment_time

    # Check if there will be a failure on this node from any element
    def does_failure_exist(self):
        pass
        if self.node_failure:
            return True

        if self.sc_failure:
            return True

        for app in self.apps:
            if app.failure:
                return True
        return False

    # returns True of there is an app on this node
    def does_app_exist(self):
        for app in self.apps:
            return True
        return False

    # add a failure to the next stage, and iteration if necessary
    def add_random_failure(self, iteration):
        return
        # Node.random_count += 1
        r = random.random()
        # print(f"count = {Node.random_count}, random r = {r}, fr = {Node.failure_rate}")
        if r == 0.0 or r > Node.failure_rate or self.does_failure_exist():
            return

        stage = random.randint(1, 5)
        failure = Failure(iteration, stage)
        components = 2
        components += len(self.apps)
        r = random.randint(1, components)

        if components == 2:
            if Node.num_failed_nodes < Node.num_failed_scs:
                # Node.num_failed_nodes += 1
                self.set_node_failure(failure)
            else:
                # Node.num_failed_scs += 1
                self.set_sc_failure(failure)
        else:
            if Node.num_failed_nodes < Node.num_failed_scs and Node.num_failed_nodes < Node.num_failed_apps:
                # Node.num_failed_nodes += 1
                self.set_node_failure(failure)
            elif Node.num_failed_scs < Node.num_failed_nodes and Node.num_failed_scs < Node.num_failed_apps:
                # Node.num_failed_scs += 1
                self.set_sc_failure(failure)
            else:
                # Node.num_failed_apps += 1
                idx = random.randint(1, len(self.apps)) - 1
                self.apps[idx].set_failure(failure)

    def add_failure(self, failure_type, iteration):
        if self.does_failure_exist():
            return 0

        stage = random.randint(1, 5)
        failure = Failure(iteration, stage)
        failure_count = 0
        if failure_type == "node":
            self.set_node_failure(failure)
            self.set_sc_failure(failure)

            failure_count = 2
            for app in self.apps:
                if iteration < app.iterations:
                    failure_count += 1
                    app.set_failure(failure)

        elif failure_type == "sc":
            self.set_sc_failure(failure)
            failure_count = 1
        elif failure_type == "app" and len(self.apps) != 0:
            idx = random.randint(0, len(self.apps) - 1)

            app = self.apps[idx]  # .set_failure(failure)
            its = app.iterations
            its2 = random.randint(0, its - 1)
            failure = Failure(its2, stage)
            app.set_failure(failure)
            failure_count = 1
        return failure_count

    # triggers failure for anything that is set to fail according to stage or iteration
    # returns true if failure is invoked
    def invoke_failure(self, iteration, stage):

        layer_name = "edge-fog layer"
        if self.cloud_layer:
            layer_name = "cloud layer"

        if self.node_failure:
            if iteration == self.node_failure.iteration and stage == self.node_failure.stage:
                self.node_deployed = False
                self.sc_deployed = False
                Node.num_failed_nodes += 1
                Node.num_failed_scs += 1

                fail_info = f"Node {self.node_num} failed on {layer_name}, iteration={iteration}, stage={stage}\n"

                # make sure all apps fail so that they are redeployed
                for app in self.apps:
                    if iteration < app.iterations:
                        fail_info += f" app {app.app_num} failed\n"
                        app.reset_app()
                        Node.num_failed_apps += 1
                l = len(self.rds)
                i = 0
                # set rds array to zero
                while i < l:
                    self.rds[i] = 0
                    i += 1
                return True, fail_info

        elif self.sc_failure:
            if iteration == self.sc_failure.iteration and stage == self.sc_failure.stage:
                fail_info = f"SC failed on Node {self.node_num} of {layer_name}, iteration={iteration}, stage={stage}\n"
                self.sc_deployed = False
                Node.num_failed_scs += 1
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

    # stage t1, t3 and t5 of app
    def exec_app(self, iteration, stage):
        if not self.node_deployed:
            return 0

        tmax = 0
        for app in self.apps:
            t = app.exec_app(iteration)
            if t > tmax:
                tmax = t

        return tmax

    # stage t2 of app
    def write_app(self, iteration, stage):
        if not self.node_deployed:
            return 0

        tmax = 0
        for app in self.apps:
            t = app.write_app(self.rds, iteration)
            if t > tmax:
                tmax = t

        return tmax

    # stage t3 of sc and leader (fetches RDS data for this app
    def fetch_sc(self, iteration, stage):
        if not self.node_deployed:
            return 0

        if not self.sc_deployed:
            return 0

        return self.fetch_from_rds

    # stage t4 of app
    def read_external_app(self, iteration, stage):
        if not self.node_deployed:
            return 0

        tmax = 0
        for app in self.apps:
            t = app.read_external_app(iteration)
            if t > tmax:
                tmax = t
        return tmax

    # stage 4 of app
    def send_to_leader(self, leader_node, iteration, stage):
        # if it's the leader or of sc is not deployed, do nothing
        if self.leader or not self.sc_deployed or not self.node_deployed:
            return 0

        # if the leader node is not deployed, then data can't be sent
        if not leader_node.node_deployed or not leader_node.sc_deployed:
            return 0

        latency = leader_node.get_random_delay()
        bw = leader_node.get_random_bw()
        tmax = 0
        for app in self.apps:
            # if app.deploy_app:  # the data is sent by the sc to the leader, so the app isn't involved,
            # that's my assumption
            leader_node.rds[app.app_num] = self.rds[app.app_num]  # update leader with rds slot value for app
            data_size = app.app_data
            bw_delay = data_size / bw
            t = latency + bw_delay  # equation from page 3 of Storage access pdf, L(Dk, Dj)
            if t > tmax:
                tmax = t

        return tmax

    # stage 5 of app, pass in node_leader
    def broadcast(self, leader_node, iteration, stage):
        if self.leader or not self.node_deployed or not self.sc_deployed:
            return 0

        # if the leader node is not deployed, then data can't be sent
        if not leader_node.node_deployed or not leader_node.sc_deployed:
            return 0

        # duplicate the rds from the leader
        self.add_rds(leader_node.rds.copy())
        latency = leader_node.get_random_delay()
        bw = leader_node.get_random_bw()
        tmax = 0
        for data in self.app_data_array:
            # if app.deploy_app: # the data is sent by the sc to the leader, so the app isn't involved,
            # that's my assumption
            data_size = data
            bw_delay = data_size/bw
            t = latency + bw_delay   # equation from page 3 of Storage access pdf, L(Dk, Dj)
            if t > tmax:
                tmax = t

        return tmax

    # add application if it fits on the node.  Return True if it fits, else False
    def add_app(self, app):
        if app.ram <= self.ram and app.storage <= self.storage:
            # self.mips -= app.mips
            self.ram -= app.ram
            self.storage -= app.storage
            self.apps.append(app)
            # add the node mips to application to update its execution time
            app.add_node_mips(self.mips)
            return True
        return False

    # attach the rds array for the applications
    def add_rds(self, rds):
        self.rds = rds

    # attach the data_array for the quantity of data sent for each application. This will be in kilobytes
    def add_app_data_array(self, data_array):
        self.app_data_array = data_array

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

    # determine if the passed in rds array is equal to the self.rds array of this node
    # return True if it is, False if it is not
    def rds_equal(self, rds):
        l = len(rds)
        i = 0
        while i < l:
            if rds[i] != self.rds[i]:
                return False
            i +=1
        return True

    def print_rds(self):
        print(self.rds)

    def get_max_iterations(self):
        max_iterations = 0
        for app in self.apps:
            iter = app.iterations
            if iter > max_iterations:
                max_iterations = iter
        return max_iterations

    def set_node_failure(self, failure):
        self.node_failure = failure

    def set_sc_failure(self, failure):
        self.sc_failure = failure

    def add_iteration_to_apps(self):
        for app in self.apps:
            app.iterations += 1

    # returns string with node data
    def node_data(self):
        data_string = ""

        for app in self.apps:
            data_string += "  app number: " + str(app.app_num) + "\n"
        return data_string

    def print_failure(self, component, iteration, stage):
        info = component + " failed: iteration = " + iteration + ", stage = " + stage + "\n"
        print(info)

