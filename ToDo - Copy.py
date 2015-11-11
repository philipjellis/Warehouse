import wx
import wx.html
import os
from datetime import date, datetime, timedelta
from utilities import ConnString, getColHeads
from editscreen import EditRecord
import pyodbc
from rw_utilities import readXLList, writeXL
from collections import OrderedDict
from wx.lib.dialogs import ScrolledMessageDialog as sm

class AddTask(wx.Dialog):
    
    def __init__(self, parent, id):
        wx.Dialog.__init__(self, parent, id, pos=(100,100), title = 'Enter New Task')
        labels, controls = [],[]
        # Project 
        labels.append(wx.StaticText(self,-1,'Project'))
        controls.append(wx.Choice(self,-1,(85,18),choices = parent.projects))
        # Task Description
        labelse.append(wx.StaticText(self,-1,'Task Description'))
        controls.append(wx.TextCtrl(self, -1, value = "", size = (300,20)))
        # Due Date
        labels.append(wx.StaticText(self,-1,'Due Date'))
        controls.append(wx.GenericDatePickerCtrl(self, -1, size = (120,-1)))
        #Responsible
        labels.append(wx.StaticText(self,-1,'Responsible'))
        controls.append(wx.Choice(self,-1,(85,18),choices = parent.people))
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        label_sizer = wx.BoxSizer(wx.VERTICAL)
        control_sizer = wx.BoxSizer(wx.VERTICAL)        
        for l,c in zip(labels, controls):
            label_sizer.Add(l, 1, wx.ALIGN_LEFT|wx.ALL, 5)
            control_sizer.Add(c,1,wx.ALIGN_CENTER|wx.ALL, 5)
        sizer.Add(label_sizer)
        sizer.Add(control_sizer)
        self.SetSizer(sizer)
        sizer.Fit(self)
        

class ToDoManager(wx.Panel):
    
    def __init__(self, parent, IBPanel):
        self.parent = parent
        self.IBPanel = IBPanel
        wx.Panel.__init__(self, self.parent, -1)
        # set up the cursor to get at the to do lists
        self.td_conn = pyodbc.connect(ConnString(11))
        self.td_cur = self.td_conn.cursor()
        self.td_cols, self.td_typs = getColHeads('vw_all',self.td_cur)
        self.projectcol_ix = self.td_cols.index('tProject')
        self.taskcol_ix = self.td_cols.index('tTaskid') 
        self.clientcol_ix = self.td_cols.index('tClient')
        self.statuscol_ix = self.td_cols.index('tStatus')   
        self.responsiblecol_ix = self.td_cols.index('tResponsible')
        self.expectedcol_ix = self.td_cols.index('tExpected')
        self.progresscol_ix = self.td_cols.index('tProgress')
        self.user = os.environ['USERNAME']
    
    def getTasks(self, **fields):
        st = 'select ' + ','.join(self.td_cols) + ' from vw_all where '
        ks = [i + ' = ?' for i in fields.keys()]
        sql =  st + ' and '.join(ks) + ' order by Tdue;'
        self.td_cur.execute(sql,fields.values())
        tasks = self.td_cur.fetchall()
        return tasks

    def getTasksLT(self, **fields):
        st = 'select ' + ','.join(self.td_cols) + ' from vw_all where '
        ks = [i + ' < ?' for i in fields.keys()]
        sql =  st + ' and '.join(ks) + ' order by Tdue;'
        self.td_cur.execute(sql,fields.values())
        tasks = self.td_cur.fetchall()
        return tasks

    def fillTasks (self, tasks = None):
        self.IBPanel.doScreen() # clear old stuff out
        self.TodoBox = wx.BoxSizer(wx.VERTICAL)
        self.todoScreen()
        if tasks == None:
            self.tasks = self.getTasks(tresponsible = self.user)
        else:
            self.tasks = tasks
        # now build the list item
        self.TDlist = wx.ListCtrl(self.parent, -1, style = wx.LC_REPORT, size = (1600,400))
        for col, text in enumerate (self.td_cols) : self.TDlist.InsertColumn(col, text[1:]) # miss out the first char as it is just a table identifier
        for rownum,row in enumerate(self.tasks):
            index = self.TDlist.InsertStringItem(rownum+1, str(row[0]))
            for col, text in enumerate(row[1:]): self.TDlist.SetStringItem(index, col+1, str(text))
        for col, text in enumerate(self.td_cols): self.TDlist.SetColumnWidth(col, wx.LIST_AUTOSIZE_USEHEADER)
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
        self.fldProjs = wx.Choice(self.parent,-1,(85,18),choices = self.projects())
        self.parent.Bind(wx.EVT_CHOICE,self.proj_choice,self.fldProjs)        
        labStatus = wx.StaticText(self.parent,-1,"Status <")
        self.fldStatus = wx.Choice(self.parent,-1,(85,18),choices = self.status())
        self.parent.Bind(wx.EVT_CHOICE,self.status_choice,self.fldStatus)        
        butnAddTask = wx.Button(self.parent, -1, "Add Task ")
        self.parent.Bind(wx.EVT_BUTTON,  self.addtask, butnAddTask)
        butnLoadss = wx.Button(self.parent, -1, "Load Spreadsheet ")
        self.parent.Bind(wx.EVT_BUTTON,  self.loadss, butnLoadss)
        butnProgress = wx.Button(self.parent, -1, "Progress Report ")
        self.parent.Bind(wx.EVT_BUTTON,  self.progress, butnProgress)
        #
        # now put all the to do widgets in one box sizer
        self.todoBtns = wx.StaticBox (self.parent, -1, 'Tasks Manager')
        self.todoBtnSizer = wx.StaticBoxSizer (self.todoBtns, wx.HORIZONTAL)
        for thing in [labPeeps, self.fldPeeps, labClient, self.fldClient, labProjs, self.fldProjs, labStatus, 
                      self.fldStatus,butnAddTask,butnLoadss,butnProgress]:
            self.todoBtnSizer.Add(thing, 0, wx.ALL, 5)


    def addtask(self,event):
        pass
    
    def loadss(self, event):
        def comparekey(header,correct):
            if header <> correct:
                return 'Column heading ' + header + ' should be ' + correct +'\n'
            return ''
        
        dialog = wx.FileDialog(None, "Choose a file", os.getcwd(),"","",wx.OPEN)
        if dialog.ShowModal() == wx.ID_OK:
            ssfil = dialog.GetPath()
            xl_data = readXLList(ssfil)
            headers = xl_data[0].keys()
            correct_keys = ['Client', 'Project' 'TaskId', 'Owner', 'Responsible', 'Description', 'Due']
            proper_keys = ['Client', 'pProject' 'tTaskId', 'pOwner', 'tResponsible', 'tDescription', 'tDue']
            msg = ''
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
                    if not msg: #still ok
                        self.new_task(row)
            if msg:
                print msg
                dlg = sm(self.parent,
                            msg,
                            'Errors in input spreadsheet', 
                            pos=wx.wx.DefaultPosition,
                            size=(500,300))
                retcode = dlg.ShowModal()
                dlg.Destroy()
        dialog.Destroy()
            
    def new_proj(self, projid, projdesc, owner):
        sql = 'insert into Projects (pclient, pproject, powner, pstatus) values (?,?,?);'
        self.td_cur.execute(sql,(projid,owner, projdesc, '2 In Progress'))
        
    def new_task(self, row):
        sql = 'insert into tasks (tclient, tproject, ttaskid, tdescription, tdue, tresponsible) values (?,?,?,?);'
        self.td_cur.execute(sql,(row['Client'],row['Project'],row['TaskId'],row['Description'],row['Due'],row['Responsible']))
        
    def progress(self,event):
        pass
    
    def people(self): # list of people
        self.td_cur.execute('select username from users order by username')
        return [i[0] for i in self.td_cur.fetchall()]
    
    def peep_choice(self,event):
        person_ix = self.fldPeeps.GetSelection()
        person = self.people()[person_ix]
        tasks = self.getTasks(tresponsible = person)
        self.fillTasks(tasks)
        self.fldPeeps.SetSelection(person_ix)

    def projects(self): # list of projects
        self.td_cur.execute("select pProject from projects where pstatus < '6'")
        projects = self.td_cur.fetchall()
        return [p[0] for p in projects]

    def clients(self): # list of clients
        self.td_cur.execute("select clientcode from clients order by clientcode")
        clients = self.td_cur.fetchall()
        return [c[0] for c in clients]
    
    def client_choice(self,event):
        client_ix = self.fldClient.GetSelection()
        client = self.clients()[client_ix]
        tasks = self.getTasks(tclient = client)
        self.fillTasks(tasks)
        self.fldClient.SetSelection(client_ix)
    
    def proj_choice(self,event):
        client_ix = self.fldClient.GetSelection()
        print client_ix
        project_ix = self.fldProjs.GetSelection()
        project = self.projects()[project_ix]
        tasks = self.getTasks(tproject = project)
        self.fillTasks(tasks)
        self.fldProjs.SetSelection(project_ix)
            
    def status(self): # list of status codes
        self.td_cur.execute('select StatusDescription from Status')
        return [i[0] for i in self.td_cur.fetchall()]
        
    def status_choice(self,event):
        status_ix = self.fldStatus.GetSelection()
        status = self.status()[status_ix]
        tasks = self.getTasksLT(tstatus = status)
        self.fillTasks(tasks)
        self.fldStatus.SetSelection(status_ix)
         
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
                self.TDlist.Bind(wx.EVT_MENU, self.onPopUpUser, id = user_id)
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
        
    def getTaskDetails(self, task):
        self.client = task[self.clientcol_ix]
        self.project = task[self.projectcol_ix]
        self.task = task[self.taskcol_ix]
        self.status = task[self.statuscol_ix]
        self.responsible = task[self.responsiblecol_ix]
        self.expected = task[self.expectedcol_ix]
        self.progress = task[self.progresscol_ix]
        
    def popupStatusChange(self, new_status):
        task_item = self.tasks[self.task_ix]
        self.getTaskDetails(task_item)
        old_status = self.status
        task_item[self.statuscol_ix] = new_status
        self.TDlist.SetStringItem(self.task_ix,self.statuscol_ix,new_status)
        self.change_history(old_status, new_status, 'Tstatus')
        
    def onPopUpUser(self, event):
        print 'doing doer'
        new_doer = self.user_dick[event.Id]
        task_item = self.tasks[self.task_ix]
        self.getTaskDetails(task_item)
        old_doer = self.responsible
        task_item[self.responsiblecol_ix] = new_doer
        self.TDlist.SetStringItem(self.task_ix,self.responsiblecol_ix,new_doer)
        self.change_history(old_doer, new_doer, 'tResponsible')
        
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
        task_item = self.tasks[self.task_ix]
        self.getTaskDetails(task_item)
        old_date = self.expected
        if old_date:
            new_date = old_date + timedelta(7)
        else:
            new_date = datetime.now() + timedelta(7)
            new_date = new_date.date()
        task_item[self.expectedcol_ix] = new_date
        self.TDlist.SetStringItem(self.task_ix,self.expectedcol_ix,datetime.strftime(new_date,"%Y-%m-%d"))
        self.change_history(str(old_date), str(new_date), 'tExpected',)


    def onPopUpNine(self,event):
        task_item = self.tasks[self.task_ix]
        self.getTaskDetails(task_item)
        if not self.progress:
            progress = ''
        dlg = wx.TextEntryDialog(self, 'Edit the text if needed','Progress Report')
        dlg.SetValue(progress)
        if dlg.ShowModal() == wx.ID_OK:
            new_progress = dlg.GetValue()
            self.change_history(progress, new_progress, 'tProgress', write_log = False)
        dlg.Destroy()

    def onPopUpTen(self, event):
        task_item = self.tasks[self.task_ix]
        self.getTaskDetails(task_item)
        sql = 'select hWho, hWhen, haction from history where hclient = ? and hproject = ? and htaskid = ? order by hWhen'
        self.td_cur.execute(sql, (self.client, self.project, self.task))
        tasks = self.td_cur.fetchall()
        if tasks:
            tasktexts = [i[0] + ' at ' + datetime.strftime(i[1],"%Y-%m-%d %H:%M") + i[2] for i in tasks]
            history = '\n'.join(tasktexts)
        else:
            history = 'No history recorded'
        retcode = wx.MessageBox(history, "Information", wx.OK)

    def change_history(self, old_status, status, field, write_log = True):
        sql = 'update tasks set {0} = ? where tclient = ? and tproject = ? and tTaskId = ?'
        sql = sql.format(field)
        self.td_cur.execute(sql,(status, self.client, self.project, self.task))
        if write_log:
            sql = 'insert into history (hClient, hProject, hTaskid, hWho, hWhen, hAction) values (?,?,?,?,?,?)'
            who = self.user
            when = datetime.now()
            action = ' changed ' + str(field) + ' from ' + str(old_status) + ' to ' + status
            self.td_cur.execute(sql,(self.client, self.project, self.task, who, when, action))
        self.td_conn.commit()

    def setIndex(self,event):
        self.task_ix = event.GetIndex()

    def editTDFromList(self, event):
        #ix = event.GetIndex()
        #social = self.data[ix].socsec
        #self.EditFlag=True
        #newEditScreen = EditRecord (self, -1, 'tbIbctrl', self.EditFlag, social)
        #newEditScreen.ShowModal()
        #newEditScreen.Destroy()
        #self.getAndShowIBs()
        pass
        
