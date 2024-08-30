void RemoveInvalidFile(const char * fname, int nEv)
{
    TFile* f = new TFile(fname);
    bool needRm = false;
    if ((!f) || f->IsZombie() || f->TestBit(TFile::kRecovered) || f->GetNkeys()==0) 
    { 
        std::cerr <<"There is a problem with the file: "<<f->GetName() <<std::endl;
        needRm = true;
    }
    else
    {
        TTree* t = (TTree*)f->Get("wcsimT");
        if (!t || t->GetEntries()<nEv)
        {
            std::cerr <<"There is a problem with the TTree wcsimT" <<std::endl;
            needRm = true;
        }
    }
    f->Close();
    if (needRm)
    {
        gSystem->Exec(Form("rm -f %s",fname)); 
    }
}