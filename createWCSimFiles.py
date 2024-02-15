#!/usr/bin/env python
import time
import sys
import getopt
import os
import subprocess
import string
import random

def usage():
    '''Function to create mac, shell and batch job scripts for WCSim
    '''
    print ("Function to create mac, shell and batch job scripts for WCSim")
    print ("Usage:")
    print ("createWCSimFiles.py [-h] [-p <particleName>][-e <KE>][-w <distance>][-n <events>][-f <files>][-s <seed>][-c][-k][-d <account>]")
    print ("")
    print ("Options:")
    print ("-h, --help: prints help message")
    print ("-p, --pid=<name>: particle name (mu-, e-, etc.)")
    print ("-e, --ke=<val>: particle KE in MeV")
    print ("-w, --wall=<val>: distance from vertex to blacksheet behind in cm")
    print ("-n, --nevs=<val>: number of events per file")
    print ("-f, --nfiles=<val>: numbe of files to be generated")
    print ("-s, --seed=<val>: RNG seed used in this script")
    print ("-c, --cds: use CDS in WCSim")
    print ("-k, --sukap: submit batch jobs on sukap")
    print ("-d, --cedar=<account>: submit batch jobs on cedar with specified RAP account")
    print ("")

def createWCSimFiles():
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
    rngseed = 20240213
    ParticleName = "mu-"
    ParticleKE = 100
    ParticleDirx = 0
    ParticleDiry = 0
    ParticleDirz = -1
    ParticlePosx = 0
    ParticlePosy = -29
    radius = 319.2536/2
    wallD = 30.
    ParticlePosz= radius-wallD
    nevs = 1000
    nfiles = 100
    useCDS = False
    submit_sukap_jobs = False
    submit_cedar_jobs = False
    rapaccount = ""

    try:
        opts, args = getopt.getopt(sys.argv[1:], "hckp:e:w:n:f:s:d:",
                                   ["help", "pid=", "ke=", 
                                    "wall=", "nevs=", "nfiles=",
                                    "seed=", "cds", "sukap","cedar="])
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
        if (opt in ("-e", "--ke")):
            ParticleKE = float(val.strip())
        if (opt in ("-w", "--wall")):
            wallD = float(val.strip())
            ParticlePosz= radius - wallD
        if (opt in ("-n", "--nevs")):
            nevs = int(val.strip())
        if (opt in ("-f", "--nfiles")):
            nfiles = int(val.strip())
        if (opt in ("-s", "--seed")):
            rngseed = int(val.strip())
        if (opt in ("-c", "--cds")):
            useCDS = True
        if (opt in ("-k", "--sukap")):
            submit_sukap_jobs = True
        if (opt in ("-d", "--cedar")):
            submit_cedar_jobs = True
            rapaccount = val.strip()

    wCDSstring = "_wCDS" if useCDS else ""
    wCDSmac = "" if useCDS else "#"
    random.seed(rngseed)

    configString = "%s_%s_%.0fMeV_%icm_" % (wCDSstring,ParticleName,ParticleKE,int(wallD))

    print ("Creating mac files for WCSim")
    for i in range(nfiles):
        fi = open("template/WCTE.mac",'r')
        macLines = fi.read()
        macTemplate = string.Template(macLines)
        macFile = "%s/wcsim%s%04i.mac" % (macdir,configString,i)
        fo = open(macFile, 'w')
        macseed = random.randrange(int(1e9))
        fo.write(macTemplate.substitute(wcsimdir=wcsimdir, rngseed=macseed, wCDSmac=wCDSmac, 
                                        ParticleName=ParticleName,ParticleKE=ParticleKE,
                                        ParticleDirx=ParticleDirx,ParticleDiry=ParticleDiry,ParticleDirz=ParticleDirz,
                                        ParticlePosx=ParticlePosx,ParticlePosy=ParticlePosy,ParticlePosz=ParticlePosz,
                                        nevs=nevs,filename="%s/%s/wcsim%s%04i.root" % (mntdir,outdir,configString,i)))
        fo.close()
        fi.close()

    print ("Creating shell scripts for WCSim")
    for i in range(nfiles):
        fi = open("template/run_wcsim.sh",'r')
        shLines = fi.read()
        shTemplate = string.Template(shLines)
        shFile = "%s/wcsim%s%04i.sh" % (shelldir,configString,i)
        fo = open(shFile, 'w')
        fo.write(shTemplate.substitute(geant4dir=geant4dir, wcsim_build_dir=wcsim_build_dir,
                                   macfile="%s/%s/wcsim%s%04i.mac" % (mntdir,macdir,configString,i),
                                   tuningfile="%s/macros/tuning_parameters.mac" % (wcsimdir),
                                   logfile="%s/%s/wcsim%s%04i.log" % (mntdir,logdir,configString,i)))
        fo.close()
        fi.close()

    if submit_sukap_jobs :
        pjdir = "pjdir"
        pjoutdir = "pjout"
        pjerrdir = "pjerr"
        for dir in [pjdir,pjoutdir,pjerrdir]:
            if (not os.path.exists(dir)):
                os.makedirs(dir)
        siffile = "wcsim_sandbox/"
        print ("Creating pjsub scripts for WCSim")
        for i in range(nfiles):
            fi = open("template/pjsub_wcsim.sh",'r')
            pjLines = fi.read()
            pjTemplate = string.Template(pjLines)
            pjFile = "%s/pjsub%s%04i.sh" % (pjdir,configString,i)
            fo = open(pjFile, 'w')
            fo.write(pjTemplate.substitute(curdir=curdir, mntdir=mntdir, siffile=siffile,
                                           shfile="%s/%s/wcsim%s%04i.sh" % (mntdir,shelldir,configString,i)))
            fo.close()
            fi.close()

        print ("Submitting pjsub jobs on sukap")
        for i in range(nfiles):
            pjFile = "%s/pjsub%s%04i.sh" % (pjdir,configString,i)
            pjout = "%s/pjsub%s%04i.%%j.out" % (pjoutdir,configString,i)
            pjerr = "%s/pjsub%s%04i.%%j.err" % (pjerrdir,configString,i)
            com = subprocess.Popen("pjsub -o %s -e %s %s" % (pjout,pjerr,pjFile), shell=True, 
                                stdout = subprocess.PIPE, stderr=subprocess.PIPE, 
                                close_fds=True)
            res, err = com.communicate()
            if (len(err) > 0):
                print (err)
                sys.exit(1)
            else:
                print (res)

    if submit_cedar_jobs :
        sldir = "sldir"
        sloutdir = "slout"
        slerrdir = "slerr"
        for dir in [sldir,sloutdir,slerrdir]:
            if (not os.path.exists(dir)):
                os.makedirs(dir)
        siffile = "softwarecontainer_main.sif"
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
                                           shfile="%s/%s/wcsim%s%04i.sh" % (mntdir,shelldir,configString,i)))
            fo.close()
            fi.close()

        print ("Submitting pjsub jobs on sukap")
        for i in range(nfiles):
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


if __name__ == '__main__':
    createWCSimFiles()
