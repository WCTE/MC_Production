#!/bin/bash
source $geant4dir/bin/geant4.sh
source $wcsim_build_dir/this_wcsim.sh
export G4NEUTRONHP_USE_ONLY_PHOTONEVAPORATION=1
WCSim $macfile $tuningfile &> $logfile