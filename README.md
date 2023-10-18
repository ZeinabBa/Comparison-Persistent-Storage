# Comparison-Persistent-Storage

This repository contains a Python implementation of a simulation in which we extend our [previous simulator](https://github.com/ZeinabBa/Persistent-Storage-Simulation/tree/main)  that simulates a distributed persistent storage system for container-based architectures. This extended simulation is implemented using the specifications of Computing Continnuumm testbed at Klagenfurt University. Computing Continnum is a multi layer processing architecture encompassing, edge, fog, and cloud nodes.
In addition to extending our previous simulator, we implemented a new simulator that uses the same specification of Computing Continuum, but is aimed for centralized storage system for container-based architectures.
These two simulators help us perform analysis to compare our distributed persistent container-based storage in four-dimensions: 1- storage placement layer, 2- storage design, 3- data size of the applications using storage, and 4- failure resistncy of the storage.

# Distributed Storage Design (Previous Simulator)
Extended from [Persistent Storage Simulator](https://github.com/ZeinabBa/Persistent-Storage-Simulation/tree/main), the distributed system consists of a cluster of nodes distributed in edeg, fog, and cloud layers. The distributed storage space is called Replicated Data Structure (RDs) on each of the nodes that is managed by S

# Centralized Storage Design
The cluster of nodes distributed in edge, fog, and cloud layers use centralized storage that can be located at each of computing continnum layers.


# Getting Started
To run the simulation, we recommend you to have a Linux operating system installed on your machine. You can download the latest version of Ubuntu from the [official website](https://ubuntu.com/download).

Once you have Linux installed, clone this repository to your local machine by running the following command in your terminal:


`git clone https://github.com/ZeinabBa/Comparison-Persistent-Storage.git`

* NOTE: Python version used to implement this simulator is: Python 3.10.6

# Usage and Description
The simulation files provided in this repository allows you to perform the following operations:

- Creating your own cluster with any number of nodes (lower limit is recommended to be 10)

- In Distributed Design, by creating each node, one SC and one RDS will be automatically deployed on that node. The size of the RDS is determined based on the total number of Applications in the cluster

- Deploying any type and number of applications with the upper limit of node's capacities currently existing the cluster as per defined earlier






# Instructions
To use the simulation files, please follow these instructions: 

1- Clone/download the repository

2- Make sure all files are located in one folder

3- If using windows, add the folder address to PATH

4- Open a CLI (PowerShell recommended for windows OS)

 # Get your hands dirty with: Distributed Storage Design
Navigate to the folder "Distributed Design"

A- Run the command  `python distributedsim.py input_file output_file` $${\color{red}inputfile \space must \space be \space located \space in \space the \space same \space folder \space as \space the \space distributedsim.py \space file}$$
Replace `input_file` with the name of the input file you want to use, `output_file` with the desired name for the output log file, 
  - NOTE: Please note that if output file name is not specified either in command line or in the main code then the new results will be added (not overwritten) to the results of the previous experiment.

B- Use the input files given in the repository or make your own input file using a .txt file (you can also use the python file called `json creator` in previous repository to create your input files with json extension)
To Create your own input file as .txt use one sample Testcode and start editing with desired data, following bellow instruction:
 -NOTE: to comment out a line use # sign in the begining of the line in the input.txt file.
  a. add `percentage_of_failure` under the line "Failure Rate" to simulate random failure (e.g. 10 for 10%).
  
  b. Under "Cloud Layer" specify the configuration of each cloud node as you desire in this order, number of instances, MIPS, memory, CPU cores, Bandwith (BW) range (to have it as fixed number initial and end of the numbers must be equal), Latency range (same as indicated for BW). You need to use x with a number to let the simulator know, how many instances of that node you requie. For example x5 means 5 instances. (You can add your own data for devices rather than what is given in the table in the paper)
  
- Make sure to enter all the requested specification and at last specify if the node is a leader or not by. Either SC, or leader must be added to the line. Please note that only one leader can be there in the cluster, otherwise the results are not accutrate.
  
  c. Perform the same for the section called: Layer to specify fog and edge nodes.
  
  d. Repeat the above steps for applications (SC, leader dosnet apply here) just make sure to add itteration number and data size at the end of the line (You can add any application specifications, not limited to the ones given in the table in the paper)

  e. When done, save the file with a .txt` (recommended) extension in the same directory. 
  
  f. Use the created .txt file as the input file to run the simulation explained in item number 5
  
* A number of pre-created input files and their respected logs are available in the repository.

# Dive deep in: Centralized Storage Design

Navigate to the folder "Centralized Design"

I- Run the command  `python centralizedsim.py input_file output_file` $${\color{red}inputfile \space must \space be \space located \space in \space the \space same \space folder \space as \space the \space centralizedsim.py \space file}$$
Replace `input_file` with the name of the input file you want to use, `output_file` with the desired name for the output log file, 
  - NOTE: Please note that if output file name is not specified either in command line or in the main code then the new results will be added (not overwritten) to the results of the previous experiment.

II- Do the same as specified in B, a, and b. 

- Important Note: at the end of the line, specify if the node is a hosting centalized storage with letter "C" or it's replicat with letter "R". If none of these, leave it blank. It is important to know that in centralized design, only one node can be centralized storage and only one node can be it's replica.

III- Continue with doing as specified in c, d, e, f.  


# Interpretation of log files
The simulation generates log files that contain the result of each operation. Here are some tips for interpreting the log files generated by the simulation:

- Each log file contains the result of one operation

- In the log file, the information of number of nodes and applications, failure rate  (for example .1000 means, 10%), allocation, time stamps of synchronization in each iteration, total number of itterations, node hosting the leader for distributed design or  C/R for centralized design.

- Failure details are also included 
  - The details are about failed entities, what stage, what component and if it is SC and App then what Node they where deployed on and if it is an application then which itteration the failure has occured.
 
  - At the end of the log file, a section called "Results" show the timing results of the run, like, operation time, worst, average, and best case execution time, data transmition, broadcast, data exchange, etc.

# Examples with Images
Here is a screenshot of the input file for Distributed Design:

![Input_file_distributed_design](https://github.com/ZeinabBa/Comparison-Persistent-Storage/blob/main/Input_file_distributed_design.JPG)

When the input file is saved run the command given in Step 5 (Instruction Section in this READ ME).

To add failures to nodes add three elements to the end of a node definition line.
They are element, iteration, stage.  So, this means that component fails at that iteration in that stage. 
The element can be either "F:node" for node, and "F:sc" for SC. For example: `x1, 11200, 16, 8, 100-710, 15-100, SC, F:node, 1, 3` means the node fails at iteration 1 and stage 3 

Here is a screenshot of running program and when it's run:

![CLI_and_Program_RUN](https://github.com/ZeinabBa/Persistent-Storage-Simulation/blob/main/Pictures/Program%20Run.jpg?raw=true)

* NOTE: It is very improtant to add the files extentions if they have one. For instance if you save the JSON file as .txt then you need to enter the complete file name including its extention (.txt in this case).
* NOTE: As shown in this image output file is not specified, therefore, it writes in the deafult file: Syslog.txt (in the same folder). Details are mentioned in Step number 5.

Example fo input and output files are given in the folder named "Sample Test Codes and Log Files" in this repository. Files their names include the word "test" are input files and files their names inlcude the word"log" are output files.
