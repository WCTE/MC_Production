R__LOAD_LIBRARY(/opt/WCSim/build/install/lib/libWCSimRoot.so)

void VertexDistribution(const char * fname)
{
    gStyle->SetOptStat(0);

    TChain *t = new TChain("wcsimT");
    t->Add(fname);
    std::string single_file_name = t->GetFile()->GetName();
    // Get the first file for geometry
    TFile *f = TFile::Open(single_file_name.c_str());
    if (!f->IsOpen()){
        std::cout << "Error, could not open input file: " << single_file_name << std::endl;
        return -1;
    }
    if (!f->IsOpen()) return;

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
    if (prefix.find_last_of(".root")!=std::string::npos) 
    {   
        prefix = prefix.substr(0,prefix.find_last_of(".root")-4);
    }
    if (prefix.find_last_of("_")!=prefix.length()-1) prefix += ("_");
    std::cout<<"prefix = "<<prefix<<std::endl;

    WCSimRootEvent* wcsimrootsuperevent = new WCSimRootEvent();
    t->SetBranchAddress("wcsimrootevent",&wcsimrootsuperevent);

    WCSimRootTrigger* wcsimrootevent;

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

        // y-axis is vertical
        if (max_z<fabs(pos[1])) max_z=fabs(pos[1]);
        if (max_r<sqrt(pos[0]*pos[0]+pos[2]*pos[2]))
            if (fabs(pmt.GetOrientation(1))>0.5) max_r = sqrt(pos[0]*pos[0]+pos[2]*pos[2]);
    }

    TH3D* hist_vertices = new TH3D("Vertices","Vertices",100,-max_r,max_r,100,-max_r,max_r,100,-max_z,max_z);
    TH2D* hist_vertices_xy = new TH2D("VerticesXY","VerticesXY",100,-max_r*1.1,max_r*1.1,100,-max_r*1.1,max_r*1.1);
    TH2D* hist_vertices_yz = new TH2D("VerticesYZ","VerticesYZ",100,-max_r*1.1,max_r*1.1,100,-max_z*1.1,max_z*1.1);
    TH2D* hist_vertices_zx = new TH2D("VerticesZX","VerticesZX",100,-max_z*1.1,max_z*1.1,100,-max_r*1.1,max_r*1.1);
    for (long int nev=0;nev<t->GetEntries();nev++)
    {
        if (nev%(t->GetEntries()/100)==0) std::cout<<"Running "<<nev<<"-th event of total "<<t->GetEntries()<<" events"<<std::endl;

        delete wcsimrootsuperevent;
        wcsimrootsuperevent = 0;  // EXTREMELY IMPORTANT

        t->GetEntry(nev);
        wcsimrootevent = wcsimrootsuperevent->GetTrigger(0);

        hist_vertices->Fill(-wcsimrootevent->GetVtx(0),wcsimrootevent->GetVtx(2),wcsimrootevent->GetVtx(1));
        hist_vertices_xy->Fill(-wcsimrootevent->GetVtx(0),wcsimrootevent->GetVtx(2));
        hist_vertices_yz->Fill(wcsimrootevent->GetVtx(2),wcsimrootevent->GetVtx(1));
        hist_vertices_zx->Fill(wcsimrootevent->GetVtx(1),-wcsimrootevent->GetVtx(0));
    }

    TCanvas* c1 = new TCanvas();

    hist_vertices->Draw("box");
    c1->SaveAs(Form("/mnt/fig/%svertices.pdf",prefix.c_str()));

    hist_vertices_xy->Draw("colz");
    c1->SaveAs(Form("/mnt/fig/%sverticesXY.pdf",prefix.c_str()));

    hist_vertices_yz->Draw("colz");
    c1->SaveAs(Form("/mnt/fig/%sverticesYZ.pdf",prefix.c_str()));

    hist_vertices_zx->Draw("colz");
    c1->SaveAs(Form("/mnt/fig/%sverticesZX.pdf",prefix.c_str()));

    f->Close();
    t->Reset();
}