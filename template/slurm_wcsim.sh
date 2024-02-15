#!/bin/bash
#SBATCH --account=$account
#SBATCH --time=0-23:0:0
#SBATCH --mem=10G
#SBATCH --output=$sout.%A.out
#SBATCH --error=$serr.%A.err
#SBATCH --cpus-per-task=1

cd $curdir
singularity exec -B ./:$mntdir $siffile bash $shfile