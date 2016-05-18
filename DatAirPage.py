import wx
import wx.lib.colourdb
import csv
from decimal import *
import xlrd
from collections import namedtuple

class DatAir(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        size=wx.GetDisplaySize()
        self.maxsize=(size[0]*.9,size[1]*.8)
        #Set up the radio buttons
        self.rbChoices=['CNSREC','EEDATA','RMHCNSRP','ETMCDATA']
        self.RB  = wx.RadioBox(self,-1,"Choose File Type",(10,10),wx.DefaultSize,self.rbChoices,2,wx.RA_SPECIFY_COLS)
        btnSize = (100,25)
        btnChooseInFile = wx.Button(self, -1,"Choose DAT file", size=btnSize) 
        btnChooseOutFile=wx.Button(self, -1,"Choose CSV file", size=btnSize) 
        btnGo = wx.Button(self,-1,"Go",size=btnSize)
        self.Bind(wx.EVT_BUTTON,  self.ChooseInFile, btnChooseInFile)
        self.Bind(wx.EVT_BUTTON,  self.ChooseOutFile, btnChooseOutFile)       
        self.Bind(wx.EVT_BUTTON, self.DATFile, btnGo)
        self.labInFile = wx.StaticText(self,-1,"No .DAT input file chosen")
        self.labOutFile = wx.StaticText(self,-1,"No .CSV output file chosen")
        #Now lay the screen out
        h1=wx.BoxSizer(wx.HORIZONTAL)
        h1.Add((20,20),1)
        h1.Add(self.RB)
        h1.Add((20,20),1)
        gs = wx.GridSizer(rows=3, cols = 2,hgap=5,vgap=5)
        gs.Add(btnChooseInFile)
        gs.Add(self.labInFile)
        gs.Add(btnChooseOutFile)
        gs.Add(self.labOutFile)
        gs.Add(btnGo)
        h1.Add(gs,0, wx.ALIGN_LEFT|wx.ALL, 4)
        v1=wx.BoxSizer(wx.VERTICAL)
        v1.Add((20,20),0)
        v1.Add(h1,0,wx.ALIGN_TOP| wx.ALL, 4)
        self.SetSizerAndFit(v1)
        r2run = namedtuple('r2run','infileIn outfileIn')
        self.infNm, self.outfNm = '',''
        self.readyToRun = r2run(False,False) 
        self.errMsg=('Please enter an input file name./n','Please enter an output file name./n')

    def ChooseInFile(self,event):
        Findlg = wx.FileDialog(
            self, message="Open file...", defaultDir="", 
            defaultFile="", wildcard="*.*", style=wx.OPEN
            )
        if Findlg.ShowModal() == wx.ID_OK:
            self.infNm = Findlg.GetPath()              
            self.inf=open(self.infNm,'r')
            self.labInFile.SetLabel(self.infNm)
            self.readyToRun = self.readyToRun._replace(infileIn=True)
        Findlg.Destroy()

    def ChooseOutFile(self,event):
        Foutdlg = wx.FileDialog(
            self, message="Save file as...", defaultDir="", 
            defaultFile="", wildcard="*.*", style=wx.SAVE
            )
        if Foutdlg.ShowModal() == wx.ID_OK:
            self.outfNm = Foutdlg.GetPath()
            self.outf=open(self.outfNm,'wb')
            self.labOutFile.SetLabel(self.outfNm)
            self.readyToRun = self.readyToRun._replace(outfileIn=True)
        Foutdlg.Destroy()
 
    def DATFile(self,event):
        if self.readyToRun == (True,True):
            self.processDATFile()
        else:
            retCode = wx.MessageBox('/n'.join([msg for msg,flg in zip(self.errMsg,self.readyToRun) if flg]),caption='Message',style=wx.OK)
            
    def processDATFile(self):
        StRMH=[-1,3,34,46,56,65,74,83,126,131,134,142,145,
         153,165,177,189,199,209,219,229,239,249,259]
        EnRMH=[3,34,46,56,65,74,83,126,131,134,142,145,
                 153,165,177,189,199,209,219,229,239,249,259,263]
        
        StCNS=[-1,3,34,46,56,65,74,83,126,131,134,142,145,
                 153,165,177,189,199,209,219,229,239,249]
        EnCNS=[3,34,46,56,65,74,83,126,131,134,142,145,
                 153,165,177,189,199,209,219,229,239,249,259]
        
        StETMC=[-1,30,42,46,50,59,68,77,86,89,91,106,108,110,121,132,143,154,166,177,
                188,199,211,215,219,231,242,253,264,275,286]
        EnETMC=[30,42,46,50,59,68,77,86,89,91,106,108,110,121,132,143,154,166,177,
                188,199,211,215,219,231,242,253,264,275,286,327]
        
        StEE=[-1,30,42,46,55,64,73,82,92,94,109,111,113,124,135,146,157,169,180,
              191,202,214,218,230,241,252,263,274]
        EnEE=[30,42,46,55,64,73,82,92,94,109,111,113,124,135,146,157,169,180,
              191,202,214,218,230,241,252,263,274,285]
        Choice = self.rbChoices[self.RB.GetSelection()]
        HeaderRow = ['CNSREC','RMHCNSRP']
        Stt=StETMC
        End=EnETMC
        if Choice == 'CNSREC':
            Stt=StCNS
            End=EnCNS
        elif Choice == 'EEDATA':
            Stt=StEE
            End=EnEE
        elif Choice == 'RMHCNSRP':
            Stt=StRMH
            End=EnRMH
        writer=csv.writer(self.outf, dialect='excel')
        FirstLine=True
        linesout=0
        for line in self.inf:
            if FirstLine and Choice in HeaderRow:
                FirstLine=False
            else:
                sss=[line[i+1:j].strip() for i,j in zip(Stt, End) ]
                writer.writerow(sss)
                linesout+=1
        msgDialog=wx.MessageDialog(None, str(linesout)+' rows written. Finished.','Message', wx.OK)
        retcode=msgDialog.ShowModal()
        msgDialog.Destroy()
        self.outf.close()
        self.inf.close()
