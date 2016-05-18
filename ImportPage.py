import wx
import wx.lib.colourdb
import  wx.lib.scrolledpanel as scrolled
import csv
from decimal import *
import xlrd
from datetime import datetime, date
from utilities import *
from collections import namedtuple
import copy
import os
from ProValLoad import *
import BU_Create

class MsgBox(wx.Dialog):
    def __init__(self, parent, title, message):
        wx.Dialog.__init__(self, parent, title=title)
        text = wx.TextCtrl(self, size = (1200,600), style=wx.TE_READONLY|wx.BORDER_NONE|wx.TE_MULTILINE)
        text.SetValue(message)
        text.SetBackgroundColour(wx.SystemSettings.GetColour(4))
        self.ShowModal()
        self.Destroy()
        
class Importer(wx.Panel):
    cnxn = accP2()
    cursor = cnxn.cursor()
    
    Instructions = """To use this program you will need an Excel file containing \
the records you wish to import.  \n 
Only the first workbook (tab) will be processed. The column names must constitute the first\
 row in the spreadsheet.  The columns must contain valid data \
for every row in the table you are importing.  The Excel file must have exactly the\
 same column names as the export file for that plan.  Columns with no updated data may\
 be deleted, but  please do not delete the columns ending in 'id'.\
  Run the extract program to see an example of the column names.\
  For more details please see the documentation website at\
  L:/Warehouse/Documentation/build/html/index.html"""
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        # some flags to check preliminary data entered
        self.fnEntered = False
        self.EREntered = False
        self.planEntered = False
        self.loadDateEntered = False
        self.EffDateEntered = False
        self.parent = parent
        
        size=wx.GetDisplaySize()
        self.maxsize=(size[0]*.9,size[1]*.8)
        #
        #These are some variables and whatnot
        #
        self.ER =  'ANS' #just something to start with
        self.planID = 0
        self.loadDate = None
        self.effDate = None
        self.ERChoices = self.getERs()
        self.planChoices = self.getplanChoices(self.ER) #  Returns a list
        self.startYears = None #returns a list of years starting with today's
        #
        # now the buttons and labels
        #
        self.btnInstruct = wx.Button(self,-1,"Instructions")
        self.btnInFile = wx.Button(self, -1,"Select input file") 
        labER = wx.StaticText(self,-1,"Employer")
        self.fldER = wx.Choice(self,-1,(85,18),choices = [str(i) for i in self.ERChoices])
        labplan = wx.StaticText(self, -1, "Plan")
        self.fldplan = wx.Choice(self,-1,(85,18),choices=[str(i) for i in self.planChoices])

        self.btnLoad = wx.Button(self, -1,"Step 1\nLoad the files")
        self.btnCheck = wx.Button(self, -1,"Step 2\nCheck the data")        
        self.btnSave = wx.Button(self, -1,"Step 3\nSave to database")
        self.labFn = wx.StaticText(self,-1,"Filename:")
        self.btnBackup = wx.Button(self, -1,"Back up the production\ndatabase")        
        self.btnRestore = wx.Button(self, -1,"Restore the test database\nfrom production backup")    
        # switch off the check and save buttons for now
        self.btnCheck.Disable()
        self.btnSave.Disable()
        #self.btnBackup.Disable()
        #elf.btnRestore.Disable()
        # now bind the buttons to their functions
        self.Bind(wx.EVT_BUTTON,  self.Instruct, self.btnInstruct)
        self.Bind(wx.EVT_BUTTON,  self.selInFile, self.btnInFile)
        self.Bind(wx.EVT_BUTTON,  self.step1Load, self.btnLoad)
        self.Bind(wx.EVT_BUTTON,  self.step2Check, self.btnCheck)
        self.Bind(wx.EVT_BUTTON,  self.step3Save, self.btnSave)
        self.Bind(wx.EVT_CHOICE,self.ERChoiceHr,self.fldER)
        self.Bind(wx.EVT_CHOICE, self.planChoiceHr, self.fldplan)  
        self.Bind(wx.EVT_BUTTON, self.wh_backup, self.btnBackup)  
        self.Bind(wx.EVT_BUTTON, self.wh_restore, self.btnRestore)            

        #Now lay the screen out
        InstructionBox=wx.StaticBox(self,-1,'Read this first')
        InstructionBoxSizer=wx.StaticBoxSizer(InstructionBox, wx.HORIZONTAL)
        InstructionBoxSizer.Add(self.btnInstruct,0,wx.ALL,2)
        self.ImportMesage = 'Set up the import in this box'
        ImportBox=wx.StaticBox(self,-1,self.ImportMesage)
        ImportBoxSizer=wx.StaticBoxSizer(ImportBox, wx.HORIZONTAL)
        for thing in [self.btnInFile,labER,self.fldER,labplan,self.fldplan]:
            ImportBoxSizer.Add(thing,0,wx.ALL,5)
        self.BUMesage = 'Backup and Restore'
        BUBox=wx.StaticBox(self,-1,self.BUMesage)
        BUBoxSizer=wx.StaticBoxSizer(BUBox, wx.HORIZONTAL)
        for thing in [self.btnBackup,self.btnRestore]:
            BUBoxSizer.Add(thing,0,wx.ALL,5)
        GoBox=wx.StaticBox(self,-1,'Import')
        GoBoxSizer=wx.StaticBoxSizer(GoBox, wx.HORIZONTAL)
        for butt in [self.btnLoad, self.btnCheck, self.btnSave]:
            GoBoxSizer.Add(butt,0,wx.ALL,5)
        h1=wx.BoxSizer(wx.HORIZONTAL)        
        h1.Add(InstructionBoxSizer,0, wx.ALIGN_LEFT|wx.ALL, 14)        
        h1.Add(ImportBoxSizer,0, wx.ALIGN_LEFT|wx.ALL, 14)
        h1.Add(BUBoxSizer,0, wx.ALIGN_LEFT|wx.ALL, 14)
        h2=wx.BoxSizer(wx.HORIZONTAL) 
        h2.Add(GoBoxSizer,0, wx.ALIGN_LEFT|wx.ALL, 14)
        h2.Add(self.labFn,0, wx.ALIGN_LEFT|wx.ALL, 14)        
        self.v1=wx.BoxSizer(wx.VERTICAL)
        for box in [h1, h2]:
            self.v1.Add(box,0,wx.ALIGN_TOP| wx.ALL, 4)
#        self.v1.Add(self.labFn,0,wx.ALIGN_TOP | wx.ALL, 4)
        self.SetSizer(self.v1)
        self.Layout()
        size=wx.GetDisplaySize()
        self.maxsize=(size[0]*.9,size[1]*.8)
        
    def Instruct(self, event):
        #print 'instructions'
        msgDialog=wx.MessageDialog(None, self.Instructions, "Message",wx.OK)
        retCode=msgDialog.ShowModal()
        msgDialog.Destroy()

    def ErrBar(self, message):
        msgDialog=wx.MessageDialog(None, message,'Messages', wx.OK)
        retCode=msgDialog.ShowModal()
        msgDialog.Destroy()
        return
    
    def getERs(self): # just gets all the Employer TLAs and Ids
        sql = 'select rID, rTLA from tbEmployer where rPersonFlag = 1 order by rTLA asc'
        self.cursor.execute(sql)
        data = self.cursor.fetchall()
        self.ERs = [i[0] for i in data]
        self.TLAs = [i[1] for i in data]
        return self.TLAs
    
    def getplanChoices(self,ER): # gets all the plans for an Employer 
        rix = self.TLAs.index(ER) # lookup the row number of the TLA
        rID = self.ERs[rix] # the rID is the same number in the self.ERs list
        sql = 'select nid, nshortplanname  from tbplan where nrid = ?'
        self.cursor.execute(sql,(rID,))
        data = self.cursor.fetchall()
        self.sIDs = [i[0] for i in data]
        self.plans = [i[1] for i in data]
        try: # this will fail first time through,  as fldplan has not been created.  Just let it, it doesn't matter
            self.fldplan.SetItems(self.plans)
        except:
            pass
        return self.plans

    def selInFile (self, event):
        dlg = wx.FileDialog(
            self, message="Import Excel filename.  NB only .xls files can be imported ...", defaultDir="", 
            defaultFile="mydata.xls", wildcard="*.xls", style=wx.SAVE
        )
        if dlg.ShowModal() == wx.ID_OK:
            self.fileName = dlg.GetPath()
            self.fnEntered = True
            self.ImportMesage = 'Filename: '+self.fileName
            #label = '            ' + 'Employee Records: ' + self.fileName
            self.labFn.SetLabel('Filename: '+self.fileName)              
            self.Layout()
        dlg.Destroy()

    def step1Load (self, event):
        msg=''
        if not self.fnEntered: msg += "Please enter a file name for the input spreadsheet.  \n"
        if not self.EREntered: msg += "Please select an employer.  \n"
        if not self.planEntered: msg += "Please select a pension plan.  \n"
        #if not self.loadDateEntered: msg += "Please select a load date.  \n"
        #if not self.EffDateEntered: msg += "Please select an effective date.  \n"        
        if msg: 
            msgDialog=wx.MessageDialog(None, msg,'Message', wx.OK)
            retCode=msgDialog.ShowModal()
            msgDialog.Destroy()
        else:
            self.PVData = ProValLoad(self,self.fileName, self.planID,self.ERNum)  
            MsgBox(None, 'Messages from Load Process', self.PVData.errorMessages)
            if self.PVData.goodToGo:
                self.btnLoad.Disable()
                self.btnCheck.Enable()
            self.fnEntered = False
            
    def step2Check (self, event):
        self.PVData.checkData()
        MsgBox(None, 'Messages from Check Process', self.PVData.errorMessages)
        if self.PVData.goodToGo:
            self.btnCheck.Disable()
            self.btnSave.Enable()        
            
    def step3Save (self, event):
        self.PVData.saveData()
        MsgBox(None, 'Messages from Save Process', self.PVData.errorMessages)
        if self.PVData.goodToGo:
            self.btnSave.Disable()
            self.labFn.SetLabel('')
            self.btnLoad.Enable()
            #self.__init__(None)

    def wh_backup (self, event):
        #print 'starting backup'
        result = BU_Create.do_backup()
        if result:
            MsgBox(None, 'Backup Status','Backup completed')
        else:
            MsgBox(None, 'Backup Status','Backup encountered an error.\n Please contact the technology team')

    def wh_restore (self, event):
        #print 'starting restore'
        result = BU_Create.do_restore()
        if result:
            MsgBox(None, 'Restore Status','Restore completed')
        else:
            MsgBox(None, 'Restore Status','Restore encountered an error.\n Please contact the technology team')

    def ERChoiceHr (self, event): # in the following functions, Hr stands for Handler
        ERix = self.fldER.GetSelection()
        self.ER = self.ERChoices[ERix] # this is the ER code of the ER chosen
        self.ERNum = self.ERs[ERix]
        self.planChoices=self.getplanChoices(self.ER) # this sets the choices field for the next drop down box
        self.EREntered = True
        
    def planChoiceHr(self,event):
        Schix = self.fldplan.GetSelection()
        self.planID = self.sIDs[Schix]
        self.planEntered = True
        
    def AdjustWXDate (self, WXdate):
        # This takes a date from WX and formats it as a python date (ready for
        # the database)
        # It puts the month forward by 1 as WX has January = 0!
        upd = False # update flag to force date to reshow on screen
        if WXdate.IsValid():
            Yr = WXdate.GetYear()
            if Yr < 10:
                Yr += 2000
            elif Yr < 30:
                Yr += 2000
                upd = True
            elif Yr < 100:
                Yr += 1900
            upd = True
            Mo = WXdate.GetMonth() + 1
            Dy = WXdate.GetDay() 
            return date(Yr,Mo,Dy), upd
        else:
            return None

    def FormatWXDate (self, normDate):
        try:
            return wx.DateTimeFromDMY(normDate.day, normDate.month-1, normDate.year)
        except:
            return wx.DateTime()