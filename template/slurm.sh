#!/bin/bash
#SBATCH --account=$account
#SBATCH --time=0-24:0:0
#SBATCH --mem=16000M
#SBATCH --output=$sout.%A.out
#SBATCH --error=$serr.%A.err
#SBATCH --cpus-per-task=1

module load apptainer

cd $curdir
bash $shFile