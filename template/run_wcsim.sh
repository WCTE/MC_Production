#!/bin/bash
source $geant4dir/bin/geant4.sh
source $wcsim_build_dir/this_wcsim.sh
WCSim $macfile $tuningfile &> $logfile