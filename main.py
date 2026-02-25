from fastapi import FastAPI, Request, Form, BackgroundTasks, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import runSimulation
import os
import sys
import io
from contextlib import redirect_stdout

# Check Environment Variables on startup
if not os.environ.get("SOFTWARE_SIF_FILE") and not os.environ.get("SOFTWARE_SANDBOX_DIR"):
    print("\033[91mCRITICAL ERROR: Environment not configured.\033[0m")
    print("You must source 'setup.sh' before starting this server.")
    print("Usage: source setup.sh <sif_file> [sandbox_dir]")
    sys.exit(1)

app = FastAPI()

# Ensure templates directory exists
if not os.path.exists("templates"):
    os.makedirs("templates")

templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/submit")
async def submit_simulation(
    particle_name: str = Form(...),
    mode: str = Form("beam"),
    energy: float = Form(100),
    wall_distance: float = Form(0),
    energy_low: float = Form(0),
    energy_high: float = Form(2000),
    nevs: int = Form(1000),
    nfiles: int = Form(100),
    batch_system: str = Form("none"), # none, sukap, cedar, condor
    rap_account: str = Form(""),
    sukap_queue: str = Form("all"),
    condor_queue: str = Form("tomorrow"),
    seed: int = Form(20260129),
    # Boolean flags: Default to False so that if unchecked (sending nothing), they are False.
    # The HTML form will have them checked by default, sending 'true'.
    run_wcsim: bool = Form(False),
    run_mdt: bool = Form(False),
    run_fq: bool = Form(False)
):
    # Check Environment Variables manually to avoid sys.exit() in SimulationConfig.validate()
    siffile = os.environ.get("SOFTWARE_SIF_FILE")
    sandbox = os.environ.get("SOFTWARE_SANDBOX_DIR")
    
    if not siffile and not sandbox:
        msg = ("Server Error: SOFTWARE_SIF_FILE and SOFTWARE_SANDBOX_DIR are not set in the environment.<br>"
               "Please source the setup script before running the server:<br>"
               "<code>source setup.sh &lt;sif_file&gt; [sandbox_dir] [--build]</code>")
        raise HTTPException(status_code=500, detail=msg)

    # Initialize Configuration
    config = runSimulation.SimulationConfig()
    config.ParticleName = particle_name
    config.nevs = nevs
    config.nfiles = nfiles
    config.rngseed = seed
    
    # Set Toggles
    config.runWCSim = run_wcsim
    config.runMDT = run_mdt
    config.runFQ = run_fq

    # Configure Mode
    if mode == "beam":
        config.useBeam = True
        config.useUniform = False
        config.useCosmics = False
        config.ParticleKE = energy
        config.wallD = wall_distance
        config.ParticlePosz = -(config.TankRadius - config.wallD)
    elif mode == "uniform":
        config.useBeam = False
        config.useUniform = True
        config.useCosmics = False
        config.ParticleKELow = energy_low
        config.ParticleKEHigh = energy_high
    elif mode == "cosmics":
        config.useBeam = False
        config.useUniform = False
        config.useCosmics = True
    
    # Configure Batch System
    if batch_system == "sukap":
        if not sandbox:
             raise HTTPException(status_code=400, detail="Configuration Error: SOFTWARE_SANDBOX_DIR is required for Sukap submission.")
        config.submit_sukap_jobs = True
        config.sukap_queue = sukap_queue
    elif batch_system == "cedar":
        config.submit_cedar_jobs = True
        config.rapaccount = rap_account
    elif batch_system == "condor":
        config.submit_condor_jobs = True
        config.condor_queue = condor_queue
        
    # Generate Files
    try:
        fgen = runSimulation.FileGenerator(config)
        fgen.create_directories()
        fgen.generate_mac_files()
        fgen.generate_shell_scripts()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File Generation Failed: {str(e)}")

    # Submit Jobs
    submitter = runSimulation.JobSubmitter(config, fgen)
    
    # Scan jobs to get counts for the response message
    n_submit, n_skip = submitter.scan_jobs()
    msg_suffix = f" (Submitted {n_submit} jobs, Skipped {n_skip} existing)"
    
    try:
        if config.submit_sukap_jobs:
            submitter.submit_sukap()
        if config.submit_cedar_jobs:
            submitter.submit_cedar()
        if config.submit_condor_jobs:
            submitter.submit_condor()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    return {
        "status": "success", 
        "message": f"Simulation configured for {particle_name}. Job submission to ({batch_system}) completed.{msg_suffix}",
        "config_string": config.get_config_string()
    }

@app.get("/status")
async def get_job_status(batch_system: str = "none"):
    # Initialize config
    config = runSimulation.SimulationConfig()
    
    if batch_system == "sukap":
        config.submit_sukap_jobs = True
    elif batch_system == "cedar":
        config.submit_cedar_jobs = True
    elif batch_system == "condor":
        config.submit_condor_jobs = True
    
    status_checker = runSimulation.JobStatus(config)
    return status_checker.get_jobs()

@app.post("/kill")
async def kill_all_jobs(batch_system: str = Form("none")):
    config = runSimulation.SimulationConfig()
    
    if batch_system == "sukap":
        config.submit_sukap_jobs = True
    elif batch_system == "cedar":
        config.submit_cedar_jobs = True
    elif batch_system == "condor":
        config.submit_condor_jobs = True
    else:
        return {"status": "error", "message": "Invalid batch system selected."}

    status_checker = runSimulation.JobStatus(config)
    
    # Capture the output of the kill_jobs function
    f = io.StringIO()
    with redirect_stdout(f):
        status_checker.kill_jobs()
    output = f.getvalue()
    
    return {"status": "success", "message": output}