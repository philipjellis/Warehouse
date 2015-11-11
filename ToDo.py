import wx
import wx.html
import  wx.lib.masked as masked
import os
from datetime import date, datetime, timedelta
from utilities import ConnString, getColHeads
from editscreen import EditRecord
import pyodbc
from rw_utilities import readXLList, writeXL
from collections import OrderedDict
from wx.lib.dialogs import ScrolledMessageDialog as sm

#utilities
class CursorConnection (object):
    pass

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
        d = datetime.now().date()
    tt = d.timetuple()
    dmy = (tt[2], tt[1]-1, tt[0])
    return wx.DateTimeFromDMY(*dmy)

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
            self.control = wx.GenericDatePickerCtrl(parent, -1, size = (120,-1))
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
            self.control.SetValue(self.data)        
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
                     'tdue','tstarted','texpected','tprogress','tstatus']
        self.keycols = ['tclient','tproject','ttaskid']
        self.datacols = ['tdescription','tresponsible','tdue','tstarted','texpected','tprogress','tstatus']
        self.tasktablecols = self.keycols + self.datacols
        self.heads =[i[1:].title() for i in self.cols]
        self.cc = cc
        self.user = user
        if taskdata:
            for i in self.cols:
                setattr(self,i,getattr(taskdata,i))
        else:
            self.create(tclient, tproject)

    def create(self, tclient, tproject):
        for i in self.cols:
            setattr(self,i,None)
        self.tdue = datetime.now().date()
        self.texpected = datetime.now().date()
        self.tclient = tclient
        self.tproject = tproject
        self.ttaskid = self.max_task()
        self.tstatus = '1 Not Started'

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
        print'old data', self.old_data
        
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
            print 'nothing changed'

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
        self.widgets['tprogress'] = Widget(self,'Progress','t',dataval = t.tprogress)        
        self.widgets['tstatus'] = Widget(self,'Status','c',choices = sts, dataval = t.tstatus)        		
        # buttons
        save = wx.Button(self,wx.ID_OK)
        save.SetDefault()
        cancel = wx.Button(self,wx.ID_CANCEL)

        sizer = wx.BoxSizer(wx.VERTICAL)
        fgs = wx.FlexGridSizer(10,2,5,5)
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
        self.userdefault = os.environ['USERNAME']        
        self.dt = Task(self.cc, self.userdefault, tclient = self.tclient, tproject = self.tproject) # dummy task for col names etc
        self.columns = self.dt.cols
        self.projectcol_ix = self.columns.index('tproject')
        self.taskcol_ix = self.columns.index('ttaskid') 
        self.clientcol_ix = self.columns.index('tclient')
        self.statuscol_ix = self.columns.index('tstatus')   
        self.responsiblecol_ix = self.columns.index('tresponsible')
        self.expectedcol_ix = self.columns.index('texpected')
        self.progresscol_ix = self.columns.index('tprogress')
        self.startedcol_ix = self.columns.index('tstarted')
        self.duecol_ix = self.columns.index('tdue')
        self.descriptioncol_ix = self.columns.index('tdescription')
        self.ownercol_ix = self.columns.index('powner')
        self.user = os.environ['USERNAME']
        self.person_ix = self.people().index(self.userdefault)
        self.tl = TaskList(self)
        self.tl.getTasks(tresponsible=self.user)
        self.client_ix,self.project_ix, self.status_ix = -1,-1,-1
        self.fillTasks()

    def fillTasks (self):
        self.IBPanel.doScreen() # clear old stuff out
        self.TodoBox = wx.BoxSizer(wx.VERTICAL)
        self.todoScreen()
        # now build the list item
        self.TDlist = wx.ListCtrl(self.parent, -1, style = wx.LC_REPORT, size = (1600,400))
        first_col = self.dt.cols[0]
        for col, text in enumerate (self.dt.heads) : 
            self.TDlist.InsertColumn(col, text) 
        for rownum,task in enumerate(self.tl.data):
            index = self.TDlist.InsertStringItem(rownum+1, str(getattr(task,first_col)))
            for colnum, col in enumerate(self.dt.cols[1:]): 
                self.TDlist.SetStringItem(index, colnum+1, str(getattr(task,col)))
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
        butnLoadss = wx.Button(self.parent, -1, "Load Spreadsheet ")
        self.parent.Bind(wx.EVT_BUTTON,  self.loadss, butnLoadss)
        butnProgress = wx.Button(self.parent, -1, "Progress Report ")
        self.parent.Bind(wx.EVT_BUTTON,  self.progress_rpt, butnProgress)
        butnNewClient = wx.Button(self.parent, -1, "Add Client ")
        self.parent.Bind(wx.EVT_BUTTON,  self.addClientProject, butnNewClient)
        butnNewProject = wx.Button(self.parent, -1, "Add Project ")
        self.parent.Bind(wx.EVT_BUTTON,  self.addClientProject, butnNewProject)
        
        #
        # now put all the to do widgets in one box sizer
        self.todoBtns = wx.StaticBox (self.parent, -1, 'Tasks Manager')
        self.todoBtnSizer = wx.StaticBoxSizer (self.todoBtns, wx.HORIZONTAL)
        for thing in [labPeeps, self.fldPeeps, labClient, self.fldClient, labProjs, self.fldProjs, labStatus, 
                      self.fldStatus,butnAddTask,butnLoadss,butnProgress, butnNewClient, butnNewProject]:
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

    def new_proj(self, projid, projdesc, owner):
        sql = 'insert into Projects (pclient, pproject, powner, pstatus) values (?,?,?,?);'
        self.td_cur.execute(sql,(projid, projdesc, owner, '2 In Progress'))

    def new_task(self, row):
        sql_check = 'select ttaskid from tasks where tclient = ? and tproject = ? and ttaskid = ?'
        self.td_cur.execute(sql_check,(row['Client'],row['Project'],row['TaskId']))
        if self.td_cur.fetchone(): # then something came back
            return 'Row present in task table for client {0}, project {1}, taskid {2}'.format(row['Client'],row['Project'],row['TaskId']) +'\n'
        else:
            sql = 'insert into tasks (tclient, tproject, ttaskid, tdescription, tdue, texpected, tresponsible, tstatus) values (?,?,?,?,?,?,?,?);'
            self.td_cur.execute(sql,(row['Client'],row['Project'],row['TaskId'],row['Description'],row['Due'],row['Due'],row['Responsible'], '1 Not Started'))
            return ''

    def progress_rpt(self,event):
        #msg = 'This function not developed yet.'
        #rc = wx.MessageBox(msg, 'Progress Report', wx.OK | wx.ICON_INFORMATION)  
        #pass
        dialog = wx.FileDialog(None, "Choose a file", os.getcwd(),"","",wx.SAVE)
        if dialog.ShowModal() == wx.ID_OK:
            ssfil = dialog.GetPath()
            msg = ''
            heads = [i[0] + (i[1]).upper() + i[2:] for i in self.dt.cols] # capitalizes it in a sensible way
            if self.tl.data:
                ss_data = [OrderedDict((k,v) for k,v in zip(heads,[getattr(row,i) for i in self.dt.cols])) for row in self.tl.data]
            else:
                msg = 'No rows in task list.\n The report function writes all the rows selected to a spreadsheet'
            try:
                writeXL(ssfil, ss_data)
                msg = str(len(self.tl.data)) + ' rows written to ' + ssfil
            except:
                msg = 'Error writing rows to spreadsheet - probably permissions or something.  \nSee Phil!'
            rc = wx.MessageBox(msg , 'Report', wx.OK | wx.ICON_INFORMATION) 
        
        

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
        self.tl.getTasks(tclient = self.tclient, tproject = self.tproject, tresponsible = self.user, tstatus = self.tstatus)
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
        self.td_cur.execute('select StatusDescription from Status')
        return [i[0] for i in self.td_cur.fetchall()] + ['unselect']

    def peep_choice(self,event):
        self.getSelections()

    def client_choice(self,event):
        self.getSelections()

    def proj_choice(self,event):
        self.getSelections()

    def status_choice(self,event):
        self.getSelections()

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
            self.parent.Bind(wx.EVT_MENU, self.onPopUpOne, id = self.popupId1)
            self.parent.Bind(wx.EVT_MENU, self.onPopUpTwo, id = self.popupId2)            
            self.parent.Bind(wx.EVT_MENU, self.onPopUpThree, id = self.popupId3)
            self.parent.Bind(wx.EVT_MENU, self.onPopUpFour, id = self.popupId4)            
            self.parent.Bind(wx.EVT_MENU, self.onPopUpFive, id = self.popupId5)
            self.parent.Bind(wx.EVT_MENU, self.onPopUpSix, id = self.popupId6)            
            #self.parent.Bind(wx.EVT_MENU, self.onPopUpSeven, id = self.popupId7)
            self.parent.Bind(wx.EVT_MENU, self.onPopUpEight, id = self.popupId8)
            self.parent.Bind(wx.EVT_MENU, self.onPopUpNine, id = self.popupId9)
            self.parent.Bind(wx.EVT_MENU, self.onPopUpTen, id = self.popupId10)
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
        menu.Append(self.popupId1,"Change Status - 1 Not Started")
        menu.Append(self.popupId2,"Change Status - 2 In Progress")   
        menu.Append(self.popupId3,"Change Status - 3 In Checking")           
        menu.Append(self.popupId4,"Change Status - 4 In Rework")   
        menu.Append(self.popupId5,"Change Status - 5 Complete")   
        menu.Append(self.popupId6,"Change Status - 6 Cancelled")
        menu.AppendMenu(self.popupId7,"Reassign",usermenu)
        menu.Append(self.popupId8,"Add a week to completion date")  
        menu.Append(self.popupId9,"Update progress and issues")          
        menu.Append(self.popupId10,"Show History")   
        self.parent.PopupMenu(menu)
        menu.Destroy()        

    def popupStatusChange(self, new_status):
        old_status = self.task.tstatus
        self.task.tstatus = new_status
        self.TDlist.SetStringItem(self.task_ix,self.statuscol_ix,new_status)
        self.change_history(old_status, new_status, 'Tstatus')

    def onPopUpUser(self, event):
        new_doer = self.user_dick[event.Id]
        old_doer = self.task.tresponsible
        self.task.tresponsible = new_doer
        self.TDlist.SetStringItem(self.task_ix,self.responsiblecol_ix,new_doer)
        self.change_history(old_doer, new_doer, 'tResponsible')
        #self.fillTasks()

    def onPopUpOne(self,event):
        self.popupStatusChange('1 Not Started')

    def onPopUpTwo(self,event):
        self.popupStatusChange("2 In Progress")

    def onPopUpThree(self,event):
        self.popupStatusChange("3 In Checking")

    def onPopUpFour(self,event):
        self.popupStatusChange("4 In Rework")

    def onPopUpFive(self,event):
        self.popupStatusChange("5 Complete")

    def onPopUpSix(self,event):
        self.popupStatusChange("6 Cancelled")

    # onPopUpSeven is just the submenu - see above

    def onPopUpEight(self,event):
        old_date = self.task.texpected
        if old_date:
            new_date = old_date + timedelta(7)
        else:
            new_date = datetime.now() + timedelta(7)
            new_date = new_date.date()
        self.task.texpected = new_date
        self.TDlist.SetStringItem(self.task_ix,self.expectedcol_ix,datetime.strftime(new_date,"%Y-%m-%d"))
        self.change_history(str(old_date), str(new_date), 'tExpected')

    def onPopUpNine(self,event):
        if not self.task.tprogress:
            self.task.tprogress = ''
        dlg = wx.TextEntryDialog(self, 'Edit the text if needed','Progress Report',
                                 style=wx.TE_MULTILINE|wx.OK|wx.CANCEL)
        dlg.SetValue(self.task.tprogress)
        if dlg.ShowModal() == wx.ID_OK:
            new_progress = dlg.GetValue()
            self.task.tprogress = new_progress
            self.change_history(self.task.tprogress, new_progress, 'tProgress', write_log = False)
            self.TDlist.SetStringItem(self.task_ix,self.progresscol_ix,new_progress)
        dlg.Destroy()

    def onPopUpTen(self, event):
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

