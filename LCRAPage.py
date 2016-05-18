import wx
import wx.lib.colourdb
import  wx.lib.scrolledpanel as scrolled
import csv
from decimal import *
from datetime import datetime, date
from utilities import *
from collections import namedtuple
import copy
import os
from ProValLoad import *
import BU_Create
from LCRAFileProcess import extract_person, hi60calc, latestpay, load_month_warehouse, load_month_website

class MsgBox(wx.Dialog):
    def __init__(self, parent, title, message):
        wx.Dialog.__init__(self, parent, title=title)
        text = wx.TextCtrl(self, size = (1200,600), style=wx.TE_READONLY|wx.BORDER_NONE|wx.TE_MULTILINE)
        text.SetValue(message)
        text.SetBackgroundColour(wx.SystemSettings.GetColour(4))
        self.ShowModal()
        self.Destroy()
        
class LCRA(wx.Panel):
    cnxn = accP2()
    cursor = cnxn.cursor()
    Instructions = """To use this program you will need the monthly payroll file from LCRA.\n
The records will be added to a database table called LCRAMonthlyPay\n in the database ClientMonthly.\n
There are three steps to the process:\n
    a) Select the file you want to load.
    b) An optional check to see if this data is new.
    c) The load itself.\n
Note: if  you load data that has already been loaded, you will just
overwrite the existing data.  No harm will be done, which is why 
step b is optional."""
    def __init__(self, parent, home): 
        wx.Panel.__init__(self, parent)
        # some flags to check preliminary data entered
        self.home = home # this is the home screen - the top level screen we are going to put the status message into 
        self.fnEntered = False
        size=wx.GetDisplaySize()
        self.maxsize=(size[0]*.9,size[1]*.8)
        # now the buttons and labels for the monthly load
        #
        self.labfn = wx.StaticText(self, -1, "                    ",(85,18)) # label for the file selected
        lab_wh_latest = wx.StaticText(self, -1, "Latest Warehouse record: "+ str(latestpay('lcramonthlypay')))
        lab_web_latest = wx.StaticText(self, -1, "Latest Website record: "+ str(latestpay('tbmonthly')))        
        self.btnInstruct = wx.Button(self,-1,"Instructions")
        self.btnInFile = wx.Button(self, -1,"Step 1 Select input file") 
        self.btnCheck = wx.Button(self, -1,"Step 2 Check the data")        
        self.btnSave = wx.Button(self, -1,"Step 3 Save to database")
        self.btnWebsite = wx.Button(self, -1,"Step 4 Save to website") 

        # switch off the check and save buttons for now
        self.btnCheck.Disable()
        self.btnSave.Disable()
        self.btnWebsite.Disable()
        #now the buttons and labels for the Hi60 and file extract
        self.btnOutFile = wx.Button(self, -1,"Select output file")
        self.btnRetrieve = wx.Button(self, -1,"Retrieve")
        self.btnHi60 = wx.Button(self, -1,"Hi60")
        labssn = wx.StaticText(self, -1, "SSN: ")
        self.fldssn = wx.TextCtrl(self, -1, value="", size=(80,20))
        self.btnRetrieve.Disable()
        # now bind the buttons to their functions
        self.Bind(wx.EVT_BUTTON,  self.Instruct, self.btnInstruct)
        self.Bind(wx.EVT_BUTTON,  self.selInFile, self.btnInFile)
        self.Bind(wx.EVT_BUTTON,  self.step2Check, self.btnCheck)
        self.Bind(wx.EVT_BUTTON,  self.step3Save, self.btnSave)
        self.Bind(wx.EVT_BUTTON,  self.step4website, self.btnWebsite)        
        self.Bind(wx.EVT_BUTTON,  self.hi60, self.btnHi60)
        self.Bind(wx.EVT_BUTTON,  self.retrieve, self.btnRetrieve)
        self.Bind(wx.EVT_BUTTON,  self.selOutFile, self.btnOutFile)        
        #Now lay the screen out
        #Load box
        LoadBox = wx.StaticBox(self,-1,'Warehouse and website update')
        LoadBoxSizer = wx.StaticBoxSizer(LoadBox, wx.VERTICAL)
        for thing in [self.btnInstruct, lab_wh_latest, lab_web_latest, self.btnInFile,self.btnCheck, self.btnSave, self.btnWebsite]:
            LoadBoxSizer.Add(thing,0,wx.ALL,15)
        # now the social label and field
        hboxsocial=wx.BoxSizer(wx.HORIZONTAL)
        hboxsocial.Add((20,20),1)
        hboxsocial.Add(labssn,0, wx.ALIGN_LEFT|wx.ALL, 4)
        hboxsocial.Add(self.fldssn,0, wx.ALIGN_LEFT|wx.ALL, 4)
        # now the box for the Hi60 and extract
        Hi60Box = wx.StaticBox(self,-1,'Extract and Hi60')
        Hi60BoxSizer=wx.StaticBoxSizer(Hi60Box, wx.VERTICAL)
        for thing in [hboxsocial, self.btnOutFile, self.btnRetrieve, self.btnHi60]:
            Hi60BoxSizer.Add(thing,0,wx.ALIGN_RIGHT|wx.ALL,15)
        #Now the file name box
        fnbox = wx.StaticBox(self,-1,'Filename', size=(400,100))
        fnBoxSizer=wx.StaticBoxSizer(fnbox, wx.VERTICAL)
        fnBoxSizer.Add(self.labfn,0,wx.ALIGN_RIGHT|wx.ALL,15)
        h1=wx.BoxSizer(wx.HORIZONTAL)        
        h1.Add(LoadBoxSizer,0, wx.ALIGN_LEFT|wx.ALL, 20)        
        h1.Add(Hi60BoxSizer,0, wx.ALIGN_LEFT|wx.ALL, 20)
        h1.Add(fnBoxSizer,0, wx.ALIGN_LEFT|wx.ALL, 20)        
        self.SetSizer(h1)
        self.Layout()
        size=wx.GetDisplaySize()
        self.maxsize=(size[0]*.9,size[1]*.8)
        
    def Instruct(self, event):
        msgDialog=wx.MessageDialog(None, self.Instructions, "Message",wx.OK)
        retCode=msgDialog.ShowModal()
        msgDialog.Destroy()

    def ErrBar(self, message):
        msgDialog=wx.MessageDialog(None, message,'Messages', wx.OK)
        retCode=msgDialog.ShowModal()
        msgDialog.Destroy()
        return
    
    def displayFileName(self):
        label = '            ' + 'Employee Records: ' + self.fileName
        self.labfn.SetLabel(label)
        return

    def selInFile (self, event):
        dlg = wx.FileDialog(
            self, message="Import Excel filename.  NB only .txt files can be imported ...", defaultDir="", 
            defaultFile="mydata.xls", wildcard="*.txt", style=wx.SAVE
        )
        if dlg.ShowModal() == wx.ID_OK:
            self.fileName = dlg.GetPath()
            self.fnEntered = True
            self.displayFileName()
            self.Layout()
            self.btnCheck.Enable()
            self.btnSave.Enable()            
        dlg.Destroy()

    def selOutFile (self, event):
        dlg = wx.FileDialog(
            self, message="Save file as ...", defaultDir="", 
            defaultFile="temp.xls", wildcard="*.*", style=wx.SAVE
        )
        if dlg.ShowModal() == wx.ID_OK:
            self.fileName = dlg.GetPath()
            self.fnEntered = True
            self.displayFileName()
            self.btnRetrieve.Enable()
        dlg.Destroy()

    def getsocial(self):
        self.social=self.fldssn.GetValue()

    def hi60 (self, event):
        self.getsocial()
        if not self.social:
            self.ErrBar('Please enter a social')
        else:
            self.ErrBar(hi60calc(self.social))
        
    def retrieve (self,event):
        self.getsocial()
        msg = extract_person(self.social,self.fileName)
        self.ErrBar(msg)
            
    def step2Check (self, event):
        msg = load_month_warehouse(self.fileName,check = True)
        self.ErrBar(msg)
        self.btnWebsite.Enable()
            
    def step3Save (self, event):
        msg = load_month_warehouse(self.fileName, check = False)
        self.ErrBar(msg)

    def step4website (self, event):
        msg = load_month_website(self.fileName, self.home) 
        self.ErrBar(msg)
         