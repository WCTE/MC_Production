#!/usr/bin/env python
import time
import sys
import getopt
import os
import subprocess
import string
import random
import getpass

class SimulationConfig:
    def __init__(self):
        # Default parameters
        self.wcsimdir = "/opt/WCSim"
        self.geant4dir = "/opt/geant4"
        self.wcsim_build_dir = "/opt/WCSim/build"
        self.mntdir = "/mnt"
        
        self.curdir = os.getcwd()
        
        # Environment
        self.siffile = os.environ.get("SOFTWARE_SIF_FILE")
        self.sandbox = os.environ.get("SOFTWARE_SANDBOX_DIR")

        self.rngseed = 20260129
        self.ParticleName = "mu-"

        self.TankRadius = 307.5926/2
        self.TankHalfz = 271.4235/2

        self.nevs = 1000
        self.nfiles = 100
        self.useCDS = True
        self.runWCSim = True
        self.runMDT = True
        self.runFQ = True
        
        self.submit_sukap_jobs = False
        self.submit_cedar_jobs = False
        self.submit_condor_jobs = False
        self.rapaccount = ""

        self.useBeam = True
        self.ParticleKE = 100
        self.ParticleDirx = 0
        self.ParticleDiry = 0
        self.ParticleDirz = 1
        self.ParticlePosx = 0
        self.ParticlePosy = -42.47625
        self.wallD = 0.
        self.ParticlePosz = -(self.TankRadius - self.wallD)

        self.useUniform = False
        self.ParticleKELow = 0.
        self.ParticleKEHigh = 2000.

        self.useCosmics = False

    def validate(self):
        if not self.siffile and not self.sandbox:
            print ("ERROR: SOFTWARE_SIF_FILE and SOFTWARE_SANDBOX_DIR not set.")
            sys.exit(1)
        if self.submit_sukap_jobs and not self.sandbox:
            print ("ERROR: SOFTWARE_SANDBOX_DIR is needed for sukap submission.")
            sys.exit(1)

    def get_config_string(self):
        wCDSstring = "_wCDS" if self.useCDS else ""
        
        beamstring = "Beam_%.0fMeV_%icm_" % (self.ParticleKE, int(self.wallD)) if self.useBeam else ""
        
        uniformstring = "Uniform_%.0f_%.0fMeV_" % (self.ParticleKELow, self.ParticleKEHigh) if self.useUniform else ""
        
        cosmicsstring = "Comsics_" if self.useCosmics else ""

        configString = "%s_%s_%s%s" % (wCDSstring, self.ParticleName, beamstring, uniformstring)
        if self.useCosmics:
            configString = "%s_%s" % (wCDSstring, cosmicsstring)
        
        return configString

class FileGenerator:
    def __init__(self, config):
        self.cfg = config
        self.macdir = "mac"
        self.outdir = "out"
        self.logdir = "log"
        self.shelldir = "shell"
        self.figdir = "fig"
        self.pjdir = "pjdir"
        self.pjoutdir = "pjout"
        self.pjerrdir = "pjerr"
        self.sldir = "sldir"
        self.sloutdir = "slout"
        self.slerrdir = "slerr"
        self.condordir = "condor_dir"
        self.condorout = "condor_out"
        self.condorerr = "condor_err"
        self.condorlog = "condor_log"

    def create_directories(self):
        dirs = [self.macdir, self.outdir, self.logdir, self.shelldir, self.figdir]
        if self.cfg.submit_sukap_jobs:
            dirs.extend([self.pjdir, self.pjoutdir, self.pjerrdir])
        if self.cfg.submit_cedar_jobs:
            dirs.extend([self.sldir, self.sloutdir, self.slerrdir])
        if self.cfg.submit_condor_jobs:
            dirs.extend([self.condordir, self.condorout, self.condorerr, self.condorlog])

        for d in dirs:
            if not os.path.exists(d):
                os.makedirs(d)

    def generate_mac_files(self):
        print ("Creating mac files for WCSim")
        configString = self.cfg.get_config_string()
        
        wCDSmac = "" if self.cfg.useCDS else "#"
        beammac = "" if self.cfg.useBeam else "#"
        uniformmac = "" if self.cfg.useUniform else "#"
        comsicsmac = "" if self.cfg.useCosmics else "#"

        with open("template/WCTE.mac", 'r') as f:
            macTemplate = string.Template(f.read())
        with open("template/tuning_parameters.mac", 'r') as f:
            tuningTemplate = string.Template(f.read())

        random.seed(self.cfg.rngseed)

        for i in range(self.cfg.nfiles):
            macFile = "%s/wcsim%s%04i.mac" % (self.macdir, configString, i)
            macseed = random.randrange(int(1e9))
            
            with open(macFile, 'w') as fo:
                fo.write(macTemplate.substitute(
                    wcsimdir=self.cfg.wcsimdir, 
                    rngseed=macseed, 
                    wCDSmac=wCDSmac, 
                    beammac=beammac,
                    uniformmac=uniformmac,
                    comsicsmac=comsicsmac,
                    ParticleName=self.cfg.ParticleName,
                    ParticleKE=self.cfg.ParticleKE,
                    ParticleDirx=self.cfg.ParticleDirx,
                    ParticleDiry=self.cfg.ParticleDiry,
                    ParticleDirz=self.cfg.ParticleDirz,
                    ParticlePosx=self.cfg.ParticlePosx,
                    ParticlePosy=self.cfg.ParticlePosy,
                    ParticlePosz=self.cfg.ParticlePosz,
                    ParticleKELow=self.cfg.ParticleKELow,
                    ParticleKEHigh=self.cfg.ParticleKEHigh, 
                    rmac=self.cfg.TankRadius, 
                    zmac=self.cfg.TankHalfz,
                    nevs=self.cfg.nevs,
                    filename="%s/%s/wcsim%s%04i.root" % (self.cfg.mntdir, self.outdir, configString, i)
                ))

            tuningFile = "%s/tuning_parameters%s%04i.mac" % (self.macdir, configString, i)
            with open(tuningFile, 'w') as fo:
                fo.write(tuningTemplate.substitute(wcsimdir=self.cfg.wcsimdir))

    def generate_shell_scripts(self):
        print ("Creating shell scripts for simulation")
        configString = self.cfg.get_config_string()
        
        cern_condor = "" if self.cfg.submit_condor_jobs else "#"
        userns = "-u" if self.cfg.submit_sukap_jobs else ""
        siffile = self.cfg.sandbox if self.cfg.submit_sukap_jobs else self.cfg.siffile
        
        runwcsim = "" if self.cfg.runWCSim else "#"
        runmdt = "" if self.cfg.runMDT else "#"
        runfq = "" if self.cfg.runFQ else "#"

        with open("template/run.sh", 'r') as f:
            shTemplate = string.Template(f.read())

        for i in range(self.cfg.nfiles):
            shFile = "%s/run%s%04i.sh" % (self.shelldir, configString, i)
            wcsimfile = "%s/%s/wcsim%s%04i.root" % (self.cfg.mntdir, self.outdir, configString, i)
            mdtfile = "%s/%s/mdt%s%04i.root" % (self.cfg.mntdir, self.outdir, configString, i)
            fqfile = "%s/%s/fq%s%04i.root" % (self.cfg.mntdir, self.outdir, configString, i)
            
            with open(shFile, 'w') as fo:
                fo.write(shTemplate.substitute(
                    curdir=self.cfg.curdir,
                    cern_condor=cern_condor, 
                    userns=userns,
                    mntdir=self.cfg.mntdir,
                    siffile=siffile,
                    runwcsim=runwcsim,
                    runmdt=runmdt,
                    runfq=runfq,
                    macfile="%s/%s/wcsim%s%04i.mac" % (self.cfg.mntdir, self.macdir, configString, i),
                    tuningfile="%s/%s/tuning_parameters%s%04i.mac" % (self.cfg.mntdir, self.macdir, configString, i),
                    logfile="%s/%s/run%s%04i.log" % (self.cfg.mntdir, self.logdir, configString, i),
                    wcsimfile=wcsimfile, 
                    nevs=self.cfg.nevs,
                    mdtfile=mdtfile,
                    fqfile=fqfile,
                    rngseed=random.randrange(int(1e9))
                ))

class JobSubmitter:
    def __init__(self, config, file_generator):
        self.cfg = config
        self.fgen = file_generator

    def is_job_missing(self, i):
        configString = self.cfg.get_config_string()
        if self.cfg.runWCSim and not os.path.exists("%s/wcsim%s%04i.root" % (self.fgen.outdir, configString, i)):
            return True
        if self.cfg.runMDT and not os.path.exists("%s/mdt%s%04i.root" % (self.fgen.outdir, configString, i)):
            return True
        if self.cfg.runFQ and not os.path.exists("%s/fq%s%04i.root" % (self.fgen.outdir, configString, i)):
            return True
        return False

    def scan_jobs(self):
        n_to_submit = 0
        n_skipped = 0
        for i in range(self.cfg.nfiles):
            if self.is_job_missing(i):
                n_to_submit += 1
            else:
                n_skipped += 1
        return n_to_submit, n_skipped

    def submit_sukap(self):
        if not self.cfg.submit_sukap_jobs: return

        configString = self.cfg.get_config_string()
        print ("Submitting pjsub jobs on sukap")
        
        with open("template/pjsub.sh", 'r') as f:
            shTemplate = string.Template(f.read())

        n_submitted = 0
        n_skipped = 0
        for i in range(self.cfg.nfiles):
            if self.is_job_missing(i):
                n_submitted += 1
                while True:
                    com = subprocess.Popen("pjstat | wc -l", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True)
                    res, err = com.communicate()
                    try:
                        queueCount = int(res)
                    except:
                        queueCount = 9999
                    if queueCount < 300:
                        break
                    time.sleep(10)

                shFile = "%s/run%s%04i.sh" % (self.fgen.shelldir, configString, i)
                pjFile = "%s/pjsub%s%04i.sh" % (self.fgen.pjdir, configString, i)
                pjout = "%s/pjsub%s%04i.out" % (self.fgen.pjoutdir, configString, i)
                pjerr = "%s/pjsub%s%04i.err" % (self.fgen.pjerrdir, configString, i)
                
                with open(pjFile, 'w') as fo:
                    fo.write(shTemplate.substitute(
                        curdir=self.cfg.curdir,
                        shFile=shFile,
                        pjout=pjout,
                        pjerr=pjerr
                    ))

                while True:
                    com = subprocess.Popen("pjsub %s" % (pjFile), shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True)
                    res, err = com.communicate()
                    if len(err) == 0:
                        print (res)
                        break
                    print (err)
                    time.sleep(1)
            else:
                n_skipped += 1
        print ("Submitted %d jobs. Skipped %d jobs due to existing files." % (n_submitted, n_skipped))

    def submit_cedar(self):
        if not self.cfg.submit_cedar_jobs: return
        
        configString = self.cfg.get_config_string()
        print ("Creating slurm scripts for WCSim")
        
        with open("template/slurm_wcsim.sh", 'r') as f:
            slTemplate = string.Template(f.read())
            
        siffile = self.cfg.siffile

        for i in range(self.cfg.nfiles):
            slFile = "%s/slurm%s%04i.sh" % (self.fgen.sldir, configString, i)
            slout = "%s/slurm%s%04i" % (self.fgen.sloutdir, configString, i)
            slerr = "%s/slurm%s%04i" % (self.fgen.slerrdir, configString, i)
            
            with open(slFile, 'w') as fo:
                fo.write(slTemplate.substitute(
                    account=self.cfg.rapaccount, 
                    curdir=self.cfg.curdir, 
                    mntdir=self.cfg.mntdir, 
                    siffile=siffile, 
                    sout=slout, 
                    serr=slerr,
                    shfile="%s/run%s%04i.sh" % (self.fgen.shelldir, configString, i)
                ))

        print ("Submitting slurm jobs on cedar")
        n_submitted = 0
        n_skipped = 0
        for i in range(self.cfg.nfiles):
            if self.is_job_missing(i):
                n_submitted += 1
                slFile = "%s/slurm%s%04i.sh" % (self.fgen.sldir, configString, i)
                com = subprocess.Popen("sbatch %s" % (slFile), shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True)
                res, err = com.communicate()
                if len(err) > 0:
                    print (err)
                    sys.exit(1)
                else:
                    print (res)
            else:
                n_skipped += 1
        print ("Submitted %d jobs. Skipped %d jobs due to existing files." % (n_submitted, n_skipped))

    def submit_condor(self):
        if not self.cfg.submit_condor_jobs: return

        configString = self.cfg.get_config_string()
        print ("Creating condor scripts")
        
        with open("template/condor_submit.sub", 'r') as f:
            condorTemplate = string.Template(f.read())

        for i in range(self.cfg.nfiles):
            condorFile = "%s/condor%s%04i.sub" % (self.fgen.condordir, configString, i)
            out = "%s/condor%s%04i" % (self.fgen.condorout, configString, i)
            err = "%s/condor%s%04i" % (self.fgen.condorerr, configString, i)
            log = "%s/condor%s%04i" % (self.fgen.condorlog, configString, i)
            shfile = "%s/run%s%04i.sh" % (self.fgen.shelldir, configString, i)
            
            with open(condorFile, 'w') as fo:
                fo.write(condorTemplate.substitute(shfile=shfile, out=out, err=err, log=log))

        print ("Submitting condor jobs on lxplus")
        n_submitted = 0
        n_skipped = 0
        for i in range(self.cfg.nfiles):
            if self.is_job_missing(i):
                n_submitted += 1
                condorFile = "%s/condor%s%04i.sub" % (self.fgen.condordir, configString, i)
                com = subprocess.Popen("module load lxbatch/eossubmit && condor_submit %s" % (condorFile), shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True)
                res, err = com.communicate()
                if len(err) > 0:
                    print (err)
                    sys.exit(1)
                else:
                    print (res)
            else:
                n_skipped += 1
        print ("Submitted %d jobs. Skipped %d jobs due to existing files." % (n_submitted, n_skipped))

class JobStatus:
    def __init__(self, config):
        self.cfg = config
        self.user = os.environ.get('USER')
        if not self.user:
            self.user = getpass.getuser()

    def get_jobs(self):
        jobs = {}
        if self.cfg.submit_sukap_jobs:
            jobs['sukap'] = self.get_sukap_jobs()
        if self.cfg.submit_cedar_jobs:
            jobs['cedar'] = self.get_cedar_jobs()
        if self.cfg.submit_condor_jobs:
            jobs['condor'] = self.get_condor_jobs()
        return jobs

    def get_sukap_jobs(self):
        jobs = []
        header = ""
        try:
            com = subprocess.Popen("pjstat", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True)
            res, err = com.communicate()
            if res:
                lines = res.decode('utf-8').split('\n')
                for line in lines:
                    parts = line.split()
                    if len(parts) < 5: continue
                    if parts[0] == "JOB_ID":
                        header = line
                        continue
                    if parts[4] == self.user:
                        jobs.append(line)
        except Exception as e:
            print ("Error getting sukap jobs: %s" % str(e))
        
        if len(jobs) > 0 and header != "":
            jobs.insert(0, header)
        return jobs

    def get_cedar_jobs(self):
        jobs = []
        header = ""
        try:
            com = subprocess.Popen("squeue", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True)
            res, err = com.communicate()
            if res:
                lines = res.decode('utf-8').split('\n')
                for line in lines:
                    parts = line.split()
                    if len(parts) < 4: continue
                    if parts[0] == "JOBID":
                        header = line
                        continue
                    if parts[3] == self.user:
                        jobs.append(line)
        except Exception as e:
            print ("Error getting cedar jobs: %s" % str(e))
            
        if len(jobs) > 0 and header != "":
            jobs.insert(0, header)
        return jobs

    def get_condor_jobs(self):
        jobs = []
        try:
            com = subprocess.Popen("condor_q -global", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True)
            res, err = com.communicate()
            if res:
                lines = res.decode('utf-8').split('\n')
                current_schedd = ""
                current_header = ""
                current_jobs = []

                for line in lines:
                    if line.startswith("-- Schedd"):
                        if len(current_jobs) > 0:
                            jobs.append(current_schedd)
                            jobs.append(current_header)
                            jobs.extend(current_jobs)
                            jobs.append("")
                        current_schedd = line
                        current_header = ""
                        current_jobs = []
                    elif line.startswith("OWNER"):
                        current_header = line
                    else:
                        parts = line.split()
                        if len(parts) > 0 and parts[0] == self.user:
                            current_jobs.append(line)
                
                if len(current_jobs) > 0:
                    jobs.append(current_schedd)
                    jobs.append(current_header)
                    jobs.extend(current_jobs)

        except Exception as e:
            print ("Error getting condor jobs: %s" % str(e))
        return jobs

def usage():
    print ("Function to create mac, shell and batch job scripts for WCSim, MDT and fiTQun")
    print ("Usage:")
    print ("runSimulation.py [-h] [-p <particleName>][-b <KE,wallDistance>][-u <KElow,KEhigh>][-n <events>][-f <files>][-s <seed>][-c][--wcsim][--mdt][--fq][-k][-d <account>][--condor]")
    print ("")
    print ("Options:")
    print ("-h, --help: prints help message")
    print ("-p, --pid=<name>: particle name (mu-, e-, etc.)")
    print ("-b, --beam=<KE,wallDistance>: generate beam with KE in MeV, wallDistance (distance from vertex to blacksheet behind) in cm")
    print ("-u, --uniform=<KElow,KEhigh>: generate random vertices with uniform KE in MeV")
    print ("-m, --cosmics: generate cosmic muon events")
    print ("-n, --nevs=<val>: number of events per file")
    print ("-f, --nfiles=<val>: numbe of files to be generated")
    print ("-s, --seed=<val>: RNG seed used in this script")
    print ("-c, --cds: disable CDS in WCSim")
    print ("--wcsim: disable WCSim execution")
    print ("--mdt: disable MDT execution")
    print ("--fq: disable fiTQun execution")
    print ("-k, --sukap: submit batch jobs on sukap")
    print ("-d, --cedar=<account>: submit batch jobs on cedar with specified RAP account")
    print ("--condor: submit condor jobs on lxplus")
    print ("")

def main():
    config = SimulationConfig()

    try:
        opts, args = getopt.getopt(sys.argv[1:], "hckmp:n:f:s:d:b:u:",
                                   ["help", "pid=", "beam=", "uniform=", 
                                    "cosmics", "nevs=", "nfiles=",
                                    "seed=", "cds", "wcsim", "mdt", "fq",
                                    "sukap","cedar=","condor"])
    except getopt.GetoptError as err:
        print (str(err))
        usage()
        sys.exit(2)

    for opt, val in opts:
        if (opt in ("-h", "--help")):
            usage()
            sys.exit()
        if (opt in ("-p", "--pid")):
            config.ParticleName = val.strip()
        if (opt in ("-b", "--beam")):
            config.useBeam = True
            config.useUniform = False
            config.useCosmics = False
            vals = val.strip().split(",")
            config.ParticleKE = float(vals[0])
            config.wallD = float(vals[1])
            config.ParticlePosz = -(config.TankRadius - config.wallD)
        if (opt in ("-u", "--uniform")):
            config.useBeam = False
            config.useUniform = True
            config.useCosmics = False
            vals = val.strip().split(",")
            config.ParticleKELow = float(vals[0])
            config.ParticleKEHigh = float(vals[1])
        if (opt in ("-m", "--cosmics")):
            config.useBeam = False
            config.useUniform = False
            config.useCosmics = True
        if (opt in ("-n", "--nevs")):
            config.nevs = int(val.strip())
        if (opt in ("-f", "--nfiles")):
            config.nfiles = int(val.strip())
        if (opt in ("-s", "--seed")):
            config.rngseed = int(val.strip())
        if (opt in ("-c", "--cds")):
            config.useCDS = False
        if (opt == "--wcsim"):
            config.runWCSim = False
        if (opt == "--mdt"):
            config.runMDT = False
        if (opt == "--fq"):
            config.runFQ = False
        if (opt in ("-k", "--sukap")):
            config.submit_sukap_jobs = True
        if (opt in ("-d", "--cedar")):
            config.submit_cedar_jobs = True
            config.rapaccount = val.strip()
        if (opt == "--condor"):
            config.submit_condor_jobs = True

    config.validate()

    fgen = FileGenerator(config)
    fgen.create_directories()
    fgen.generate_mac_files()
    fgen.generate_shell_scripts()

    submitter = JobSubmitter(config, fgen)
    submitter.submit_sukap()
    submitter.submit_cedar()
    submitter.submit_condor()

if __name__ == '__main__':
    main()
