#!/bin/bash


EXE=singularity

${cern_condor}export APPTAINER_BINDPATH=/afs,/cvmfs,/cvmfs/grid.cern.ch/etc/grid-security:/etc/grid-security,/cvmfs/grid.cern.ch/etc/grid-security/vomses:/etc/vomses,/eos,/etc/pki/ca-trust,/etc/tnsnames.ora,/run/user,/var/run/user
${cern_condor}EXE=apptainer

# run wcsim
$$EXE exec $userns -B $curdir:$mntdir $siffile bash -c 'source /opt/entrypoint.sh && WCSim $macfile $tuningfile &> $logfile'

# Remove in valid files
$$EXE exec $userns -B $curdir:$mntdir $siffile bash -c 'source /opt/entrypoint.sh && root -l -b -q $mntdir/validation/RemoveInvalidFile.c\(\"$wcsimfile\",$nevs\)'

# run mdt
$$EXE exec $userns -B $curdir:$mntdir $siffile bash -c 'source /opt/entrypoint.sh && $$MDTROOT/app/application/appWCTESingleEvent -i $wcsimfile -p $$MDTROOT/parameter/MDTParamenter_WCTE.txt -o $mdtfile -s $rngseed -n -1 &>> $logfile'

# run fiTQun
$$EXE exec $userns -B $curdir:$mntdir $siffile bash -c 'source /opt/entrypoint.sh && $$FITQUN_ROOT/runfiTQunWC -p $$FITQUN_ROOT/ParameterOverrideFiles/nuPRISMBeamTest_16cShort_mPMT.parameters.dat -r $fqfile $mdtfile &>> $logfile'
