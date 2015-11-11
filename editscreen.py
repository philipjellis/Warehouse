# This contains classes and helper functions to prepare the general edit screen
# used on page 1 and page 2
import wx
from wx.lib import masked
from utilities import *
from collections import namedtuple

class userChooser(wx.Dialog):
	""" 
	Allows the user to choose from several records when several are returned.  eg if a person has 3 IB Control records
	This will display details about them and let the user choose the one she wants.
	"""
	def __init__(self, heads, data):
		wx.Dialog.__init__(self,None,-1,'Please select the record you want to edit', size=(600,500))
		self.list=wx.ListCtrl(self,wx.ID_OK,style=wx.LC_REPORT, size=(500,400))
		for col,text in enumerate(heads):
			self.list.InsertColumn(col, text)
		for row in data:
			index = self.list.InsertStringItem(sys.maxint, row[0])
			for col, text in enumerate(row[1:]):
				self.list.SetStringItem(index,col+1,text)
		self.list.SetColumnWidth(0,wx.LIST_AUTOSIZE_USEHEADER)
		self.list.SetColumnWidth(1,wx.LIST_AUTOSIZE)
		self.list.SetColumnWidth(2,wx.LIST_AUTOSIZE)
		self.list.SetColumnWidth(3,wx.LIST_AUTOSIZE)
		self.list.SetColumnWidth(4,wx.LIST_AUTOSIZE)
		self.list.SetItemState(0, wx.LIST_STATE_SELECTED, wx.LIST_STATE_SELECTED)
		okButton = wx.Button(self,wx.ID_OK, "OK", pos=(15,15))
		okButton.SetDefault()
		cancelButton = wx.Button(self,wx.ID_CANCEL, "Cancel", pos=(115,15))
		self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.Clicked, self.list)
		szr1 = wx.BoxSizer(wx.HORIZONTAL)
		szr1.Add(okButton)
		szr1.Add(cancelButton)
		szr2 = wx.BoxSizer(wx.VERTICAL)
		szr2.Add(self.list)
		szr2.Add(szr1)
		self.SetSizerAndFit(szr2)
		self.ix = 0

	def Clicked(self, event):
		self.ix = event.GetIndex()

class ColData:
	def __init__ (self, Position, Type, Length, Name):
		self.type = Type
		self.length = Length
		if self.length > 50: self.length = 50
		if self.type in ['int','smallint','decimal','money','tinyint']:
			self.value = 0
		elif self.type in ['char', 'varchar','nchar']:
			self.value = ''
		elif self.type in ['date']:
			self.value = None
		else:
			self.value = None
		self.control = None
		self.name = Name
		self.label = ''
		self.id = wx.NewId() # id needed for date and number handling

	def showMe(self):
		strin =  'Name:{0:20}'.format(self.name)
		strin += ' Type:{0:10}'.format(self.type)
		strin += ' Length:{0:10}'.format(self.length)
		strin += ' Value:{0:10}'.format(self.value)
		#strin += ' Label:{0:10}'.format(self.label)
		strin += ' Id:{0:10}'.format(self.id)
		return strin+'\n'
		
	def setLabel(self, EditScreen):
		self.label = None
		labtext = self.name
		if self.type == 'money': labtext += '$'
		self.label = wx.StaticText(EditScreen,-1,labtext)
			
	def setControl(self, EditScreen): #Edit Screen is the calling screen - adds links and event handling back into the Edit Screen
		self.control =None
		if self.type in ['int','smallint', 'tinyint']:
			self.control = masked.NumCtrl(EditScreen, -1, self.value,integerWidth=7, fractionWidth=0, allowNone = True)
		elif self.type in ['char', 'varchar', 'nchar']:
			wid = 8*self.length
			if wid < 40:
				wid = 40
			sz=(wid,-1)
			self.control = wx.TextCtrl(EditScreen,-1,str(self.value),size = sz)
		elif self.type == 'date':
			self.control = wx.GenericDatePickerCtrl(EditScreen,self.id, size=(120,-1), 
		        style = wx.DP_DROPDOWN | wx.DP_SHOWCENTURY | wx.DP_ALLOWNONE | wx.TAB_TRAVERSAL)
			self.control.SetValue(EditScreen.FormatWXDate(self.value))
			EditScreen.Bind(wx.EVT_DATE_CHANGED, EditScreen.DtChg, self.control)
		elif self.type in ['money', 'decimal']:
			if self.value <> None:
				floaty = float(self.value)
			else:
				floaty = float(0.00)
			if self.type == 'money':
				fwidth = 2
			else:
				fwidth = 4
			self.control = masked.NumCtrl(EditScreen, self.id, floaty, integerWidth=9, fractionWidth=fwidth)
			EditScreen.Bind(masked.EVT_NUM, EditScreen.NumChg, self.control)      
		if self.name in EditScreen.Rec.SF.noEdit:
			self.control.Enable(False)
		if self.name == 'ER' and self.name not in EditScreen.Rec.SF.key: # these next two pieces just set up things for the IB Control record
			self.control.Destroy()
			self.control = wx.Choice(EditScreen,self.id,(185,18),choices=EditScreen.ERKeys)
			if (self.value <> '') and (self.value <> None): 
				try:
					ERix = EditScreen.Employers.index(self.value)
				except:
					pass 
				else:
					EmpKey = EditScreen.ERKeys[ERix]
					EditScreen.ER = EditScreen.ERs[ERix]
					EditScreen.Employer = EditScreen.Employers[ERix]
					EditScreen.Plans = PlanList(EditScreen.ER)
					self.control.SetStringSelection(EmpKey)
			EditScreen.Bind(wx.EVT_CHOICE, EditScreen.ERChosen, self.control)
		if self.name == 'EmployerPlan':
			#self.Plans = PlanList(EditScreen.ER)
			self.control.Destroy()
			self.control = wx.Choice(EditScreen,self.id,(250,18),choices=EditScreen.Plans)
			if (self.value <> '') and (self.value <> None): 
				self.control.SetStringSelection(self.value)

class SchemaData:
	def __init__ (self, table, filledOnly, keyData):
		self.SF = specialFields(table)
		self.table = table
		cnxn = accP2()
		cursor = cnxn.cursor()
		sql = """select column_name, ordinal_position, data_type,
character_maximum_length from information_schema.columns where table_name
= '{0}'"""
		sql=sql.format(table)
		cursor.execute(sql)
		results = cursor.fetchall()
		#if self.display is False (this is set in the MetaData table) then
		#  -  The control and label will not be created, and nothing will be shown on the screen
		#  -  Nothing will be done in any insert or update statement
		#  So if this field is False, the field is untouchable (unless you delete the whole record of course)
		for num, row in enumerate(results):
			if row[0] in self.SF.noDisplay: results.pop(num)
		
		self.colNames = [i[0] for i in results]
		if filledOnly: #this just gets columns with actual data in - employee table
			# will have lots of blank columns for any given employer
			tempDick = dict(zip(self.colNames,results))
			memberKey = Snapshots[table]
			colsNeeded = []
			sql = 'select '+','.join(self.colNames) + ' from ' + table + ' join tbmember on mId =  ' + memberKey
			sql += ' where '+ memberKey + ' in (select mid from tbMember  where mNId = (select mNid from tbMember where mid = ?))'
			cursor.execute(sql,(keyData,))
			bigData = cursor.fetchall()
			for ix, name in enumerate(self.colNames):
				# this added 17 Jan 2012 PJE....  this allows possibly empty but useful fields such as AccountType to be forced to appear
				if name in self.SF.helper:
					colsNeeded.append(name)
				else:
					datCol = [row[ix] for row in bigData]
					if set(datCol) - EmptSet <> set([]) :  # if not all rows in that column are blanks then we need that row
						colsNeeded.append(name)
			self.colNames = colsNeeded
			results = [tempDick[i] for i in self.colNames] # just pick out the results rows we need
		colD = namedtuple('colD',self.colNames)
		self.columnData = colD(*[ColData(i[1],i[2],i[3],i[0]) for i in results])
		cnxn.close()
			
	def showMe(self):
		strin='colNames'+str(self.colNames)+'\n'
		for col in self.columnData:
			strin+=col.showMe()
		return strin

	def getPlanName(self,planID):
		cnxn = accP2()
		cursor = cnxn.cursor()
		sql = 'select nShortPlanName from tbPlan where nId = ?'
		cursor.execute(sql,(planID,))
		return cursor.fetchone()[0]
	
	def getRec (self, table, key):
		cnxn = accP2()
		cursor = cnxn.cursor()
		sql = 'select '+', '.join(self.colNames)
		keyCol = self.SF.key[0] # this is from the MetaData table and is the col we use to get records
		sql2 = " from {0} where {1} = ?".format(table, keyCol)
		datTuple = (key,)
		sql+=sql2
		try:
			cursor.execute(sql,datTuple)
			DBData = cursor.fetchall()
		except:
			DBData = []
		cnxn.close()
		msgPart = " is not in the "+self.SF.tableName[0]+" table.\nPlease enter new data in the following screen."
		Data=[]
		if len(DBData) == 0:
			error = wx.MessageDialog(None,keyCol+' '+str(key)+' '+msgPart,'Cannot edit data', wx.OK)
			error.ShowModal()
			error.Destroy()
			self.edit = False
			tempColData = getattr(self.columnData,keyCol)
			tempColData.value = key
		elif len(DBData) == 1:
			Data = DBData[0]
		else: # more than 1 row returned
			choices = []
			for row in DBData:
				rowdata=[]
				for field in self.SF.helper:
					ix = self.colNames.index(field)
					dataVal = row[ix] # this is the value from the database
					# next does a lookup for planId to get the plan Name, add more to this if more lookups needed for future tables
					if field == 'mNId': dataVal = self.getPlanName(dataVal) 
					rowdata.append(str(dataVal))
				choices.append(rowdata)
			dialog=userChooser(self.SF.helper,choices)
			choice = dialog.ShowModal()
			if choice == wx.ID_OK:
				Data = DBData[dialog.ix]
			else:
				Data = DBData[dialog.ix]
			dialog.Destroy()
		if Data <> []:
			for col, dat in zip(self.columnData,Data):
				col.value = dat 

	def saveRec (self):
		cols=self.colNames
		data=[i.value for i in self.columnData]
		keys = self.SF.trueKey
		cnxn = accP2()
		cursor = cnxn.cursor()
		if self.edit:
			for k in keys:
				if k in cols: # worth checking as it can get deleted the previous time through - eg if you click and have to correct something
					ix = cols.index(k)
					cols.pop(ix)
					data.pop(ix)
			columns = ' = ?, '.join(cols)
			columns += ' = ? '
			keysql = '= ? AND '.join(keys)
			keyvals=[getattr(self.columnData,k).value for k in keys]
			keysql += '=?'
			sql = 'update {0} set '.format(self.SF.table[0])
			sql += columns + ' where ' + keysql
			valtuple = data + keyvals
		else:
			for k in self.SF.noInsert:
				if k in cols: # see comment above...
					ix = cols.index(k)
					cols.pop(ix)
					data.pop(ix)
			columns = ', '.join(cols)
			qs = ','.join(['?']*len(cols))
			sql = 'insert into {0} ('.format(self.SF.table[0])
			sql += columns+') values ('+qs+')'
			valtuple = data
		err = False
		msg = """I got an error when I tried to put your data into the {0} table.  Please \
    contact the technology team with this SQL. """.format(self.SF.tableName[0])
		rows = 0
		try:
			rows = cursor.execute(sql,valtuple).rowcount
			cnxn.commit()
		except:
			err = True
		if not err and rows <> 1:
			err = True
			msg = 'rowcount =' + str(rows) ++ msg
			msg += ' check invalid rowcount'			
		if err: 
			msg+='\nSql='+sql+'\nValues='+str(valtuple)
		else:
			msg=''
		cnxn.close()
		return msg

def specialFields(table):
	#fieldTypes = namedtuple('fieldTypes','key helper noDisplay noEdit tableName table needText noInsert')
	#key - not obvious - the key used to select a row in the edit screen - ie SSN for tbPerson (not pId the real key)
	#helper - these are fields displayed to the user when we are asking them to choose between several rows
	#noDisplay - not displayed on screen
	#noEdit - uneditable on screen
	#tableName - title for use in screen panels and messages
	#table - used for constructing queries - the real table name
	#needText - fields that will be checked for non-blank values.  Error message returned if any are blank.
	#noInsert - fields that should not be part of an insert/update statement - eg autoIncrement fields will fail
	#trueKey - this is the key, use this for insert and update statements 

	def splt(strin): #  function to return lists from strings, allowing sensibly for NULL value
		try:
			return strin.split()
		except:
			return []

	cnxn = accP2()
	cursor = cnxn.cursor()
	fldTypes = 'key helper noDisplay noEdit tableName table needText noInsert trueKey'.split()
	colNames = ['MD_'+i for i in fldTypes]
	fieldTypes = namedtuple('fieldTypes',fldTypes)
	sql = 'select '+', '.join(colNames)+' from tbMetaData'
	cursor.execute(sql)
	data=cursor.fetchall()
	cnxn.close()
	tableData = [fieldTypes(*[splt(j) for j in i]) for i in data]
	for i in range(len(tableData)) :
		tabln = tableData[i].tableName[0].replace('_',' ')
		tabln = [tabln]
		tableData[i] = tableData[i]._replace(tableName = tabln)
	MetaData = dict(zip([i.table[0] for i in tableData],tableData))
	if table == 'All': return MetaData        
	return (MetaData[table])

def checkTextEntered(text,field):
	if text <> None:
		return ''
	else:
		return 'You must enter something in the {0} field. \n'.format(field)

def ERNamesKeys(): 
	cnxn = accP2()
	cursor = cnxn.cursor()
	sql = 'select rTla, rName from tbEmployer'
	sqlwhereIB = ' where rIBctrlFlag = 1 '
	sqlwhereEE = ' where rPersonFlag = 1 '
	sqlorder = ' order by rTla asc'
	#if IBControlFlag == True:
	sql = sql + sqlwhereIB + sqlorder
	#else:
		#sql = sql + sqlwhereEE + sqlorder
	cursor.execute(sql)
	data=cursor.fetchall()
	cnxn.close()
	Keys = [row[0]+' '+row[1] for row in data]
	ERs = [row[0] for row in data] # ER is the three letter code for employer
	Employers = [row[1] for row in data] # Employer is the full name 
	return Keys, ERs, Employers

def PlanList(ER=None):
	cnxn = accP2()
	cursor = cnxn.cursor()
	if ER <> None:
		sql = "select nShortPlanName from tbPlan where nRID = (select rID from tbEmployer where rTLA = '{0}')".format(ER)
	else:
		sql = 'select nShortPlanName from tbPlan'
	cursor.execute(sql)
	data=cursor.fetchall()
	cnxn.close()
	Plans = [row[0] for row in data]
	return Plans

class EditRecord (wx.Dialog):
	def __init__ (self, parent, id, table, edit, keyData):
		if table in Snapshots.keys() : # see comment in SchemaData class
			filledOnly = True 
		else:
			filledOnly = False
		self.table = table
		self.Rec = SchemaData(table, filledOnly,keyData)
		self.Rec.edit = edit
		self.Rec.key = keyData
		if self.Rec.edit:
			self.Rec.getRec(table, keyData)
			title = 'Edit '+self.Rec.SF.tableName[0]+' Record'
		if not self.Rec.edit: # note that self.edit flag gets reset if getRec finds nothing
			title = 'Create '+self.Rec.SF.tableName[0]+' Record'
			tempColData = getattr(self.Rec.columnData,self.Rec.SF.key[0])
			tempColData.value = keyData
		wx.Dialog.__init__(self, parent, id, pos=(100,100),title=title)
		if table == IBControlTable:
			self.ERKeys, self.ERs, self.Employers = ERNamesKeys() # just returns Employer details for all employers
		self.Plans = PlanList()
		for col in self.Rec.columnData:
			col.setLabel(self)
			col.setControl(self)
			
		self.btnSave = wx.Button(self,-1,'Save')
		self.Bind(wx.EVT_BUTTON,self.Save,self.btnSave)

		self.btnCancel = wx.Button(self, -1, 'Cancel')
		self.Bind(wx.EVT_BUTTON,self.Cancel,self.btnCancel)

		self.btnDelete = wx.Button(self, -1, 'Delete')
		self.Bind(wx.EVT_BUTTON, self.Delete, self.btnDelete)

		self.FGSizer = wx.GridBagSizer (hgap = 5, vgap = 5)
		position  = (0,0)
		spann = (1,1)

		#now some rough and ready calculations to set the size of the window 
		Ndataitems = len(self.Rec.columnData)
		Nscreenitems = 2*Ndataitems # each screen item has a label and a field
		if Nscreenitems < 33:
			self.MaxW = 3
		elif Nscreenitems < 49:
			self.MaxW = 5
		else:
			self.MaxW = 7
		Ncols = self.MaxW + 1 #max width counts from zero - see VAdd function below

		for k,v in zip(self.Rec.colNames, self.Rec.columnData):
			# 1 how many cells wide are the label + field?
			if v.length > 30 : 
				fieldSpan = 3
			else:
				fieldSpan = 1
			totalSpan = fieldSpan + 1 # label is always 1 cell
			# 2 are there totalSpan columns left in this row?
			if position[1] + totalSpan > Ncols:
				position = (position[0]+1,0) # then move on to the next row
			#now put the label in
			self.FGSizer.Add(v.label, pos = position, span = (1,1), flag = wx.ALIGN_LEFT|wx.ALL)
			position = (position[0], position[1]+1)
			# now the field
			self.FGSizer.Add(v.control, pos = position, span = (1,fieldSpan), flag = wx.ALIGN_LEFT|wx.ALL)
			position = (position[0], position[1]+fieldSpan)
		ScreenX = 30 + 150 * Ncols #X is the width of the screen, Y is the height
		ScreenY = 10 + 30 * (position[0] + 2) #+ 1 is for the save/cancel buttons
		self.VSizer=wx.BoxSizer(wx.VERTICAL)
		self.VSizer.Add(self.FGSizer)
		self.HSizer=wx.BoxSizer(wx.HORIZONTAL)
		self.HSizer.Add(self.btnSave,0,wx.ALIGN_LEFT|wx.ALL,4)
		self.HSizer.Add(self.btnCancel,0,wx.ALIGN_LEFT|wx.ALL,4)
		self.HSizer.Add(self.btnDelete,0,wx.ALIGN_LEFT|wx.ALL,4)
		self.VSizer.Add(self.HSizer)
		#self.SetSizer(self.VSizer)
		self.SetSize((ScreenX,ScreenY))
		self.SetSizerAndFit(self.VSizer)
		self.Layout()

	def Cancel(self, event):
		self.EndModal(0)

	def ERChosen(self, event):
		id = event.GetId()
		ix = [v.id for v in self.Rec.columnData].index(id)
		EmployerChosen = self.Rec.columnData[ix].control.GetStringSelection()
		ERix = self.ERKeys.index(EmployerChosen)
		self.ER = self.ERs[ERix]
		self.Employer = self.Employers[ERix]
		Plans = PlanList(self.ER)
		Planix = self.Rec.colNames.index('EmployerPlan')
		self.Rec.columnData[Planix].control.SetItems(Plans)

	def DtChg (self, event):
		#Takes a normal/python date - from the database - and gets it ready
		#for the abnormal WX format with Jan = 0 -  see FormatWXDate below
		Evid=event.GetId()
		ix = [v.id for v in self.Rec.columnData].index(Evid)
		dt = self.Rec.columnData[ix].control.GetValue()
		Pydt , update = self.AdjustWXDate(dt)
		self.Rec.columnData[ix].value = Pydt
		if update: 
			newDt = self.FormatWXDate(Pydt)
			self.Rec.columnData[ix].control.SetValue(newDt)
				
	def NumChg (self, event):
		#Puts the new value in the record if a decimal or money field edited
		id=event.GetId()
		ix = [v.id for v in self.Rec.columnData].index(id)
		nm = self.Rec.columnData[ix].control.GetValue()
		self.Rec.columnData[ix].value = Decimal(str(nm))

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
			return datetime.date(Yr,Mo,Dy), upd
		else:
			return None

	def FormatWXDate (self, normDate):
		try:
			return wx.DateTimeFromDMY(normDate.day, normDate.month-1, normDate.year)
		except:
			return wx.DateTime()

	def Save (self, event):
		ok = True
		msg= ''
		# Note IBID,SOCSEC not changed as not editable, leave as they were
		# Dates not changed as they already have triggered their own update
		for k,v in zip(self.Rec.colNames, self.Rec.columnData):
			if not hasattr(self,'Employer') : self.Employer = None
			if (k not in self.Rec.SF.noEdit) and (v.type not in [ 'date','decimal','money']):
				if k == 'ER' and k not in self.Rec.SF.trueKey:
					v.value = self.Employer
				elif k == 'EmployerPlan':
					v.value = v.control.GetStringSelection()
				else :
					v.value = v.control.GetValue()
			if v.value in EmptSet: v.value = None
		msg = ''
		for k in self.Rec.SF.needText:
			v = getattr(self.Rec.columnData, k)
			msg+=checkTextEntered(v.value,k)+''
		#Check essential fields have been entered
		if msg ==  '':
			test4 = self.Rec.saveRec()
			if test4 == '':
				if self.Rec.edit:
					infomsg = self.Rec.SF.tableName[0]+' Updated'
				else:
					infomsg = self.Rec.SF.tableName[0]+' Record Inserted'
				close = wx.MessageDialog(self,infomsg,'Database updated', wx.OK)
				close.ShowModal()
				close.Destroy()
				self.EndModal(1)
			else:
				msg+=test4
		if msg <> '' : # not all tests good
			error = wx.MessageDialog(self,msg,'Cannot save data', wx.OK)
			error.ShowModal()
			error.Destroy()

	def Delete (self, event):
		dlg = wx.MessageDialog(None, "Clicking OK will delete this row forever from the table", "Warning", wx.OK | wx.CANCEL | wx.ICON_EXCLAMATION)
		retcode = dlg.ShowModal()
		cnxn = accP2()
		cursor = cnxn.cursor()
		if retcode == wx.ID_OK:
			sql = 'delete from {0} where '.format(self.table)
			vals = []
			sqlAND = '=? AND '.join(self.Rec.SF.trueKey)
			sql += sqlAND + '=?'
			vals = tuple(getattr(self.Rec.columnData,k).value for k in self.Rec.SF.trueKey)
			cursor.execute(sql,vals)
			rowsDeleted = cursor.rowcount
			msgText = "'{0}' row deleted".format(rowsDeleted)
			if rowsDeleted == 1:
				Msg = wx.MessageDialog(None,msgText,'Message', wx.OK)
				cnxn.commit()
			else:
				cnxn.rollback()
				msgText+='\nTransaction rolled back.  \nDatabase has not been changed. Please contact the technology team'
				msgText+='\nsql='+sql+'\ndata='+str(vals)
			Msg.ShowModal()
			Msg.Destroy()
			cnxn.close()
		dlg.Destroy()