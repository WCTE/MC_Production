#!/usr/bin/env python
import time
import sys
import getopt
import os
import subprocess
import string
import random

def usage():
    '''Function to create mac, shell and batch job scripts for WCSim, MDT and fiTQun
    '''
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

def runSimulation():
    '''Function to create mac files for WCSim'''

    # make necessary directories
    macdir = "mac"
    outdir = "out"
    logdir = "log"
    shelldir = "shell"
    figdir = "fig"

    curdir = os.getcwd()

    for dir in [macdir,outdir,logdir,shelldir,figdir]:
        if (not os.path.exists(dir)):
            os.makedirs(dir)

    # default parameters
    wcsimdir = "/opt/WCSim"
    geant4dir="/opt/geant4"
    wcsim_build_dir="/opt/WCSim/build"
    mntdir="/mnt"

    # Get container configuration from environment
    siffile = os.environ.get("SOFTWARE_SIF_FILE")
    sandbox = os.environ.get("SOFTWARE_SANDBOX_DIR")
    if not siffile and not sandbox:
        print ("ERROR: SOFTWARE_SIF_FILE and SOFTWARE_SANDBOX_DIR not set.")
        sys.exit(1)

    rngseed = 20260129
    ParticleName = "mu-"

    TankRadius = 307.5926/2
    TankHalfz = 271.4235/2

    nevs = 1000
    nfiles = 100
    useCDS = True
    runWCSim = True
    runMDT = True
    runFQ = True
    submit_sukap_jobs = False
    submit_cedar_jobs = False
    submit_condor_jobs = False
    rapaccount = ""

    useBeam = True
    ParticleKE = 100
    ParticleDirx = 0
    ParticleDiry = 0
    ParticleDirz = 1
    ParticlePosx = 0
    ParticlePosy = -42.47625
    wallD = 0.
    ParticlePosz= -(TankRadius-wallD)

    useUniform = False
    ParticleKELow = 0.
    ParticleKEHigh = 2000.

    useCosmics = False

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
            ParticleName = val.strip()
        if (opt in ("-b", "--beam")):
            useBeam = True
            useUniform = False
            useCosmics = False
            vals = val.strip().split(",")
            ParticleKE = float(vals[0])
            wallD = float(vals[1])
            ParticlePosz = -(TankRadius - wallD)
        if (opt in ("-u", "--uniform")):
            useBeam = False
            useUniform = True
            useCosmics = False
            vals = val.strip().split(",")
            ParticleKELow = float(vals[0])
            ParticleKEHigh = float(vals[1])
        if (opt in ("-m", "--cosmics")):
            useBeam = False
            useUniform = False
            useCosmics = True
        if (opt in ("-n", "--nevs")):
            nevs = int(val.strip())
        if (opt in ("-f", "--nfiles")):
            nfiles = int(val.strip())
        if (opt in ("-s", "--seed")):
            rngseed = int(val.strip())
        if (opt in ("-c", "--cds")):
            useCDS = False
        if (opt == "--wcsim"):
            runWCSim = False
        if (opt == "--mdt"):
            runMDT = False
        if (opt == "--fq"):
            runFQ = False
        if (opt in ("-k", "--sukap")):
            submit_sukap_jobs = True
        if (opt in ("-d", "--cedar")):
            submit_cedar_jobs = True
            rapaccount = val.strip()
        if (opt == "--condor"):
            submit_condor_jobs = True

    if submit_sukap_jobs and not sandbox:
        print ("ERROR: SOFTWARE_SANDBOX_DIR is needed for sukap submission.")
        sys.exit(1)

    wCDSstring = "_wCDS" if useCDS else ""
    wCDSmac = "" if useCDS else "#"
    random.seed(rngseed)

    beamstring = "Beam_%.0fMeV_%icm_" % (ParticleKE,int(wallD)) if useBeam else ""
    beammac = "" if useBeam else "#"

    uniformstring = "Uniform_%.0f_%.0fMeV_" % (ParticleKELow,ParticleKEHigh) if useUniform else ""
    uniformmac = "" if useUniform else "#"

    cosmicsstring = "Comsics_" if useCosmics else ""
    comsicsmac = "" if useCosmics else "#"

    configString = "%s_%s_%s%s" % (wCDSstring,ParticleName,beamstring,uniformstring)
    if useCosmics:
        configString = "%s_%s" % (wCDSstring,cosmicsstring)
    configString_TChain = configString
    if ParticleName[-1]=="+":
        configString_TChain= "%s_%s\\\\\\\\+_%s%s" % (wCDSstring,ParticleName[:-1],beamstring,uniformstring)


    print ("Creating mac files for WCSim")
    for i in range(nfiles):
        fi = open("template/WCTE.mac",'r')
        macLines = fi.read()
        macTemplate = string.Template(macLines)
        macFile = "%s/wcsim%s%04i.mac" % (macdir,configString,i)
        fo = open(macFile, 'w')
        macseed = random.randrange(int(1e9))
        fo.write(macTemplate.substitute(wcsimdir=wcsimdir, rngseed=macseed, wCDSmac=wCDSmac, 
                                        beammac=beammac,uniformmac=uniformmac,comsicsmac=comsicsmac,
                                        ParticleName=ParticleName,ParticleKE=ParticleKE,
                                        ParticleDirx=ParticleDirx,ParticleDiry=ParticleDiry,ParticleDirz=ParticleDirz,
                                        ParticlePosx=ParticlePosx,ParticlePosy=ParticlePosy,ParticlePosz=ParticlePosz,
                                        ParticleKELow=ParticleKELow,ParticleKEHigh=ParticleKEHigh, 
                                        rmac=TankRadius, zmac=TankHalfz,
                                        nevs=nevs,filename="%s/%s/wcsim%s%04i.root" % (mntdir,outdir,configString,i)))
        fo.close()
        fi.close()
        fi = open("template/tuning_parameters.mac",'r')
        macLines = fi.read()
        macTemplate = string.Template(macLines)
        macFile = "%s/tuning_parameters%s%04i.mac" % (macdir,configString,i)
        fo = open(macFile, 'w')
        fo.write(macTemplate.substitute(wcsimdir=wcsimdir))
        fo.close()
        fi.close()

    cern_condor="" if submit_condor_jobs else "#"
    userns="-u" if submit_sukap_jobs else ""
    siffile=sandbox if submit_sukap_jobs else siffile
    runwcsim="" if runWCSim else "#"
    runmdt="" if runMDT else "#"
    runfq="" if runFQ else "#"

    print ("Creating shell scripts for simulation")
    for i in range(nfiles):
        fi = open("template/run.sh",'r')
        shLines = fi.read()
        shTemplate = string.Template(shLines)
        shFile = "%s/run%s%04i.sh" % (shelldir,configString,i)
        fo = open(shFile, 'w')
        wcsimfile="%s/%s/wcsim%s%04i.root" % (mntdir,outdir,configString,i)
        mdtfile="%s/%s/mdt%s%04i.root" % (mntdir,outdir,configString,i)
        fqfile="%s/%s/fq%s%04i.root" % (mntdir,outdir,configString,i)
        fo.write(shTemplate.substitute
            (curdir=curdir,cern_condor=cern_condor, userns=userns,
            mntdir=mntdir,siffile=siffile,
            runwcsim=runwcsim,runmdt=runmdt,runfq=runfq,
            macfile="%s/%s/wcsim%s%04i.mac" % (mntdir,macdir,configString,i),
            tuningfile="%s/%s/tuning_parameters%s%04i.mac" % (mntdir,macdir,configString,i),
            logfile="%s/%s/run%s%04i.log" % (mntdir,logdir,configString,i),
            wcsimfile=wcsimfile, nevs=nevs,
            mdtfile=mdtfile,
            fqfile=fqfile,
            rngseed=random.randrange(int(1e9))))
        fo.close()
        fi.close()

    if submit_sukap_jobs :
        pjdir = "pjdir"
        pjoutdir = "pjout"
        pjerrdir = "pjerr"
        for dir in [pjdir,pjoutdir,pjerrdir]:
            if (not os.path.exists(dir)):
                os.makedirs(dir)

        allFilesOK = False

        while not allFilesOK:

            job_id = []

            print ("Submitting pjsub jobs on sukap")
            for i in range(nfiles):
                if (not os.path.exists("%s/wcsim%s%04i.root" % (outdir,configString,i))):
                    # wait until job count is small enough
                    while True:
                        com = subprocess.Popen("pjstat | wc -l" , shell=True, stdout = subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True)
                        res, err = com.communicate()
                        queueCount = int(res)
                        if queueCount < 300:
                            break
                        time.sleep(10)

                    fi = open("template/pjsub.sh",'r')
                    shLines = fi.read()
                    shTemplate = string.Template(shLines)
                    shFile = "%s/run%s%04i.sh" % (shelldir,configString,i)
                    pjFile = "%s/pjsub%s%04i.sh" % (pjdir,configString,i)
                    pjout = "%s/pjsub%s%04i.out" % (pjoutdir,configString,i)
                    pjerr = "%s/pjsub%s%04i.err" % (pjerrdir,configString,i)
                    fo = open(pjFile, 'w')
                    fo.write(shTemplate.substitute
                        (curdir=curdir,shFile=shFile,pjout=pjout,pjerr=pjerr))
                    fo.close()
                    fi.close()

                    # repeatedly submit job until success
                    while True:
                        com = subprocess.Popen("pjsub %s" % (pjFile), shell=True, 
                                            stdout = subprocess.PIPE, stderr=subprocess.PIPE, 
                                            close_fds=True)
                        res, err = com.communicate()
                        if (len(err) == 0):
                            print (res)
                            job_id.append([int(res.split()[-2]),i])
                            break
                        print (err)
                        time.sleep(1)
            
            allFilesOK = True
            # for i in range(len(job_id)):
            #     # check if a job is completed
            #     while True:
            #         com = subprocess.Popen("pjstat %i | wc -l" % job_id[i][0], shell=True, stdout = subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True)
            #         res, err = com.communicate()
            #         time.sleep(10)
            #         print ("sleep for 10s")
                    
        # # Make validation plots
        # if useBeam:
        #     print("singularity exec -u -B ./:%s %s root -l -b -q %s/validation/EventDisplay.c\(\\\"%s/%s/wcsim%s\*\[0-9\].root\\\"\)" % (mntdir,sandbox,mntdir,mntdir,outdir,configString_TChain))
        #     com = subprocess.Popen("singularity exec -u -B ./:%s %s root -l -b -q %s/validation/EventDisplay.c\(\\\"%s/%s/wcsim%s\*\[0-9\].root\\\"\)" % (mntdir,sandbox,mntdir,mntdir,outdir,configString_TChain), shell=True, 
        #                             stdout = subprocess.PIPE, stderr=subprocess.PIPE, 
        #                             close_fds=True)
        #     res, err = com.communicate()
        #     if (len(err)>0):
        #         print (err)
        #         sys.exit(1)
        #     else:
        #         print (res)

        # else:
        #     com = subprocess.Popen("singularity exec -u -B ./:%s %s root -l -b -q %s/validation/VertexDistribution.c\(\\\"%s/%s/wcsim%s\*\[0-9\].root\\\"\)" % (mntdir,sandbox,mntdir,mntdir,outdir,configString), shell=True, 
        #                             stdout = subprocess.PIPE, stderr=subprocess.PIPE, 
        #                             close_fds=True)
        #     res, err = com.communicate()
        #     if (len(err)>0):
        #         print (err)
        #         sys.exit(1)
        #     else:
        #         print (res)

    if submit_cedar_jobs :
        sldir = "sldir"
        sloutdir = "slout"
        slerrdir = "slerr"
        for dir in [sldir,sloutdir,slerrdir]:
            if (not os.path.exists(dir)):
                os.makedirs(dir)
        print ("Creating slurm scripts for WCSim")
        for i in range(nfiles):
            fi = open("template/slurm_wcsim.sh",'r')
            slLines = fi.read()
            slTemplate = string.Template(slLines)
            slFile = "%s/slurm%s%04i.sh" % (sldir,configString,i)
            slout = "%s/slurm%s%04i" % (sloutdir,configString,i)
            slerr = "%s/slurm%s%04i" % (slerrdir,configString,i)
            fo = open(slFile, 'w')
            fo.write(slTemplate.substitute(account=rapaccount, curdir=curdir, mntdir=mntdir, siffile=siffile, sout=slout, serr=slerr,
                                           shfile="%s/run%s%04i.sh" % (shelldir,configString,i)))
            fo.close()
            fi.close()

        print ("Submitting slurm jobs on cedar")
        for i in range(nfiles):
            if (not os.path.exists("%s/wcsim%s%04i.root" % (outdir,configString,i))):
                slFile = "%s/slurm%s%04i.sh" % (sldir,configString,i)
                com = subprocess.Popen("sbatch %s" % (slFile), shell=True, 
                                    stdout = subprocess.PIPE, stderr=subprocess.PIPE, 
                                    close_fds=True)
                res, err = com.communicate()
                if (len(err) > 0):
                    print (err)
                    sys.exit(1)
                else:
                    print (res)

    if submit_condor_jobs :
        print ("Creating condor scripts")
        condordir = "condor_dir"
        condorout = "condor_out"
        condorerr = "condor_err"
        condorlog = "condor_log"
        for dir in [condordir,condorout,condorerr,condorlog]:
            if (not os.path.exists(dir)):
                os.makedirs(dir)
        for i in range(nfiles):
            fi = open("template/condor_submit.sub",'r')
            condorLines = fi.read()
            condorTemplate = string.Template(condorLines)
            condorFile = "%s/condor%s%04i.sub" % (condordir,configString,i)
            fo = open(condorFile, 'w')
            out="%s/condor%s%04i" % (condorout,configString,i)
            err="%s/condor%s%04i" % (condorerr,configString,i)
            log="%s/condor%s%04i" % (condorlog,configString,i)
            shfile="%s/run%s%04i.sh" % (shelldir,configString,i)
            fo.write(condorTemplate.substitute(shfile=shfile, out=out, err=err, log=log))
            fo.close()
            fi.close()
        print ("Submitting condor jobs on lxplus")
        for i in range(nfiles):
            if (not os.path.exists("%s/wcsim%s%04i.root" % (outdir,configString,i))):
                condorFile = "%s/condor%s%04i.sub" % (condordir,configString,i)
                com = subprocess.Popen("module load lxbatch/eossubmit && condor_submit %s" % (condorFile), shell=True, 
                                    stdout = subprocess.PIPE, stderr=subprocess.PIPE, 
                                    close_fds=True)
                res, err = com.communicate()
                if (len(err) > 0):
                    print (err)
                    sys.exit(1)
                else:
                    print (res)



if __name__ == '__main__':
    runSimulation()
