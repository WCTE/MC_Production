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
    print ("createWCSimFiles.py [-h] [-p <particleName>][-e <KE>][-w <distance>][-n <events>][-f <files>][-s <seed>][-c][-k]")
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
    print ("")

def createWCSimFiles():
    '''Function to create mac files for WCSim'''

    # make necessary directories
    macdir = "mac"
    outdir = "out"
    logdir = "log"
    shelldir = "shell"
    pjdir = "pjdir"
    pjoutdir = "pjout"
    pjerrdir = "pjerr"
    figdir = "fig"

    curdir = os.getcwd()

    for dir in [macdir,outdir,logdir,shelldir,pjdir,pjoutdir,pjerrdir,figdir]:
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
    ParticlePosz= radius-30
    nevs = 1000
    nfiles = 100
    useCDS = False
    submit_sukap_jobs = False

    try:
        opts, args = getopt.getopt(sys.argv[1:], "hckp:e:w:n:f:s:",
                                   ["help", "pid=", "ke=", 
                                    "wall=", "nevs=", "nfiles=",
                                    "seed=", "cds", "sukap"])
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
            ParticlePosz= radius - float(val.strip())
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

    wCDSstring = "_wCDS" if useCDS else ""
    wCDSmac = "" if useCDS else "#"
    random.seed(rngseed)

    print ("Creating mac files for WCSim")
    for i in range(nfiles):
        fi = open("template/WCTE.mac",'r')
        macLines = fi.read()
        macTemplate = string.Template(macLines)
        macFile = "%s/wcsim%s_%s_%.0fMeV_%04i.mac" % (macdir,wCDSstring,ParticleName,ParticleKE,i)
        fo = open(macFile, 'w')
        macseed = random.randrange(int(1e9))
        fo.write(macTemplate.substitute(wcsimdir=wcsimdir, rngseed=macseed, wCDSmac=wCDSmac, 
                                        ParticleName=ParticleName,ParticleKE=ParticleKE,
                                        ParticleDirx=ParticleDirx,ParticleDiry=ParticleDiry,ParticleDirz=ParticleDirz,
                                        ParticlePosx=ParticlePosx,ParticlePosy=ParticlePosy,ParticlePosz=ParticlePosz,
                                        nevs=nevs,filename="%s/%s/wcsim%s_%s_%.0fMeV_%04i.root" % (mntdir,outdir,wCDSstring,ParticleName,ParticleKE,i)))
        fo.close()
        fi.close()

    print ("Creating shell scripts for WCSim")
    for i in range(nfiles):
        fi = open("template/run_wcsim.sh",'r')
        shLines = fi.read()
        shTemplate = string.Template(shLines)
        shFile = "%s/wcsim%s_%s_%.0fMeV_%04i.sh" % (shelldir,wCDSstring,ParticleName,ParticleKE,i)
        fo = open(shFile, 'w')
        fo.write(shTemplate.substitute(geant4dir=geant4dir, wcsim_build_dir=wcsim_build_dir,
                                   macfile="%s/%s/wcsim%s_%s_%.0fMeV_%04i.mac" % (mntdir,macdir,wCDSstring,ParticleName,ParticleKE,i),
                                   tuningfile="%s/macros/tuning_parameters.mac" % (wcsimdir),
                                   logfile="%s/%s/wcsim%s_%s_%.0fMeV_%04i.log" % (mntdir,logdir,wCDSstring,ParticleName,ParticleKE,i)))
        fo.close()
        fi.close()

    if submit_sukap_jobs :
        siffile = "wcsim_sandbox/"
        print ("Creating pjsub scripts for WCSim")
        for i in range(nfiles):
            fi = open("template/pjsub_wcsim.sh",'r')
            pjLines = fi.read()
            pjTemplate = string.Template(pjLines)
            pjFile = "%s/pjsub%s_%s_%.0fMeV_%04i.sh" % (pjdir,wCDSstring,ParticleName,ParticleKE,i)
            fo = open(pjFile, 'w')
            fo.write(pjTemplate.substitute(curdir=curdir, mntdir=mntdir, siffile=siffile,
                                        shfile="%s/%s/wcsim%s_%s_%.0fMeV_%04i.sh" % (mntdir,shelldir,wCDSstring,ParticleName,ParticleKE,i)))
            fo.close()
            fi.close()

        print ("Submitting pjsub jobs on sukap")
        for i in range(nfiles):
            pjFile = "%s/pjsub%s_%s_%.0fMeV_%04i.sh" % (pjdir,wCDSstring,ParticleName,ParticleKE,i)
            pjout = "%s/pjsub%s_%s_%.0fMeV_%04i.%%j.out" % (pjoutdir,wCDSstring,ParticleName,ParticleKE,i)
            pjerr = "%s/pjsub%s_%s_%.0fMeV_%04i.%%j.err" % (pjerrdir,wCDSstring,ParticleName,ParticleKE,i)
            com = subprocess.Popen("pjsub -o %s -e %s %s" % (pjout,pjerr,pjFile), shell=True, 
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
