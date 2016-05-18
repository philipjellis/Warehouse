import wx
import wx.html
from wx.lib import masked
import os
from datetime import date, datetime, timedelta
from utilities import *
from hts import htmlString
from collections import namedtuple
from editscreen import *
import HTML
import xlwt
from getFlatRecs import xyz99
import pyodbc
from ToDo import ToDoManager
from pubsub import pub
#from utilities import ConnString,getColHeads

class IndividualBenefit(wx.Panel):
    maxsize=(1600,800)
    SPhtmlPanes=[]
    #PanelList=[]
    htmlList=[]

    def __init__(self, parent):
        self.subPans=wx.BoxSizer(wx.HORIZONTAL) # this for the subpanels
        size=wx.GetDisplaySize()
        self.maxsize=(size[0]*.9,size[1]*.8)
        wx.Panel.__init__(self, parent)
        #
        #set up all the buttons and labels and whatnot
        #
	self.rbProd = wx.RadioButton(self,-1,'Production',style=wx.RB_GROUP)
	self.rbTest = wx.RadioButton(self,-1,'Test')
	self.Bind(wx.EVT_RADIOBUTTON, self.ProdTest, self.rbProd)
	self.Bind(wx.EVT_RADIOBUTTON, self.ProdTest, self.rbTest)
        lab1=wx.StaticText(self, -1, "Please enter socials, separated by spaces")
        self.intxt = wx.TextCtrl(self, -1, value="", size=(300,20)) 
        butnRetr=wx.Button(self, -1, "Retrieve")
        self.Bind(wx.EVT_BUTTON,  self.retrieveData, butnRetr)
        butnPrint=wx.Button(self, -1, "Print")
        self.Bind(wx.EVT_BUTTON,  self.Print, butnPrint)        
        butnExcel=wx.Button(self, -1, "Excel")
        self.Bind(wx.EVT_BUTTON,  self.Excel, butnExcel)       
        butnAddIB=wx.Button(self, -1, "Add")
        self.Bind(wx.EVT_BUTTON,  self.AddIB, butnAddIB) 
        butnEditIB=wx.Button(self, -1, "Edit ")
        self.Bind(wx.EVT_BUTTON,  self.EditIB, butnEditIB) 
        butnIBReport = wx.Button(self, -1, "Total unbilled")
        self.Bind(wx.EVT_BUTTON, self.IBReport, butnIBReport)
        labER = wx.StaticText(self,-1,"Choose Employer")
        self.ERTLAs = getERs(False, onlyIBs = True) # we DO NOT want the All option, we DO want the IBControl employers and not the rest
        self.fldER = wx.Choice(self, -1, (85,18), choices = [str(i) for i in self.ERTLAs])
        self.Bind(wx.EVT_CHOICE, self.displayIBs, self.fldER)
        butnBillIB=wx.Button(self, -1, "Mark unbilled IB Control Records")
        self.Bind(wx.EVT_BUTTON,  self.MarkIB, butnBillIB) 
        butnTasks=wx.Button(self, -1, "Show Tasks")
        self.Bind(wx.EVT_BUTTON,  self.Tasks, butnTasks) 
        
        #
        # now lay out the static boxes - these are the little boxes to group buttons with some explanatory text
        # 
        # the social security box
        SSBox = wx.StaticBox (self, -1, 'Details for a Social Security Number')
        SSBoxSizer = wx.StaticBoxSizer (SSBox, wx.HORIZONTAL)
        for btn in [butnRetr, butnPrint, butnExcel]:
            SSBoxSizer.Add(btn, 0, wx.ALL, 2)
        #the IB add and edit box
        IBBox = wx.StaticBox (self,-1, 'IB Control Add and Edit')
        IBBoxSizer = wx.StaticBoxSizer(IBBox, wx.HORIZONTAL)
        for btn in [butnAddIB, butnEditIB]:
            IBBoxSizer.Add(btn, 0 , wx.ALL, 2)
        # the IB display box
        IBDisplayBox = wx.StaticBox (self,-1, 'IB Control Summary Report')
        IBDisplayBoxSizer = wx.StaticBoxSizer(IBDisplayBox, wx.HORIZONTAL)
        for thing in [butnIBReport, labER, self.fldER]:
            IBDisplayBoxSizer.Add(thing, 0 , wx.ALL, 2)
        # The tasks panel
        IBTaskBox = wx.StaticBox (self,-1, 'Task Manager')
        IBTaskBoxSizer = wx.StaticBoxSizer(IBTaskBox, wx.HORIZONTAL)
        for thing in [butnTasks]:
            IBTaskBoxSizer.Add(thing, 0 , wx.ALL, 2)
        # the mark unbilled box
        IBeomBox = wx.StaticBox (self,-1, 'IB Control End of Month')
        IBeomBoxSizer = wx.StaticBoxSizer(IBeomBox, wx.HORIZONTAL)
        for btn in [butnBillIB]: #, butnTest]:
            IBeomBoxSizer.Add(btn, 0 , wx.ALL, 2)
        self.bigPanel=wx.Panel(self, -1, size=(self.maxsize),style=wx.RESIZE_BORDER|wx.RAISED_BORDER ) #style=wx.RAISED_BORDER
        self.todolist = ToDoManager(self.bigPanel, self)        
        self.todolist.fillTasks()
        #
        #now put them all into the screen with BoxSizers
        #
        h1=wx.BoxSizer(wx.HORIZONTAL) # first box has the social entry field and radio buttons for live/test
	for thing in [self.rbProd,self.rbTest,lab1,self.intxt]:
	    h1.Add(thing,0, wx.ALIGN_LEFT|wx.ALL, 4)
        #h1.Add(self.intxt,0, wx.ALIGN_LEFT|wx.ALL, 4)
        self.v1=wx.BoxSizer(wx.VERTICAL)
        h2=wx.BoxSizer(wx.HORIZONTAL) # for the buttons
        h2.Add(SSBoxSizer, 0, wx.ALL, 10)
        h2.Add(IBBoxSizer, 0, wx.ALL, 10)
        h2.Add(IBTaskBoxSizer,0,wx.ALL, 10)
        h2.Add(IBDisplayBoxSizer, 0, wx.ALL, 10)
        h2.Add(IBeomBoxSizer, 0, wx.ALL, 10)
        self.v1.Add(h1, 0, wx.ALIGN_TOP | wx.ALL, 4)
        self.v1.Add(h2, 0, wx.ALIGN_TOP | wx.ALL, 4)
        self.v1.Add(self.bigPanel)
        self.intxt.SetFocus()
        self.SetSizerAndFit(self.v1)

    def doScreen(self):
        self.subPans.Clear(True) # true will destroy all the children windows, poor things
        return

#    def TestMe(self,Event):
#        print 'called me'
#        self.subPans.Clear(True) #delete_windows=True)
#        return

    def ProdTest(self,Event):
	if self.rbProd.GetValue() == True: #then production has been selected
	    self.Production = 'Prod'
	else:
	    self.Production = 'Test'
	pub.sendMessage('Production',arg1 = self.Production)
	
            

    def Tasks(self,Event):
        self.todolist = ToDoManager(self.bigPanel, self)        
        self.todolist.fillTasks()

    def Addapanel(self, HtmlText):
        #print 'adding panel', HtmlText.v[:500]
        self.htmlList.append(HtmlText)
        self.SPhtmlPanes.append(wx.html.HtmlWindow(self.bigPanel,-1,size=(570,self.maxsize[1]*.97)))
        self.SPhtmlPanes[-1].SetMinSize((800,self.maxsize[1]*.97))
        self.SPhtmlPanes[-1].SetPage(HtmlText.v)
        self.subPans.Add(self.SPhtmlPanes[-1], 1, wx.ALIGN_LEFT|wx.ALL|wx.EXPAND, 4)
        return

    def Print (self, event):
        dumFrame = wx.Frame(None)
        wxprt = wx.html.HtmlEasyPrinting('Print', dumFrame)
        if len(self.htmlList) == 0:
            wx.MessageBox('No data retrieved. \nPlease enter a social and try again.','Message',wx.OK)
        else:
            for row in self.htmlList:
                htmlSt=row.vreduceFont()
                wxprt.PreviewText(htmlSt)

    def Excel(self,event):

        def writeRows(rowList, TypeList,IncRowNum, IncColNum):
            for rowNum, row in enumerate(rowList): # now write the data
                for colNum, cell in enumerate(row):
                    if isinstance(cell,date):
                        st = dateStyle
                    elif TypeList[colNum] == 'money':
                        st = currStyle
                    else:
                        st = genStyle
                    ws0.write(rowNum+IncRowNum+1,colNum+IncColNum,cell,st)

        msg = 1 # 1 is OK, other values are error
        msgs = ['No data retrieved. \nPlease enter a social and try again.','Spreadsheet {0} created',\
                'Could not save spreadsheet.\nPlease check the filename is good and the sheet is not open.']
        try:
            if len(self.EEDataXL) == 0:
                msg = 0
        except:
            msg = 0
        if msg == 1:
            Filename = os.getenv("HOMEDRIVE") + os.getenv("HOMEPATH") + "\\Desktop\\"+self.EEDataXL[0][1]+'.xls' # first item in EEData is the social
            wb = xlwt.Workbook()
            ws0 = wb.add_sheet('Sheet1')
            dateStyle = xlwt.easyxf(num_format_str='MM/DD/YYYY')
            currStyle = xlwt.XFStyle()
            currStyle.num_format_str = '"$"#,##0_);("$"#,##'
            genStyle = xlwt.XFStyle()
            genStyle.num_format_str = 'general'
            writeRows([('Employee Data','','','IB Control Data')],['Text','Text','Text','Text'],1,1)
            writeRows(self.EEDataXL,self.EETypes,2,1)
            writeRows(self.ibRecs,['Text' for i in self.ibRecs],2,4)
            # not compatible with Excel 2007
            try:
                wb.save(Filename)
                msg=1
                msgs[1] = msgs[1].format(Filename)
            except:
                msg = 2
        wx.MessageBox(msgs[msg],'Message',wx.OK)
        if msg == 1:
            FNquotes = '"'+Filename+'"'
            goExcelStr = 'start excel.exe {0}'.format(FNquotes)
            os.system(goExcelStr)
        return       

    def displayIBs (self, event):
        # first get the employer returned
        ERix = self.fldER.GetSelection()
        self.ER = self.ERTLAs[ERix]
        self.getAndShowIBs()
    
    
    def getAndShowIBs(self):
        self.doScreen() # clear old stuff out
        # now get the last 20 IB Control Records for that ER
        columns = 'IBID Requested SocSec EmployerPlan EEName ARI LumpSumAmount BilledFlag Comments Mailed AddDataRequest \
        AddDataReceived TerminationDate Assistant Checked Reviewed' .split()
        sql = 'select '+','.join(columns) +' from tbIbctrl where ER = (select rName from tbEmployer where rTLA = ?) \
        and billedflag is null order by IBID desc'
        cnxn = accP2()
        cursor = cnxn.cursor()
        cursor.execute(sql,(self.ER,))
        data = cursor.fetchall()
        cnxn.close()
        self.data = data#[:20] this used to limit the number of rows displayed
        # now build the list item
        self.IBlist = wx.ListCtrl(self.bigPanel, -1, style = wx.LC_REPORT, size = (1600,400))
        for col, text in enumerate (columns) : self.IBlist.InsertColumn(col, text)
        for row in self.data:
            index = self.IBlist.InsertStringItem(sys.maxint, str(row[0]))
            for col, text in enumerate(row[1:]): self.IBlist.SetStringItem(index, col+1, str(text))
        for col, text in enumerate(columns): self.IBlist.SetColumnWidth(col, wx.LIST_AUTOSIZE_USEHEADER)
        self.IBlist.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.editIBFromList, self.IBlist)
        # now the tricky bit - get it on the screen without blowing it all up!
        self.subPans.Add(self.IBlist, 1, wx.ALL|wx.EXPAND, 4)
        self.bigPanel.SetSizerAndFit(self.subPans)
        self.bigPanel.Layout()

    def IBReport(self, event):
        self.doScreen() # clear old stuff out
        today = date.today()
        cnxn = accP2()
        cursor = cnxn.cursor()
        sql = "select employerplan, requested, mailed from tbibctrl where billedflag is null"
        cursor.execute(sql)
        data = cursor.fetchall()
        cnxn.close()
        plans = sorted(set([i[0] for i in data]))
        dataDick = dict((i, {'Plan':i,'Unbilled':0,'Unmailed':0,'Gt 1 week old':0, 'Gt 2 weeks old':0, 'No date':0}) for i in plans)
        for p in plans:
            subset = [i for i in data if i.employerplan == p]
            dataDick[p]['Unbilled']= len(subset)
            unmailed = [i for i in subset if not i.mailed]
            dataDick[p]['Unmailed'] = len(unmailed)
            gt1week = 0
            gt2week = 0
            no_date = 0
            for row in unmailed:
                if row.requested:
                    if row.requested + timedelta(7) < today:
                        gt1week += 1
                    elif row.requested + timedelta(14) < today:
                        gt2week += 1
                else:
                    no_date += 1
            dataDick[p]['Gt 1 week old'] = gt1week
            dataDick[p]['Gt 2 weeks old'] = gt2week
            dataDick[p]['No date'] = no_date
        columns = ['Plan','Unbilled','Unmailed','Gt 1 week old', 'Gt 2 weeks old', 'No date']
        TotalUnMailed = sum([dataDick[p]['Unmailed'] for p in plans])
        TotalUnBilled = sum([dataDick[p]['Unbilled'] for p in plans])        
        TotalGt1week = sum([dataDick[p]['Gt 1 week old'] for p in plans])        
        TotalGt2week = sum([dataDick[p]['Gt 2 weeks old'] for p in plans])   
        TotalNoDate = sum([dataDick[p]['No date'] for p in plans])   
        dataDick['_Total'] = {
            'Plan':'_Total',
            'Unbilled': TotalUnBilled,
            'Unmailed': TotalUnMailed,
            'Gt 1 week old': TotalGt1week,
            'Gt 2 weeks old': TotalGt2week,
            'No date': TotalNoDate
        }
        plans.append('_Total')
        # now build the list item
        self.IBRlist = wx.ListCtrl(self.bigPanel, -1, style = wx.LC_REPORT, size = (700,600))
        for col, text in enumerate (columns) : self.IBRlist.InsertColumn(col, text)
        for plan in sorted(plans):
            row = [dataDick[plan][i] for i in columns]
            index = self.IBRlist.InsertStringItem(sys.maxint, str(row[0]))
            for col, text in enumerate(row[1:]): self.IBRlist.SetStringItem(index, col+1, str(text))
        for col, text in enumerate(columns): self.IBRlist.SetColumnWidth(col, wx.LIST_AUTOSIZE_USEHEADER)
        # now the tricky bit - get it on the screen without blowing it all up!
        self.subPans.Add(self.IBRlist, 1, wx.ALL|wx.EXPAND, 4)
        self.bigPanel.SetSizerAndFit(self.subPans)
        self.bigPanel.Layout()

    def retrieveData (self,event):
        socials=self.intxt.GetLineText(1).split(' ')
        self.doScreen() #fix the screens coming back with old data
        self.htmlList=[] #clear out html pages
        cnxn=accP2()
        cursor=cnxn.cursor()
        for social in socials:
            if len(social) < 11:
                social=social[0:3]+'-'+social[3:5]+'-'+social[5:] # get all socsecs if just the number entered
            htmlText=htmlString() # set up an instance of the html string
            EEData = xyz99(None,'ssn',None,None,social)
            for i,j in zip(EEData.Fields, EEData.Types):
		pass
               # print i,j
            EEHTML = HTML.table([['No employee found'],['No data returned']])
            if len(EEData.OutData) > 0:
                self.EEDataXL =  [(field,data) for field,data in zip(EEData.Fields , EEData.OutData[0])]
                self.EETypes = [(field,data) for field,data in zip(EEData.Fields , EEData.Types)]
                EEHTML = HTML.table(EEData.outStringTable())
                #then get the IB data
            self.ibRecs = getibData(social,cursor) 
            IBHTML = HTML.table([['No record in IBControl table'],['No data returned']])
            if max([len(i) for i in self.ibRecs]) > 1: # getibData returns a list of tuples, which only have the column name in each if they are empty

                columnAlign = ['top' ]* len(self.ibRecs[0])
                IBHTML = HTML.table(self.ibRecs,col_valign=columnAlign)
            OutputTable = [['Employee Data','IB Control Data'],[EEHTML, IBHTML]]
            htmlText.v+= HTML.table(OutputTable,col_valign=('top','top'))
            htmlText.v+='</td>'
            htmlText.vend()
            htmlText.vreduceFont()
            self.Addapanel(htmlText)        
        cnxn.close()
        self.bigPanel.SetSizerAndFit(self.subPans)
        self.bigPanel.Layout()

    def StartIB(self):
        """ This checks a valid social has been entered and then
        calls up the panel to enter/edit
        """
        socials = self.intxt.GetLineText(1).split(' ')
        msg = '\nPlease enter social in format 123-45-6789 or 123456789\n'
        Good = True
        if len (socials) > 0:
            social = socials[0]
        else:
            Good = False
        #first check for format : with or without the dashes
        if Good:
            (Good, social) = socialCheck(social)
        if Good:
            newEditScreen = EditRecord (self, -1, 'tbIbctrl', self.EditFlag, social)
            newEditScreen.ShowModal()
            newEditScreen.Destroy()
        else:
            error = wx.MessageBox(social+msg,'Invalid social security number', wx.OK)

    
    def AddIB (self, event):
        self.EditFlag = False
        self.StartIB()

    def EditIB (self, event):
        self.EditFlag = True
        self.StartIB()

    def editIBFromList(self, event):
        ix = event.GetIndex()
        social = self.data[ix].socsec
        self.EditFlag=True
        newEditScreen = EditRecord (self, -1, 'tbIbctrl', self.EditFlag, social)
        newEditScreen.ShowModal()
        newEditScreen.Destroy()
        self.getAndShowIBs()

    def MarkIB (self, event):
        msg="""This will mark all mailed but unbilled IB Control Records with the current date.\n
Type the password and press OK to continue.\n"""
        pw = wx.GetTextFromUser(msg,caption = 'Prepare records for billing', parent = None)
        if pw <> '':
            cnxn = accP2()
            cursor = cnxn.cursor()
            sql = 'select IBPW from pws'
            cursor.execute(sql)
            pwIB = cursor.fetchone()
            pwIB = pwIB[0].strip()
            if pw.strip() == pwIB:
                today=datetime.datetime.now()
                vals = today.strftime('%Y-%m-%d')
                sql = """update tbIbctrl set BilledFlag = '{0}' where BilledFlag is null and mailed is not null"""
                sql = sql.format(vals)
                rows = cursor.execute(sql).rowcount
                cnxn.commit()
                finish = wx.MessageBox(str(rows)+' records updated', 'Message', wx.OK)
            else:
                finish = wx.MessageBox('Incorrect password - please re-enter', 'Message', wx.OK)
