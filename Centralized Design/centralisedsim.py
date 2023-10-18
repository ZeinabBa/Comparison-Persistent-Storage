# This is a sample Python script.
from nodes import Node, App, Failure
import logging
from datetime import datetime
import sys
import random


# if state is 'l' the info is logged according to logging settings
# if the state is 'p' it just prints to screen
# If the state is other it does both
def log(data_string, state='o'):

    if state.lower() == "l":
        logging.info(data_string)
    elif state.lower() == "p":
        print(data_string)
    else:
        logging.info(data_string)
        print(data_string)


def get_failure_rate(line):
    failure_rate = float(line)
    failure_rate /= 100.0
    return failure_rate


def create_nodes(line, nodes, cloud_layer):
    params = line.split(",")
    l = len(params)
    i = 0
    while i < l:
        params[i] = params[i].strip()
        i += 1

    number_of_nodes = int(params[0][1:])
    mips = float(params[1])
    ram = float(params[2])
    storage = float(params[3])

    bw_range = params[4].split('-')
    bw_start = int(bw_range[0])
    bw_end = int(bw_range[1])

    delay_range = params[5].split('-')
    delay_start = float(delay_range[0])
    delay_end = float(delay_range[1])
    leader = False
    node_type = "N"  # default
    if params[6].lower() == "cs":
        node_type = "CS"
    elif params[6].lower() == "r":
        node_type = "R"

    node_failure = False

    failure = None
    # add failure to node (this only works when one node is defined, because can't add to more than one at once)
    #  failures are set at the end of a line, so there will be 10 parameters
    if number_of_nodes == 1 and l == 10:
        if params[7].lower() == "f:node":
            node_failure = True

        iteration = int(params[8])
        stage = int(params[9])
        failure = Failure(iteration, stage)

    i = 0
    while i < number_of_nodes:
        node = Node(mips, ram, storage, bw_start, bw_end, delay_start, delay_end, node_type, cloud_layer)
        if node_failure:
            node.set_node_failure(failure)

        nodes.append(node)
        i += 1


def create_apps(line, apps):
    # print(line)
    params = line.split(",")
    l = len(params)
    i = 0
    while i < l:
        params[i] = params[i].strip()
        i += 1

    number_of_apps = int(params[0][1:])
    mips = float(params[1])
    ram = float(params[2])
    storage = float(params[3])
    deployment_time = int(params[4])
    # exec_time = int(params[5])
    iterations = int(params[5])

    data_size = float(params[6][:-2])
    decimal_place = params[6][-2:]
    # convert all data sizes to kilobytes
    if decimal_place.lower() == "mb":
        data_size *= 1000  # megabytes to kilobyte size

    app_failure = False
    failure = None
    if number_of_apps == 1 and l == 11:
        if params[8].lower() == "f":
            app_failure = True
            iteration = int(params[9])
            stage = int(params[10])
            # failure = Failure(iteration, stage)

    i = 0
    while i < number_of_apps:
        app_num = len(apps)  # this is the unique index value given to this app
        app = App(mips, ram, storage, deployment_time, iterations, data_size, app_num)
        if app_failure:
            app.set_failure(failure)
        apps.append(app)
        i += 1


def parse_script(script):
    edge_fog_layer = []
    cloud_layer = []
    apps = []
    failure_rate = 0.0

    state = "start"

    for line in script:
        line = line[:-1].strip()
        if len(line) != 0:
            if line[0] == '#':
                continue

            if line.lower() == "cloud layer":
                state = "cloud"
            elif line.lower() == "layer":
                state = "layer"
            elif line.lower() == "apps":
                state = "apps"
            elif line.lower() == "failure rate":
                state = "failure rate"
            else:
                if state == "cloud":
                    create_nodes(line, cloud_layer, True)
                elif state == "layer":
                    create_nodes(line, edge_fog_layer, False)
                elif state == "apps":
                    create_apps(line, apps)
                elif state == "failure rate":
                    failure_rate = get_failure_rate(line)

    # enumerate the nodes for each layer
    num = 0
    for node in edge_fog_layer:
        node.node_num = num
        num += 1

    for node in cloud_layer:
        node.node_num = num
        num += 1

    return cloud_layer, edge_fog_layer, apps, failure_rate


# This adds apps to the edge_fog_layer
def add_apps(edge_fog_layer, apps):
    idx = 0

    for app in apps:
        l = len(edge_fog_layer)
        start_idx = idx
        break_out = False
        # Iterate through each node to find a free spot for an app, once cycle through layer max per app
        while idx < l:
            if edge_fog_layer[idx].add_app(app):
                break_out = True

            idx += 1
            if idx >= l:
                idx = 0

            if break_out:
                break
            # failed to add app
            elif idx == start_idx:
                break


def get_last_iteration(edge_fog_layer):
    last_iteration = 0
    for node in edge_fog_layer:
        itr = node.get_max_iterations()
        if itr > last_iteration:
            last_iteration = itr
    return last_iteration


def add_failures(cloud_layer, edge_fog_layer, apps, failure_rate):
    num_cnodes = len(cloud_layer)
    num_fnodes = len(edge_fog_layer)
    num_apps = len(apps)

    # the -2 below is for the Centralized Storage and Replica Nodes
    # neither of which can fail randomly, only manually
    num_to_fail = failure_rate*(num_apps + num_cnodes + num_fnodes - 2)
    last_iteration = get_last_iteration(edge_fog_layer)
    print(f" number to fail = {num_to_fail}")
    node_count = 0
    sc_count = 0
    app_count = 0

    i = 0
    c = 0
    # iteration limits, 20% failure rate limit, nodes cause apps 1 sc to fail and 0 or more apps
    #  if a node has a failed app on it, I will not fail the node
    # I'll add all failed nodes first...  after that I will add failed SCs and Apps to non-failed nodes
    #

    # add node failures first.  I'll make 1/4 of failures node failures
    node_count = num_to_fail / 4
    c = 0
    i = 0
    total_fails = 0
    loop_limit = num_to_fail * 10  # fail safe to make sure that it doesn't get stuck in the loop
    count = 0
    # add node failures, which will include scs and probably apps
    while c < node_count:
        if i == 0:
            i = 1
            idx = random.randint(0, num_fnodes - 1)
            node = edge_fog_layer[idx]
            # can't add failure to CS or Replica node and can't already have failure added
            if not node.node_failure and node.node_type == "N":
                itr = random.randint(0, last_iteration - 1)
                fc = node.add_failure("node", itr)
                total_fails += fc
                c += 1

        else:
            i = 0
            if num_cnodes != 0:
                idx = random.randint(0, num_cnodes - 1)
                node = cloud_layer[idx]
                # can't add failure to CS or Replica node and can't already have failure added
                if not node.node_failure and node.node_type == "N":
                    itr = random.randint(0, last_iteration - 1)
                    fc = node.add_failure("node", itr)
                    total_fails += fc
                    c += 1
        if total_fails > num_to_fail:
            return total_fails
        count += 1
        if count > loop_limit:
            break

    count = 0
    # add failures for apps and scs
    while total_fails < num_to_fail:
        idx = random.randint(0, num_fnodes - 1)
        node = edge_fog_layer[idx]
        if not node.node_failure and node.get_app_count() > 0:
            # passing in '1' for iteration of "app", because
            # the node.add_failure() function randomly selects an iteration for apps
            fc = node.add_failure("app", 1)
            total_fails += fc

        count += 1
        if count > loop_limit:
            return total_fails

    return total_fails


# Display the central storage and replica nodes
def display_cs_and_r(cloud_layer, edge_fog_layer):
    data = ""
    if len(cloud_layer) == 0:
        for node in edge_fog_layer:
            if node.node_type == "CS":
                data += "\nThe Central Storage is on edge_fog layer, node " + str(node.node_num) + "\n"
            elif node.node_type == "R":
                data += "\nThe Replica is on edge_fog layer, node " + str(node.node_num) + "\n"
    else:
        for node in cloud_layer:
            if node.node_type == "CS":
                data += "\nThe Centralized Storage is on cloud layer, node " + str(node.node_num) + "\n"
            elif node.node_type == "R":
                data += "\nThe Replica is on cloud layer, node " + str(node.node_num) + "\n"
    log(data)
    return data


def layer_info(edge_fog_layer):
    data = "Edge & Fog Layer Nodes:\n"
    for node in edge_fog_layer:
        data += " node: " + str(node.node_num) + "\n"
        for app in node.apps:
            data += "  app number: " + str(app.app_num) + "\n"
        if len(node.apps) == 0:
            data += "  empty\n"
    log(data)


# Find the central storage node and return it
# If not found, return None
def get_central_storage_node(cloud_layer, edge_fog_layer):
    for node in cloud_layer:
        if node.node_type == "CS":
            return node

    for node in edge_fog_layer:
        if node.node_type == "CS":
            return node
    return None


# Find the replica node and return it
# If not found, return None
def get_replica_node(cloud_layer, edge_fog_layer):
    for node in cloud_layer:
        if node.node_type == "R":
            return node

    for node in edge_fog_layer:
        if node.node_type == "R":
            return node
    return None


# triggers any failures for any component on this iteration and at this stage
def update_failures(cloud_layer, edge_fog_layer, iteration, stage):
    for node in cloud_layer:
        r, failure_info = node.invoke_failure(iteration, stage)
        if r:
            log(failure_info)

    for node in edge_fog_layer:
        r, failure_info = node.invoke_failure(iteration, stage)
        if r:
            log(failure_info)


def central_store_failure(edge_fog_layer, central_storage_node, replica_node, number_of_apps):
    failure_time = 0
    catastrophic_failure = False
    if not central_storage_node.node_deployed and not replica_node.node_deployed:
        failure_time = 60.0 * number_of_apps * 0.1 * 1000  # in milliseconds
        central_storage_node.node_deployed = True
        replica_node.node_deployed = True

        # set everything back to zer
        central_storage_node.zero_storage_nodes()
        for node in edge_fog_layer:
            node.zero_apps()
        catastrophic_failure = True

    elif not central_storage_node.node_deployed:
        failure_time = number_of_apps * 0.1 * 1000  # in milliseconds
        central_storage_node.node_deployed = True
    elif not replica_node.node_deployed:
        None

    return failure_time, catastrophic_failure


# prints out the simulation data.   Each iteration is stored in a list
# each list contains the info for an iteration
#  iteration_data = [iteration, t0, t1, t2, t3, t4, t5, t6, failure_time, t_iteration]
def print_simulation_data2(simulation_data):
    for id in simulation_data:
        log(f" iteration {id[0]}) t0={id[1]:.2f}, t1={id[2]:.2f}, t2={id[3]:.2f}, t3={id[4]:.2f} ")
        log(f"   t4={id[5]:.2f}, t5={id[6]:.2f}, t6={id[7]:.2f}, failure_time={id[8]:.2f}")
        log(f"   total iteration time = {id[9]:.2f}\n")


# prints out the simulation data.   Each iteration is stored in a list
# each list contains the info for an iteration
#  iteration_data = [iteration, t0, t1, t2, t3, t4, t5, t6, failure_time, t_iteration]
def print_simulation_data(simulation_data):
    best = simulation_data[0][9]
    worst = simulation_data[0][9]
    count = 0
    sum_values = 0
    average = 0
    for id in simulation_data:
        d = id[9]
        sum_values += d
        count += 1
        if d > worst:
            worst = d
        if d < best:
            best = d

    if count > 0:
        average = sum_values/count

    log(f"response-time: worst={worst:.2f} ms, average={average:.2f} ms, best={best:.2f} ms")
    log("Data access times and Replication times for each iteration:")
    for id in simulation_data:
        data_access_time = id[3] + id[5]   # i.e. T2 + T4
        log(f" {id[0]}) Data access:{data_access_time:.2f} ms, Replication:{id[7]:.2f} ms, failure_time={id[8]:.2f}")
        log(f"    t0:{id[1]:.2f}, t1:{id[2]:.2f}, t2:{id[3]:.2f}, t3:{id[4]:.2f}, t4:{id[5]:.2f}, t5:{id[6]:.2f}, "
            f"total time = {id[9]:.2f}")  # The "total time" is the total time of this iteration


def run_simulation(cloud_layer, edge_fog_layer, number_of_apps):
    #  I need to do this for two cases: with just edge_fog_layer and with both layers
    iteration = 0
    loop = True
    tsync = 0
    sync_times = []
    last_iteration = get_last_iteration(edge_fog_layer)
    total_operation_time = 0  # operation time aka simulation time
    store_iteration_info = []
    central_storage_node = get_central_storage_node(cloud_layer, edge_fog_layer)
    replica_node = get_replica_node(cloud_layer, edge_fog_layer)
    simulation_data = []
    t0 = t1 = t2 = t3 = t4 = t5 = t6 = 0.0
    failure_time = 0  # failure time
    catastrophic_failure = False

    while loop:

        t0 = t1 = t2 = t3 = t4 = t5 = t6 = 0.0

        failure_time = 0  # failure time
        # t0  Deploy Apps
        t0 = 0
        for node in edge_fog_layer:
            node.deploy_node()
            t = node.deploy_app()

            if t > t0:
                t0 = t

        for node in cloud_layer:
            node.deploy_node()

        # t1 App Exec (S=1)
        t1 = 0
        update_failures(cloud_layer, edge_fog_layer, iteration, 1)
        ft, catastrophic_failure = central_store_failure(edge_fog_layer, central_storage_node, replica_node,
                                                         number_of_apps)
        failure_time += ft
        if catastrophic_failure:

            break

        for node in edge_fog_layer:
            t = node.apps_execute(iteration)
            if t > t1:
                t1 = t

        # t2 App Write S
        t2 = 0

        update_failures(cloud_layer, edge_fog_layer, iteration, 2)
        ft, catastrophic_failure = central_store_failure(edge_fog_layer, central_storage_node, replica_node,
                                                         number_of_apps)
        failure_time += ft
        if catastrophic_failure:
            break

        for node in edge_fog_layer:
            t = node.apps_write_to_cs(iteration, central_storage_node)
            # t = node.write_app(iteration, 2)
            if t > t2:
                t2 = t

        # t3 App Exec
        t3 = 0
        update_failures(cloud_layer, edge_fog_layer, iteration, 3)
        ft, catastrophic_failure = central_store_failure(edge_fog_layer, central_storage_node, replica_node,
                                                         number_of_apps)
        failure_time += ft
        if catastrophic_failure:
            break

        for node in edge_fog_layer:
            t = node.apps_execute(iteration)
            if t > t3:
                t3 = t

        # t4 App Read from CS
        t4 = 0
        update_failures(cloud_layer, edge_fog_layer, iteration, 4)
        ft, catastrophic_failure = central_store_failure(edge_fog_layer, central_storage_node, replica_node,
                                                         number_of_apps)
        failure_time += ft
        if catastrophic_failure:
            break

        # update_failures(cloud_layer, edge_fog_layer, leader_node, iteration, 2)
        for node in edge_fog_layer:
            t = node.apps_read_from_cs(iteration, central_storage_node)
            if t > t4:
                t4 = t

        # t5 App Exec
        t5 = 0
        update_failures(cloud_layer, edge_fog_layer, iteration, 5)
        ft, catastrophic_failure = central_store_failure(edge_fog_layer, central_storage_node, replica_node,
                                                         number_of_apps)
        failure_time += ft
        if catastrophic_failure:
            break

        # update_failures(cloud_layer, edge_fog_layer, leader_node, iteration, 1)
        for node in edge_fog_layer:
            t = node.apps_execute(iteration)
            if t > t5:
                t5 = t

        # t6 update replica
        t6 = central_storage_node.update_replica(edge_fog_layer, replica_node)

        t_iteration = t0 + t1 + t2 + t3 + t4  + t6 + failure_time
        total_operation_time += t_iteration

        iteration_data = [iteration, t0, t1, t2, t3, t4, t5, t6, failure_time, t_iteration]
        simulation_data.append(iteration_data)

        log(f"iteration {iteration}, t_iteration time = {t_iteration:.2f} ms")
        log(f" last_iteration = {last_iteration}\n")
        log(f" central storage:\n {Node.central_array}\n", "p")
        log(f" replica storage:\n {Node.replica_array}\n", "p")

        log("--------------------------------------------------\n")

        # recalibrate iterations end
        last_iteration = get_last_iteration(edge_fog_layer)

        iteration += 1
        if iteration >= last_iteration:
            loop = False

    # Simulation has exited, evaluate the results
    if catastrophic_failure:
        log(f"*** Exiting due to catastrophic failure ***\n")
        t_iteration = t0 + t1 + t2 + t3 + t4 + t5 + t6 + failure_time
        total_operation_time += t_iteration
        iteration_data = [iteration, t0, t1, t2, t3, t4, t5, t6, failure_time, t_iteration]
        simulation_data.append(iteration_data)

    log(f"Results:")
    log(f" Total Operation Time = {total_operation_time:.2f} ms")
    log(f" There were {iteration} iterations.")
    print_simulation_data(simulation_data)
    number_of_failed_components = Node.num_failed_nodes + Node.num_failed_apps + Node.cs_failed + Node.replica_failed
    log(f"{number_of_failed_components} components failed:")
    log(f" {Node.num_failed_nodes} Nodes, {Node.cs_failed } CS, {Node.replica_failed} replica and "
        f"{Node.num_failed_apps} apps.")


def start(script_file, output_file):
    # file_object = 0
    try:
        file_object = open(script_file, 'r')
    except IOError as var:
        print("Error:", var)
        exit(0)

    network_script = file_object.readlines()
    file_object.close()

    cloud_layer, edge_fog_layer, apps, failure_rate = parse_script(network_script)

    # Create the arrays for centralized storage and replica storage
    number_of_apps = len(apps)
    Node.central_array = [0] * number_of_apps
    Node.replica_array = [0] * number_of_apps

    # Add apps to the edge-fog layer
    add_apps(edge_fog_layer, apps)
    Node.failure_rate = failure_rate
    total_fails = add_failures(cloud_layer, edge_fog_layer, apps, failure_rate)

    num_apps = len(apps)
    num_cloud_nodes = len(cloud_layer)
    num_edge_fog_nodes = len(edge_fog_layer)

    logging.basicConfig(filename=output_file, level=logging.INFO)

    log("\n========================\nStarting New Simulation: ")
    log("Layers and apps created from script")
    log(f" {num_apps} apps, {num_cloud_nodes} cloud nodes and {num_edge_fog_nodes} edge-fog nodes created\n")
    log(f" failure rate set at {failure_rate:.4f}")
    print(f" total fails set at {total_fails}")
    display_cs_and_r(cloud_layer, edge_fog_layer)
    layer_info(edge_fog_layer)

    run_simulation(cloud_layer, edge_fog_layer, number_of_apps)


def program_usage():
    print("Program Usage:")
    print(" python centralnetsim.py script_file output_file")


# Here is where the  CentralNetSim.py script starts
if __name__ == '__main__':

    # script_file = "CentralizedSim5.txt"
    # output_file = "blap.txt"
    #
    # start(script_file, output_file)
    num = len(sys.argv)

    if num == 3:
        start(sys.argv[1], sys.argv[2])
    else:
        program_usage()

