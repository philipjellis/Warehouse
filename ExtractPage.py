import wx
import wx.lib.colourdb
import csv
from decimal import *
import xlrd
from utilities import *
from xlwt import *
import datetime
from getFlatRecs import *



class Extractor(wx.Panel):
    
    cnxn = accP2()
    cursor = cnxn.cursor()
    
    def __init__(self, parent):
        # some flags to check preliminary data entered
        self.fnEntered = False
        self.EREntered = False
        self.SchemeEntered = False
        self.YearEntered = False
        wx.Panel.__init__(self, parent)
        size=wx.GetDisplaySize()
        self.maxsize=(size[0]*.9,size[1]*.8)
        #
        # These are the parameters themselves
        # The whole point of this screen is to put valid values in here and then call the extract program with them
        #
        self.ER =  'ANS' #just something to start with
        self.SchemeID = 0
        self.startYear = 2010
        self.numYears = 10 #only other value is 50 (= all years)
        #
        # These are the labels to put on the start screen
        #
        labER = wx.StaticText(self,-1,"Employer")
        labScheme = wx.StaticText(self, -1, "Plan: ")
        labYear = wx.StaticText(self,-1,"Snapshot year")
        labNumYears = wx.StaticText(self, -1, "Number of years pay to retrieve")
        self.labOutfn = wx.StaticText(self, -1, "                    ",(85,18)) # label for the file selected
        #
        #These are the variables we are populating on the start screen
        #
        self.ERChoices = self.getERs()
        self.schemeChoices=self.getSchemeChoices(self.ER) #  Returns a list
        self.startYears = self.getYears() #returns a list of years starting with today's
        #
        #These are the fields we are using to retrive the users parameters for the extract
        #
        self.fldER = wx.Choice(self,-1,(85,18),choices = [str(i) for i in self.ERChoices])
        self.fldScheme = wx.Choice(self,-1,(85,18),choices=[str(i) for i in self.schemeChoices])
        self.fldYear = wx.Choice(self,-1,(85,18), choices=[str(i) for i in self.startYears])
        self.fldNumYears = wx.Choice(self,-1,(85,18), choices=['10','All'])
        self.btnOutFile = wx.Button(self, -1,"Select output file") 
        self.btnRetrieve = wx.Button(self, -1,"Retrieve") 
        #
        #These fields bind the user's choices to the functions that handled the selections
        #
        self.Bind(wx.EVT_CHOICE,self.ERChoiceHr,self.fldER)
        self.Bind(wx.EVT_CHOICE, self.SchemeChoiceHr, self.fldScheme)
        self.Bind(wx.EVT_CHOICE, self.startYearHr, self.fldYear)        
        self.Bind(wx.EVT_CHOICE, self.numYearsHr, self.fldNumYears)        
        self.Bind(wx.EVT_BUTTON,  self.selOutFile, self.btnOutFile)
        self.Bind(wx.EVT_BUTTON,  self.Retrieve, self.btnRetrieve)
        
        #Now lay the screen out
        h1=wx.BoxSizer(wx.HORIZONTAL)
        h1.Add((20,20),1)
        h1.Add(labER,0, wx.ALIGN_LEFT|wx.ALL, 4)
        h1.Add(self.fldER,0, wx.ALIGN_LEFT|wx.ALL, 4)
        h1.Add(labScheme,0, wx.ALIGN_LEFT|wx.ALL, 4)
        h1.Add(self.fldScheme,0, wx.ALIGN_LEFT|wx.ALL, 4)
        h1.Add(labYear,0, wx.ALIGN_LEFT|wx.ALL, 4)
        h1.Add(self.fldYear,0, wx.ALIGN_LEFT|wx.ALL, 4)
        h1.Add(labNumYears,0, wx.ALIGN_LEFT|wx.ALL, 4)
        h1.Add(self.fldNumYears,0, wx.ALIGN_LEFT|wx.ALL, 4)
        h2=wx.BoxSizer(wx.HORIZONTAL)        
        h2.Add(self.btnOutFile,0, wx.ALIGN_LEFT|wx.ALL, 4)
        h2.Add(self.btnRetrieve,0, wx.ALIGN_LEFT|wx.ALL, 4)
        h2.Add(self.labOutfn,0, wx.ALIGN_LEFT|wx.ALL, 4)
        self.v1=wx.BoxSizer(wx.VERTICAL)
        self.v1.Add(h1,0,wx.ALIGN_TOP| wx.ALL, 4)
        self.v1.Add(h2,0,wx.ALIGN_TOP| wx.ALL, 4)        
        self.SetSizer(self.v1)
        self.Layout()

    def displayFileName(self):
        label = '            ' + 'Employee Records: ' + self.fileName
        self.labOutfn.SetLabel(label)
        return
    
    def getYears(self): # just a utility to get the year number of this year
        # and return a list of  the 10 years prior.
        today = datetime.datetime.now()
        thisY = today.year
        return [i for i in range(thisY,thisY-10,-1)]    
    
    def getERs(self): # just gets all the Employer TLAs and Ids
        sql = 'select rID, rTLA from tbEmployer where rPersonFlag = 1 order by rTLA asc'
        self.cursor.execute(sql)
        data = self.cursor.fetchall()
        self.ERs = [i[0] for i in data]
        self.TLAs = [i[1] for i in data]
        return self.TLAs
    
    def getSchemeChoices(self,ER): # gets all the schemes for an Employer 
        rix = self.TLAs.index(ER) # lookup the row number of the TLA
        rID = self.ERs[rix] # the rID is the same number in the self.ERs list
        sql = 'select nid, nshortplanname  from tbplan where nrid = ?'
        self.cursor.execute(sql,(rID,))
        data = self.cursor.fetchall()
        self.sIDs = [i[0] for i in data]
        self.Schemes = [i[1] for i in data]
        try: # this will fail first time through,  as fldScheme has not been created.  Just let it, it doesn't matter
            self.fldScheme.SetItems(self.Schemes)
        except:
            pass
        return self.Schemes
    
    def selOutFile (self, event):
        dlg = wx.FileDialog(
            self, message="Save file as ...", defaultDir="", 
            defaultFile="temp.xls", wildcard="*.*", style=wx.SAVE
        )
        if dlg.ShowModal() == wx.ID_OK:
            self.fileName = dlg.GetPath()
            self.fnEntered = True
            self.displayFileName()
        dlg.Destroy()

    def Retrieve (self, event):
        msgs = [' an output filename,',' an employer,',' a start year for most recent pay,',' a scheme,']
        flgs = [self.fnEntered,self.EREntered, self.YearEntered, self.SchemeEntered]
        if set(flgs) - set([True]) == set([]): # if all flags true
            dataSet = xyz99(self, 'scheme', self.SchemeID, self.startYear, None, self.numYears)
            dataSet.WriteSS(self.fileName)
            msg = 'Participant file: '+self.fileName + ', '+ str(dataSet.rnge) + ' records written.\n'
            msgDialog=wx.MessageDialog(None, msg,'Message', wx.OK)
            retCode=msgDialog.ShowModal()
            msgDialog.Destroy()
        else:
            msg = 'Please enter'
            for f, m in zip(flgs,msgs):
                if not f: msg += m
            msg = msg[:-1]+'.'
            msgDialog=wx.MessageDialog(None, msg,'Message', wx.OK)
            retCode=msgDialog.ShowModal()
            msgDialog.Destroy()

    def ERChoiceHr (self, event): # in the following functions, Hr stands for Handler
        ERix = self.fldER.GetSelection()
        self.ER = self.ERChoices[ERix] # this is the ER code of the ER chosen
        self.schemeChoices=self.getSchemeChoices(self.ER) # this sets the choices field for the next drop down box
        self.EREntered = True
        
    def SchemeChoiceHr(self,event):
        Schix = self.fldScheme.GetSelection()
        self.SchemeID = self.sIDs[Schix]
        self.SchemeEntered = True
        
    def startYearHr (self,event):
        Yearix = self.fldYear.GetSelection()
        self.startYear = int(self.startYears[Yearix])
        self.YearEntered = True
        
    def numYearsHr(self,event):
        Yearix = self.fldNumYears.GetSelection()
        if Yearix == 0:
            self.numYears = 10
        else:
            self.numYears = 50