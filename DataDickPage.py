import wx
import wx.html
from collections import OrderedDict
from utilities import *
import HTML

code_columns = 'cCode cDescription cColumnTitle cAnnuals cSnapShots cServiceCodes cMoney'.split()
flag_columns = 'fid fName fType fDescription'.split()

def translate_binary(x):
    if x:
        return 'Yes'
    else:
        return 'No'

def show_props(table, column, cursor):
    sql1 = """select data_type, character_maximum_length,
        numeric_precision_radix, numeric_scale
        from information_schema.columns
        where table_name = '{0}'
        and column_name = '{1}';"""
    sql1Go = sql1.format(table, column)
    cursor.execute(sql1Go)
    try:
        data_type, field_length, numeric_radix, numeric_precision = cursor.fetchone()
        if not field_length: field_length = 'N/A'
        if not numeric_radix: numeric_radix = 'N/A'
        if not numeric_precision: numeric_precision = 'N/A'
    except:
        data_type, field_length, numeric_radix, numeric_precision = 'Not found', None, None, None
    sql2 = """select CAST(name as VARCHAR(200)) as colname, CAST(value as VARCHAR(200)) as val from fn_listextendedproperty
            (NULL, 'schema','dbo','table','{0}','column','{1}');"""
    sql2Go = sql2.format(table,column)
    cursor.execute(sql2Go)
    return_dick = {}
    try:
        return_dick = dict((row[0],row[1]) for row in cursor.fetchall())
    except:
	pass
    if 'Field_Description' not in return_dick:
	return_dick['Field_Description'] = 'Not found'
    if 'Additional_Info' not in return_dick:
	return_dick['Additional_Info'] = None
    if 'Field_Use' not in return_dick:
	return_dick['Field_Use'] = None
    return_dick['data_type'] = data_type
    return_dick['field_length'] = field_length
    return_dick['numeric_radix'] = numeric_radix
    return_dick['numeric_precision'] = numeric_precision
    return return_dick

def get_code_detail(column, cursor):
    sql = 'select ' + ','.join(code_columns) + ' from tbcodes where ccode = ?'
    result = cursor.execute(sql,(column,)).fetchone()
    msg =  "Field Description: " + result.cDescription + '\n'
    msg += "Field Title: " + result.cColumnTitle + '\n'
    msg += "Annual Field? " + translate_binary(result.cAnnuals) + '\n'
    msg += "SnapShot Field? " + translate_binary(result.cSnapShots) + '\n'
    msg += "ServiceCodes? " +  translate_binary(result.cServiceCodes) + '\n'
    msg += "Money? " +  translate_binary(result.cMoney)
    return msg, dict((code_column, code_data) for code_column, code_data in zip(code_columns,result))

def get_flag_detail(column, cursor):
    sql = 'select '+','.join(flag_columns) + " from tbflag where fname = '{0}'"
    sql = sql.format(column)
    result = cursor.execute(sql).fetchone()
    if not result.fType: result.fType = 'Not found'
    if not result.fDescription: result.fDescription = 'Not found'
    msg = "Flag Type: " + result.fType+ '\n'
    msg += "Flag Description: " + result.fDescription
    return msg, dict((flag_column, flag_data) for flag_column, flag_data in zip(flag_columns,result))

def edit_column(table, column, fields, cursor):
    def extendedproperties_sql(propname, table, column, cursor):
	properties = show_props(table, column, cursor)
	if properties[propname] in ['Not found', None]:
	    # need to insert
	    sql1 = """exec sp_addextendedproperty
	    @name = '{0}',
	    @value = ?,
	    @level0type = N'Schema', @level0name = 'dbo',
	    @level1type = N'Table', @level1name = '{1}',	
	    @level2type = N'Column', @level2name = '{2}';
	    """
	    sql = sql1.format(propname, table, column)
	else:
	    # need to update
	    sql2 = """exec sp_updateextendedproperty
	    @name = '{0}',
	    @value = ?,
	    @level0type = N'Schema', @level0name = 'dbo',
	    @level1type = N'Table', @level1name = '{1}',	
	    @level2type = N'Column', @level2name = '{2}';
	    """
	    sql = sql2.format(propname, table, column)
	return sql

    def code_sql(column, val):
	value = val
	sql = "update tbcodes set cdescription = ? where ccode = '{0}'"
	sql = sql.format(column)
	if (not val) or (val == 'Not found'):
	    value = ''
	return sql, value

    def flag_sql(column, val):
	value = val
	sql = "update tbflag set fdescription = ? where fname = '{0}'"
	sql = sql.format(column)
	if (not val) or (val == 'Not found'):
	    value = ''
	return sql, value
    
    def result_update(oldresult, newresult):
	if oldresult == 'error':
	    return oldresult
	else:
	    return newresult
	
    result = 'ok'
    cursor = cursor
    for k,v in fields.iteritems():
	k = k.replace(' ','_')
	# the keys in the incoming dictionary 'fields' are the extended property names
	# the values in fields are the extended property values
	# for codes and flags the values are just the description fields in the database table
	if table.lower() == 'tbcodes':
	    sql, val = code_sql(column, v)
	elif table.lower() == 'tbflag':
	    sql, val = flag_sql(column, v)
	else:
	    sql = extendedproperties_sql(k, table, column, cursor) 
	    val = v
	#print sql, val
	try:
	    cursor.execute(sql, val)
	    result = result_update(result, 'ok')
	except pyodbc.Error as er:
	    errNo, errData = er
	    #print errData
	    result = result_update(result, 'error')
    return result


def get_columns(table, cursor):
    if table.lower() == 'tbcodes':
        sql = "select ccode from tbcodes"
    elif table.lower() == 'tbflag':
        sql = "select fname from tbflag"
    else:
        sql = """select column_name from information_schema.columns
        where table_name = '{0}';"""
        sql = sql.format(table);
    cols = cursor.execute(sql).fetchall()
    return [str(i[0]) for i in cols]

def get_tabledata(table, cursor):

    def getMaxLen(col):
        return max([len(i) for i in col])

    def get_tabledata_sub(table):
        headsForTitles=['Column Name','Data Type', 'Field Length', 'Field Description', 'Numeric Radix', 'Numeric Precision', 
	       'Field Use', 'Additional Info']
	headsInProperties=['data_type', 'field_length', 'Field_Description', 'numeric_radix', 'numeric_precision', 
		       'Field_Use', 'Additional_Info']	
	result = [headsForTitles]
        for col in get_columns(table, cursor):
	    properties = show_props(table, col, cursor)
            result.append([col]+[properties[i] for i in headsInProperties])
        return result

    def get_codesdata():
        sql = 'select '+','.join(code_columns)+' from tbcodes;'
        data = cursor.execute(sql).fetchall()
        for row in data:
            row.cannuals = translate_binary(row.cannuals)
            row.csnapshots = translate_binary(row.csnapshots)
            row.cservicecodes = translate_binary(row.cservicecodes)
            row.cmoney = translate_binary(row.cmoney)
        return [code_columns] + data

    def get_flagsdata():
        sql = 'select '+','.join(flag_columns)+' from tbflag'
        result = [flag_columns] + cursor.execute(sql).fetchall()
        return result


    if table.lower() == 'tbcodes':
        result = get_codesdata()
    elif table.lower() == 'tbflag':
        result = get_flagsdata()
    else:
        result = get_tabledata_sub(table)
    #make everyting a string - we want to calculate widths
    result = [[str(i) for i in j] for j in result]
    resultTransp = zip(*result)
    colWidths = [getMaxLen(i)+1 for i in resultTransp]
    width = sum(colWidths)
    height = len(result)
    htmlString = HTML.table(result[1:],header_row=result[0])
    return result, htmlString, width, height
	
class EditDialog(wx.Dialog):
    def __init__(self, parent, wxid, table, column, cursor, fields):
        self.table = table
        self.column = column
        self.fields = fields
        self.keys = self.fields.keys()
	self.cursor = cursor
        wx.Dialog.__init__(self, parent, wxid, pos=(100,100), title="Edit fields")
        self.paint_screen()
        
    def paint_screen(self):
        vsizer = wx.BoxSizer(wx.VERTICAL) # main size
        bsizer = wx.BoxSizer(wx.HORIZONTAL) # button sizer
        self.dataControls = []
        FGSizer = wx.FlexGridSizer(rows = len(self.keys), cols = 2, hgap = 5, vgap = 5)
        for f in self.fields:
            FGSizer.Add(wx.StaticText(self, -1, f+": "),wx.ALIGN_LEFT|wx.ALL, 5)
            self.dataControls.append(wx.TextCtrl(self, -1,self.fields[f] , size=(280,-1)))
            FGSizer.Add(self.dataControls[-1], wx.ALIGN_LEFT|wx.ALL, 5)
	# set up the buttons
        self.btnSave = wx.Button(self, -1, "Save")
        self.btnCancel = wx.Button(self, -1, "Cancel")
        bsizer.Add(self.btnSave, 0, wx.ALIGN_LEFT|wx.ALL, 4)
        bsizer.Add(self.btnCancel, 0, wx.ALIGN_LEFT|wx.ALL, 4)        
	self.Bind(wx.EVT_BUTTON, self.onCancel, self.btnCancel)
	self.Bind(wx.EVT_BUTTON, self.onSave, self.btnSave)	
	line = wx.StaticLine(self, -1,  style=wx.LI_HORIZONTAL)
	for thing in [FGSizer, line, bsizer]:
	    vsizer.Add(thing, flag=wx.ALIGN_CENTER|wx.TOP|wx.BOTTOM, border = 5)
	self.SetSizer(vsizer)
	self.Layout()
	
    def onCancel(self, event):
	self.EndModal(0)
	
    def onSave(self, event):
	# 1 get the field values from the text controls
	for f, t in zip(self.keys, self.dataControls):
	    self.fields[f] =t.GetValue()
	# 2 if codes, update codes, if flag update flag, else update extended properties
	if edit_column(self.table, self.column, self.fields, self.cursor) == 'ok':
	# 3 if error/success display error/success message
	    retcode = wx.MessageBox("Data Changed ok.", "Result message", wx.OK)
	else:
	    retcode = wx.MessageBox("An error occurred, please check", "Result message", wx.OK)
	# 4 shut everything down
	self.EndModal(1)
	
class DataDick(wx.Panel):
    def __init__(self, parent):
	cnst = connStringViewCreate()
	cnxn = pyodbc.connect(cnst)
	self.cursor = cnxn.cursor()
        #
        dropdownsize = (85,18)
        wx.Panel.__init__(self, parent)
        size=wx.GetDisplaySize()
        self.maxsize=(size[0]*.9,size[1]*.8)        
        self.tables = OrderedDict({'tbPerson':{'normal':True},
                                   'tbEmployee':{'normal':True},
                                   'tbEmployer':{'normal':True},
                                   'tbPlan':{'normal':True},
                                   'tbMember':{'normal':True},
                                   'tbService':{'normal':True},
                                   'tbBhSnapshot':{'normal':True},
                                   'tbBcSnapshot':{'normal':True},
                                   'tbAnnual':{'normal':True},
                                   'tbBeneficiaryQDRO':{'normal':True},
                                   'tbFlag':{'normal':False},
                                   'tbCodes':{'normal':False},
                                   'tbFlagValue':{'normal':True}})
        lab_table = wx.StaticText(self,-1,"Table")
        lab_column = wx.StaticText(self,-1,"Column")
        self.table_chosen = 'tbPerson' #just start with the first table
        self.column_chosen = '' 
        self.column_choices = ''#get_columns(self.table_chosen, self.cursor)
        self.choose_tables = wx.Choice(self,-1,dropdownsize, choices = self.tables.keys())
        self.choose_column = wx.Choice(self,-1,dropdownsize, choices = self.column_choices)
        #bind the choices to their functions
        self.Bind(wx.EVT_CHOICE,self.onTable_event,self.choose_tables)
        self.Bind(wx.EVT_CHOICE, self.onColumn_event, self.choose_column)
        # now the buttons and their bindings
        self.table_btn = wx.Button(self, -1, "Show data dictionary for table")
        self.edit_btn = wx.Button(self, -1, "Edit column description")        
        self.Bind(wx.EVT_BUTTON,  self.onShow_table, self.table_btn)         
        self.Bind(wx.EVT_BUTTON,  self.onEdit_column, self.edit_btn)                 
        #now put the sizers together
        # first the user chooses a table, and a column if she wants a column
        ShowColBox = wx.StaticBox (self,-1, 'Choose a table.  Add a column if you want to edit the data.')
        ShowColSizer = wx.StaticBoxSizer(ShowColBox, wx.HORIZONTAL)
        for thing in [lab_table,self.choose_tables,lab_column, self.choose_column]:
            ShowColSizer.Add(thing, 0 , wx.ALL, 5)
        ShowBtnBox = wx.StaticBox (self,-1, 'Choose the action you want to take.')
        ShowBtnSizer = wx.StaticBoxSizer(ShowBtnBox, wx.HORIZONTAL)
        for thing in [self.table_btn, self.edit_btn]:
            ShowBtnSizer.Add(thing, 0 , wx.ALL, 2)
        self.v1=wx.BoxSizer(wx.VERTICAL)
        self.v1.Add(ShowColSizer,0,wx.ALIGN_TOP| wx.ALL, 4)
        self.v1.Add(ShowBtnSizer,0,wx.ALIGN_TOP| wx.ALL, 4)        
        self.SetSizer(self.v1)
        self.Layout()

    def onTable_event(self, event):
        table_ix = self.choose_tables.GetSelection()
        self.table_chosen = self.tables.keys()[table_ix]
        self.column_choices = get_columns(self.table_chosen, self.cursor)
        self.choose_column.SetItems(self.column_choices)

    def onColumn_event(self, event):
        column_ix = self.choose_column.GetSelection()
        self.column_chosen = self.column_choices[column_ix]

    def onShow_table(self, event):
        tableData, tableStr, width, height = get_tabledata(self.table_chosen, self.cursor)
        width_in_mm = width*1.797-2.4
        width_in_px = width_in_mm * 3.814
        height_in_mm = height * 8.675 - 2.697
        height_in_mm = min([height_in_mm, 270])
        height_in_px = height_in_mm * 3.814
        frm = HTMLWindow(None, 'Data Dictionary for '+self.table_chosen, tableStr, width_in_px, height_in_px)
        frm.Show()

    def onEdit_column(self,event):
        if self.table_chosen.lower() == 'tbcodes':
            msg, d = get_code_detail(self.column_chosen, self.cursor)
            fields = {'Description': d['cDescription']}
        elif self.table_chosen.lower() == 'tbflag':
            msg, d = get_flag_detail(self.column_chosen, self.cursor)
            fields = {'Description': d['fDescription']}
        else:
	    properties = show_props(self.table_chosen, self.column_chosen, self.cursor)
            fields = OrderedDict([('Field Description', properties['Field_Description']),
	                          ('Field Use', properties['Field_Use']),
	                          ('Additional Info', properties['Additional_Info'])
	                          ])
        dialog = EditDialog(self, -1, self.table_chosen, self.column_chosen, self.cursor, fields)
        dialog.ShowModal()
        dialog.Destroy()
	


