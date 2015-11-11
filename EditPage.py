import wx
import datetime
from collections import namedtuple
from utilities import *
from editscreen import *

Aboutxt = """Select the table to edit and enter the key data."""
# comment out this bit until we put dates back PJE  Select the start and \
#stop dates to limit the number of records returned."""

class Editor(wx.Panel):
    Instructions = """To use this program you need to enter the key.  \n 
For the Person, Employee and Member tables, the key is the social.\n
For tables hanging from these tables, the key is the id field of the parent.\n
For example the Annuals table hangs from the Member table (see Data Model).  \
And so to see the Annual records for a member, the value to put in the key is the Member id.  \
You can find the Member id by entering the social and seeing the member details first.\n
The Member id is also on the extract spreadsheet.\n\n"""
    clicks=0
    h2 = wx.BoxSizer(wx.HORIZONTAL) # this for the subpanels
    def __init__(self, parent):
        size=wx.GetDisplaySize()
        self.maxsize=(size[0]*.9,size[1]*.8)
        wx.Panel.__init__(self, parent)
        #Set up the text labels
        labkD = wx.StaticText(self, -1, "Key value : ")
        labAbout = wx.StaticText(self, -1, Aboutxt)
        labAbout.SetForegroundColour('BLUE')
        metaData  = specialFields('All')
        del metaData[IBControlTable] # remove ibctrl as this edited in prev page
        del metaData [bcSnapShotTable]
        self.metaTables = [i.table[0] for i in metaData.values()]
        self.metaTableNames = [i.tableName[0] for i in metaData.values()] 

        self.fldkD = wx.TextCtrl(self, -1, value="", size=(80,20))
        self.fldTable = wx.RadioBox(self,-1, "Choose Table to Edit",
            wx.DefaultPosition, wx.DefaultSize, self.metaTableNames,1)
        btnGo = wx.Button(self, -1,"Get the data") 
        self.Bind(wx.EVT_BUTTON,  self.GetData, btnGo)
        btnHelp = wx.Button(self, -1,"Help") 
        self.Bind(wx.EVT_BUTTON,  self.HelpMe, btnHelp)
        self.bigPanel=wx.ScrolledWindow(self, -1, size = (self.maxsize), 
            style=wx.RAISED_BORDER)
        #Now lay the screen out
        h1=wx.BoxSizer(wx.HORIZONTAL)
        h1.Add((20,20),1)
        h1.Add(self.fldTable,0, wx.ALIGN_LEFT|wx.ALL, 4)
        h1.Add(labkD,0, wx.ALIGN_LEFT|wx.ALL, 4)
        h1.Add(self.fldkD,0, wx.ALIGN_LEFT|wx.ALL, 4)
        h1.Add((20,10),1)
        h3=wx.BoxSizer(wx.HORIZONTAL)
        h3.Add((30,20),1)
        h3.Add(labAbout,0, wx.ALIGN_TOP|wx.ALL, 10)
        h3.Add(btnGo, 0, wx.ALIGN_LEFT | wx.ALL, 4)
        h3.Add(btnHelp, 0, wx.ALIGN_LEFT | wx.ALL, 4)        
        self.v1=wx.BoxSizer(wx.VERTICAL)
        self.v1.Add(h3)
        self.v1.Add(h1)
        self.v1.Add(self.bigPanel)
        self.SetSizerAndFit(self.v1)

    def GetData(self, event):
        msg=''
        # 1 get table name
        tableix=self.fldTable.GetSelection()
        table = self.metaTables[tableix]
        keyData=self.fldkD.GetValue()
        try:
            newEditScreen.Destroy()
        except:
            pass
        newEditScreen = EditRecord(self,-1,table,True,keyData)
        newEditScreen.ShowModal()
        newEditScreen.Destroy()

    def HelpMe(self, event):
        wx.MessageBox(self.Instructions,'Help',wx.OK)
