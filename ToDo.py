import wx
import wx.html
import  wx.lib.masked as masked
import os
from datetime import date, datetime, timedelta
from utilities import ConnString, getColHeads, HTMLWindow
from editscreen import EditRecord
import pyodbc
from rw_utilities import readXLList, writeXL
from collections import OrderedDict
from wx.lib.dialogs import ScrolledMessageDialog as sm
from dateutil import relativedelta as rd
import string
import HTML 

#utilities
class CursorConnection (object):
    pass

conn = pyodbc.connect(ConnString(11))
cursor = conn.cursor()


class Status:
    """ There are two percentage fields for status
    a) percentcomplete - this is the percent of the schedule you can burn up and still be considered ok for this
    step
    b) percentlate - this is the percentage that will count as behind schedule
    """
    sql = 'select sstatusdescription, spercentcomplete, spercentlate from status'
    cursor.execute(sql)
    data = cursor.fetchall()
    onsched_dick = dict((i.sstatusdescription,i.spercentcomplete) for i in data)
    late_dick =  dict((i.sstatusdescription,i.spercentlate) for i in data)
    statlist = [i.sstatusdescription for i in data]

def sqlUpd (table, colNames, keyColNames):
    sqlUpd = "update {0} set ".format(table)
    sqlUpd2 = " = ?,".join(colNames) + '=? where '
    sqlUpd3 = '=? and '.join(keyColNames) + '=?'
    return sqlUpd+sqlUpd2+sqlUpd3

def sqlIns (table,colNames, outkey = None):
    sqlIns = 'insert into {0} '.format(table)
    sqlIns2 ='('+', '.join(colNames) + ') '
    if outkey : 
        sqlIns2 += 'output inserted.{0}'.format(OutKey)
    sqlIns2 += ' values ('
    sqlIns3 = ','.join(['?']* len(colNames)) + ')'
    return sqlIns + sqlIns2 + sqlIns3

def dbupdate (sql, dat, cc):
    """ this carries out a database update call.
    """
    errStrin = 'sql-->'+sql+'\n'+'data-->'+str(dat)+'\n'
    error = False
    try:
        cc.cursor.execute(sql,dat)
    except pyodbc.Error as er:
        errNo, errData = er
        errStrin += 'Unexpected update error-->'+str(errNo)+str(errData)+'\n'
        error = True
    if cc.cursor.rowcount <> 1 :
        error = True
        errStrin += '\nUnexpected update error, rowcount = '+str(cc.cursor.rowcount)+'\n'
    if error:
        cc.conn.rollback()
        return errStrin
    else:
        cc.conn.commit()


def dbinsert (sql,dat, cc):
    errStrin = 'sql-->'+sql+'\n'+'data-->'+str(dat)+'\n'
    try:
        cc.cursor.execute(sql,dat)
    except pyodbc.Error as er:
        errNo, errData = er
        errStrin += 'Unexpected insert error-->'+str(errNo)+str(errData)+'\n'
        return errStrin
    else:
        cc.conn.commit()

def delete(sql, table, cc, **params):
    sql = 'delete from ' + table + ' where ' + ' and '.join([i+ ' = ?' for i in params.keys()])
    errStrin = 'sql-->'+sql+'\n'+'data-->'+str(dat)+'\n'
    try:
        cc.cursor.execute(sql,params.values())
    except pyodbc.Error as er:
        errNo, errData = er
        errStrin += 'Unexpected delete error '+str(errNo)+str(errData)+'\n'
        return errStrin
    cc.conn.commit()

def pydate2wxdate(d):
    try:
        test = d.year
    except:
        d = None
    if d:
        tt = d.timetuple()
        dmy = (tt[2], tt[1]-1, tt[0])
        return wx.DateTimeFromDMY(*dmy)
    return wx.DateTime()

def wxdate2pydate(d):
    assert isinstance(d, wx.DateTime)
    if d.IsValid():
        ymd = map(int, d.FormatISODate().split('-'))
        return date(*ymd)
    else:
        return None

class Widget(object):
    def __init__(self, parent, name, typ, size=(300,20), dataval = None, choices=None, greyed = False):
        self.label = wx.StaticText(parent,-1,name)
        self.name = name
        self.choices = choices
        self.typ = typ
        self.data = dataval
        if typ == 't' : # text
            self.control = wx.TextCtrl(parent,-1,value="",size=size)
        elif typ == 'c': # choice
            self.control = wx.Choice(parent,-1,(85,18),choices = self.choices)
        elif typ == 'd': # date
            self.control = wx.GenericDatePickerCtrl(parent, -1, size = (120,-1),
			    style=wx.DP_ALLOWNONE)
        elif typ == 'i': # integer
            self.control = masked.NumCtrl(parent, -1,size=size,
                                          value = 0, 
                                          integerWidth = 5, 
                                          fractionWidth = 0, 
                                          allowNegative = False, 
                                          min = 0, 
                                          max = 10000, 
                                          )
        self.add_data()
        if greyed:
            self.control.Enable(False)

    def add_data(self):
        # refresh the data in the widget - eg from the database
        if self.typ == 't':
            self.control.SetValue(str(self.data))
        elif self.typ == 'i':
	    if self.data:
		ins_data = self.data
	    else:
		ins_data = 0
            self.control.SetValue(ins_data)        
        elif self.typ == 'c':
            if self.data:
                self.control.SetStringSelection(self.data)
        elif self.typ == 'd': 
            wxdate = pydate2wxdate(self.data)
            self.control.SetValue(wxdate)

    def get_data(self):
        # find out what the user has done
        if self.typ in ['t','i']:
            self.data = self.control.GetValue()
            if self.name == 'Task Description':
                self.data = self.data[:50]
	    if self.typ == 't':
		self.data = filter(lambda x: x in string.printable, self.data)
        elif self.typ == 'c':
            self.data = self.control.GetStringSelection()
            #print 'got choice',self.print_data()
            #print 'slct' ,self.control.GetStringSelection()
        elif self.typ == 'd': 
            data = self.control.GetValue()
            self.data = wxdate2pydate(data)
        self.print_data()

    def print_data(self):
        #print self.name, self.data
        return

class Task (object):

    def __init__(self, cc, user, tclient=None, tproject = None, taskdata=None):
        self.cols = ['tclient','tproject','powner','ttaskid','tdescription','tresponsible',
                     'tdue','tstarted','texpected','tstatus','tbudgetdays','tcomments']
        self.keycols = ['tclient','tproject','ttaskid']
        self.datacols = ['tdescription','tresponsible','tdue','tstarted','texpected','tcomments','tstatus']
        self.tasktablecols = self.keycols + self.datacols
        self.heads =[i[1:].title() for i in self.cols]
        self.cc = cc
	self.user = user
        if taskdata:
            for i in self.cols:
                setattr(self,i,getattr(taskdata,i,None))
        else:
            self.create(tclient, tproject)
	self.LATE = '#FF3333' # red
	self.PROBABLY_LATE = '#FF8433' #orange
	self.BEHIND = '#FFFF00' # yellow
	self.ONHOLD = '#7FCBC9' # light blue
	self.NOBUDGET = '#83541E' #brown
	self.NODUE = '#CCFFCC' # light green
	self.LATEtxt = 'Late'
	self.PROBABLY_LATEtxt = 'Behind Schedule'
	self.BEHINDtxt = 'Behind Schedule'
	self.ONHOLDtxt = 'On Hold'
	self.NOBUDGETtxt = 'No budget'
	self.NODUEtxt = 'No due date'
        self.ONHOLDSTATUS = '0 On Hold'
	self.COMPLETESTATUS = '6 Complete'
	self.CANCELLEDSTATUS = '7 Cancelled'

    def create(self, tclient, tproject):
        for i in self.cols:
            setattr(self,i,None)
        self.tdue = datetime.now().date()
        self.texpected = datetime.now().date()
        self.tclient = tclient
        self.tproject = tproject
        self.ttaskid = self.max_task()
        self.tstatus = '1 Not Started'
	self.tbudgetdays = 0

    def return_constants(self):
	return [(self.LATE, self.LATEtxt),
		(self.PROBABLY_LATE, self.PROBABLY_LATEtxt),
		(self.BEHIND, self.PROBABLY_LATEtxt),
		(self.ONHOLD, self.ONHOLDtxt),
		(self.NOBUDGET, self.NOBUDGETtxt),
		(self.NODUE, self.NODUEtxt)
		]

    def colour(self):
	pctcomplete = 1.0 - Status.onsched_dick[self.tstatus] / 100.0
	pctlate = 1.0 - Status.late_dick[self.tstatus] / 100.0
	today = date.today()
	""" You have to think about this order:
	a) if it is complete or cancelled - just quit
	b) if it HAS a due date and this is before today - return LATE
	c) if it is ONHOLD return ONHOLD - this takes priority over the next one
	d) if it does not have a due date - return NODUE 
	e) once you have got here just calculate the categories of late and 
	f) if it is late return late
	g) else return nothing
	"""
	if self.tstatus in [self.COMPLETESTATUS, self.CANCELLEDSTATUS]:
	    return None, None
        if self.tdue:
	    if self.tdue < today:
	        return self.LATE, self.LATEtxt
        if self.tstatus == self.ONHOLDSTATUS:
            return self.ONHOLD, self.ONHOLDtxt
	if not self.tdue:
	    return self.NODUE, self.NODUEtxt
	if self.tbudgetdays:
	    well_behind = (today + rd.relativedelta(days = int(pctlate * self.tbudgetdays))) > self.tdue
	    if well_behind:
		return self.PROBABLY_LATE, self.PROBABLY_LATEtxt
	    behind = (today + rd.relativedelta(days = int(pctcomplete * self.tbudgetdays))) > self.tdue
	    if behind:
		return self.BEHIND, self.BEHINDtxt
	else:
	    return self.NOBUDGET, self.NOBUDGETtxt
        return None, None

    def duedateout(self):
	try:
            return self.tdue.strftime("%m-%d-%Y")
        except:
	    return 'N/A'

    def max_task(self):
        sql = 'select max(ttaskid) from tasks where tclient = ? and tproject = ?'
        self.cc.cursor.execute(sql,(self.tclient, self.tproject))
        #print 'sql',sql, 'c',self.tclient, 'p',self.tproject
        t = self.cc.cursor.fetchone()
        #print 't',t
        if t[0]:
            return t[0] + 10
        else:
            return 10

    def ins(self):
        sql = sqlIns('tasks',self.tasktablecols)
        insert_val = dbinsert(sql,[getattr(self,i) for i in self.tasktablecols],self.cc)
        if insert_val:
            print 'error',insert_val
            wx.MessageBox(insert_val, 'Error Inserting Tasks', wx.OK | wx.ICON_INFORMATION)
            return False
        else:
            details = '\nsql'+sql+'\ndata'+str(insert_val)
            details = '' # comment this out if you want the details
            wx.MessageBox('Inserted new task'+details, 'Message', wx.OK | wx.ICON_INFORMATION)          
            return True

    def upd(self):
        sql = sqlUpd('tasks',self.datacols,self.keycols)
        vals = [getattr(self, i) for i in self.datacols] + [getattr(self, i) for i in self.keycols]

        upd_val = dbupdate(sql,vals,self.cc)
        if upd_val:
            print 'error',upd_val
            wx.MessageBox(upd_val, 'Error Updating Tasks', wx.OK | wx.ICON_INFORMATION)
            return False
        else:
            msg = '\n'+sql+'\n'+str(vals)
            msg = ''
            #wx.MessageBox('Updated task'+msg,'Message', wx.OK | wx.ICON_INFORMATION)            
            return True

    def copy_data(self):
        self.old_data = OrderedDict((col, getattr(self,col)) for col in self.cols)
        #print'old data', self.old_data
        
    def write_history(self):
        # first identify the changed data columns
        msg = ''
        for col in self.datacols:
            if self.old_data[col] <> getattr(self,col): # then something has changed
                msg += '\nchanged ' + col + ' from ' + str(self.old_data[col]) + ' to ' + str(getattr(self,col))
        if msg:
            history_columns = ['hClient','hProject','hTaskid','hWho','hWhen','hAction']
            sql = sqlIns('history',history_columns)
            ins_msg = dbinsert(sql,
                               (self.tclient,self.tproject,self.ttaskid,self.user,datetime.now(),msg),
                               self.cc)
            if ins_msg: #error!
                retcode = wx.MessageBox(ins_msg,"Error", wx.OK)
            else:
                #print 'updated',sql,
                #print msg
                self.cc.conn.commit()
        else:
            pass
            #print 'nothing changed'

    def printme(self,msg):
        print 'task ', msg
        for i in self.cols:
            print i, getattr(self,i)

class TaskDialog(wx.Dialog):

    def __init__(self, parent, id, t, ps, sts, edit = False): #t=task, ps = people list, sts = status list
        wx.Dialog.__init__(self, parent, id, pos=(100,100), title = 'Enter New Task')
        self.widgets = OrderedDict()
        self.task = t
        #t.printme('3')
        self.widgets['tclient'] = Widget(self,'Client','t',dataval = t.tclient, greyed = True)
        self.widgets['tproject'] = Widget(self,'Project','t',dataval = t.tproject, greyed = True)
        self.widgets['ttaskid'] = Widget(self,'Taskid','i', dataval = t.ttaskid, greyed = edit)        
        self.widgets['tdescription'] = Widget(self,'Task Description','t', dataval = t.tdescription)
        self.widgets['tresponsible'] = Widget(self,'Responsible','c',choices=ps, dataval = t.tresponsible)
        self.widgets['tdue'] = Widget(self,'Due Date','d', dataval = t.tdue)
        self.widgets['tstarted'] = Widget(self,'Started','d', dataval = t.tstarted)		
        self.widgets['texpected'] = Widget(self,'Expected Date','d', dataval = t.texpected)        
        self.widgets['tcomments'] = Widget(self,'Comments','t',dataval = t.tcomments)        
        self.widgets['tstatus'] = Widget(self,'Status','c',choices = sts, dataval = t.tstatus)        		
        self.widgets['tbudgetdays'] = Widget(self,'Budget Days','i', dataval = t.tbudgetdays)        		
        # buttons
        save = wx.Button(self,wx.ID_OK)
        save.SetDefault()
        cancel = wx.Button(self,wx.ID_CANCEL)

        sizer = wx.BoxSizer(wx.VERTICAL)
        fgs = wx.FlexGridSizer(11,2,5,5)
        for widget in self.widgets.values():
            fgs.Add(widget.label,0,wx.ALIGN_RIGHT)
            fgs.Add(widget.control,0,wx.LEFT)
        fgs.AddGrowableCol(1)
        sizer.Add(fgs,0,wx.EXPAND|wx.ALL, 5)
        btns = wx.StdDialogButtonSizer()
        btns.AddButton(save)
        btns.AddButton(cancel)
        btns.Realize()
        sizer.Add(btns, 0 , wx.EXPAND|wx.ALL, 5)

        self.SetSizer(sizer)
        sizer.Fit(self)

    def add_data(self,params):
        for key,value in params.iteritems():
            self.widgets[key].add_data(value)

    def get_data(self):
        result = {}
        for key in self.widgets.keys():
            self.widgets[key].get_data()
            setattr(self.task,key,self.widgets[key].data)
        #self.task.printme('4')

    def print_data(self):
        for v in self.widgets.values():
            v.print_data()


class TaskList (object):
    """ This is the current task list being worked on by the ToDo Manager"""
    def __init__(self, parent):
        self.data = []
        self.tclient = parent.tclient
        self.tproject = parent.tproject
        self.tstatus = parent.tstatus
        self.user = parent.user
        self.parent = parent
        self.cc = parent.cc

    def getTasks(self, **fields):
        testfields = fields
        lessthan = False
        dummy = Task(self.cc, self.user, tclient = self.tclient, tproject = self.tproject )
        st = 'select ' + ','.join(dummy.cols) + ' from vw_all where '
        ks = []
        vals = []
        self.fields = {}
        # first check that all the fields are not zero - if so just stick tresponsible = os.environ['USERNAME']
        testvals = testfields.values()
        if set(testvals) == set([None]):
            testfields = {'tresponsible': self.parent.userdefault}
        for k,v in testfields.iteritems():
            if (k == 'tstatus'):
                if v:
                    ks.append(' tstatus < ? ')
                    vals.append(v)
                else:
                    pass
	    elif (k == 'tduein100'):
		if v:
	            due_date = date.today() + rd.relativedelta(days = 100)
		    ks.append(' tdue < ? ')
		    vals.append(due_date)
		else:
	            pass
            else:
                if v:
                    ks.append(k + ' = ?')
                    vals.append(v)	
        ks = ' and '.join(ks)
        sql =  st + ks + ' order by Tdue;'
        #print 'sql',sql
        #print 'vals', [str(i) for i in vals]
        self.cc.cursor.execute(sql,vals)

        self.data = [Task(self.cc, self.parent.userdefault, self.tclient, self.tproject, taskdata = i) for i in self.cc.cursor.fetchall()]


    def newTask(self, client, project):
        self.new_t = Task(self.cc, self.parent.userdefault, tclient = self.parent.tclient, tproject = self.parent.tproject) #empty task
        #self.new_t.printme('2')
        td = TaskDialog(self.parent, -1, self.new_t, self.parent.people(), self.parent.statuses(), edit = False)
        finished = False
        while not finished:
            result = td.ShowModal()
            if result == wx.ID_OK:
                td.get_data()
                if self.new_t.ins(): # then the insert went ok
                    self.data.append(self.new_t)
                    finished  = True
            else:
                finished = True
            td.Destroy()
        self.parent.fillTasks()

    def editTask(self, task):
        t = task
        td = TaskDialog(self.parent, -1, t, self.parent.people(), self.parent.statuses(), edit = True)
        finished = False
        while not finished:
            result = td.ShowModal()
            if result == wx.ID_OK:
                t.copy_data()
                td.get_data()
                if t.upd(): # then the update went ok
                    t.write_history()
                    finished  = True
            else:
                finished = True
            td.Destroy()
        self.parent.fillTasks()	

class ToDoManager(wx.Panel):

    def __init__(self, parent, IBPanel):
        self.parent = parent
        self.IBPanel = IBPanel
        wx.Panel.__init__(self, self.parent, -1)
        # set up the cursor to get at the to do lists
        self.td_conn = pyodbc.connect(ConnString(11))
        self.td_cur = self.td_conn.cursor()
        self.pw = self.td_cur.execute('select pw from pw').fetchone()[0]
        self.cc = CursorConnection()
        self.cc.cursor = self.td_cur
        self.cc.conn = self.td_conn
        self.tclient = None #self.clients()[0]
        self.tproject = None #self.projects(self.tclient)[0]
        self.tprojectlist = self.projects(self.tclient)
        self.tstatus = None #self.statuses()[0]
        self.userdefault = os.environ['USERNAME'].capitalize()        
        self.dt = Task(self.cc, self.userdefault, tclient = self.tclient, tproject = self.tproject) # dummy task for col names etc
        self.columns = self.dt.cols
        self.projectcol_ix = self.columns.index('tproject')
        self.taskcol_ix = self.columns.index('ttaskid') 
        self.clientcol_ix = self.columns.index('tclient')
        self.statuscol_ix = self.columns.index('tstatus')   
        self.budgetdayscol_ix = self.columns.index('tbudgetdays')   
        self.responsiblecol_ix = self.columns.index('tresponsible')
        self.expectedcol_ix = self.columns.index('texpected')
        self.commentscol_ix = self.columns.index('tcomments')
        self.startedcol_ix = self.columns.index('tstarted')
        self.duecol_ix = self.columns.index('tdue')
        self.descriptioncol_ix = self.columns.index('tdescription')
        self.ownercol_ix = self.columns.index('powner')
	self.user = os.environ['USERNAME'].capitalize()
        self.person_ix = self.people().index(self.userdefault)
        self.tl = TaskList(self)
        self.tl.getTasks(tresponsible=self.user)
        self.client_ix,self.project_ix, self.status_ix = -1,-1,-1
	self.duein100 = False
	self.butnduelabel = 'Show All Relevant Tasks'
        self.fillTasks()

    def fillTasks (self):
        self.IBPanel.doScreen() # clear old stuff out
        self.TodoBox = wx.BoxSizer(wx.VERTICAL)
        self.todoScreen()
        # now build the list item
        self.TDlist = wx.ListCtrl(self.parent, -1, style = wx.LC_REPORT, size = (1600,400))
        first_col = self.dt.cols[0]
	comments_col = len(self.dt.cols) - 2 
	# relies upon the comments being the last column, which it should be, notice it is -2 as 
	#  it is set in the enumerate(1:) code five lines down
        for col, text in enumerate (self.dt.heads) : 
            self.TDlist.InsertColumn(col, text) 
	# now put the strings into the list control
        for rownum,task in enumerate(self.tl.data):
	    colour,error = task.colour()
            index = self.TDlist.InsertStringItem(rownum+1, str(getattr(task,first_col)))
            for colnum, col in enumerate(self.dt.cols[1:]): 
		column_text = str(getattr(task,col))
		if (colnum == comments_col):
		    if column_text == 'None':
			column_text = '' 
		    if error:
		        if column_text:
			    column_text = ': ' + column_text
			column_text = error + column_text
                self.TDlist.SetStringItem(index, colnum+1, column_text)
	    if colour:
		self.TDlist.SetItemBackgroundColour(index,colour)
        for col, text in enumerate(self.columns): 
            self.TDlist.SetColumnWidth(col, wx.LIST_AUTOSIZE_USEHEADER)
        self.TDlist.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.editTDFromList, self.TDlist)
        self.TDlist.Bind(wx.EVT_LIST_ITEM_SELECTED, self.setIndex, self.TDlist)
        self.TDlist.Bind(wx.EVT_COMMAND_RIGHT_CLICK, self.OnRightClick)
        # now the tricky bit - get it on the screen without blowing it all up!
        self.TodoBox.Add(self.todoBtnSizer, 0, wx.ALIGN_TOP, 5)
        self.TodoBox.Add(self.TDlist, 1, wx.EXPAND|wx.ALL|wx.ALIGN_TOP,5)
        self.IBPanel.subPans.Add(self.TodoBox, 1, wx.ALL|wx.EXPAND, 4)
        self.parent.SetSizerAndFit(self.IBPanel.subPans)
        self.parent.Layout()

    def todoScreen(self):
        #
        # now the buttons for the to do list
        #
	self.taskprojtext = 'Task View   '
        #self.butnTaskProj = wx.Button(self.parent,-1,self.taskprojtext)
	#self.parent.Bind(wx.EVT_BUTTON, self.task_projbtn,self.butnTaskProj)
        labPeeps = wx.StaticText(self.parent,-1,"Person")
        self.fldPeeps = wx.Choice(self.parent,-1,(85,18),choices = self.people())
        self.parent.Bind(wx.EVT_CHOICE,self.peep_choice,self.fldPeeps)
        labClient = wx.StaticText(self.parent,-1,"Client")
        self.fldClient = wx.Choice(self.parent,-1,(85,18),choices = self.clients())
        self.parent.Bind(wx.EVT_CHOICE,self.client_choice,self.fldClient)        
        labProjs = wx.StaticText(self.parent,-1,"Projects")
        self.fldProjs = wx.Choice(self.parent,-1,(85,18),choices = self.tprojectlist)
        self.parent.Bind(wx.EVT_CHOICE,self.proj_choice,self.fldProjs)        
        labStatus = wx.StaticText(self.parent,-1,"Status <")
        self.fldStatus = wx.Choice(self.parent,-1,(85,18),choices = self.statuses())
        self.parent.Bind(wx.EVT_CHOICE,self.status_choice,self.fldStatus)        
        butnAddTask = wx.Button(self.parent, -1, "Add Task ")
        self.parent.Bind(wx.EVT_BUTTON,  self.addtask, butnAddTask)
        butnVwReport = wx.Button(self.parent, -1, "View Report ")
        self.parent.Bind(wx.EVT_BUTTON,  self.vwreport, butnVwReport)
        butnXLReport = wx.Button(self.parent, -1, "Excel Report ")
        self.parent.Bind(wx.EVT_BUTTON,  self.xlreport, butnXLReport)
        self.butnDue100 = wx.Button(self.parent, -1, "First Time?")
	self.butnDue100.SetLabel(self.butnduelabel)
        self.parent.Bind(wx.EVT_BUTTON,  self.due100, self.butnDue100)
#        butnNewProject = wx.Button(self.parent, -1, "Add Project ")
#        self.parent.Bind(wx.EVT_BUTTON,  self.addClientProject, butnNewProject)
        
        #
        # now put all the to do widgets in one box sizer
        self.todoBtns = wx.StaticBox (self.parent, -1, 'Tasks Manager')
        self.todoBtnSizer = wx.StaticBoxSizer (self.todoBtns, wx.HORIZONTAL)
        for thing in [labPeeps, self.fldPeeps, labClient, self.fldClient, labProjs, self.fldProjs, labStatus, 
                      self.fldStatus, butnAddTask, self.butnDue100, butnVwReport, butnXLReport]:
            self.todoBtnSizer.Add(thing, 0, wx.ALL, 5)
        self.print_selection()
        if self.person_ix > -1:
            self.fldPeeps.SetSelection(self.person_ix)
        else:
            self.fldPeeps.SetLabel(' ')
        if self.client_ix > -1:
            self.fldClient.SetSelection(self.client_ix)
        else:
            self.fldClient.SetLabel(' ')
        if self.project_ix > -1:
            self.fldProjs.SetSelection(self.project_ix)
        else:
            self.fldProjs.SetLabel(' ')
        if self.status_ix > -1:
            self.fldStatus.SetSelection(self.status_ix)
        else:
            self.fldStatus.SetLabel(' ')

    def addtask(self,event):
        if (self.tclient <> None) and (self.tproject <> None):
            self.tl.newTask(self.tclient,  self.tproject)
        else:
            rc = wx.MessageBox('Please select a client \nand a project before adding a task.' , 'Error Creating Tasks', wx.OK | wx.ICON_INFORMATION)

    def loadss(self, event):
        def comparekey(header,correct):
            if header <> correct:
                return 'Column heading ' + header + ' should be ' + correct +'\n'
            return ''

        dialog = wx.FileDialog(None, "Choose a file", os.getcwd(),"","",wx.OPEN)
        if dialog.ShowModal() == wx.ID_OK:
            ssfil = dialog.GetPath()
            msg = ''
            try:
                xl_data = readXLList(ssfil)
            except:
                msg = 'To load multiple tasks from a spreadsheet, I need to see\n \
a simple spreadsheet with columns titled:\nClient\nProject\nOwner\nResponsible\nDescription\nDue.\n\n\
There is an example at l:\warehouse\jokenacoloadproject.xlsx.\n \
See Phil if you want more explanation.'
            if not msg:
                headers = xl_data[0].keys()
                correct_keys = ['Client', 'Project', 'TaskId', 'Owner', 'Responsible', 'Description', 'Due']
                proper_keys = ['Client', 'pProject', 'tTaskId', 'pOwner', 'tResponsible', 'tDescription', 'tDue']
                while len(headers) < len(correct_keys): # this and the next statement make sure we deal with too long or short headers ok
                    headers.append('')
                while len(correct_keys) < len(headers):
                    correct_keys.append('')
                for h,c in zip(headers,correct_keys):
                    msg += comparekey(h,c)
            if not msg: # then we are ok
                for rownum, row in enumerate(xl_data):
                    if row['Project'] not in self.projects():
                        if row['Owner'] in self.people():
                            self.new_proj(row['Client'],row['Project'],row['Owner'])
                        else:
                            msg += 'Bad owner ' + row['Owner'] + ' in line ' + str(rownum) + '\n'
                    if row['Responsible'] not in self.people():
                        msg += 'Bad responsible person ' + row['Responsible'] + ' in line ' + str(rownum) + '\n'
                    try:
                        row['Due'].year
                    except:
                        msg += 'Bad due date ' + str(row['Due']) + ' in line ' + str(rownum) + '\n'
                    msg += self.new_task(row)
            if msg:
                dlg = sm(self.parent,
                         msg,
                         'Errors in input spreadsheet', 
                         pos=wx.wx.DefaultPosition,
                         size=(500,300))
                retcode = dlg.ShowModal()
                dlg.Destroy()
                self.td_conn.rollback()
            else:
                rc = wx.MessageBox(str(rownum+1)+' rows inserted.' , 'Loaded Tasks', wx.OK | wx.ICON_INFORMATION)                
                self.td_conn.commit()
        dialog.Destroy()

#    def new_proj(self, projid, projdesc, owner):
#        sql = 'insert into Projects (pclient, pproject, powner, pstatus) values (?,?,?,?);'
#        self.td_cur.execute(sql,(projid, projdesc, owner, '2 In Preparation'))

    def new_task(self, row):
        sql_check = 'select ttaskid from tasks where tclient = ? and tproject = ? and ttaskid = ?'
        self.td_cur.execute(sql_check,(row['Client'],row['Project'],row['TaskId']))
        if self.td_cur.fetchone(): # then something came back
            return 'Row present in task table for client {0}, project {1}, taskid {2}'.format(row['Client'],row['Project'],row['TaskId']) +'\n'
        else:
            sql = 'insert into tasks (tclient, tproject, ttaskid, tdescription, tdue, texpected, tresponsible, tstatus) values (?,?,?,?,?,?,?,?);'
            self.td_cur.execute(sql,(row['Client'],row['Project'],row['TaskId'],row['Description'],row['Due'],row['Due'],row['Responsible'], '1 Not Started'))
            return ''

#    def progress_rpt(self,event):
#        #msg = 'This function not developed yet.'
#        #rc = wx.MessageBox(msg, 'Progress Report', wx.OK | wx.ICON_INFORMATION)  
#        #pass
#        dialog = wx.FileDialog(None, "Choose a file", os.getcwd(),"","",wx.SAVE)
#        if dialog.ShowModal() == wx.ID_OK:
#            ssfil = dialog.GetPath()
#            msg = ''
#            heads = [i[0] + (i[1]).upper() + i[2:] for i in self.dt.cols] # capitalizes it in a sensible way
#            if self.tl.data:
#                ss_data = [OrderedDict((k,v) for k,v in zip(heads,[getattr(row,i) for i in self.dt.cols])) for row in self.tl.data]
 #           else:
#                msg = 'No rows in task list.\n The report function writes all the rows selected to a spreadsheet'
#            try:
#                writeXL(ssfil, ss_data)
#                msg = str(len(self.tl.data)) + ' rows written to ' + ssfil
#            except:
#                msg = 'Error writing rows to spreadsheet - probably permissions or something.  \nSee Phil!'
#            rc = wx.MessageBox(msg , 'Report', wx.OK | wx.ICON_INFORMATION) 
        
    def vwreport(self,event):
	# this assumes we are getting all projects of the type yyyiy actuarial Tasks
        #msg = 'Report view not yet programmed.'
        #rc = wx.MessageBox(msg, 'Error', wx.OK | wx.ICON_INFORMATION) 
        #width_in_mm = width*1.797-2.4
	html = self.reporthtml()
        width_in_px = 600 #width_in_mm * 3.814
        #height_in_mm = height * 8.675 - 2.697
        #height_in_mm = min([height_in_mm, 270])
        height_in_px = 300 #height_in_mm * 3.814
	title = 'Status Report on ' + date.today().strftime("%m-%d-%Y")
        frm = HTMLWindow(None, title, html, width_in_px, height_in_px)
        frm.Show()

    def reporthtml(self):
        clientcols = getColHeads('clients', cursor)[0]
	sql_client = 'select ' + ','.join(clientcols) + ' from clients'
	cursor.execute(sql_client)
	clients = cursor.fetchall()
	year = str(date.today().year)
	project = year + ' Actuarial Tasks'
	taskcols = getColHeads('tasks', cursor)[0]
	sql_tasks = "select " + ",".join(taskcols) + " from tasks where tproject = '{0}'".format(project)
	tasks = cursor.execute(sql_tasks).fetchall()
	# now we have the raw data let's make the tasks and data stores
	task_data = OrderedDict()
	for cli in clients:
	    task_data[cli.clientcode] = OrderedDict(zip(clientcols,cli))
	tskDict = {}
	for t in tasks:
	    tsk = Task(cc=None,user=None,tclient=t.tclient,tproject=t.tproject,taskdata=t)
	    tskDict[(t.tclient,t.tdescription)] = tsk
	task_order = ['8955-SSA','FundVal or Alloc','Acct Val BoY','Acct Val EoY','STMT','PBGC','5500','SAR/AFN','SB']
        output = HTML.Table(header_row = clientcols + task_order)
	for cli in clients:
	    row = list(cli)
	    for task in task_order:
	        if (cli.clientcode,task) in tskDict:
		    t = tskDict[(cli.clientcode, task)]
		    colour = t.colour()[0]
		    coloured_cell = HTML.TableCell(t.duedateout(), bgcolor = colour)
		    row.append(coloured_cell)
		else:
		    row.append('No data')
            output.rows.append(row)
	keys = t.return_constants()
	k = HTML.Table(header_row=['Key'])
	for key in keys:
	    cell = HTML.TableCell(key[1],bgcolor=key[0])
	    k.rows.append([cell])
	
	return str(k) + str(output)


    def xlreport (self, event):
	datestr = date.today().strftime("%m-%d-%Y")
        dlg = wx.FileDialog(
            self, message="Export html filename.", defaultDir="", 
            defaultFile="taskdata_"+datestr+".html", wildcard="*.html*", style=wx.SAVE
            )
        if dlg.ShowModal() == wx.ID_OK:
            self.htmlfileName = dlg.GetPath()
            outf = open(self.htmlfileName,'w')
            outf.write(self.reporthtml())
            outf.close()
        dlg.Destroy()
        msg = 'Excel File Created.'
        rc = wx.MessageBox(msg, 'Error', wx.OK | wx.ICON_INFORMATION)  

    def due100(self,event):
        if self.duein100:
	    self.duein100 = False
	    self.butnduelabel = 'Show All Relevant Tasks'
        else:
	    self.duein100 = True
	    self.butnduelabel = 'Tasks Due in 100 Days'
	self.butnDue100.SetLabel(self.butnduelabel)
	self.Refresh()
	self.getSelections()
	

    def print_selection(self):
        nothing = True # there's nihilism for you
        #print 'ixes client',self.client_ix, 'person',self.person_ix, 'project',self.project_ix, 'status',self.status_ix
        #print 'data client',self.tclient,'person',self.user,'project',self.tproject,'status',self.tstatus

    def getSelections(self):
        self.client_ix = self.fldClient.GetSelection()
        self.person_ix = self.fldPeeps.GetSelection()	
        self.project_ix = self.fldProjs.GetSelection()
        self.status_ix = self.fldStatus.GetSelection()
        # just a test
        #print 'client_ix', self.client_ix
        #print 'client string', self.fldClient.GetStringSelection()
        if self.client_ix > -1: 
            self.tclient = self.clients()[self.client_ix]
            if self.tclient == 'unselect':
                self.tclient = None
                self.client_ix = -1
        else:
            self.tclient = None

        if self.person_ix > -1:
            self.user = self.people()[self.person_ix]
            if self.user == 'unselect':
                self.user = None #os.environ['USERNAME']
                self.person_ix = -1	    
        else:
            self.user = self.userdefault

        if self.project_ix > -1:
            self.tproject = self.tprojectlist[self.project_ix]
            if self.tproject == 'unselect':
                self.tproject = None
                self.project_ix = -1
        else:
            self.tproject = None

        if self.status_ix > -1:
            self.tstatus = self.statuses()[self.status_ix]
            if self.tstatus == 'unselect':
                self.tstatus = None
                self.status_ix = -1
        else:
            self.tstatus = None
        self.tprojectlist = self.projects(self.tclient)
        self.tl.getTasks(tduein100 = self.duein100, tclient = self.tclient, tproject = self.tproject, tresponsible = self.user, tstatus = self.tstatus)
        self.fillTasks()

    def addClientProject(self, event):
        msg = 'For the time being, please give Phil a call if you would like to add a new client or project.'
        rc = wx.MessageBox(msg, 'New Client and Project', wx.OK | wx.ICON_INFORMATION)  


    def projects(self, client = None): # list of projects
        if client:
            self.td_cur.execute("select pProject from projects where pstatus < '6' and pclient = ?", (client,))
        else:
            self.td_cur.execute("select pProject from projects where pstatus < '6'")
        projects = self.td_cur.fetchall()
        return [p[0] for p in projects] + ['unselect']

    def people(self): # list of people
        self.td_cur.execute('select username from users order by username')
        return [i[0] for i in self.td_cur.fetchall()] + ['unselect']      

    def clients(self): # list of clients
        self.td_cur.execute("select clientcode from clients order by clientcode")
        clients = self.td_cur.fetchall()
        return [c[0] for c in clients] + ['unselect']

    def statuses(self): # list of status codes
        self.td_cur.execute('select sStatusDescription from Status')
        return [i[0] for i in self.td_cur.fetchall()] + ['unselect']

    def peep_choice(self,event):
        self.getSelections()

    def client_choice(self,event):
        self.getSelections()

    def proj_choice(self,event):
        self.getSelections()

    def status_choice(self,event):
        self.getSelections()

    def task_projbtn(self,event):
	if self.taskprojtext == 'Task View   ':
	    self.taskprojtext = 'Project View'
        else:
	    self.taskprojtext = 'Task View   '
	self.butnTaskProj.SetLabel(self.taskprojtext)

    def OnRightClick(self, event):
        if not hasattr(self,"popupId1"):
            self.popupId1 = wx.wx.NewId()
            self.popupId2 = wx.wx.NewId()
            self.popupId3 = wx.wx.NewId()
            self.popupId4 = wx.wx.NewId()
            self.popupId5 = wx.wx.NewId()
            self.popupId6 = wx.wx.NewId()  
            self.popupId7 = wx.wx.NewId() 
            self.popupId8 = wx.wx.NewId() 
            self.popupId9 = wx.wx.NewId()             
            self.popupId10 = wx.wx.NewId() 
            self.popupId11 = wx.wx.NewId() 
            self.popupId12 = wx.wx.NewId() 
            self.parent.Bind(wx.EVT_MENU, self.onPopUpOne, id = self.popupId1)
            self.parent.Bind(wx.EVT_MENU, self.onPopUpTwo, id = self.popupId2)            
            self.parent.Bind(wx.EVT_MENU, self.onPopUpThree, id = self.popupId3)
            self.parent.Bind(wx.EVT_MENU, self.onPopUpFour, id = self.popupId4)            
            self.parent.Bind(wx.EVT_MENU, self.onPopUpFive, id = self.popupId5)
            self.parent.Bind(wx.EVT_MENU, self.onPopUpSix, id = self.popupId6)            
            self.parent.Bind(wx.EVT_MENU, self.onPopUpSeven, id = self.popupId7) 
            self.parent.Bind(wx.EVT_MENU, self.onPopUpEight, id = self.popupId8)
            #self.parent.Bind(wx.EVT_MENU, self.onPopUpNine, id = self.popupId9)
            self.parent.Bind(wx.EVT_MENU, self.onPopUpTen, id = self.popupId10)
            self.parent.Bind(wx.EVT_MENU, self.onPopUpEleven, id = self.popupId11)
            self.parent.Bind(wx.EVT_MENU, self.onPopUpTwelve, id = self.popupId12)
            # now build the sub menu
            users = self.people()
            self.user_dick = OrderedDict()
            for u in users:
                user_id = wx.wx.NewId()
                self.user_dick[user_id] = u
                self.parent.Bind(wx.EVT_MENU, self.onPopUpUser, id = user_id)
        usermenu = wx.Menu() # menu of users to move responsibility around
        for userid, user in self.user_dick.iteritems():
            usermenu.Append(userid,user)        
        menu = wx.Menu()
        menu.Append(self.popupId1,"Change Status - 0 On Hold")
        menu.Append(self.popupId2,"Change Status - 1 Not Started")
        menu.Append(self.popupId3,"Change Status - 2 In Preparation")   
        menu.Append(self.popupId4,"Change Status - 3 Checking")           
        menu.Append(self.popupId5,"Change Status - 4 Edits")   
        menu.Append(self.popupId6,"Change Status - 5 In Review")   
        menu.Append(self.popupId7,"Change Status - 6 Complete")
        menu.Append(self.popupId8,"Change Status - 7 Cancelled")
        menu.AppendMenu(self.popupId9,"Reassign",usermenu)
        menu.Append(self.popupId10,"Add a week to completion date")  
        menu.Append(self.popupId11,"Update Comments")          
        menu.Append(self.popupId12,"Show History")   
        self.parent.PopupMenu(menu)
        menu.Destroy()        

    def popupStatusChange(self, new_status):
        old_status = self.task.tstatus
        self.task.tstatus = new_status
        self.TDlist.SetStringItem(self.task_ix,self.statuscol_ix,new_status)
        self.change_history(old_status, new_status, 'Tstatus')
        self.fillTasks()

    def onPopUpUser(self, event):
        new_doer = self.user_dick[event.Id]
        old_doer = self.task.tresponsible
        self.task.tresponsible = new_doer
        self.TDlist.SetStringItem(self.task_ix,self.responsiblecol_ix,new_doer)
        self.change_history(old_doer, new_doer, 'tResponsible')
        #self.fillTasks()

    def onPopUpOne(self,event):
        self.popupStatusChange('0 On Hold')

    def onPopUpTwo(self,event):
        self.popupStatusChange('1 Not Started')

    def onPopUpThree(self,event):
        self.popupStatusChange("2 In Preparation")

    def onPopUpFour(self,event):
        self.popupStatusChange("3 Checking")

    def onPopUpFive(self,event):
        self.popupStatusChange("4 Edits")

    def onPopUpSix(self,event):
        self.popupStatusChange("5 In Review")

    def onPopUpSeven(self,event):
        self.popupStatusChange("6 Complete")

    def onPopUpEight(self,event):
        self.popupStatusChange("7 Cancelled")

# onPopUpNine is just the submenu - see above

    def onPopUpTen(self,event):
        old_date = self.task.texpected
        if old_date:
            new_date = old_date + timedelta(7)
        else:
            new_date = datetime.now() + timedelta(7)
            new_date = new_date.date()
        self.task.texpected = new_date
        self.TDlist.SetStringItem(self.task_ix,self.expectedcol_ix,datetime.strftime(new_date,"%Y-%m-%d"))
        self.change_history(str(old_date), str(new_date), 'tExpected')
        self.fillTasks()

    def onPopUpEleven(self,event):
        if not self.task.tcomments:
            self.task.tcomment = ''
        dlg = wx.TextEntryDialog(self, 'Edit the text if needed','Comments',
                                 style=wx.TE_MULTILINE|wx.OK|wx.CANCEL)
        dlg.SetValue(unicode(self.task.tcomments))
        if dlg.ShowModal() == wx.ID_OK:
            new_comments = dlg.GetValue()
            self.task.tcomments = new_comments
            self.change_history(self.task.tcomments, new_comments, 'tComments', write_log = False)
            self.TDlist.SetStringItem(self.task_ix,self.commentscol_ix,new_comments)
        dlg.Destroy()

    def onPopUpTwelve(self, event):
        sql = 'select hWho, hWhen, haction from history where hclient = ? and hproject = ? and htaskid = ? order by hWhen'
        vals = (self.task.tclient, self.task.tproject, self.task.ttaskid)
        self.td_cur.execute(sql, vals)
        tasks = self.td_cur.fetchall()
        if tasks:
            tasktexts = [i[0] + ' at ' + datetime.strftime(i[1],"%Y-%m-%d %H:%M") + i[2] for i in tasks]
            history = '\n'.join(tasktexts)
        else:
            history = 'No history recorded'
        retcode = wx.MessageBox(history, "Information", wx.OK)

    def change_history(self, old_status, status, field, write_log = True):
        self.task.upd()
        if write_log:
            history_columns = ['hClient', 'hProject', 'hTaskid', 'hWho', 'hWhen', 'hAction']
            sql = sqlIns('history',history_columns)
            action = ' changed ' + str(field) + ' from ' + str(old_status) + ' to ' + str(status)
            ins_msg = dbinsert(sql,(self.task.tclient,
                                    self.task.tproject,
                                    self.task.ttaskid,
                                    self.userdefault,datetime.now(), 
                                    action),
                               self.cc)
            if ins_msg: # an error occurred
                retcode = wx.MessageBox(ins_msg, "Error", wx.OK)
            else:
                self.td_conn.commit()

    def setIndex(self,event):
        self.task_ix = event.GetIndex()
        self.task = self.tl.data[self.task_ix]

    def editTDFromList(self, event):
        self.task_ix = event.GetIndex()
        self.task = self.tl.data[self.task_ix]
        self.tl.editTask(self.task)

