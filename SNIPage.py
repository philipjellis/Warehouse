import wx
#import wx.html
import pyodbc
from collections import OrderedDict
from utilities import sniCn, getColHeads, HTMLWindow
from SNIsocialReview import processSSN, dataSSN
from SNILoader import processFile

class SNI(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        size=wx.GetDisplaySize()
        self.maxsize=(size[0]*.9,size[1]*.8)
        #Set up the buttons
        btnSize = (130,25)
        cbSize = (150,20)
        cn = sniCn()
        cursor = cn.cursor()
        self.fileName = None
        colNames, colTypes = getColHeads('snimonthlypay',cursor, lower=True)
        self.btnChooseInFile = wx.Button(self, -1,"Choose file to load", size=btnSize) 
        self.Bind(wx.EVT_BUTTON,  self.onClickChooseInFile, self.btnChooseInFile)
        self.btnLoadFile = wx.Button(self, -1,"Load file", size=btnSize) 
        self.Bind(wx.EVT_BUTTON,  self.onClickLoadDBFile, self.btnLoadFile)
        self.btnShowChanges = wx.Button(self, -1,"ShowChanges", size=btnSize) 
        self.Bind(wx.EVT_BUTTON,  self.onClickShowChanges, self.btnShowChanges)
        self.btnShowData = wx.Button(self, -1,"Show Data", size=btnSize) 
        self.Bind(wx.EVT_BUTTON,  self.onClickShowData, self.btnShowData)
        socialtxt = wx.StaticText(self, -1, "Enter social", size=btnSize)
        self.socialEntered = wx.TextCtrl(self, -1, "", size = btnSize)
        self.chkXLFormat = wx.CheckBox(self, -1, "Save file in Excel format", size = btnSize)
        self.chkDBFormat = wx.CheckBox(self, -1, "Save file to Database", size = btnSize)
        self.chkXLFormat.SetValue(True)
        self.chkDBFormat.SetValue(True)
        self.txtLoadFile = wx.StaticText(self, -1, "")
        ffBox = wx.StaticBox (self, -1, 'Load monthly file')
        dbBox = wx.StaticBox (self, -1, 'Inquiry about social')
        colBoxload = wx.StaticBox (self, -1, 'Select columns to load')        
        colBoxinq = wx.StaticBox (self, -1, 'Select columns to compare')                
        ffBoxSizer = wx.StaticBoxSizer (ffBox, wx.VERTICAL)
        inqBoxSizer = wx.StaticBoxSizer (dbBox, wx.VERTICAL)
        colBoxloadsizer = wx.StaticBoxSizer (colBoxload, wx.VERTICAL)
        colBoxinqsizer = wx.StaticBoxSizer (colBoxinq, wx.VERTICAL)        
        self.loadChecks = OrderedDict(zip(colNames,[wx.CheckBox(self, -1, name[1:], size = cbSize) for name in colNames]))
        self.inqChecks =  OrderedDict(zip(colNames,[wx.CheckBox(self, -1, name[1:], size = cbSize) for name in colNames]))
        for checks in [self.loadChecks, self.inqChecks]:
            for check in checks.values():
                check.SetValue(True) # start by setting them all on.  Then edit a few below.
        for check in [self.loadChecks['mbegindate'], self.loadChecks['menddate'], self.inqChecks['mbegindate'], 
                      self.inqChecks['menddate'], self.loadChecks['mssn'],self.inqChecks['mssn']]:
            check.Enable(False)
        for check in [self.inqChecks['mearns'], self.inqChecks['mbonusearns'],self.inqChecks['mhours'], 
                      self.inqChecks['mbegindate'], self.inqChecks['menddate'], self.inqChecks['mssn']]:
            check.SetValue(False)
        #lay out the screen
        # load panels first
        h1 = wx.BoxSizer(wx.HORIZONTAL)
        for thing in [self.btnChooseInFile, self.chkXLFormat, self.chkDBFormat,  self.btnLoadFile]:
            h1.Add(thing)
            h1.Add((5,5))
        for chk in self.loadChecks.values():
            colBoxloadsizer.Add(chk)
        for thing in [h1, self.txtLoadFile, colBoxloadsizer]:
            ffBoxSizer.Add(thing, 0, wx.ALL, 2)
        # query panel now
        h2=wx.BoxSizer(wx.HORIZONTAL)
        for thing in [socialtxt, self.socialEntered, self.btnShowChanges, self.btnShowData]:
            h2.Add(thing)
            h2.Add((5,5))
        for chk in self.inqChecks.values():
            colBoxinqsizer.Add(chk)
        for thing in [h2,colBoxinqsizer]:
            inqBoxSizer.Add(thing, 0, wx.ALL, 2)
        h3 = wx.BoxSizer(wx.HORIZONTAL)
        for thing in [ffBoxSizer, inqBoxSizer]:
            #h3.Add((20,20),1)
            h3.Add((5,5))
            h3.Add(thing)
        v1 = wx.BoxSizer(wx.VERTICAL)
        v1.Add((10,10))
        v1.Add(h3)
        self.SetSizerAndFit(v1)

 
    def onClickChooseInFile(self,event):
        Findlg = wx.FileDialog(
            self, message="Open file...", defaultDir="", 
            defaultFile="", wildcard="*.*", style=wx.OPEN
        )
        if Findlg.ShowModal() == wx.ID_OK:
            self.fileName = Findlg.GetPath()
            self.txtLoadFile.SetLabel(self.fileName)
        Findlg.Destroy()

    def onClickLoadDBFile(self, event):
        writeXL = self.chkXLFormat.IsChecked()
        writeDB = self.chkDBFormat.IsChecked()        
        if not self.fileName:
            retcode = wx.MessageBox("Please enter a filename.", "Information", wx.OK)
        elif not writeDB and not writeXL:
            retcode = wx.MessageBox("You have not checked either Excel or Database.\nNothing processed.", "Information", wx.OK)
        else:
            msg = processFile(self.fileName, writeXL, writeDB)
            retcode = wx.MessageBox(msg, "Result message", wx.OK)

    def onClickShowChanges(self, event):
        # find which columns have been clicked
        colsNeeded = [k for k,v in self.inqChecks.iteritems() if v.IsChecked()]
        social = self.socialEntered.GetValue()
        # call the processor which generates a bunch of messages 
        # all messages are going to be put into an HTML window.
        htString = processSSN(social, colsNeeded)
        frm = HTMLWindow(None, 'Changes for social '+social, htString)
        frm.Show()
        
    
    def onClickShowData (self, event):
        # similar to function above 
        social = self.socialEntered.GetValue()
        htString = dataSSN(social)
        frm = HTMLWindow(None, 'Monthly data  held for social '+social, htString)
        frm.Show()
