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
It generates mu- particle gun mac files under `mac/`, and container run scripts under `shell/`. The particle is shot from the approximate beam window position towards the tank center (negative z-direction).

All available options are
```
-h, --help: prints help message
-p, --pid=<name>: particle name (mu-, e-, etc.)
-e, --ke=<val>: particle KE in MeV
-w, --wall=<val>: distance from vertex to blacksheet behind in cm
-n, --nevs=<val>: number of events per file
-f, --nfiles=<val>: numbe of files to be generated
-s, --seed=<val>: RNG seed used in this script
-c, --cds: use CDS in WCSim
-k, --sukap: submit batch jobs on sukap
-d, --cedar=<account>: submit batch jobs on cedar with specified RAP account
```

To run the shell scripts with singularity,
```
# assume you have already run python3 createWCSimFiles.py which produced 
# mac/wcsim_mu-_100MeV_30cm_0000.mac and shell/wcsim_mu-_100MeV_30cm_0000.sh
singularity exec -B ./:/mnt softwarecontainer_main.sif bash /mnt/shell/wcsim_mu-_100MeV_30cm_0000.sh
```
The `-B` option binds the current directory to `/mnt` inside the container so you can access the files and write the outputs there. The output root file and log are located at `out/` and `log/`.

### Batch job submission on sukap
To submit batch jobs on sukap, you first need to create a sandbox
```
singularity build --sandbox wcsim_sandbox softwarecontainer_main.sif
```
Then you can run `createWCSimFiles.py` with `-k`
```
python3 createWCSimFiles.py -k
```
This produces the batch job scripts under `pjdir`, and batch job logs (if any) are produced at `pjout/` and `pjerr/`. The `-u` option is used with singularity to bypass the binding issue.

## Validation
Two event display root macros are placed under `validation/`. They can be run with the container.

### EventDisplay.c
```
singularity exec -B ./:/mnt softwarecontainer_main.sif root -l -b -q /mnt/validation/EventDisplay.c\(\"/mnt/out/wcsim_mu-_100MeV_30cm_\*[0-9\].root\"\)
```
This reads the files `out/wcsim_mu-_100MeV_30cm_*[0-9].root` and aggregates all events to produce PMT hit histograms of charges and times under `fig/`.

### EventDisplay_Compare.c
```
singularity exec -B ./:/mnt softwarecontainer_main.sif root -l -b -q /mnt/validation/EventDisplay_Compare.c\(\"/mnt/out/wcsim_mu-_100MeV_30cm_\*[0-9\].root\",\"/mnt/out/wcsim_wCDS_mu-_100MeV_30cm_\*[0-9\].root\"\,\"mu-\"\)
```
This reads two different sets of files, aggregates all events to produce PMT hit histograms and calculate the ratio between the two sets of histograms.