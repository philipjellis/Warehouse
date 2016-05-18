import wx
import wx.lib.colourdb
import  wx.lib.scrolledpanel as scrolled
from wx.lib import masked
import csv
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, date
from dateutil import relativedelta as rd
from utilities import *
import copy
import os
import xlrd
from collections import OrderedDict
import HTML

cn_month = pyodbc.connect(monthlyString())
cn_wh = accP2()
curs_month = cn_month.cursor()
curs_wh = cn_wh.cursor()

def social_fix(ssn):
    #takes an integer social and puts in the dashes
    ss = str(int(ssn))
    while len(ss) < 9:
        ss = '0' + ss
    return ss[:3] + '-' + ss[3:5] + '-' + ss[5:]

def isint(s):
    try:
        int(s)
        return True
    except:
        return False

def goodsocial(social):
    if len(social) == 11:
        s1 = social[:3]
        s2 = social[4:6]
        s3 = social[7:]
        d1 = social[3]
        d2 = social[6]
	if ((d1 == '-') 
            and (d2 == '-') 
            and isint(s1)
            and isint(s2)
            and isint(s3)):
            return True
    return False

def get_rows(sht,row1):
    good_rows = []
    for row_num in range(1,sht.nrows):
        row = [i.value for i in sht.row(row_num)]
        row_d = dict((k,v) for k,v in zip(row1,row))
        if row_d['ELNAME'] and row_d['EFNAME'] and row_d['ESSNUM']: #then there are data - it is a good row and not, eg a subtotal
            good_rows.append(row_d)
    for row in good_rows:
        yield row

def decimal_round(val):
    data = val or 0.0
    data = Decimal(str(data)).quantize(Decimal('.01'), rounding = ROUND_HALF_UP)
    return data

def process_xl(parent, fn, start, end, curs_mon, curs_wh):
    cols_needed = ['ELNAME','EFNAME','EINIT','ESSNUM','KTEARN']
    cols_written = ['NameLast','NameFirst','NameMiddle','SSN_NoHyphens','SSN','StartDate',\
            'EndDate','FullTimeComp','PartTimeComp','EECont','pid','eid']
    rows_written = 0
    msg = ''
    xl_workbook = xlrd.open_workbook(fn)
    sheet_names = xl_workbook.sheet_names()
    sheets_wanted = [i for i in sheet_names if ((i[-1] == '%') or (i in ['Other','Capped']))]
    sql_pideid = 'select eid, epid from tbemployee where essn = ? and erid = 25'
    sql_ins = 'insert into nacomonthlypay (' + ','.join(cols_written) + ') values (' + \
            ','.join(['?' for i in cols_written]) + ')'
    sql_check = 'select id, fulltimecomp, parttimecomp, eecont from nacomonthlypay where ssn = ? and enddate = ?'
    sql_upd = 'update nacomonthlypay set ' 
    sql_upd2 = ' = ?,'.join(['fulltimecomp', 'parttimecomp', 'eecont'])+' = ?'
    sql_upd3 = ' where id = ?'
    sql_upd = sql_upd + sql_upd2 + sql_upd3
    for sheet in sheets_wanted:
        xl_sht = xl_workbook.sheet_by_name(sheet)
        #check we have the cols we need
        row1 = [i.value for i in xl_sht.row(0)]
        if all([True if i in row1  else False for i in cols_needed]):
            if 'FUNDING' in row1:
                funding = True
            else:
                funding = False
            for row in get_rows(xl_sht,row1):
                new_row = {}
                new_row['NameLast'] = row['ELNAME']
                new_row['NameFirst'] = row['EFNAME']
                new_row['NameMiddle'] = row['EINIT']
                new_row['SSN_NoHyphens'] = str(int(row['ESSNUM']))
                new_row['SSN'] = social_fix(row['ESSNUM'])
                new_row['StartDate'] = str(start)
                new_row['EndDate'] = str(end)
                new_row['FullTimeComp'] = Decimal('0.0')
                new_row['PartTimeComp'] = Decimal('0.0')
                new_row['EECont'] = Decimal('0.0')
                if sheet == 'Other':
                    new_row['PartTimeComp'] = decimal_round(row['KTEARN'])
                else:
                    new_row['FullTimeComp'] = decimal_round(row['KTEARN'])
                if funding:
                    new_row['EECont'] = decimal_round(row['FUNDING'])
                curs_wh.execute(sql_pideid,(new_row['SSN'],))
                ids = curs_wh.fetchone()
                if ids:
                    new_row['pid'] = ids[1]
                    new_row['eid'] = ids[0]
                else:
                    new_row['pid'] = None
                    new_row['eid'] = None
                # now check to see if this ssn / enddate has already been put in.  Update if so...
                curs_mon.execute(sql_check,(new_row['SSN'],new_row['EndDate']))
                existing_row = curs_mon.fetchone()
                if existing_row: # then we need to do an update
                    row_id, ftc, ptc, eec = existing_row
                    ftc += new_row['FullTimeComp']
                    ptc += new_row['PartTimeComp']
                    eec += new_row['EECont']
                    curs_mon.execute(sql_upd,(ftc,ptc,eec,row_id))
                else:
                    # insert if nothing to update
                    curs_mon.execute(sql_ins,[new_row[i] for i in cols_written])
                rows_written += 1
        else:
            msg += '\nSome of the following columns are missing from sheet ' + sheet + ': ' + ','.join(cols_needed)
    if msg:
        OK(parent,msg)
    else:
        msg = str(rows_written) + ' rows to be written from these sheets: ' + ','.join(sheets_wanted) + '.'
        write_them = OKCancel(parent,msg)
        if write_them:
            cn_month.commit()
            OK (parent,str(rows_written) + ' rows written')
        else:
            cn_month.rollback()
            OK (parent,'File processing cancelled')
#
def OKCancel(parent, question, caption = 'OK or Cancel'):
    dlg = wx.MessageDialog(parent, question, caption, wx.OK | wx.CANCEL | wx.ICON_QUESTION)
    result = dlg.ShowModal() == wx.ID_OK
    dlg.Destroy()
    return result

def OK(parent, message):
    dlg = wx.MessageDialog(parent, message,'Messages', wx.OK)
    retCode = dlg.ShowModal()
    dlg.Destroy()
    return
    
def get_summary_dates():
    sqlminmon = 'select min(enddate) from NacoMonthlyPay'
    sqlmaxmon = 'select max(enddate) from NacoMonthlyPay'
    sqlmaxwh = 'select max(yenddate) from tbpayrecords where yeid in (select eid from tbemployee where erid = 25)'
    minmon = curs_month.execute(sqlminmon).fetchone()[0]
    maxmon = curs_month.execute(sqlmaxmon).fetchone()[0]
    cnwh = accP2()
    cursorwh = cnwh.cursor()
    maxwh = cursorwh.execute(sqlmaxwh).fetchone()[0]
    return maxmon.strftime("%m-%d-%Y"), minmon.strftime("%m-%d-%Y"), maxwh.strftime("%m-%d-%Y"), maxmon

def get_checktotals(d): # pass a date in and it will return sum for three pay fields
    sql = 'select sum(fulltimecomp), sum(parttimecomp), sum(eecont) from NacoMonthlyPay where enddate = ?'
    curs_month.execute(sql,(d,))
    return curs_month.fetchone()

class Naco(wx.Panel):
    cursor = curs_wh
    Instructions = """To use this program you will need the monthly pay and contributions spreadsheet from Naco.\n
The records will be added to a database table called NacoMonthlyPay\n in the database ClientMonthly.\n
There are three steps to the process:\n
    a) Select the file you want to load and the pay period Start and End dates.
    b) Check to see if this data is ok.
    c) If the check is ok, you can write all the records to the database.\n
Note: if  you load data that has already been loaded, you will just
overwrite the existing data.  No harm will be done.\n
If you want to delete a set of data, just set the start date\nand end date and press the delete button.
"""
    def __init__(self, parent, home):
        
        cn_month = pyodbc.connect(monthlyString())
        cn_wh = accP2()
        curs_month = cn_month.cursor()
        curs_wh = cn_wh.cursor()
        wx.Panel.__init__(self, parent)
        # some flags to check preliminary data entered
        self.home = home # this is the home screen - the top level screen we are going to put the status message into 
        self.fnEntered = False
        self.startEntered, self.endEntered = False, False
        self.ed_end = None
        self.eystartEntered, self.eyendEntered = False, False
        size=wx.GetDisplaySize()
        self.maxsize=(size[0]*.9,size[1]*.8)
        latest_date_mon, earliest_date_mon, latest_date_wh, latest_date_mon_dt = get_summary_dates()
        latest_ftc, latest_ptc, latest_eec = get_checktotals(latest_date_mon_dt)
        lab_latest_mon = wx.StaticText(self, -1, "Latest monthly data: " + latest_date_mon)        
        lab_earliest_mon = wx.StaticText(self, -1, "Earliest monthly data: " + earliest_date_mon)        
        lab_latest_wh = wx.StaticText(self, -1, "Latest warehouse data: " + latest_date_wh)        
        lab_check_ftp = wx.StaticText(self, -1, "Check FT Pay for latest month: " + '${:,.2f}'.format(latest_ftc))
        lab_check_ptp = wx.StaticText(self, -1, "Check PT Pay for latest month: " +  '${:,.2f}'.format(latest_ptc))
        lab_check_eec = wx.StaticText(self, -1, "Check EECont for latest month: " +  '${:,.2f}'.format(latest_eec))

        # now the buttons and labels for the monthly load
        #
        self.labfn = wx.StaticText(self, -1, "                    ",(85,18)) # label for the file selected
        self.btnInstruct = wx.Button(self,-1,"Instructions")
        lab_start = wx.StaticText(self, -1, " Start Date")        
        self.start_dt = wx.GenericDatePickerCtrl(self, size=(120,-1),
                                       style = wx.TAB_TRAVERSAL
                                       | wx.DP_DROPDOWN
                                       | wx.DP_SHOWCENTURY
                                       | wx.DP_ALLOWNONE )
        lab_end = wx.StaticText(self, -1, " End Date")        
        self.end_dt = wx.GenericDatePickerCtrl(self, size=(120,-1),
                                       style = wx.TAB_TRAVERSAL
                                       | wx.DP_DROPDOWN
                                       | wx.DP_SHOWCENTURY
                                       | wx.DP_ALLOWNONE )

        self.btnInFile = wx.Button(self, -1,"Step 1 Select input file") 
        self.btnCheck = wx.Button(self, -1,"Step 2 Check and save the data")        
        self.btnDelete = wx.Button(self, -1,"Delete Records") 
        # end of year widgets preceded by 'ey'
        self.eybtnInstruct = wx.Button(self,-1,"Instructions")
        lab_eystart = wx.StaticText(self, -1, " Start Date")        
        self.eystart_dt = wx.GenericDatePickerCtrl(self, size=(120,-1),
                                       style = wx.TAB_TRAVERSAL
                                       | wx.DP_DROPDOWN
                                       | wx.DP_SHOWCENTURY
                                       | wx.DP_ALLOWNONE )
        lab_eyend = wx.StaticText(self, -1, " End Date")        
        self.eyend_dt = wx.GenericDatePickerCtrl(self, size=(120,-1),
                                       style = wx.TAB_TRAVERSAL
                                       | wx.DP_DROPDOWN
                                       | wx.DP_SHOWCENTURY
                                       | wx.DP_ALLOWNONE )
        self.eybtnCheck = wx.Button(self,-1,"Check Socials all in Warehouse")
        self.eybtnPush = wx.Button(self,-1,"Push the records to the Warehouse")
        # edit box widgets
        lab_ed_ssn = wx.StaticText(self, -1, "Social Security Number:  ")        
        self.ed_ssn = wx.TextCtrl(self, -1, value="", size=(300,20)) 
        lab_ed_pw = wx.StaticText(self, -1, "Password:  ")        
        self.ed_pw = wx.TextCtrl(self, -1, value="", size=(300,20)) 
        lab_ed_end = wx.StaticText(self, -1, " End Date  ")        
        self.ed_end_dt = wx.GenericDatePickerCtrl(self, size=(120,-1),
                                       style = wx.TAB_TRAVERSAL
                                       | wx.DP_DROPDOWN
                                       | wx.DP_SHOWCENTURY
                                       | wx.DP_ALLOWNONE )
        self.btnedit = wx.Button(self, -1, "Edit Record")
        #now the view box widgets - just a social
        lab_vw_ssn = wx.StaticText(self, -1, "Social Security Number:  ")        
        self.vw_ssn = wx.TextCtrl(self, -1, value="", size=(300,20)) 
        self.vwJuly = wx.RadioButton(self,-1,'July Start',style=wx.RB_GROUP)
        self.vwDec = wx.RadioButton(self,-1,'January Start')
        self.trigger = 7
        self.goodssn = False
        self.Bind(wx.EVT_RADIOBUTTON, self.JulDec, self.vwJuly)
        self.Bind(wx.EVT_RADIOBUTTON, self.JulDec, self.vwDec)
        self.btnview = wx.Button(self, -1, "View records")
        self.btnvwfile = wx.Button(self,-1,'Write records to file')
        # switch off the check button for now
        #self.btnCheck.Disable()
        #self.btnWebsite.Disable()
        # now bind the buttons to their functions
        self.Bind(wx.EVT_BUTTON,  self.Instruct, self.btnInstruct)
        self.Bind(wx.EVT_BUTTON,  self.selInFile, self.btnInFile)
        self.Bind(wx.EVT_BUTTON,  self.step2Check, self.btnCheck)
        self.Bind(wx.EVT_BUTTON,  self.delete, self.btnDelete)        
        self.Bind(wx.EVT_DATE_CHANGED, self.start_date, self.start_dt)
        self.Bind(wx.EVT_DATE_CHANGED, self.end_date, self.end_dt)
        self.Bind(wx.EVT_DATE_CHANGED, self.eystart_date, self.eystart_dt)
        self.Bind(wx.EVT_DATE_CHANGED, self.eyend_date, self.eyend_dt)
        self.Bind(wx.EVT_BUTTON,  self.eyInstruct, self.eybtnInstruct)        
        self.Bind(wx.EVT_BUTTON,  self.eyCheck, self.eybtnCheck)        
        self.Bind(wx.EVT_BUTTON,  self.eyPush, self.eybtnPush)        
        self.Bind(wx.EVT_DATE_CHANGED, self.ed_end_date, self.ed_end_dt)
        self.Bind(wx.EVT_BUTTON,  self.eyPush, self.eybtnPush)
        self.Bind(wx.EVT_BUTTON, self.viewRecords, self.btnview)
        self.Bind(wx.EVT_BUTTON, self.viewwriteRec,self.btnvwfile)
        self.Bind(wx.EVT_BUTTON, self.editRecord, self.btnedit)
        #Now lay the screen out
        # first put dates in two boxes with their labels
        hboxstart = wx.BoxSizer(wx.HORIZONTAL)
        hboxstart.Add(self.start_dt)
        hboxstart.Add(lab_start)
        hboxend = wx.BoxSizer(wx.HORIZONTAL)
        hboxend.Add(self.end_dt)
        hboxend.Add(lab_end)
        #Load box
        LoadBox = wx.StaticBox(self,-1,'Naco Monthly Pay Records Update')
        LoadBoxSizer = wx.StaticBoxSizer(LoadBox, wx.VERTICAL)
        for thing in [self.btnInstruct, lab_latest_mon, lab_earliest_mon, lab_latest_wh,\
            lab_check_ftp, lab_check_ptp, lab_check_eec,\
            hboxstart, hboxend, self.btnInFile,self.btnCheck, self.btnDelete]:
            LoadBoxSizer.Add(thing,0,wx.ALL,15)
        # Now the end of year box
        eyBox = wx.StaticBox(self,-1,'End of year process')
        eyBoxSizer = wx.StaticBoxSizer(eyBox, wx.VERTICAL)
        hboxeystart = wx.BoxSizer(wx.HORIZONTAL)
        hboxeystart.Add(self.eystart_dt)
        hboxeystart.Add(lab_eystart)
        hboxeyend = wx.BoxSizer(wx.HORIZONTAL)
        hboxeyend.Add(self.eyend_dt)
        hboxeyend.Add(lab_eyend)
        for thing in [self.eybtnInstruct,hboxeystart,hboxeyend,self.eybtnCheck,self.eybtnPush]:
            eyBoxSizer.Add(thing,0,wx.ALL,15)
        #Now the file name box
        fnbox = wx.StaticBox(self,-1,'Filename', size=(400,100))
        fnBoxSizer=wx.StaticBoxSizer(fnbox, wx.VERTICAL)
        fnBoxSizer.Add(self.labfn,0,wx.ALIGN_RIGHT|wx.ALL,15)
        # now the edit box
        edbox = wx.StaticBox(self,-1,'Edit a record', size=(400,100))
        edboxssn = wx.BoxSizer(wx.HORIZONTAL)
        edboxssn.Add(lab_ed_ssn)
        edboxssn.Add(self.ed_ssn)
        edboxpw = wx.BoxSizer(wx.HORIZONTAL)
        edboxpw.Add(lab_ed_pw)
        edboxpw.Add(self.ed_pw)
        edboxdate = wx.BoxSizer(wx.HORIZONTAL)
        edboxdate.Add(lab_ed_end)
        edboxdate.Add(self.ed_end_dt)
        edBoxSizer=wx.StaticBoxSizer(edbox, wx.VERTICAL)
        edBoxSizer.Add(edboxssn,0,wx.ALIGN_RIGHT|wx.ALL,15)
        edBoxSizer.Add(edboxpw,0,wx.ALIGN_RIGHT|wx.ALL,15)
        edBoxSizer.Add(edboxdate,0,wx.ALIGN_RIGHT|wx.ALL,15)
        edBoxSizer.Add(self.btnedit,0,wx.ALIGN_RIGHT|wx.ALL,15)
        # Pje - this will disable the edit boxes 
        #for thing in [lab_ed_ssn,self.ed_ssn, lab_ed_pw, self.ed_pw, self.ed_end_dt,lab_ed_end, self.btnedit]:
        #    thing.Disable()
        # now the view box
        vwbox = wx.StaticBox(self,-1,'View records for a social', size=(400,100))
        vwboxssn = wx.BoxSizer(wx.HORIZONTAL)
	for thing in [lab_vw_ssn,self.vw_ssn]:
	    # PJE note - this is just to disable this, we may want it in future - or something like it
	    #try:
	#	thing.Disable()
	#    except:
	#	pass
	    vwboxssn.Add(thing)
        vwBoxSizer=wx.StaticBoxSizer(vwbox, wx.VERTICAL)
        for thing in [vwboxssn,self.vwJuly, self.vwDec, self.btnview,self.btnvwfile]:
            # PJE note - this is just to disable this, we may want it in future - or something like it
	#    try:
	#        thing.Disable()
	#    except:
	#	pass
            vwBoxSizer.Add(thing,0,wx.ALIGN_LEFT|wx.ALL,15)
        #now put the edit and view boxes in one vertical sizer
        edvwbox = wx.StaticBox(self,-1,'',size = (800,100))
        edvwBoxSizer=wx.StaticBoxSizer(edvwbox, wx.VERTICAL)
        edvwBoxSizer.Add(vwBoxSizer,0,wx.ALIGN_RIGHT|wx.ALL,15)
        edvwBoxSizer.Add(edBoxSizer,0,wx.ALIGN_RIGHT|wx.ALL,15)
        # Build up screen
        h1=wx.BoxSizer(wx.HORIZONTAL)        
        h1.Add(LoadBoxSizer,0, wx.ALIGN_LEFT|wx.ALL, 20)
        h1.Add(eyBoxSizer,0,wx.ALIGN_LEFT|wx.ALL, 20)
        h1.Add(fnBoxSizer,0, wx.ALIGN_LEFT|wx.ALL, 20)        
        h1.Add(edvwBoxSizer,0, wx.ALIGN_LEFT|wx.ALL, 20)        
        self.SetSizer(h1)
        self.Layout()
        size=wx.GetDisplaySize()
        self.maxsize=(size[0]*.9,size[1]*.8)
        
    def Instruct(self, event):
        msgDialog=wx.MessageDialog(None, self.Instructions, "Message",wx.OK)
        retCode=msgDialog.ShowModal()
        msgDialog.Destroy()

    def displayFileName(self):
        label = '            ' + 'Naco Pay Records: ' + self.fileName
        self.labfn.SetLabel(label)
        return

    def enable_butt(self):
        if self.fnEntered and self.endEntered and self.startEntered:
            self.btnCheck.Enable()

    def start_date(self, evt):
        d = evt.GetDate()
        self.start = wxdate2pydate(d)
        self.startEntered = True
        self.enable_butt()

    def end_date(self, evt):
        d = evt.GetDate()
        self.end = wxdate2pydate(d)
        self.endEntered = True
        self.enable_butt()

    def ed_end_date(self,evt): # this is the event for editing 
        d = evt.GetDate()
        self.ed_end = wxdate2pydate(d)
        self.ed_endEntered = True

    def selInFile (self, event):
        dlg = wx.FileDialog(
            self, message="Import Excel filename.", defaultDir="", 
            defaultFile="mydata.xls", wildcard="*.xls*", style=wx.SAVE
            )
        if dlg.ShowModal() == wx.ID_OK:
            self.fileName = dlg.GetPath()
            self.fnEntered = True
            self.enable_butt()
            self.displayFileName()
            self.Layout()
        dlg.Destroy()

    def step2Check (self, event):
        process_xl(self, self.fileName, self.start, self.end, curs_month, curs_wh)
            
    def delete (self, event):
        #msg = 'This function has not been built yet.\nPhil Ellis will delete any records you need.'
        st = self.start.strftime("%m-%d-%Y")
        en = self.start.strftime("%m-%d-%Y")
        sql1 = 'select count(*) from nacomonthlypay where startdate = ? and enddate = ?'
	if hasattr(self,'end') and hasattr(self,'start'):
	    curs_month.execute(sql1,(self.start,self.end))
            rows = curs_month.fetchone()[0]
            confirm = OKCancel(self,'This will delete ' + str(rows) + ' rows from ' + st + ' to ' + en)
            if confirm:
                sql2 = 'delete from nacomonthlypay where startdate = ? and enddate = ?'
                curs_month.execute(sql2,(self.start,self.end))
                cn_month.commit()
                OK(self,'The rows have been deleted')
            else:
                OK(self,'Cancelled')
	else:
	    OK(self,'Please enter a start and stop date for the deletion')

    def eyInstruct(self, event):
        OK(self,"This instruction button has not been written yet.  Ask Phil")

    def eyCheck(self,event):
        OK(self,"This button has not been written yet.  Ask Phil")

    def eyPush(self,event):
        OK(self,"This data push button has not been written yet.  Ask Phil")

    def editRecord(self, event): # take the 
        sql_findmon = 'select id, startdate, enddate, fulltimecomp, parttimecomp, eecont from \
            nacomonthlypay where ssn = ? and enddate = ?'
        sql_find_eid = 'select eid from tbemployee where essn = ? and erid = 25'
        sql_findwh = 'select yid, yeid, yenddate, ystartdate, yamount, ytype from \
            tbpayrecords where yeid = ? and yenddate = ?'
        self.social = self.ed_ssn.GetValue()
        self.pw = self.ed_pw.GetValue()
        sql_getpw = 'select password from nacopassword'
        dbpw = curs_month.execute(sql_getpw).fetchone()[0]
        if self.pw <> dbpw:
            OK(self,'You did not enter the correct password.')
            return
        if goodsocial(self.social):
            if self.ed_end:
                # try and find a record for this social and end date
                curs_month.execute(sql_findmon,(self.social, self.ed_end))
                data = curs_month.fetchone()
                if data: # then call the edit dialog with the monthly pay record
                    dlg = EditDialog(self,-1,records = data, warehouse = False,social = self.social, date = self.ed_end)
		    dlg.ShowModal()
		    dlg.Destroy()
                else:
                    curs_wh.execute(sql_find_eid,(self.social,))
                    data = curs_wh.fetchone()
                    if data:
                        self.eid = data[0]
			print 'got eid', self.eid
                        curs_wh.execute(sql_findwh,(self.eid,self.ed_end))
                        data = curs_wh.fetchall()
			if data:
			    dlg = EditDialog(self,-1,records = data, warehouse = True, social=self.social, date=self.ed_end, eid=self.eid)
			    dlg.ShowModal()
			    dlg.Destroy()
		        else: OK(self,'This is not a valid month for this Nacogdoches employee.\n' +
                            'Please check this is a good social and month and try again.\n ' + 
			    self.social + ' ' + self.ed_end.strftime("%m-%d-%Y"))
                    else:
                        OK(self,'This employee is not currently in the Nacogdoches Data Warehouse.\n' +
                            'Please check this is a good social and month and try again.\n' + 
			    self.social + ' ' + self.ed_end.strftime("%m-%d-%Y"))
            else:
                OK(self,'You must enter an end data.  Please try again.')
        else:
            OK(self,'You must enter a social formatted with the dashes.')
    
    def viewRecords(self, event):
        self.makeHtmlRecords()
        if self.goodssn:
            frm = HTMLWindow(None, 'Pay Records for ' + self.social,
                            self.output_html,
                            self.width_in_px, self.height_in_px)
            frm.Show()
        else:
            OK(self,'Please enter a social with the dashes.')

    def viewwriteRec (self, event):
        dlg = wx.FileDialog(
            self, message="Export html filename.", defaultDir="", 
            defaultFile="Nacodata.html", wildcard="*.html*", style=wx.SAVE
            )
        if dlg.ShowModal() == wx.ID_OK:
            self.htmlfileName = dlg.GetPath()
            self.makeHtmlRecords()
            if self.goodssn:
                outf = open(self.htmlfileName,'w')
                outf.write(self.output_html)
                outf.close()
            else:
                OK(self,'Please enter a social with the dashes.')
        dlg.Destroy()
        if self.goodssn:
            OK(self,'File Created')

    def makeHtmlRecords(self):
        # a first get all the records out of the NacoMonthlyPay

        def get_nacomonthlypay(social):
            sql_mon = 'Select startdate, enddate, fulltimecomp, parttimecomp, eecont from \
            nacomonthlypay where ssn = ? order by enddate asc;'
            curs_month.execute(sql_mon,(social,))
            result = []
            for row in curs_month.fetchall():
                nrow = newrow(row.startdate,row.enddate,row.fulltimecomp,row.parttimecomp,row.eecont)
                nrow = floatise(nrow)
                nrow = row_add(nrow)
                result.append(nrow)
            return result

        def floatise(r):
            row = r
            float_these = ['FullTimeComp','PartTimeComp','EEContribution']
            for cell in float_these:
		if row[cell]:
	            row[cell] = float(row[cell])
		else:
		    row[cell] = 0.0
            return row

        def newrow (sd=date(1914,1,1),ed=date(1914,1,1),ftc=0.0,ptc=0.0,eec=0.0,cumftc=0.0,cumptc=0.0,cumeec=0.0):
            return OrderedDict([('StartDate',sd),
            ('EndDate',ed),
            ('FullTimeComp',ftc),
            ('CumulativeFTC',cumftc),
            ('PartTimeComp',ptc),
            ('CumulativePTC',cumptc),
            ('TotalComp',0.0),
            ('CumTotalComp',0.0),
            ('EEContribution',eec),
            ('CumulativeEEC',cumeec)]
            )

        def row_add(row):
            row['TotalComp'] = row['FullTimeComp'] + row['PartTimeComp']
            return row

        def get_whmonthlypay(social):
            sql_eid = 'select eid from tbemployee where erid = 25 and essn = ?'
            curs_wh.execute(sql_eid,(social,))
            data = curs_wh.fetchone()
            result = []
            if data:
                sql_wh = 'select ystartdate, yenddate, yamount, ytype from tbpayrecords where yeid = ? \
                        order by ystartdate asc'
                curs_wh.execute(sql_wh,(data.eid,))
                #initialize a few things before processing rows
                rows = curs_wh.fetchall()
                thisrow = newrow(rows[0].ystartdate,rows[0].yenddate)
                for row in rows:
                    if row.ystartdate <> thisrow['StartDate']:
                        thisrow = floatise(thisrow)
                        thisrow = row_add(thisrow)
                        result.append(thisrow)
                        thisrow = newrow(row.ystartdate,row.yenddate)
                    if row.ytype == '51':
                        thisrow['FullTimeComp'] = row.yamount
                    elif row.ytype == '52':
                        thisrow['PartTimeComp'] = row.yamount
                    elif row.ytype == '53':
                        thisrow['EEContribution'] = row.yamount
                thisrow = floatise(thisrow)
                thisrow = row_add(thisrow)
                result.append(thisrow) # just done for the last row - other rows processed in the if above
            return result

        def next_dates():
            if self.trigger == 7:
                sql = "select enddate from nacoyeardates where datetype = 'Fiscal' order by enddate asc"
            else:
                sql = "select enddate from nacoyeardates where datetype = 'Annual' order by enddate asc"
            curs_month.execute(sql)
            for row in curs_month.fetchall():
                yield row[0]

        def accumulator():
            self.annuals = []
            self.total_headings = ['Year Ending','Full Time Compensation','Part Time Compensation','Total Compensation','Employee Contributions']
            self.total_colformat = ['right' for i in self.total_headings]
            nextdate = next_dates()
            next_d = nextdate.next() 
            cum_ftc, cum_ptc, cum_eec, = 0.0, 0.0, 0.0
            for row in self.records:
               # print row
                if row['EndDate'] > next_d:
                    ann_tot = [next_d ,cum_ftc, cum_ptc, cum_ftc + cum_ptc, cum_eec]
                    self.annuals.append(ann_tot)
                    cum_ftc, cum_ptc, cum_eec, cum_tot = 0.0, 0.0, 0.0, 0.0
                    next_d = nextdate.next()
                cum_ftc += row['FullTimeComp']
                cum_ptc += row['PartTimeComp']
                cum_eec += row['EEContribution']
                row['CumulativeFTC'] = cum_ftc
                row['CumulativePTC'] = cum_ptc
                row['CumulativeEEC'] = cum_eec
                row['CumTotalComp'] = row['CumulativeFTC'] + row['CumulativePTC']

            self.annuals = [string_formtotals(i) for i in self.annuals]

        def getMaxLen(col):
            return max([len(i) for i in col])

        def date_str (d):
            return d.strftime("%m-%d-%Y")

        def money_str(m):
            return '${:,.2f}'.format(m)
 
        def string_format(row): # assumes a row from newrow is coming in - ie columns in that order
            return [date_str(col) for col in row[:2]] + [money_str(col) for col in row[2:]]

        def string_formtotals(row): # assumes a row from the total table is coming in
            return [date_str(row[0])] + [money_str(col) for col in row[1:]]

        self.social = self.vw_ssn.GetValue()
        self.records = []
        self.goodssn = goodsocial(self.social)
        if self.goodssn:
            self.records.extend(get_whmonthlypay(self.social))
            self.records.extend(get_nacomonthlypay(self.social))
            accumulator()
            #print self.records
            self.totHtml = HTML.table(self.annuals,header_row = self.total_headings, col_align = self.total_colformat)
            self.records = [i.values() for i in self.records]
            self.records = [string_format(i) for i in self.records] # just sort out the date formats and currency
            col_styles = ['right' for i in newrow().keys()]
            self.htmlcode = HTML.table(self.records, header_row=newrow().keys(),col_align=col_styles)
            resultTransp = zip(*self.records)
            colWidths = [len(i) for i in newrow().keys()] #[getMaxLen(i)+1 for i in resultTransp]
            width = sum(colWidths) * 1.5 # fudge factor! (PJE))
            height = len(self.records)
            width_in_mm = width*1.797-2.4
            self.width_in_px = width_in_mm * 3.814
            height_in_mm = height * 8.675 - 2.697
            height_in_mm = min([height_in_mm, 270])
            self.height_in_px = height_in_mm * 3.814
            head = "<html><h1>Pay Summary for {0} :  {1}</h1><h2>{2} start</h2><br>"
            curs_month.execute('select namefirst, namelast from nacomonthlypay where ssn = ?',(self.social,))
            namerow = curs_month.fetchone()
            if self.trigger == 7:
                start_text = 'July'
            else:
                start_text = 'December'
            if namerow:
                name = ' '.join(namerow)
            else:
                name = 'Unknown social'
            header_html = head.format(self.social,name,start_text)
            self.output_html = header_html + self.totHtml + '<br>' + self.htmlcode

    def eystart_date(self, evt):
        d = evt.GetDate()
        self.eystart = wxdate2pydate(d)
        self.eystartEntered = True

    def eyend_date(self, evt):
        d = evt.GetDate()
        self.eyend = wxdate2pydate(d)
        self.eyendEntered = True

    def JulDec(self,Event):
        if self.vwJuly.GetValue() == True: #then production has been selected
            self.trigger = 7
        else:
            self.trigger = 1

class EditDialog(wx.Dialog):

    def __init__(self, parent, id, warehouse, records, social, date, eid = None):
        wx.Dialog.__init__(self, parent, id, pos=(100,100), 
			title = 'Update screen for social ' + social + ' on ' + date.strftime("%m-%d-%Y"))
        self.startdate, self.enddate = None, None
        self.warehouse = warehouse
	self.eid = eid
        self.records = records
	self.start_data = {}
	self.start_data['51'] = self.empty_rec('Full Time Comp')
	self.start_data['52'] = self.empty_rec('Part Time Comp')
	self.start_data['53'] = self.empty_rec('EE Contribution')
        if self.warehouse: # then we should have one to three records from the warehouse
            for record in self.records:
	        self.start_data[record.ytype]['yid'] = record.yid
		self.start_data[record.ytype]['amt'] = record.yamount
            self.startdate = record.ystartdate
            self.enddate = record.yenddate
        else: # it was a monthly record, and there is only one
            record = self.records
            self.start_data['51']['amt'] = record.fulltimecomp
            self.start_data['52']['amt'] = record.parttimecomp
            self.start_data['53']['amt'] = record.eecont
            self.startdate = record.startdate
            self.enddate = record.enddate
	#print 'start data', self.start_data
        lab_ftc = wx.StaticText(self, -1, "Full time compensation: ")        
        lab_ptc = wx.StaticText(self, -1, "Part time compensation: ")        
        lab_eec = wx.StaticText(self, -1, "Employee contribution: ")        
        sz=(300,20) # size of num ctrl
        self.ctrl_ftc = masked.NumCtrl(self,-1,size=sz,integerWidth=7,fractionWidth=2)
        self.ctrl_ptc = masked.NumCtrl(self,-1,size=sz,integerWidth=7,fractionWidth=2)
        self.ctrl_eec = masked.NumCtrl(self,-1,size=sz,integerWidth=7,fractionWidth=2)
        self.ctrl_ftc.SetValue(float(self.start_data['51']['amt']))
        self.ctrl_ptc.SetValue(float(self.start_data['52']['amt']))
        self.ctrl_eec.SetValue(float(self.start_data['53']['amt']))
        # buttons
        self.btnSave = wx.Button(self,-1,'Save')
        cancel = wx.Button(self,wx.ID_CANCEL)
        self.btnDel = wx.Button(self,-1,'Delete')
        # bindings
        self.Bind(wx.EVT_BUTTON, self.save, self.btnSave)
        self.Bind(wx.EVT_BUTTON, self.delete, self.btnDel)
        sizer = wx.BoxSizer(wx.VERTICAL)
        fgs = wx.FlexGridSizer(3,2,5,5)
        for widget in [lab_ftc,self.ctrl_ftc,lab_ptc,self.ctrl_ptc,lab_eec,self.ctrl_eec]:
            fgs.Add(widget,0,wx.ALIGN_RIGHT)
        fgs.AddGrowableCol(1)
        sizer.Add(fgs,0,wx.EXPAND|wx.ALL, 5)
        btnsizer = wx.BoxSizer(wx.HORIZONTAL)
	for button in [self.btnSave, cancel, self.btnDel]:
	    btnsizer.Add(button,0,wx.ALIGN_LEFT|wx.ALL,20)
        sizer.Add(btnsizer, 0 , wx.EXPAND|wx.ALL, 5)

        self.SetSizer(sizer)
        sizer.Fit(self)

    def empty_rec(self,dsc):
	return {'yid': None,'eid':None,'amt':Decimal('0.0'),'dsc':dsc}

    def save(self,evt):
        ftc = Decimal(str(self.ctrl_ftc.GetValue()))
        ptc = Decimal(str(self.ctrl_ptc.GetValue()))
        eec = Decimal(str(self.ctrl_eec.GetValue()))
        sql_whupd = 'update tbpayrecords set yamount = ? where yid = ?'
        sql_whget = 'select yamount, yid from tbpayrecords where yeid = ? and yenddate = ? and ytype = ?'
        sql_whdel = 'delete from tbpayrecords where yid = ?'
        sql_whins = 'insert into tbpayrecords (yeid,ystartdate, yenddate,yamount, ytype) values (?,?,?,?,?)'
        sql_monupd = 'update nacomonthlypay set fulltimecomp = ?, parttimecomp = ?, eecont = ? where id = ?'
        sql_mondel = 'delete from nacomonthlypay where id = ?'
        """ Here are the possibilities
        WAREHOUSE - every type of comp has its own record
        a) Record exists and has not been changed - do nothing, 
        b) Record exists and has been changed to non-zero amount, do update
        c) Record exists and has been changed to zero, do delete
        d) Record does not exist and has not been changed - will show up as zero and is left as zero, do nothing
        e) Record does not exist and has been changed - do insert
        MONTHLY - each record has all three types of compensation.  Deletes only possibly by pressing delete 
        key - not handled in this function. 
        f) Record exists and has not been changed - do nothing
        g) Record exists and has been changed - do update
        """
	upd_done = False
        if self.warehouse: # use the warehouse cursor
	    msg = ''
            for typ, comp in zip(['51','52','53'],[ftc,ptc,eec]):
            # first get the record and see if it has changed
                start_data = self.start_data[typ]
                if comp <> None:
                    comp = Decimal(str(comp))
                else:
                    comp = Decimal(str('0.0'))
                if not start_data['amt'] and comp == Decimal('0.0'): # d
                    #then do nothing
                    msg += start_data['dsc'] + ' no update \n'
                elif start_data['amt'] and comp == Decimal('0'): # this is effectively a delete ie c
                    curs_wh.execute(sql_whdel,(start_data['yid'],))
		    msg += start_data['dsc'] + ' record deleted\n'
	        elif start_data['amt'] and (comp <> Decimal('0.0')):
		    if (start_data['amt'] <> comp): # b
                        curs_wh.execute(sql_whupd,(comp,start_data['yid']))
		        msg += start_data['dsc'] + ' record updated to ' + str(float(comp)) + '\n'
		    else:
			msg += start_data['dsc'] + ' record not changed\n' #a
                elif (not start_data['amt']) and (comp <> Decimal('0')): # e then we insert
                    curs_wh.execute(sql_whins,(self.eid, self.startdate, self.enddate, comp, typ))
		    print sql_whins, start_data['eid'], self.startdate, self.enddate, comp, typ
		    msg += start_data['dsc'] + ' record inserted with ' + str(float(comp)) + '\n'
 	    cn_wh.commit()
	    OK(self,'Data warehouse compensation updated\n' + msg)
            self.EndModal(0)
	else: # use the monthly cursor
            if (ftc == self.start_data['51']['amt']) and \
	       (ptc == self.start_data['52']['amt']) and \
	       (eec == self.start_data['52']['amt']):
                OK(self,'No update posted')
                self.EndModal(0)
            else:
                curs_month.execute(sql_monupd,(ftc,ptc,eec,self.records.id))
		cn_month.commit()
                OK(self,'Monthly compensation record updated.')
		self.EndModal(0)
        
    def delete(self,evt):
        sql_whdel = 'delete from tbpayrecords where yid = ?'
        sql_mondel = 'delete from nacomonthlypay where id = ?'
        if self.warehouse: # then delete each record
            for record in self.records:
                curs_wh.execute(sql_whdel,(record.yid,))
		cn_wh.commit()
        else:
            curs_month.execute(sql_mondel, (self.records.id))
	    cn_month.commit()
        OK (self,'Records deleted')
	self.EndModal(0)



