R__LOAD_LIBRARY(/opt/WCSim/build/install/lib/libWCSimRoot.so)

std::vector<TH1*> EventDisplay(const char * fname)
{
    gStyle->SetOptStat(0);

    TChain *t = new TChain("wcsimT");
    t->Add(fname);
    std::string single_file_name = t->GetFile()->GetName();
    // Get the first file for geometry
    TFile *f = TFile::Open(single_file_name.c_str());
    if (!f->IsOpen()){
        std::cout << "Error, could not open input file: " << single_file_name << std::endl;
        return std::vector<TH1*>();
    }
    if (!f->IsOpen()) return std::vector<TH1*>();

    std::string prefix = fname;
    if (prefix.find_last_of("/")!=std::string::npos) 
    {   
        prefix = prefix.substr(prefix.find_last_of("/")+1);
    }
    if (prefix.find_last_of("[")!=std::string::npos) 
    {   
        prefix = prefix.substr(0,prefix.find_last_of("["));
    }
    if (prefix.find_last_of("*")!=std::string::npos) 
    {   
        prefix = prefix.substr(0,prefix.find_last_of("*"));
    }
    std::cout<<"prefix = "<<prefix<<std::endl;

    WCSimRootEvent* wcsimrootsuperevent = new WCSimRootEvent();
    t->SetBranchAddress("wcsimrootevent",&wcsimrootsuperevent);

    WCSimRootTrigger* wcsimrootevent;
    // Get vertex and beam direction from first event
    t->GetEntry(0);
    wcsimrootevent=wcsimrootsuperevent->GetTrigger(0);
    TVector3 vtx(wcsimrootevent->GetVtx(0),wcsimrootevent->GetVtx(1),wcsimrootevent->GetVtx(2));
    TVector3 BeamDir(((WCSimRootTrack*)wcsimrootevent->GetTracks()->At(0))->GetDir(0),((WCSimRootTrack*)wcsimrootevent->GetTracks()->At(0))->GetDir(1),((WCSimRootTrack*)wcsimrootevent->GetTracks()->At(0))->GetDir(2));
    std::cout<<"BeamDir = "<<BeamDir.x()<<" "<<BeamDir.y()<<" "<<BeamDir.z()<<std::endl;

    // Geometry tree - only need 1 "event"
    WCSimRootGeom *geo = 0;
    TTree *geotree = (TTree*)f->Get("wcsimGeoT");
    geotree->SetBranchAddress("wcsimrootgeom", &geo);
    std::cout << "Geotree has " << geotree->GetEntries() << " entries" << std::endl;
    if (geotree->GetEntries() == 0) {
        exit(9);
    }
    geotree->GetEntry(0);
    int nPMTs_type0=geo->GetWCNumPMT();
    std::cout << "geo has " << nPMTs_type0 << " PMTs" << std::endl;
    std::vector<std::vector<double>> pmt_pos(nPMTs_type0);
    std::vector<TVector3> pmt_posT(nPMTs_type0);
    std::vector<std::vector<double>> pmt_dir(nPMTs_type0);
    std::vector<double> pmt_ang(nPMTs_type0);
    std::vector<double> pmt_tof(nPMTs_type0);
    double vg = 2.20027795333758801e8*100/1.e9; // rough speed of light in water in cm/ns
    double max_r = 0, max_z = 0;
    for (int i=0;i<nPMTs_type0;i++) 
    {
        WCSimRootPMT pmt;
        pmt = geo->GetPMT(i);
        std::vector<double> pos(3);
        std::vector<double> dir(3);
        for(int j=0;j<3;j++){
            pos[j] = pmt.GetPosition(j);
            dir[j] = pmt.GetOrientation(j);
        }
        pmt_pos[i] = pos;
        pmt_dir[i] = dir;

        TVector3 pmtpos(pos[0],pos[1],pos[2]);
        pmt_posT[i] = pmtpos;
        pmt_ang[i] = BeamDir.Angle(pmtpos-vtx)*180/TMath::Pi();

        pmt_tof[i] = (pmtpos-vtx).Mag()/vg;

        // y-axis is vertical
        if (max_z<fabs(pos[1])) max_z=fabs(pos[1]);
        if (max_r<sqrt(pos[0]*pos[0]+pos[2]*pos[2]))
            if (fabs(pmt.GetOrientation(1))>0.5) max_r = sqrt(pos[0]*pos[0]+pos[2]*pos[2]);
    }

    double barrelCut = max_z-10;
    TH2D* hist_event_display = new TH2D("Charges","Charges",250,-TMath::Pi()*max_r,TMath::Pi()*max_r,250,-max_z-2*max_r,max_z+2*max_r);
    std::vector<std::vector<double>> eventDiplayXY;
    for (int i=0;i<nPMTs_type0;i++)
    {
        // rotation for event display
        double x = -pmt_pos.at(i).at(0);
        double y = pmt_pos.at(i).at(2);
        double z = pmt_pos.at(i).at(1);
        std::vector<double> pmtXY;
        if (fabs(z)<barrelCut) // barrel
        {
            double th = atan2(y,x);
            pmtXY.push_back(-max_r*th);
            pmtXY.push_back(z);
        }
        else if (z>barrelCut) //top
        {
            pmtXY.push_back(-y);
            pmtXY.push_back(max_z+max_r-x);
        }
        else //bot
        {
            pmtXY.push_back(-y);
            pmtXY.push_back(-max_z-max_r+x);
        }
        eventDiplayXY.push_back(pmtXY);
    }

    std::vector<double> pmt_hit(nPMTs_type0,0.);
    TH1D* hist_timetof = new TH1D("DigiTime-TOF","DigiTime-TOF",1000,-20,40);
    TH1D* hist_timetof_true = new TH1D("TrueTime-TOF","TrueTime-TOF",1000,-1,5);
    for (long int nev=0;nev<t->GetEntries();nev++)
    {
        if (nev%(t->GetEntries()/100)==0) std::cout<<"Running "<<nev<<"-th event of total "<<t->GetEntries()<<" events"<<std::endl;

        delete wcsimrootsuperevent;
        wcsimrootsuperevent = 0;  // EXTREMELY IMPORTANT

        t->GetEntry(nev);
        wcsimrootevent = wcsimrootsuperevent->GetTrigger(0);

        std::vector<double> triggerInfo = wcsimrootevent->GetTriggerInfo();
        double triggerShift=0, triggerTime=0;
        if(wcsimrootevent->GetTriggerType()!=kTriggerNoTrig && triggerInfo.size()>=3)
        {
            triggerShift = triggerInfo[1];
            triggerTime = triggerInfo[2];
        }

        int nhits = wcsimrootevent->GetNcherenkovdigihits(); 

        // Fill digi hit histogram
        for (int i=0; i< nhits ; i++)
        {
            WCSimRootCherenkovDigiHit* wcsimrootcherenkovdigihit = (WCSimRootCherenkovDigiHit*) (wcsimrootevent->GetCherenkovDigiHits())->At(i);
            int tubeNumber     = wcsimrootcherenkovdigihit->GetTubeId()-1;
            double peForTube      = wcsimrootcherenkovdigihit->GetQ();
            double time = wcsimrootcherenkovdigihit->GetT()+triggerTime-triggerShift;

            pmt_hit[tubeNumber] += peForTube;

            hist_timetof->Fill(time-pmt_tof[tubeNumber],peForTube);
        }

        // Fill true hit histgram
        int ncherenkovhits     = wcsimrootevent->GetNcherenkovhits();
        TClonesArray *timeArray = wcsimrootevent->GetCherenkovHitTimes();
        for (int i=0; i< ncherenkovhits ; i++)
        {
            WCSimRootCherenkovHit *wcsimrootcherenkovhit = (WCSimRootCherenkovHit*) (wcsimrootevent->GetCherenkovHits())->At(i);
            int tubeNumber     = wcsimrootcherenkovhit->GetTubeID()-1;
            int timeArrayIndex = wcsimrootcherenkovhit->GetTotalPe(0);
            int peForTube      = wcsimrootcherenkovhit->GetTotalPe(1);
            for (int idx = timeArrayIndex; idx<timeArrayIndex+peForTube; idx++)
            {
                WCSimRootCherenkovHitTime * cht = (WCSimRootCherenkovHitTime*) timeArray->At(idx);
                TVector3 endPos(cht->GetPhotonEndPos(0)/10.,cht->GetPhotonEndPos(1)/10.,cht->GetPhotonEndPos(2)/10.); // mm to cm
                TVector3 endDir(cht->GetPhotonEndDir(0),cht->GetPhotonEndDir(1),cht->GetPhotonEndDir(2));
                hist_timetof_true->Fill(cht->GetTruetime()-(endPos-vtx).Mag()/vg);
            }
        }
    }

    for (int i=0;i<nPMTs_type0;i++)
    {
        hist_event_display->Fill(eventDiplayXY.at(i).at(0),eventDiplayXY.at(i).at(1),pmt_hit[i]);
    }
    TCanvas* c1 = new TCanvas();

    hist_event_display->Draw("colz");
    double vtx_x = -vtx.x(), vtx_y = vtx.z(), vtx_z = vtx.y();
    // Extrapolate beam target point on the other side of the tank
    double target_x = vtx_x - BeamDir.x(), target_y = vtx_y + BeamDir.z(), target_z = vtx_z + BeamDir.y();
    while (sqrt(target_x*target_x+target_y*target_y)<max_r && fabs(target_z)<max_z)
    {
        target_x += -BeamDir.x(); target_y += BeamDir.z(); target_z += BeamDir.y();
    }
    double evtx, evty;
    if (fabs(vtx_z)<barrelCut)
    {
        double th = atan2(vtx_y,vtx_x);

        evtx = -max_r*th;
        evty = vtx_z;
    }
    else if (vtx_z>barrelCut)
    {
        evtx = -vtx_y;
        evty = max_z+max_r-vtx_x;
    }
    else
    {
        evtx = -vtx_y;
        evty = -max_z-max_r+vtx_x;
    }
    TMarker m1(evtx,evty,29);
    m1.SetMarkerColor(kRed);
    m1.Draw();
    if (fabs(target_z)<barrelCut)
    {
        double th = atan2(target_y,target_x);

        evtx = -max_r*th;
        evty = target_z;
    }
    else if (target_z>barrelCut)
    {
        evtx = -target_y;
        evty = max_z+max_r-target_x;
    }
    else
    {
        evtx = -target_y;
        evty = -max_z-max_r+target_x;
    }
    TMarker m2(evtx,evty,29);
    m2.SetMarkerColor(kBlack);
    m2.Draw();
    c1->SaveAs(Form("/mnt/fig/%sdisplay.pdf",prefix.c_str()));

    hist_timetof->GetXaxis()->SetTitle("Digi Time (ns)");
    hist_timetof_true->GetXaxis()->SetTitle("Raw Time (ns)");

    hist_timetof->Draw("hist");
    c1->SaveAs(Form("/mnt/fig/%stimetof.pdf",prefix.c_str()));

    hist_timetof_true->Draw("hist");
    //c1->SetLogy();
    c1->SaveAs(Form("/mnt/fig/%stimetof_true.pdf",prefix.c_str()));

    hist_event_display->SetDirectory(0);
    hist_timetof->SetDirectory(0);
    hist_timetof_true->SetDirectory(0);

    f->Close();
    t->Reset();

    return std::vector<TH1*>{hist_event_display,hist_timetof,hist_timetof_true};
}

void EventDisplay_Compare(const char * fname1, const char * fname2, const char * tag)
{
    std::vector<TH1*> hists1 = EventDisplay(fname1);
    std::vector<TH1*> hists2 = EventDisplay(fname2);

    TCanvas* c1 = new TCanvas();

    hists2[0]->Divide(hists1[0]);
    hists2[0]->GetZaxis()->SetRangeUser(0.5,1.5);
    hists2[0]->SetTitle("Ratio");
    hists2[0]->Draw("colz");
    c1->SaveAs(Form("/mnt/fig/Compare_display_%s.pdf",tag));
    TH1D* hist_ratio = new TH1D("Ratio","Ratio",100,0.5,1.5);
    for (int i=1;i<=hists2[0]->GetNbinsX();i++)
        for (int j=1;j<=hists2[0]->GetNbinsY();j++)
    {
        double val = hists2[0]->GetBinContent(i,j);
        if (val>0) hist_ratio->Fill(val);
    }
    c1->SetGridx();
    c1->SetGridy();
    hist_ratio->Draw("hist");
    c1->SaveAs(Form("/mnt/fig/Compare_display_ratio_%s.pdf",tag));

    hists1[1]->Draw("hist");
    hists2[1]->SetLineColor(kRed);
    hists2[1]->Draw("hist same");
    c1->SaveAs(Form("/mnt/fig/Compare_timetof_%s.pdf",tag));

    hists2[1]->Divide(hists1[1]);
    hists2[1]->GetYaxis()->SetTitle("Ratio");
    hists2[1]->GetYaxis()->SetRangeUser(0,2);
    hists2[1]->Draw("hist");
    c1->SaveAs(Form("/mnt/fig/Compare_timetof_ratio_%s.pdf",tag));

    hists1[2]->Draw("hist");
    hists2[2]->SetLineColor(kRed);
    hists2[2]->Draw("hist same");
    c1->SaveAs(Form("/mnt/fig/Compare_timetof_true_%s.pdf",tag));

    hists2[2]->Divide(hists1[2]);
    hists2[2]->GetYaxis()->SetTitle("Ratio");
    hists2[2]->GetYaxis()->SetRangeUser(0,2);
    hists2[2]->Draw("hist");
    c1->SaveAs(Form("/mnt/fig/Compare_timetof_true_ratio_%s.pdf",tag));
}