#!/bin/bash

cd $curdir
singularity exec -u -B ./:$mntdir $siffile bash $shfile