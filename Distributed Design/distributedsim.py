# This is a sample Python script.

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.

from nodes import Node, App, Failure
import logging
from datetime import datetime
import sys
import random
import time


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
    if params[6].lower() == "leader":
        leader = True

    node_failure = False
    sc_failure = False
    # add failures of node or sc
    if number_of_nodes == 1 and l == 10:
        if params[7].lower() == "f:node":
            node_failure = True
        elif params[7].lower() == "f:sc":
            sc_failure = True

        iteration = int(params[8])
        stage = int(params[9])
        failure = Failure(iteration, stage)

    i = 0
    while i < number_of_nodes:
        node = Node(mips, ram, storage, bw_start, bw_end, delay_start, delay_end, leader, cloud_layer)
        if node_failure:
            node.set_node_failure(failure)
        elif sc_failure:
            node.set_sc_failure(failure)
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
    exec_time = int(params[5])
    iterations = int(params[6])

    data_size = float(params[7][:-2])
    decimal_place = params[7][-2:]
    # convert all data sizes to kilobytes
    if decimal_place.lower() == "mb":
        data_size *= 1000  # megabytes to kilobyte size

    app_failure = False
    if number_of_apps == 1 and l == 11:
        if params[8].lower() == "f":
            app_failure = True
            iteration = int(params[9])
            stage = int(params[10])
            failure = Failure(iteration, stage)

    i = 0
    while i < number_of_apps:
        app_num = len(apps)  # this is the unique index value given to this app
        app = App(mips, ram, storage, deployment_time, exec_time, iterations, data_size, app_num)
        if app_failure:
            app.set_failure(failure)
        apps.append(app)
        i += 1


def get_failure_rate(line):
    failure_rate = float(line)
    failure_rate /= 100.0
    return failure_rate


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


def add_rds_and_data_arrays(cloud_layer, edge_fog_layer, apps):
    rds = []
    number_of_apps = len(apps)
    rds = [0] * number_of_apps
    app_data_array = [0] * number_of_apps

    #  mapping app to slot in app_data_array
    for app in apps:
        app_data_array[app.app_num] = app.app_data

    # add rds array and app_data_array copies to each node of both layers
    for node in cloud_layer:
        node.add_rds(rds.copy())
        node.add_app_data_array(app_data_array.copy())

    for node in edge_fog_layer:
        node.add_rds(rds.copy())
        node.add_app_data_array(app_data_array.copy())


# This adds apps to the edge_fog_layer
def add_apps(edge_fog_layer, apps):
    idx = 0
    added_apps = []
    failed_to_add = []
    count = 0
    for app in apps:
        l = len(edge_fog_layer)
        start_idx = idx
        break_out = False
        # Iterate through each node to find a free spot for an app, once cycle through layer max per app
        while idx < l:
            if app.app_num == 45:
                print(f" ====>  app #45 ram = {app.ram} storage = {app.storage}")
                count = 1

            if edge_fog_layer[idx].add_app(app):
                added_apps.append(app.app_num)
                break_out = True

            idx += 1
            if idx >= l:
                idx = 0

            if break_out:
                break
            # failed to add app
            elif idx == start_idx:
                failed_to_add.append(app.app_num)
                break
    print(" =====> Apps successfully Added:\n")
    print(added_apps)

    print(" =====> Failed to Add these apps:\n")
    print(failed_to_add)
    print("==== End of Apps Added/Failed To Add====")


# returns true of the layer is synchronized, i.e. all rds are equal
def synchronized(layer):
    rds = layer[0].rds.copy()
    for node in layer:
        if not node.rds_equal(rds):
            return False
    return True


# triggers any failures for any component on this iteration and at this stage
def update_failures(cloud_layer, edge_fog_layer, leader_node, iteration, stage):
    for node in cloud_layer:
        r, failure_info = node.invoke_failure(iteration, stage)
        if r:
            log(failure_info)

    for node in edge_fog_layer:
        r, failure_info = node.invoke_failure(iteration, stage)
        if r:
            log(failure_info)


def get_last_iteration(edge_fog_layer):
    last_iteration = 0
    for node in edge_fog_layer:
        itr = node.get_max_iterations()
        if itr > last_iteration:
            last_iteration = itr
    return last_iteration


def change_leader(cloud_layer, edge_fog_layer, leader_node):
    # change leader
    if len(cloud_layer) == 0:
        num = len(edge_fog_layer)
        i = 0
        while i < num:
            node = edge_fog_layer[i]
            i += 1
            if node.leader == leader_node.leader:
                if i == num:
                    i = 0
                edge_fog_layer[i].leader = True
                leader_node.leader = False
                break
    else:
        num = len(cloud_layer)
        i = 0
        while i < num:
            node = cloud_layer[i]
            i += 1
            if node.leader == leader_node.leader:
                if i == num:
                    i = 0
                cloud_layer[i].leader = True
                leader_node.leader = False
                break


def get_leader_node(cloud_layer, edge_fog_layer):
    leader_node = None
    if len(cloud_layer) == 0:
        for node in edge_fog_layer:
            if node.leader:
                leader_node = node
                break
    else:
        for node in cloud_layer:
            if node.leader:
                leader_node = node
                break
    return leader_node


# prints out the simulation data.   Each iteration is stored in a list
# each list contains the info for an iteration
# t_iteration = t0 + t1 + t2 + t3 + t4 + t5, i.e. total time of the iteration
#  iteration_data = [iteration, t0, t1, t2, t3, t4, t5, t_iteration]
def print_simulation_data(simulation_data):
    log("\nThe stage times for each iteration:")
    for id in simulation_data:
        log(f" {id[0]}) t0:{id[1]:.2f}, t1:{id[2]:.2f}, t2:{id[3]:.2f}, t3:{id[4]:.2f}, t4:{id[5]:.2f}, t5:{id[6]:.2f},"
            f" total time = {id[7]:.2f} ms")  # The "total time" is the total time of this iteration


def run_simulation(cloud_layer, edge_fog_layer):
    #  I need to do this for two cases: with just edge_fog_layer and with both layers
    iteration = 0
    loop = True
    tsync = 0
    sync_times = []
    last_iteration = get_last_iteration(edge_fog_layer)
    total_operation_time = 0   # operation time aka simulation time
    store_iteration_info = []
    simulation_data = []

    t0 = t1 = t2 = t3 = t4 = t5 = 0.0
    while loop:

        t0 = t1 = t2 = t3 = t4 = t5 = 0.0

        leader_node = None
        leader_node = get_leader_node(cloud_layer, edge_fog_layer)
        # t0  Deploy Apps and SC/Leader (L=Leader)
        t0 = 0
        for node in edge_fog_layer:
            node.deploy_node()
            # node.add_random_failure(iteration)
            t = node.deploy_app()

            if t > t0:
                t0 = t
            t = node.deploy_sc()
            if t > t0:
                t0 = t

        for node in cloud_layer:
            node.deploy_node()
            # node.add_random_failure(iteration)
            t = node.deploy_sc()
            if t > t0:
                t0 = t

        # t1 App Exec (S=1), SC/L (NoOp)
        t1 = 0
        update_failures(cloud_layer, edge_fog_layer, leader_node, iteration, 1)

        for node in edge_fog_layer:
            t = node.exec_app(iteration, 1)
            if t > t1:
                t1 = t

        # t2 App Write S to RDS, SC/L (NoOp)
        t2 = 0
        update_failures(cloud_layer, edge_fog_layer, leader_node, iteration, 2)

        for node in edge_fog_layer:
            t = node.write_app(iteration, 2)
            if t > t2:
                t2 = t

        # t3 App Exec (S=2), SC/L Fetch RDS for App (but there can be multiple apps on a node?)
        t3 = 0
        update_failures(cloud_layer, edge_fog_layer, leader_node, iteration, 3)

        for node in edge_fog_layer:
            t = node.exec_app(iteration, 3)
            if t > t3:
                t3 = t

            t = node.fetch_sc(iteration, 3)
            if t > t3:
                t3 = t

        # t4 App Read External App, SC Send App State To Leader for each app on node, L receive from SCs
        t4 = 0
        update_failures(cloud_layer, edge_fog_layer, leader_node, iteration, 4)
        #  Get the leader node

        # latency + data/bw
        for node in edge_fog_layer:
            t = node.send_to_leader(leader_node, iteration, 4)
            if t > t4:
                t4 = t

        # t5 App Exec (S=3), SCs Receive From Leader, Leader Broadcast To SCs (synchronization)
        t5 = 0
        update_failures(cloud_layer, edge_fog_layer, leader_node, iteration, 5)
        if len(cloud_layer) == 0:
            for node in edge_fog_layer:
                t = node.broadcast(leader_node, iteration, 5)
                if t > t5:
                    t5 = t
        else:
            for node in cloud_layer:
                t = node.broadcast(leader_node, iteration, 5)
                if t > t5:
                    t5 = t

        # determine if leader failed.  If so, change leader
        if not leader_node.node_deployed:
            change_leader(cloud_layer, edge_fog_layer, leader_node)

        sync_state = False
        #  check for node synchronization
        if len(cloud_layer) == 0:
            if synchronized(edge_fog_layer):
                sync_state = True
        else:
            if synchronized(cloud_layer):
                sync_state = True

        t_iteration = t0 + t1 + t2 + t3 + t4 + t5
        iteration_data = [iteration, t0, t1, t2, t3, t4, t5, t_iteration]
        simulation_data.append(iteration_data)
        total_operation_time += t_iteration
        tsync += t_iteration
        sync_time = 0
        if sync_state:
            sync_time = tsync
            sync_times.append(tsync)
            tsync = 0
            store_iteration_info.append([t4, t5, 'synced'])
        else:
            # add iterations to the apps to adjust for non-synchronized state
            for node in edge_fog_layer:
                node.add_iteration_to_apps()
            store_iteration_info.append([t4, t5, 'not synced'])

        if sync_state:
            log(f"system is synchronized, sync_time = {sync_time:.2f} ms")
        else:
            log(f"system is not synchronized")

        log(f"iteration {iteration}, t_iteration time = {t_iteration:.2f} ms")
        log(f" last_iteration = {last_iteration}\n")
        if len(cloud_layer) == 0:
            for node in edge_fog_layer:
                node.print_rds()
        else:
            for node in cloud_layer:
                node.print_rds()

        display_leader(cloud_layer, edge_fog_layer)
        log("--------------------------------------------------\n")

        # recalibrate iterations end
        last_iteration = get_last_iteration(edge_fog_layer)

        iteration += 1
        if iteration >= last_iteration:
            loop = False

    #  Summing up the simulation process
    tmax = tmin = sync_times[0]
    t_total = 0
    for t in sync_times:
        t_total += t
        if tmin > t:
            tmin = t
        if tmax < t:
            tmax = t
    num = len(sync_times)
    tsync_average = t_total/num
    log(f"Results:")
    log(f" Total Operation Time = {total_operation_time:.2f} ms")
    log(f" There were {iteration} iterations.")
    log(f"sync times: worst={tmax:.2f} ms, average={tsync_average:.2f} ms, best={tmin:.2f} ms")
    i = 1
    log("Transition times and Broadcast times for each iteration:")
    for itr_values in store_iteration_info:
        log(f" {i}) transition:{itr_values[0]:.2f} ms, broadcast:{itr_values[1]:.2f} ms, {itr_values[2]} ")
        i += 1
    number_of_failed_components = Node.num_failed_nodes + Node.num_failed_scs + Node.num_failed_apps
    log(f"{number_of_failed_components} components failed:")
    log(f" {Node.num_failed_nodes} Nodes, {Node.num_failed_scs} SCs and {Node.num_failed_apps} apps.")

    print_simulation_data(simulation_data)


def layer_info(edge_fog_layer):
    data = "Edge & Fog Layer Nodes:\n"
    for node in edge_fog_layer:
        data += " node: " + str(node.node_num) + "\n"
        for app in node.apps:
            data += "  app number: " + str(app.app_num) + "\n"
        if len(node.apps) == 0:
            data += "  empty\n"

    log(data)


def display_leader(cloud_layer, edge_fog_layer):
    data = ""
    if len(cloud_layer) == 0:
        for node in edge_fog_layer:
            if node.leader:
                data = "\nLeader is on edge_fog layer, node " + str(node.node_num) + "\n"
                break
    else:
        for node in cloud_layer:
            if node.leader:
                data = "\nLeader is on cloud layer, node " + str(node.node_num) + "\n"
                break
    log(data)
    return data


def add_random_failures(cloud_layer, edge_fog_layer, apps, failure_rate):

    if failure_rate == 0.0:
        return

    last_iteration = get_last_iteration(edge_fog_layer)
    l = len(cloud_layer)
    i = 0
    while i < l:
        r = random.random()
        node = cloud_layer[i]
        if r <= failure_rate and not node.node_failure and not node.sc_failure:
            iteration = random.randint(0, last_iteration - 1)
            stage = random.randint(1, 5)
            failure = Failure(iteration, stage)
            comp = random.randint(1,2)
            if comp == 1:
                node.set_node_failure(failure)
            else:
                node.set_sc_failure(failure)
        i += 1

    l = len(edge_fog_layer)
    i = 0
    while i < l:
        r = random.random()
        node = edge_fog_layer[i]
        if r <= failure_rate and not node.node_failure and not node.sc_failure:
            iteration = random.randint(0, last_iteration - 1)
            stage = random.randint(1, 5)
            failure = Failure(iteration, stage)
            comp = random.randint(1, 2)
            if comp == 1:
                node.set_node_failure(failure)
            else:
                node.set_sc_failure(failure)
            pass
        i += 1

    l = len(apps)
    i = 0
    while i < l:
        r = random.random()
        app = apps[i]
        if r <= failure_rate and not app.failure:
            iteration = random.randint(0, app.iterations - 1)
            stage = random.randint(1, 5)
            failure = Failure(iteration, stage)
            app.set_failure(failure)
        i += 1


def get_random_idx(used_indices, size):
    while True:
        idx = random.randint(0, size-1)
        if idx not in used_indices:
            return idx

    pass


def add_failures(cloud_layer, edge_fog_layer, apps, failure_rate):
    num_cnodes = len(cloud_layer)
    num_fnodes = len(edge_fog_layer)
    num_apps = len(apps)
    num_to_fail = failure_rate*(num_apps + 2*(num_cnodes + num_fnodes))  # multiple num_nodes by two to include SCs
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

    # add node failures first
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
            if not node.node_failure:
                itr = random.randint(0, last_iteration - 1)
                fc = node.add_failure("node", itr)
                total_fails += fc
                c += 1

        else:
            i = 0
            if num_cnodes != 0:
                idx = random.randint(0, num_cnodes - 1)
                node = cloud_layer[idx]
                if not node.node_failure:
                    itr = random.randint(0, last_iteration - 1)
                    fc = node.add_failure("node", itr)
                    total_fails += fc
                    c += 1
        if total_fails > num_to_fail:
            return total_fails
        count += 1
        if count > loop_limit:
            break

    comp_types = ["app", "sc"]
    i = 0
    count = 0
    # add failures for apps and scs
    while total_fails < num_to_fail:
        itr = random.randint(0, last_iteration - 1)
        if i == 0:  # edge_fog_layer
            if num_cnodes == 0:
                i = 0
            else:
                i = 1
            cti = random.randint(0, 1)
            ctv = comp_types[cti]
            node_span = num_fnodes
            if num_apps < num_fnodes and ctv == "app":
                node_span = num_apps

            idx = random.randint(0, node_span - 1)
            node = edge_fog_layer[idx]
            if not node.node_failure:
                fc = node.add_failure(ctv, itr)
                total_fails += fc
            pass
        else:
            i = 0
            idx = random.randint(0, num_cnodes - 1)
            node = cloud_layer[idx]
            if not node.node_failure:
                fc = node.add_failure("sc", itr)
                total_fails += fc
        count += 1
        if count > loop_limit:
            return total_fails

    return total_fails


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

    add_rds_and_data_arrays(cloud_layer, edge_fog_layer, apps)
    add_apps(edge_fog_layer, apps)
    Node.failure_rate = failure_rate  # failure_rate is set to a class level variable

    # add_failures()
    total_fails = add_failures(cloud_layer, edge_fog_layer, apps, failure_rate)


    # add_random_failures(cloud_layer, edge_fog_layer, apps, failure_rate)

    num_apps = len(apps)
    num_cloud_nodes = len(cloud_layer)
    num_edge_fog_nodes = len(edge_fog_layer)


    logging.basicConfig(filename=output_file, level=logging.INFO)

    log("\n========================\nStarting New Simulation: ")
    # log(time_now())
    log("Layers and apps created from script")
    log(f" {num_apps} apps, {num_cloud_nodes} cloud nodes and {num_edge_fog_nodes} edge-fog nodes created\n")
    log(f" failure rate set at {failure_rate:.4f}")
    print(f" total fails set at {total_fails}")
    display_leader(cloud_layer, edge_fog_layer)
    layer_info(edge_fog_layer)

    run_simulation(cloud_layer, edge_fog_layer)


def time_now():
    months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August',
              'September', 'October', 'November', 'December']
    right_now = datetime.now()
    m = int(right_now.strftime("%m"))
    month = months[m-1]
    date = right_now.strftime(" %d, %Y %H:%M:%S")
    date = month + date
    return date


def program_usage():
    print("Program Usage:")
    print(" python netsim datafile outputfile")


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    # 300 * 1000
    # bw_start = 300 * 1000 / 8  # convert to bytes per millisecond
    # bw_end = 920 * 1000 / 8  # convert to bytes per millisecond
    # r = random.randint(bw_start, bw_end)

    # start("NetworkScript1.txt")
    # start("NetworkTestScript2.txt")
    # start("NetworkTestOneLayerScript4.txt")
    # start("NetworkTestOneLayerScript6.txt")
    # start("NetworkTestScript7.txt")

    # start("NetworkScriptFailureRate9.txt", "netsimlog7.txt")

    # start("NetworkTestMoreAppsThanNodesScript.txt", "netsimlog5.txt")

    # start("TestScript-Z.txt", "netsimlog6.txt")
    # start("TestCode-D-09.txt", "netsimlog11.txt")
    # exit(0)

    # start("TestCode-D-RF-01.txt", "netsimlog13.txt")

    # num = 3.124567
    # datastr = f"number = {num:.4}"
    # print(datastr)

    num = len(sys.argv)
    if num == 3:
        start(sys.argv[1], sys.argv[2])
    else:
        program_usage()

    # start("NetworkTestScript7.txt")
