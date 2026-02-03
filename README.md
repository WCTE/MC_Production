# MC_Production
These scripts are intended to use in the WCTE MC production with software container.

## Setup
First clone this repository.
```
git clone https://github.com/WCTE/MC_Production.git
cd MC_Production
```
Then get the software container image according to [instructions](https://github.com/WCTE/SoftwareContainer).

### Environment Setup
Before running any scripts, you must set up the environment variables using `setup.sh`.

If you only have a Singularity Image File (.sif):
```bash
source setup.sh /path/to/softwarecontainer.sif
```

If you need a sandbox (required for Sukap submission): 
```bash 
# If sandbox exists 
source setup.sh /path/to/softwarecontainer.sif /path/to/sandbox_dir 
# If you need to build the sandbox from the SIF 
source setup.sh /path/to/softwarecontainer.sif /path/to/sandbox_dir --build
```
## runSimulation.py
This script generates the mac files, shell scripts, and handles batch job submission for WCSim, MDT, and fiTQun.

```bash
python3 runSimulation.py [options]
```

### Options
```
 -h, --help: prints help message 
 -p, --pid=: particle name (mu-, e-, etc.) 
 -b, --beam=<KE,wallDistance>: generate beam with KE in MeV, wallDistance (distance from vertex to blacksheet behind) in cm 
 -u, --uniform=<KElow,KEhigh>: generate random vertices with uniform KE in MeV 
 -m, --cosmics: generate cosmic muon events 
 -n, --nevs=: number of events per file 
 -f, --nfiles=: number of files to be generated 
 -s, --seed=: RNG seed used in this script 
 -c, --cds: disable CDS in WCSim 
 -wcsim: disable WCSim execution 
 -mdt: disable MDT execution 
 -fq: disable fiTQun execution 
 -k, --sukap: submit batch jobs on sukap 
 -d, --cedar=: submit batch jobs on cedar with specified RAP account 
 -condor: submit condor jobs on lxplus
 ```

### Examples

**1. Generate scripts only (Beam mode):**
```bash
python3 runSimulation.py -p mu- -b 100,30 -n 1000 -f 10
```
This generates 10 files for 100 MeV muons, 30cm from the wall. Macros are in mac/ and execution scripts in shell/. 

**2. Submit jobs to Sukap:**
Requires SOFTWARE_SANDBOX_DIR to be set. 
```bash 
python3 runSimulation.py -p e- -u 10,50 -n 1000 -f 100 -k
```

**3. Submit jobs to Cedar:**
```bash
python3 runSimulation.py -m -n 1000 -f 50 -d def-myaccount
```

**4. Submit jobs to Condor (LXPLUS):** 
```bash 
python3 runSimulation.py -p mu+ -b 200,0 -n 1000 -f 20 --condor
```

## Web Application
A web interface is available to configure simulations, submit jobs, and monitor status.

### Prerequisites
Install the required Python packages:
```bash
pip install -r requirements.txt
```

### Starting the Server 
Ensure you have sourced `setup.sh` first. Then start the server on the remote cluster: 
```bash 
uvicorn main:app --host 127.0.0.1 --port 8080
```

### Accessing via Browser
Since the server runs on a remote cluster, use SSH tunneling to access it from your local machine:
```bash
ssh -L 8080:127.0.0.1:8080 user@remote_server
```

Open http://localhost:8080 in your web browser. 
### Features 
1. Configuration: Use the form to select particle type, mode (Beam/Uniform/Cosmics), energy, and execution steps (WCSim, MDT, fiTQun). 
2. Submission: Select the target batch system (Sukap, Cedar, Condor) and click "Submit Simulation". The app runs the submission in the background. 
3. Status Monitoring: Scroll down to the "Job Status" section. Select the batch system and click "Refresh" (or "Stop Refresh" to toggle auto-update) to view active jobs.

## Validation
Two event display root macros are placed under `validation/`. They can be run with the container.

### EventDisplay.c
```
singularity exec -B ./:/mnt $SOFTWARE_SIF_FILE root -l -b -q /mnt/validation/EventDisplay.c\(\"/mnt/\*.root\"\)
```
This reads the files `out/*.root` and aggregates all events to produce PMT hit histograms of charges and times under `fig/`.

### EventDisplay_Compare.c
```
singularity exec -B ./:/mnt $SOFTWARE_SIF_FILE root -l -b -q /mnt/validation/EventDisplay_Compare.c\(\"/mnt/out/[files1].root\",\"/mnt/out/[files2].root\"\,\"tag\"\)
```
This reads two different sets of files, aggregates all events to produce PMT hit histograms and calculate the ratio between the two sets of histograms.

### VertexDistribution.c
```
singularity exec -B ./:/mnt $SOFTWARE_SIF_FILE root -l -b -q /mnt/validation/VertexDistribution.c\(\"/mnt/out/\*.root\"\)
```
This plots the vertex distribution of all the events.

### EventDisplay_SingleEvent.c
```
singularity exec -B ./:/mnt $SOFTWARE_SIF_FILE root -l -b -q /mnt/validation/EventDisplay_SingleEvent.c\(\"/mnt/out/\*.root\", evtID\)
```
This produces event display for the `evtID`-th event.

## [DataTools](https://github.com/WatChMaL/DataTools)
[WatChMaL](https://github.com/WatChMaL) provides a python package to convert WCSim root output into numpy array.
```
git clone https://github.com/WatChMaL/DataTools
singularity run -B ./:/mnt $SOFTWARE_SIF_FILE bash
source /opt/WCSim/build/this_wcsim.sh
cd /mnt/DataTools
export DATATOOLS=`pwd`
python $DATATOOLS/root_utils/event_dump.py root_file -d out_dir # reads root_file and produces .npz file in out_dir
# Geometry file, only need one 
python $DATATOOLS/root_utils/full_geo_dump.py root_file geo_file_name.npz
```
To read the .npz file in python,
```
import numpy as np
npz_file = np.load(file_name, allow_pickle=True)
# check $DATATOOLS/root_utils/event_dump.py, root_file_utils.py for availale variables
hit_time = npz_file['digi_hit_time'] # this gets the pmt digi hit time
```