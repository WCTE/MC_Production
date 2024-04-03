# MC_Production
These scripts are intended to use in the WCTE MC production with software container.

## Setup
First clone this repository.
```
git clone https://github.com/WCTE/MC_Production.git
cd MC_Production
```
Then get the software container image according to [instructions](https://github.com/WCTE/SoftwareContainer).

## createWCSimFiles.py
This script generates the mac files and shell scripts for running WCSim.
```
python3 createWCSimFiles.py
```
It generates mu- particle gun mac files under `mac/`, and container run scripts under `shell/`. By default, the particle is shot from the approximate beam window position towards the tank center (negative z-direction). There is also an option to generate random vertices in the detector.

All available options are
```
-h, --help: prints help message
-p, --pid=<name>: particle name (mu-, e-, etc.)
-b, --beam=<KE,wallDistance>: generate beam with KE in MeV, wallDistance (distance from vertex to blacksheet behind) in cm
-u, --uniform=<KElow,KEhigh>: generate random vertices with uniform KE in MeV
-n, --nevs=<val>: number of events per file
-f, --nfiles=<val>: numbe of files to be generated
-s, --seed=<val>: RNG seed used in this script
-c, --cds: use CDS in WCSim
-k, --sukap: submit batch jobs on sukap
-d, --cedar=<account>: submit batch jobs on cedar with specified RAP account
```

To run the shell scripts with singularity,
```
# assume you have already run python3 createWCSimFiles.py -b 100,30 which produced 
# mac/wcsim_mu-_Beam_100MeV_30cm_0000.mac and shell/wcsim_mu-_Beam_100MeV_30cm_0000.sh
singularity exec -B ./:/mnt softwarecontainer_v1.2.sif bash /mnt/shell/wcsim_mu-_Beam_100MeV_30cm_0000.sh
```
The `-B` option binds the current directory to `/mnt` inside the container so you can access the files and write the outputs there. The output root file and log are located at `out/` and `log/`.

### Batch job submission on sukap
To submit batch jobs on sukap, you first need to create a sandbox
```
singularity build --sandbox wcsim_sandbox softwarecontainer_v1.2.sif
```
Then you can run `createWCSimFiles.py` with `-k`
```
python3 createWCSimFiles.py <other_options> -k
```
This produces the batch job scripts under `pjdir`, and batch job logs (if any) are produced at `pjout/` and `pjerr/`. The `-u` option is used with singularity to bypass the binding issue.

### Batch job submission on cedar
You need to run `createWCSimFiles.py` with `-d <account>`. If you do not know which RAP account is usable, follow the [instructions](https://docs.alliancecan.ca/wiki/Running_jobs#Accounts_and_projects) to check.
```
python3 createWCSimFiles.py <other_options> -d <account>
```
This produces the batch job scripts under `sldir`, and batch job logs (if any) are produced at `slout/` and `slerr/`. 

## Validation
Two event display root macros are placed under `validation/`. They can be run with the container.

### EventDisplay.c
```
singularity exec -B ./:/mnt softwarecontainer_v1.2.sif root -l -b -q /mnt/validation/EventDisplay.c\(\"/mnt/out/wcsim_mu-_100MeV_30cm_\*\[0-9\].root\"\)
```
This reads the files `out/wcsim_mu-_100MeV_30cm_*[0-9].root` and aggregates all events to produce PMT hit histograms of charges and times under `fig/`.

### EventDisplay_Compare.c
```
singularity exec -B ./:/mnt softwarecontainer_v1.2.sif root -l -b -q /mnt/validation/EventDisplay_Compare.c\(\"/mnt/out/wcsim_mu-_100MeV_30cm_\*\[0-9\].root\",\"/mnt/out/wcsim_wCDS_mu-_100MeV_30cm_\*\[0-9\].root\"\,\"mu-\"\)
```
This reads two different sets of files, aggregates all events to produce PMT hit histograms and calculate the ratio between the two sets of histograms.

### VertexDistribution.c
```
singularity exec -B ./:/mnt softwarecontainer_v1.2.sif root -l -b -q /mnt/validation/VertexDistribution.c\(\"/mnt/out/wcsim_mu-_100MeV_30cm_\*\[0-9\].root\"\)
```
This plots the vertex distribution of all the events.

### EventDisplay_SingleEvent.c
```
singularity exec -B ./:/mnt softwarecontainer_v1.2.sif root -l -b -q /mnt/validation/EventDisplay_SingleEvent.c\(\"/mnt/out/wcsim_mu-_100MeV_30cm_\*\[0-9\].root\", evtID\)
```
This produces event display for the `evtID`-th event.

## [DataTools](https://github.com/WatChMaL/DataTools)
[WatChMaL](https://github.com/WatChMaL) provides a python package to convert WCSim root output into numpy array.
```
git clone -b wcsim_v1.12.9 https://github.com/kmtsui/DataTools/
singularity shell -B ./:/mnt softwarecontainer_v1.2.sif
source /opt/WCSim/build/this_wcsim.sh
cd /mnt/DataTools
export DATATOOLS=`pwd`
export PYTHONPATH=$DATATOOLS:$PYTHONPATH
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