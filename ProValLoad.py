from utilities import *
import os
from datetime import date, datetime, timedelta
import xlrd # note we cannot use the xlsxrd format as we need to insert data into this spreadsheet - the new id numbers for new members
import xlwt
import pyodbc
from xlutils.copy import copy as xlcopy
import shutil
import wx
from NameFiddler import nameFiddle
from getFlatRecs import xyz99
import pprint
from collections import defaultdict
from operator import itemgetter

def convertdat(dat, typ, dMode=None):
    result = None
    if typ == 'Date':
        if dat < 20: # dat = 1 is Jan 1 1900 - there are a good few of these and they screw it up, apparently it is an ambiguous date
            result = None
        else:
            try:
                datetuple = xlrd.xldate_as_tuple(float(dat),dMode)
            except:
                errf.Add('serious','There is a bad date with the value '+str(dat))
                datetuple = (1900,1,1)
            result = date(datetuple[0],datetuple[1],datetuple[2])
    if typ == 'Number':
        result = Decimal(str(dat))
    if typ == 'Text':
        result = dat.strip()
    if dat in EmptSet: result = None
    return result

class processErr:
 
    def __init__(self):
        self.start()

    def start(self):
        self.MsgFile = defaultdict(list)
        self.NotSerious = True
        self.msgCount, self.seriousmsgCount = 0,0

    def openf(self,fn,suff=None):
        self.start()
        self.fn = fn
        if suff: self.fn = self.fn[:-4] + suff + self.fn[-4:]
        self.seriousfn = fn[:-4]+'SERIOUS.txt'
        self.errf = open(self.fn,'w')
        self.seriousf=open(self.seriousfn,'w')
    
    def close(self):
        self.errf.close()
        self.seriousf.close()
      
    def Add(self,severity, message):
        message += '\n'
        severity = severity.capitalize()
        if debug: print severity, ' ',message
        self.errf.write(severity+' '+message)
        self.MsgFile[severity].append(message)
        self.msgCount += 1
        if severity in [Serious,Setup]:
            self.NotSerious = False
            self.seriousf.write(severity+' '+message)
            self.seriousmsgCount += 1
        
    def Addpp(self, message):
        #if debug:
        pprint.pprint(message,self.errf, width=80)

    def Output(self):
        self.close()
        msg = 'Messages summary\n'
        msg += str(self.msgCount)+ ' messages'+'\n'
        msg += str(self.seriousmsgCount)+ ' serious error messages'+'\n'
        if self.seriousmsgCount > 0:
            msgList = self.MsgFile['Serious']
            if self.seriousmsgCount < 10:
                msgsShown = self.seriousmsgCount
            else:
                msgsShown = 10
            msg += 'First '+str(msgsShown)+' serious message lines as follows\n\n'
            for i in range(msgsShown):
                msg+=msgList.pop()+'\n'
        return msg
                    
def readXL(book):
    sht = book.sheet_by_index(0) #assume always sheet 0
    dMode = book.datemode
    typs={0 : 'Empty', 1 : 'Text', 2: 'Number', 3 : 'Date', 4 : 'Boolean',5 : 'Error', 6 : 'Empty'}
    rnge = sht.nrows
    for row in range(1,sht.nrows): #miss out row 0 as this is headings 
        thisR = [(sht.cell_value(row,col), sht.cell_type(row,col)) for col in range(sht.ncols)]
        yield [convertdat(cell[0],typs[cell[1]],dMode) for cell in thisR]

def sqlUpd (table, colNames, keyColNames):
    sqlUpd = "update {0} set ".format(table)
    sqlUpd2 = " = ?,".join(colNames) + '=? where '
    sqlUpd3 = '=? and '.join(keyColNames) + '=?'
    return sqlUpd+sqlUpd2+sqlUpd3

def sqlIns (table,colNames, OutKey = None):
    sqlIns = 'insert into {0} '.format(table)
    sqlIns2 ='('+', '.join(colNames) + ') '
    if OutKey : 
        sqlIns2 += 'output inserted.{0}'.format(OutKey)
    sqlIns2 += ' values ('
    sqlIns3 = ','.join(['?']* len(colNames)) + ')'
    return sqlIns + sqlIns2 + sqlIns3

def Update (sql, dat, report=True):
    """ this carries out a database update call.
    For flag table updates, we cannot be sure if a flag is in for this year or not - the latest flag may be a prior year.
    Therefore this function is called with report = False, no error report is written when / if it fails, and the updateFlag function
    will then attempt to insert a new flag
    """
    errStrin = 'sql-->'+sql+'\n'+'data-->'+str(dat)+'\n'
    SeriousError = False
    try:
        cursor.execute(sql,dat)
    except pyodbc.Error as er:
        SeriousError = True
        errNo, errData = er
        errStrin += 'Unexpected update error-->'+str(errNo)+str(errData)+'\n'
    if cursor.rowcount <> 1 :
        if report:
            SeriousError = True
            errStrin += '\nUnexpected update error, rowcount = '+str(cursor.rowcount)+'\n'
        else:
            return -1 # just go back to the flag update with a -1
    if SeriousError:
        errf.Add(Serious,errStrin)
        #silly = 1/0
    else:
        errf.Add(Normal,errStrin)
    return
            
def Insert (sql,dat, ReturnId = False):
    errStrin = 'sql-->'+sql+'\n'+'data-->'+str(dat)+'\n'
    newRowId = None
    try:
        cursor.execute(sql,dat)
    except pyodbc.Error as er:
        errNo, errData = er
        errStrin += 'Unexpected insert error-->'+str(errNo)+str(errData)+'\n'
        errf.Add(Serious,errStrin)
    else:
        errf.Add(Normal,errStrin)
        if ReturnId:
            newRowId = cursor.fetchone()[0]
    return newRowId

def Delete(sql, dat):
    errStrin = 'sql-->'+sql+'\n'+'data-->'+str(dat)+'\n'
    try:
        cursor.execute(sql,dat)
    except pyodbc.Error as er:
        errNo, errData = er
        errStrin += 'Unexpected delete error '+str(errNo)+str(errData)+'\n'
        errf.Add(Serious,errStrin)
        #silly = 1/0
    else:
        errf.Add(Normal,errStrin)
    return
    
def dbprint(s):
    if debug: print s

class ProValLoad:
    
    def __init__(self, parent, fn, PlanId, EmployerId):
        dbprint ('starting')
        self.errfile=fn[:-4]+'.txt'
        errf.openf(self.errfile,'step1')
        oldXLf = fn[:-4]+'old.xls'
        shutil.copyfile(fn,oldXLf) # this will create a copy just in case
        self.fn = fn
        book = xlrd.open_workbook(self.fn)
        sht = book.sheet_by_index(0) #assume always sheet 0

        self.PlanId = PlanId
        self.EmployerId = EmployerId
        self.colHeads  = [sht.cell_value(0,col).lower() for col in range(sht.ncols)]
        if not all(self.colHeads):
            errf.Add('serious','You have some blank column names.  They may be at the right hand end of your spreadsheet.  Please remove them.')
        try:
            self.midSScol = self.colHeads.index('mid')
        except:
            errf.Add('serious','I need a column named mid containing the member identifiers')
        try:
            self.mFDSScol = self.colHeads.index('meffectivedate')
        except:
            errf.Add('serious','I need a column named meffectivedate containing the effectivedate for this load')
        self.SSservCodes = set([i[:-1] for i in self.colHeads if i[:3] == 'dat'])
        self.suffixes = [k[15:] for k in self.colHeads if k[:15] == 'bheffectivedate']
        # now make sure the spreadsheet is not sitting open on the users' desktop!
        self.openSS()
        try:
            self.closeSS()
        except:
            errf.Add('serious','I think you have the spreadsheet\n'+self.fn+'\nopen in your desktop.\nPlease close it.')
        #Step 1 - get the spreadsheet data into a list of dictionaries
        self.SSrows = [dict((colName,col) for colName,col in zip(self.colHeads,row)) for row in readXL(book)]
        for rowNum,row in enumerate(self.SSrows):
            row['ssRowNo']=rowNum+1 # headings are first row so add 1 to get the right row number
        # now check all the effectivedates are the same
        self.EffectiveDate = self.SSrows[0]['meffectivedate']
        try:
            y = self.EffectiveDate.year
        except:
            errf.Add('serious','The meffectivedate column in the spreadsheet is not a date.\nI have '+str(self.EffectiveDate))
        FDColumn = [i['meffectivedate'] for i in self.SSrows]
        bad_dates = [i for i in FDColumn if i <> self.EffectiveDate]
        if bad_dates:
            bad_dates_str = ','.join([str(i) for i in set(bad_dates)])
            errf.Add('serious','The meffectivedate column in the spreadsheet needs to have one date.\nI have'+str(self.EffectiveDate)+'\nand '+bad_dates_str)
        self.LoadDate = self.EffectiveDate
        #  now decide how many years to get annual records for
        annualHeads = [i[-17:-9] for i in self.colHeads if i and len(i) > 17 and i[0] == 'a']
        try:
            fromDates = [datetime.strptime(i,"%Y%m%d") for i in annualHeads]
        except:
            errf.Add('serious','The annual columns dates need to be formatted YYYYMMDD_YYYYMMDD, bad data found')
        numYears = 10
        if errf.NotSerious:
            if fromDates:
                earliest_date = min(fromDates)
                earliest_year = earliest_date.year
                FD_year = self.EffectiveDate.year
                numYears = FD_year - earliest_year + 1
            else:
                numYears = 0
            # Step 2 - get the data from the database into a dictionary of mids
            self.DBData = xyz99(parent, 'scheme', self.PlanId, self.EffectiveDate.year, None, numYears)
            self.colDick = dict((k.lower().strip(),v.lower().strip()) for k,v in self.DBData.colHeads.iteritems())# this is a dictionary of colNames : colTypes
            self.colDick['ssRowNo'] = 'int'
            dbprint('got records')
            self.DBData.makeDick(self.colHeads, lowerCase = True)
            t1 = timedelta(1)
            for rowNum, row in enumerate(self.SSrows):
                for colName, value in row.iteritems():
                    if colName not in self.colDick: # two reasons why not - it is a new annual field, or there is no previous use of this column for this plan
                        if colName[0] == 'a':
                            colType = 'decimal'
                        else: # just take it as varchar for now - could be improved by looking in the database, but flags will make this complicated
                            colType = 'varchar'
                    else:
                        colType = self.colDick[colName]
                    if value: # we are not interested in testing empty cells
                        if colType in ['varchar','nchar']:
                            pass # nothing to check here
                        elif colType in ['money','int','smallint','tinyint','decimal']:
                            try: 
                                test = value + 0
                            except:
                                errf.Add('serious','Bad numeric data '+str(value)+' in row '+str(rowNum+2)+' column '+colName+'.')
                        elif colType == 'date':
                            try: 
                                test = value + t1
                            except:
                                errf.Add('serious','Bad date data  '+str(value)+' in row '+str(rowNum+2)+' column '+colName+'.')
                        else:
                            errf.Add('serious','Unknown data type '+colType+' in row '+str(rowNum+2)+' column '+colName+'.')
            #print 'db data keys',self.DBData.Dick.keys()
            #print 'db data vals0', self.DBData.Dick[self.DBData.Dick.keys()[0]]
            self.SSData = {} # this is going to get filled up after the checks, just here to remind you
            self.tableChs=['p','e','m','bq','flg','a','dat','bh','bc','l'] #the prefixes for each table
            self.headsInTables, self.rowsToUpd, self.rowsToAdd = {},{},{}
            #step3 get all the mid, pid, eids organized by social
            self.pidDick = dict((k,row['mpid']) for k,row in self.DBData.Dick.iteritems())
            self.eidDick = dict((k,row['meid']) for k,row in self.DBData.Dick.iteritems())
            self.midDick = dict((k,row['mid']) for k,row in self.DBData.Dick.iteritems())
            self.bqidDick = dict((k,row['bqid']) for k,row in self.DBData.Dick.iteritems() if row['bqid']) 
            #
            for chs in self.tableChs:
                lench = len(chs) # create a lookup of all the relevant table columns for each table
                self.headsInTables[chs]=[col for col in self.colHeads if col[:lench] == chs]  # pull out the columns for each table into a list, each list is an item in a dictionary
                self.rowsToAdd[chs] = {} # create a blank add and update dictionary for each table
                self.rowsToUpd[chs] = {}
            # now check all the column names are valid.  This a bit long-winded.
            #AnnualTable = 'tbAnnual'
            #IBControlTable = 'tbIbctrl'
            #EmployerTable = 'tbEmployer'
            #ServiceTable = 'tbService'
            #DetailTable = 'tbFinRecs'
            #PersonTable = 'tbPerson'
            #EmployeeTable = 'tbEmployee'
            #MemberTable = 'tbMember'
            #bhSnapShotTable = 'tbBHSnapshot'
            #bcSnapShotTable = 'tbBCSnapshot'
            #PayTable = 'tbPayRecords'
            #FlagValueTable = 'tbFlagValue'
            #bqTable = 'tbBeneficiaryQDRO'
            
            # this just generates a set of column titles for the various types of snapshot
            cursor.execute('select ccolumntitle from tbcodes where csnapshots = 1')
            bhtypes = [i[0].lower() for i in cursor.fetchall()]
            bhtypes = bhtypes + ['thisyr','lastyr']
            bhtypes = set(bhtypes)
            
            for colName in self.colHeads:
                if colName not in self.colDick: # then we need to check it.
                    table = 'Unknown'
                    if colName[0] == 'p':
                        table = PersonTable
                        colTitle = colName
                    elif colName[0] == 'l':
                        table = LocationTable
                        colTitle = colName
                    elif colName[0] == 'e':
                        table = EmployeeTable
                        colTitle = colName
                    elif colName[0] == 'm':
                        table = MemberTable
                        colTitle = colName
                    elif colName[:2] == 'bh':
                        table = bhSnapShotTable
                        colNameSuffixes = set([colName[-len(i):] for i in bhtypes])
                        thistypmatch = list(bhtypes & colNameSuffixes) #intersection of bhtypes with the suffixes - ie the match
                        if thistypmatch:
                            thistyp = thistypmatch[0] # will only be one member
                            colTitle = colName[:-len(thistyp)]
                        else:
                            colTitle = colName # if no match we will leave the title as the whole column name, which will generate an error below
                    # amend this bit once BC tables appear
                    #elif colName[:2] == 'bc':
                    #    table = bcSnapShotTable
                    #    colTitle = colName[:-6]
                    elif colName[:2] == 'bq':
                        table = bqTable
                        colTitle = colName
                    elif colName[0] == 'a':
                        table = AnnualTable
                        sql = 'select ccolumntitle from tbcodes where cannuals = ? and ccolumntitle = ?'
                        colTitle = colName[:-17]
                    elif colName[:3] == 'flg':
                        table = FlagValueTable
                    elif colName[:3] == 'dat':
                        table = ServiceTable
                        sql = 'select ccolumntitle from tbcodes where cservicecodes = ? and ccolumntitle = ?'
                        colTitle = colName[:-1]
                    if table in [PersonTable, EmployeeTable, MemberTable, bhSnapShotTable, bcSnapShotTable, bqTable, LocationTable]:
                        sql = 'select column_name from information_schema.columns where column_name = ? and table_name = ?'
                        cursor.execute(sql,(colTitle,table))
                    elif table in [AnnualTable, ServiceTable]:
                        cursor.execute(sql,(1,colTitle))
                    elif table == FlagValueTable:
                        cursor.execute('select fname from tbflag where fname = ?',(colName,))
                    else:
                        table = 'Unknown'
                    data = cursor.fetchall()
                    if not data:
                        errf.Add(Serious,'Bad column name ' + colName + ' in table ' + table + ' please fix or contact IT.')
        self.checkMessages()

    def checkMessages(self):
        self.errorMessages = errf.Output()
        self.goodToGo = errf.NotSerious
        
    def checkData(self):

        def checkColHeads():
            for colName in ['mssn','pname','mid']: # add any required column names to this list
                if colName not in self.colHeads:
                    msgs[0].append('no column called '+colName+' in input spreadsheet.  Please correct.')
                    
        def checkNumChars():
            # the codsta and payform fields are 'supposed' to be char fields
            # but they only ever have integers.  This causes Excel a problem as it reads them as (say) 6.0
            # this will just check for these fields and if present replace them with the string integer with 0DP
            for colName in self.colHeads:
                if ('codsta' in colName) or ('payform' in colName) or ('lstreet' in colName) or ('zip' in colName):
                    for rowNum, row in enumerate(self.SSrows):
                        test = row[colName]
                        # if it has blanks, strip them off
                        try:
                            test=test.strip()
                        except:
                            pass
                        if test not in [None, '',' ']:
                            try:
                                test = int(test)
                            except:
                                pass
                                #msgs[rowNum+1].append(' '+colName+' is supposed to be an integer less than 100. I got '+str(test))
                            row[colName] = str(test)

        def checkSex():
            # replace 'Male' etc with 'M'
            # note we do not require psex any more - if it's not here it won't get looked at (obviously)
            for rowNum, row in enumerate(self.SSrows):
                sex = row.get('psex')
                if sex: #this will not crash either if no psex item or if no value - saves checking twice
                    if len(sex) > 1:
                        row['psex'] = row['psex'][0].upper()
                    if row['psex'] not in ['M','F']:
                        msgs[rowNum+1].append(' psex  is supposed to be M or F. I got '+str(row['psex']))
            
        def checkMidSocialCombinations():
            for rowNum,row in enumerate(self.SSrows):
                goodSocial, row['mssn'] = socialCheck(row['mssn']) # we do not use the goodSocial flag here - we'll find out soon enough 4 lines down...
                if row['mid']:
                    SSid = row['mid']
                    #print 'ssid',SSid,type(SSid)
                    if SSid in self.DBData.Dick: # is this member in the database
                        if self.DBData.Dick[SSid]['mssn'] == row ['mssn']: 
                            pass # all is well, only 1 match and they are the same ssn
                        else:
                            msgs[rowNum+1].append('invalid mid in the database for spreadsheet mid '+str(SSid)+ ' and spreadsheet social '+str(row['mssn']))
                    else:
                        #for d in self.DBData.Dick.keys(): print 'key',d, type(d)
                        dbprint (row)
                        msgs[rowNum+1].append('no id in the database for spreadsheet id '+str(SSid))
                else:
                    pass # this is ok - there is no mid in this row, but this just means we are going to insert one.
                        
        def checkNeededData():
            for rowNum, row in enumerate(self.SSrows):
                if not row['mssn']: msgs[rowNum+1].append('No social security number in mSSN column.  Check this row in the spreadsheet.')
                if not row['pname']: msgs[rowNum+1].append('No name in pName column. Check this row in the spreadsheet.') # just add more rows if you want to check more columns
            
        def checkDates():
            for rowNum, row in enumerate(self.SSrows):
                for k,v in row.iteritems():
                    if v and 'dat' in k and type(v) not in [date, datetime]:
                        msgs[rowNum+1].append('bad date '+str(v)+' in column '+str(k)) # this checks that all columns with dat in the title are valid dates
                for suff in self.suffixes: # this works through each bhAccountType - Froze,Annual,Protected etc
                    suffData = dict((k[:-len(suff)],v) for k,v in row.iteritems() if k[-len(suff):] == suff)
                    dateVal = suffData.pop('bheffectivedate',None) #this gets the bheffectivedate IF there is one, if the guy is not (say) protected there will be no data
                    for k,v in suffData.iteritems():
                        if v and not dateVal: # we test if there is data (ie if v) - if so we must have a bheffectivedate
                            msgs[rowNum+1].append('need an effective snapshot date for column '+str(k)+suff)
        
        def makeDictionary():
            idNeeded = -1            
            for row in self.SSrows:
                if not row['mid']: # if no value in the id field, then this is a brand new row
                    row['mid'] = idNeeded # and so put a dummy value in 
                    idNeeded = idNeeded - 1
                idNo = row['mid'] # and use the value as the key
                self.SSData[idNo]= row
            
        def doCompareData(idNo, row):
            if rowNum % 100 == 0: dbprint(str(rowNum)+' rows')
            errf.Addpp(['mid',idNo])
            errf.Addpp(['row',row])
            if idNo in self.DBData.Dick: # then this guy is in the database
                DBLine = self.DBData.Dick[idNo]
                #fill in any columns in SS not in DBLine
                errf.Addpp(['dbLine', DBLine])
                #deal with person, employee, member table first.  The fact that someone has a member record means they must have
                #  an employee and person record too.  So we can deal with these three rows the same way
                for ch in ['p','e','m','l']:
                    DataList = [(colName, row[colName]) for colName in self.headsInTables[ch] if row[colName] <> DBLine[colName]]
                    if DataList :
                        self.rowsToUpd[ch][idNo] = dict(DataList)
                #now bq columns
                DataList = [(colName, row[colName]) for colName in self.headsInTables['bq'] if row[colName] <> DBLine[colName]]
                if DataList:
                    if idNo in self.bqidDick:
                        self.rowsToUpd['bq'][idNo] = dict(DataList)
                    else:
                        self.rowsToAdd['bq'][idNo] = dict(DataList)
                """ In these following two sections, we pick all the columns in the snapshot, but only those columns with data in for the service
                     table.  """
                for ch in ['bh','bc']: #For these tables, the update routine will carry out all of the (more complex) processing
                    DataList = [(colName,row[colName]) for colName in self.headsInTables[ch]] # PJE removed next bit 11/25/2014 as will not update zeros/blanks if row[colName]]
                    if DataList:
                        self.rowsToUpd[ch][idNo] = dict(DataList)
                for ch in ['dat']: #For these tables, the update routine will carry out all of the (more complex) processing
                    DataList = [(colName,row[colName]) for colName in self.headsInTables[ch] if row[colName]]
                    if DataList:
                        self.rowsToUpd[ch][idNo] = dict(DataList)

                for ch in ['a','flg']:#These last two tables, each column corresponds to a separate row entry
                    # in these two lines: 
                    # a) we update if the row exists in the database AND the spreadsheet has a different value
                    # b) we insert if the row does not exist in the database and the spreadsheet has a non-zero value
                    # it is written out in full - including the unnecessary Pass statements because it is bloody complicated and may still be wrong
                    UpdList, AddList = [],[] # two empty lists to start
                    for colName in self.headsInTables[ch]:
                        if colName in DBLine: # then there is a DB column for at least some rows - but it may have None in it here as it does not exist for this member
                            if DBLine[colName] <> None:
                                if row[colName] <> DBLine[colName]: 
                                    UpdList.append((colName,row[colName]))
                                else:
                                    pass # the ss row and db row ARE equal, so no need to update
                            else:
                                if row[colName]: # database has None, ie row does not exist for this member, but ss has something in it
                                    AddList.append((colName,row[colName]))
                                else: 
                                    pass #nothing in row and nothing in database so do nothing
                        else:
                            if row[colName]: # no row in database, but something non-zero in spreadsheet
                                AddList.append((colName,row[colName]))
                            else:
                                pass # nothing in database and nothing in ss either
                    if UpdList:
                        self.rowsToUpd[ch][idNo] = dict(UpdList)
                    if AddList:
                        self.rowsToAdd[ch][idNo] = dict(AddList)
            else: # then this is a new guy or an annual record and we need to add every column present
                for chs in self.tableChs:
                    tempDick = dict((colName,row[colName]) for colName in self.headsInTables[chs] if row[colName])
                    if tempDick: self.rowsToAdd[chs][idNo] = tempDick # if we just created an empty dictionary we are not interested in adding it
        
        errf.openf(self.errfile,'step2')
        dbprint('starting checkdata')
        msgs = defaultdict(list)
        checkColHeads()
        if not msgs:
            checkMidSocialCombinations()
            checkNumChars()
            checkSex()
            checkNeededData()
            checkDates()
        if msgs:
            for k,v in msgs.iteritems(): 
                errf.Add(Serious,'row '+str(k+1)+str(v))
        else:
            #print self.SSrows
            dbprint('starting SS processing')
            makeDictionary()
            rowNum=0
            for idNo,row in self.SSData.iteritems():
                doCompareData(idNo,row)
                rowNum+=1
                if rowNum % 100 == 0: dbprint(str(rowNum)+' rows')
            errf.Addpp(['rowstoadd', self.rowsToAdd])
            errf.Addpp(['rowstoupd', self.rowsToUpd])
            errf.close()
        self.checkMessages()
    
    def saveData(self):
        """ now we have processed the file and sorted out the new rows, the updated rows, and left uninteresting stuff behind
        we now have to do the updates and inserts.   """
        errf.openf(self.errfile,'step3')
        dbprint('done processing ss')
        if errf.NotSerious:
            self.openSS()
            for idNo, row in self.SSData.iteritems():
                social = row['mssn']
                self.EffectiveDate = row['meffectivedate']
                self.LoadDate = row['meffectivedate']
                #dbprint(social)
                #
                #people table
                #dbprint('people')
                if idNo in self.rowsToAdd['p']:
                    self.pidDick[idNo] = self.addPerson(self.rowsToAdd['p'][idNo], social, self.EffectiveDate,row['ssRowNo'])
                elif idNo in self.rowsToUpd['p']:
                    self.updatePerson(self.rowsToUpd['p'][idNo],self.pidDick[idNo],self.EffectiveDate,row['ssRowNo'])
                #
                #employee table
                #dbprint('employees')
                if idNo in self.rowsToAdd['e']:
                    self.eidDick[idNo] = addEmployee(self.rowsToAdd['e'][idNo], social, self.pidDick[idNo], self.EmployerId, self.EffectiveDate)
                elif idNo in self.rowsToAdd['p']: # we need to add also if just a person has been added.  
                    #There may be no specific employee columns but still need to add employee
                    self.eidDick[idNo] = self.addEmployee({}, social, self.pidDick[idNo], self.EmployerId, self.EffectiveDate)
                elif idNo in self.rowsToUpd['e']:
                    self.updateEmployee(self.rowsToUpd['e'][idNo], self.eidDick[idNo], self.EffectiveDate)
                #
                # location table
                if (idNo in self.rowsToAdd['l']):
                    self.addLocation(self.rowsToAdd['l'][idNo], self.pidDick[idNo])
                elif idNo in self.rowsToUpd['l']:
                    self.updateLocation(self.rowsToUpd['l'][idNo],self.pidDick[idNo])
                #
                #member table
                #dbprint('members')
                if idNo in self.rowsToAdd['m']:
                    self.midDick[idNo] = self.addMember(self.rowsToAdd['m'][idNo], social, self.pidDick[idNo], self.eidDick[idNo], self.PlanId)
                    self.updateSS(row['ssRowNo'],self.midSScol, self.midDick[idNo])
                elif idNo in self.rowsToUpd['m']:
                    self.updateMember(self.rowsToUpd['m'][idNo], self.midDick[idNo])
                #
                #beneficiary qdro table
                #dbprint ('beneficiary qdros')
                if idNo in self.rowsToAdd['bq']: # first check the idNo is in
                    self.bqidDick[idNo] = self.addBeneficiary(self.rowsToAdd['bq'][idNo], self.midDick[idNo], self.PlanId, self.EffectiveDate)
                elif idNo in self.rowsToUpd['bq']:
                    self.updateBeneficiary(self.rowsToUpd['bq'][idNo], self.bqidDick[idNo], self.EffectiveDate)
                #
                #annuals table
                #dbprint('annuals')
                if idNo in self.rowsToAdd['a']:
                    self.addAnnuals(self.rowsToAdd['a'][idNo], self.midDick[idNo])
                if idNo in self.rowsToUpd['a']: # note we can both add new rows and update rows - because each column represents a row
                    self.updateAnnuals(self.rowsToUpd['a'][idNo], self.midDick[idNo])
                #
                #service table
                #dbprint('service')
                if idNo in self.rowsToAdd['dat']:
                    self.addService(self.rowsToAdd['dat'][idNo], self.eidDick[idNo])
                elif idNo in self.rowsToUpd['dat']:
                    self.updateService(self.rowsToUpd['dat'][idNo],self.DBData.Dick[idNo], self.eidDick[idNo])
                #
                #bh snapshot table
                #dbprint('bcsnapshot')
                # 
                if idNo in self.rowsToAdd['bh']:
                    self.addSnapShot(self.rowsToAdd['bh'][idNo], self.midDick[idNo], self.LoadDate)
                elif idNo in self.rowsToUpd['bh']:
                    self.updatebhSnapShot(self.rowsToUpd['bh'][idNo], self.DBData.Dick[idNo], self.midDick[idNo], self.LoadDate)
                #
                #bc snapshot table
                #dbprint('bhsnapshot')
                # 
                if idNo in self.rowsToAdd['bc']:
                    self.updatebcSnapShot(self.rowsToAdd['bc'][idNo], self.midDick[idNo])
                if idNo in self.rowsToUpd['bc']:
                    self.updatebcSnapShot(self.rowsToUpd['bc'][idNo], self.midDick[idNo])
                #
                #flags table
                #dbprint('flags')
                if idNo in self.rowsToAdd['flg']:
                    self.addFlagValues(self.rowsToAdd['flg'][idNo], [self.midDick[idNo], self.eidDick[idNo], self.pidDick[idNo]],self.EffectiveDate)
                if idNo in self.rowsToUpd['flg']:
                    self.updateFlagValues(self.rowsToUpd['flg'][idNo], [self.midDick[idNo], self.eidDick[idNo], self.pidDick[idNo]], self.EffectiveDate)
            cnxn.commit()
            dbprint('committed to database')
            self.closeSS()
        self.checkMessages()
        
    def openSS(self): # 3 special functions to write out the new mids to the old spreadsheet as they are generated.  
        #1 open the spreadsheet and prepare it for writing
        rb = xlrd.open_workbook(self.fn,formatting_info=True)
        r_sheet = rb.sheet_by_index(0)
        self.wb = xlcopy(rb)
        self.w_sheet = self.wb.get_sheet(0)

    def updateSS(self,rowNo,colNo, data): # 3 special functions to write out the new mids to the old spreadsheet as they are generated.  
        #2 write a row
        self.w_sheet.write(rowNo, colNo, data)
        
    def insertNameInSS(self, dick, rowNo):
        dbprint ('working through insert '+str(rowNo)+str(dick))
        for colName in ['pnamelast','pnamefirst','pnamemiddle','pnamesuffix','pnametitle']:
            if colName in dick:
                if colName in self.colHeads:
                    colNameix = self.colHeads.index(colName)
                    self.updateSS(rowNo,colNameix,dick[colName])
        
    def closeSS(self): # 3 special functions to write out the new mids to the old spreadsheet as they are generated.  
        #3 save
        self.wb.save(self.fn)
        
    def addPerson(self, rowDick, social, effectiveDate, rowNo):
        # these pid checks should not get carried out often, so they should not slow us down
        cursor.execute('select pid from tbperson where pssn = ?',(social,))
        row = cursor.fetchone()
        psex = rowDick.get('psex')
        if not psex: # ie if nothing returned
            rowDick['psex'] = None
        if row:
            key = row.pid
            self.updatePerson(rowDick,key,effectiveDate, rowNo)
        else:
            if 'pnamelast' not in rowDick or not rowDick['pnamelast']:
                (fname, lname, middle, title, suffix, namecomment) = nameFiddle(rowDick['pname'],psex)
                rowDick['pnamelast']=lname
                rowDick['pnamefirst']=fname
                rowDick['pnamemiddle']=middle
                rowDick['pnamesuffix']=suffix
                rowDick['pnametitle']=title
                self.insertNameInSS(rowDick, rowNo)
            sql = sqlIns('tbPerson', rowDick.keys()+['pssn', 'peffectivedate'], 'pid') 
            key = Insert(sql,rowDick.values()+[social, effectiveDate],True) 
        return key
    
    def addEmployee(self,rowDick, social, pid, rid, effectiveDate):
        # same sort of check as for tbperson above
        cursor.execute('select eid from tbemployee where essn = ? and erid = ?',(social,rid))
        row = cursor.fetchone()
        if row:
            key = row.eid
            self.updateEmployee(rowDick,key, effectiveDate)
        else:
            sql = sqlIns('tbEmployee',rowDick.keys()+['essn', 'epid', 'erid','eeffectivedate'], 'eid')
            key = Insert (sql, rowDick.values()+[social, pid, rid, effectiveDate], True)
        return key
    
    def addLocation(self, rowDick, pid):
        cursor.execute('select lpid from tblocation where lpid = ?',(pid,))
        row = cursor.fetchone()
        if row:
            self.updateLocation(rowDick,pid)
        else:
            sql = sqlIns('tblocation',rowDick.keys()+['lpid'])
            Insert(sql, rowDick.values() + [pid])
    
    def addMember (self,rowDickinput, social, pid, eid, planid):
        rowDick = rowDickinput
        for key,val in zip(['mpid','meid','mnid'],[pid,eid,planid]):
            rowDick[key]=val
        rowDick.pop('mid') # we don't want the mid if we are trying to insert
        sql = sqlIns('tbMember',rowDick.keys(), 'mid')
        key = Insert (sql, rowDick.values(), True)
        return key
    
    def addBeneficiary(self,rowDick, mid, planid, effectiveDate):
        sql = sqlIns('tbBeneficiaryqdro',rowDick.keys()+['bqmid', 'bqeffectivedate'], 'bqid')
        key = Insert (sql, rowDick.values()+[mid, effectiveDate], True)
        return key
    
    def addService(self, rowDick, eid):
        #errf.Addpp(['rowDick',rowDick,'eid',eid])
        for code in self.SSservCodes:
            codeNum = servDick[code]
            SSsubset = [(k,v) for k,v in rowDick.iteritems() if v and k[:-1] == code] # the values from the spreadsheet for this code
            if SSsubset: 
                sorted(SSsubset, key = itemgetter(1)) # sort by most recent first
                for service in SSsubset:
                    Insert(sqlSvc,[eid, codeNum, service[1]])
                    #test = 1/0
                    
    def addSnapShot(self, rowDick, mid, loadDate):
        #errf.Addpp(['SSDick',rowDick,'mid',mid])    
        for suff in self.suffixes:
            if suff in ['thisyr','lastyr']:
                AccountType = None
            else:
                AccountType = sshotDick[suff]
            suffDick = dict((k[:-len(suff)],v) for k,v in rowDick.iteritems() if k[-len(suff):] == suff)
            if any (suffDick.values()): #ie if anything here, don't bother to do an insert on empty data.
                if suffDick['bheffectivedate']: # don't insert if no effective date
                    sql = sqlIns('tbbhsnapshot',suffDick.keys()+['bhmid','bhaccounttype','bhloaddate'])
                    Insert(sql,suffDick.values()+[mid,AccountType,loadDate])
                    errf.Addpp(['InsDick',suffDick])
    
    def addAnnuals(self,rowDick, mid):
        for key, value in rowDick.iteritems():
            if value: # this function can receive null values - we do not want to insert nulls
                dateStr = key
                endDate = datetime.strptime(key[-8:],"%Y%m%d")
                testStr = key[:-9]
                stDate  = datetime.strptime(testStr[-8:],"%Y%m%d")
                field = key[:-17]
                acode = annDick[field]
                sql = sqlIns('tbAnnual',['amid','astartdate','aenddate','acode','avalue'])
                Insert (sql, [mid, stDate, endDate, acode,value], False)
        return 
    
    def addFlagValues (self,rowDick, idList, EffectiveDate, force = False): # see flagValuesListOrder below
        """ the force flag will force null values to be entered in the cases where a flag has been updated to null - ie deleted.
        The alternative to this is just to delete ALL the flag history for that person/flag - but it may be interesting to see
        that someone changed flag status a few years ago from value = 3, to value = None"""
        for key,value in rowDick.iteritems():
            if value or force:
                tableCh=key[3]
                tableId = idList[flagValuesListOrder[tableCh]]
                flagId = flagDick[key]
                sql = sqlIns('tbFlagValue',['vfid','vTable','vTableid', 'vEffectiveDate', 'vValue'])
                Insert (sql, [flagId, tableCh, tableId, EffectiveDate, repr(value)])
        return
    
    def updatePerson(self,rowDick,pid, effective_date, rowNo):
        if 'pnamelast' not in rowDick or not rowDick['pnamelast']: # if there is no entry or no value in the pnamelast field then try to create one
            if ('pname' in rowDick) and ('psex' in rowDick): # need name and sex for nameFiddle routine
                (fname, lname, middle, title, suffix, namecomment) = nameFiddle(rowDick['pname'],rowDick['psex'])
                rowDick['pnamelast']=lname
                rowDick['pnamefirst']=fname
                rowDick['pnamemiddle']=middle
                rowDick['pnamesuffix']=suffix
                rowDick['pnametitle']=title
                self.insertNameInSS(rowDick, rowNo)
        if rowDick.values():
            # this next row is an experiment to remove all the None values from the row.  
            #  Columns with None will not be updated as I cannot be sure if this is just ignorance - 
            #  the previous value in the database may be perfectly ok.  If you want to overwrite a value with nothing, you 
            # will have to have something like an empty string "" or 0 as appropriate.
            rowDick_notempty = dict((k,v) for k,v in rowDick.iteritems() if v is not None)
            rowDick_notempty['pEffectiveDate'] = effective_date
            sql = sqlUpd('tbPerson',rowDick_notempty.keys(),['pid'])
            vals = rowDick_notempty.values() + [pid]
            Update (sql,vals)           
        return
    
    def updateEmployee(self,rowDick, eid, effective_date):
        if rowDick.values():
            rowDick['eEffectiveDate'] = effective_date
            sql = sqlUpd('tbEmployee',rowDick.keys(),['eid'])
            Update (sql,rowDick.values()+[eid])
        return
    
    def updateLocation(self, rowDick, pid):
        # check the guy is actually in - this table is optional so it may never have been here before
        cursor.execute('select lpid from tblocation where lpid = ?',(pid,))
        row = cursor.fetchone()
        if row:
            sql = sqlUpd('tblocation',rowDick.keys(),['lpid'])
            Update (sql, rowDick.values() + [pid])
        else:
            sql = sqlIns('tblocation',rowDick.keys()+['lpid'])
            Insert(sql, rowDick.values() + [pid])
    
    def updateMember(self,rowDick, mid):
        if rowDick.values():
            sql = sqlUpd('tbMember',rowDick.keys(),['mid'])
            Update (sql,rowDick.values()+[mid])
        return
    
    def updateBeneficiary(self,rowDick, bqid, effective_date):
        if rowDick.values():
            rowDick['bqEffectiveDate'] = effective_date
            sql = sqlUpd('tbBeneficiaryQDRO',rowDick.keys(),['bqid'])
            Update (sql,rowDick.values()+[bqid])
        return
        
    def updateAnnuals(self,rowDick, mid):
        """ NB if value is something (ie not zero or null) we are going to do an update
               if value is zero / null then we are going to do a delete
               """
        for key, value in rowDick.iteritems():
            dateStr = key
            endDate = datetime.strptime(key[-8:],"%Y%m%d")
            testStr = key[:-9]
            stDate  = datetime.strptime(testStr[-8:],"%Y%m%d")
            field = key[:-17]
            acode = annDick[field]
            if value:
                sql = sqlUpd('tbAnnual',['avalue'],['amid','astartdate','aenddate','acode'])
                Update (sql, [value,mid,stDate, endDate, acode])
            else:
                sql = 'delete from tbannual where amid = ? and acode = ? and astartdate = ? and aenddate = ?'
                cursor.execute(sql,(mid,acode,stDate,endDate))
        return 
            
    def updateService(self,rowDick, DBDick, eid):
        """ first find out if nothing has changed (most likely), 
           if so skip out
           then find out if one extra thing has been added (next most likely)
           if so add one row
           if more than this - ie some things have been edited, some have been added, it is probably easiest
           to delete everything and insert them all again correctly"""
        for code in self.SSservCodes:
            codeNum = servDick[code]
            SSsubset = [(k,v) for k,v in rowDick.iteritems() if v and k[:-1] == code] # the values from the spreadsheet for this code
            DBsubset = [(k,v) for k,v in DBDick.iteritems() if v and k[:-1] == code] # the values from the database for this code
            if DBsubset: DBsubset.sort(key = itemgetter(1)) # sort by most recent first
            if SSsubset: 
                SSsubset.sort(key = itemgetter(1)) # sort by most recent first
                if SSsubset == DBsubset: # then nothing has changed
                    pass
                elif SSsubset[:-1] == DBsubset: # then just the last item in the spreadsheet has been added, insert it
                    Insert(sqlSvc,[eid, codeNum,SSsubset[-1][1]])
                else: # more than one has changed, so delete them and reinsert
                    sql = 'delete from tbservice where seid = ? and scode = ?'
                    cursor.execute(sql,(eid, codeNum))
                    for service in SSsubset:
                        Insert(sqlSvc,[eid, codeNum, service[1]])
    
    def updatebhSnapShot(self,SSDick, DBDick, mid,loadDate):
        
        def deltaDick(ssDick, dbDick):
            """ goes through the spreadsheet dictionary looking for new or changed values from the database
                the deltas are returned for updating"""
            deltas={}
            for k,v in ssDick.iteritems():
                if k in dbDick:
                    if v <> dbDick[k]:
                        deltas[k]=v
                else:
                    deltas[k] = v
            return deltas
        
        def insertBHsnapshot(dick, accounttype):
            FD = dick.pop('bheffectivedate')
            dick = dict((k,v) for k,v in dick.iteritems() if v) # toss out the empties
            sql = sqlIns('tbbhsnapshot',dick.keys()+['bhmid','bhaccounttype','bheffectivedate','bhloaddate'])
            Insert(sql,dick.values()+[mid,accounttype,FD,loadDate])
                
        #errf.Addpp(['SSDick',SSDick,'DBDick',DBDick])    
        SSAccTypDick, DBAccTypDick = {},{}
        # Step 1 - break out the data in SSDick into the different suffixes
        for suff in self.suffixes:
            SSsuffDick = dict((k[:-len(suff)],v) for k,v in SSDick.iteritems() if k[-len(suff):] == suff)
            DBsuffDick = dict((k[:-len(suff)],v) for k,v in DBDick.iteritems() if k[-len(suff):] == suff)
            if suff in ['thisyr','lastyr']:
                if 'bheffectivedate' not in SSsuffDick:
                    SSk = None
                else:
                    SSk = SSsuffDick['bheffectivedate']
                    DBk = DBsuffDick['bheffectivedate']
            else:
                SSk = sshotDick[suff] # so k is the number 104 if suff is 'frozen' etc
                DBk = SSk
            if SSk:
                SSAccTypDick[SSk] = SSsuffDick
                DBAccTypDick[DBk] = DBsuffDick
        # Now process the types of snapshot one by one
        for k, dick in SSAccTypDick.iteritems():
            if isinstance(k,type(DummyDate)) : # ie if this is one of the lastyr / thisyr fields
                if k in DBAccTypDick: # and the same effectivedate is in the database, then we do an update
                    deltas=deltaDick(dick,DBAccTypDick[k])
                    if any (deltas.values()): # if there are any differences then we have to update
                        sql = sqlUpd('tbbhsnapshot',deltas.keys(),['bhid'])
                        Update(sql,deltas.values()+[DBAccTypDick[k]['bhid']]) 
                else: # we have to insert this row because this effective date has not been seen before
                    insertBHsnapshot(dick,None)
            else: # then we have one of the special snapshots - a protected, frozen or whatnot
                if any(DBAccTypDick[k].values()):
                    deltas = deltaDick(dick, DBAccTypDick[k])
                    if any (deltas.values()): # if there are any differences then we have to insert or update
                        sql = 'select bhid from tbbhsnapshot where bhmid = ? and bheffectivedate = ? and bhaccounttype = ? and bhloaddate = ?'
                        cursor.execute(sql,(mid, dick['bheffectivedate'], k, loadDate))
                        row = cursor.fetchone()
                        if row:
                            bhid = row[0]
                            sql = sqlUpd('tbbhsnapshot',deltas.keys(),['bhid'])
                            Update (sql,deltas.values()+[bhid])
                        else:
                            insertBHsnapshot(dick,k) 
                else:
                    if any(dick.values()):
                        insertBHsnapshot(dick,k)

                                 
    def updatebcSnapShot(self,rowDick, mid):
        pass
    
    def updateFlagValues(self,rowDick, idList, EffectiveDate):
        for key,value in rowDick.iteritems():
            tableCh=key[3]
            tableId = idList[flagValuesListOrder[tableCh]]
            flagId = flagDick[key]
            sql = sqlUpd('tbFlagValue',['vValue'],['vfid','vTable','vTableid', 'vEffectiveDate'])
            updateGood = Update (sql, [repr(value), flagId, tableCh, tableId, EffectiveDate], False) # false is the reporting flag - we don't want to report any errors
            if updateGood == -1: # then it was  not a good update
                self.addFlagValues(rowDick,idList,EffectiveDate, True) # true is the force flag - see function
        return
    
#global variables
debug = False
cnxn = accP2()
cursor = cnxn.cursor()
errf = processErr()
sql = 'select cdescription, ccode from tbcodes where cannuals = 1'
annCodes = cursor.execute(sql).fetchall()
annCodes = [(i[0].lower(),i[1]) for i in annCodes]
annDick = dict((i[0],i[1]) for i in annCodes+[code[::-1] for code in annCodes]) # an experiment, can't think of any downside to a dictionary with data in both ways!
sql = 'select ccolumntitle, ccode from tbcodes where cservicecodes = 1'
servCodes = cursor.execute(sql).fetchall()
servCodes = [(i[0].lower(), i[1]) for i in servCodes]
servTitles = [i[0] for i in servCodes]
servCodeNums = [i[1] for i in servCodes]
servDick = dict((i[0],i[1]) for i in servCodes+[code[::-1] for code in servCodes])
sql = 'select cdescription, ccode from tbcodes where csnapshots = 1'
sshotCodes = cursor.execute(sql).fetchall()
sshotDick = dict((i[0].lower(),i[1]) for i in sshotCodes)
sshotDickKeys = sshotDick.keys()
sql = 'select fid, fname from tbFlag'
flagValuesListOrder = {'m':0,'e':1,'p':2}
flagCodes = cursor.execute(sql).fetchall()
flagCodes = [(i[0],i[1].lower()) for i in flagCodes]
flagDick = dict((i[0],i[1]) for i in flagCodes+[code[::-1] for code in flagCodes]) # another dictionary that works both ways
sqlSvc = sqlIns('tbservice',['seid','scode','seffectivedate'])

if __name__ == '__main__':
    sql1="update tbPerson set pNameMiddle = 'Clare', pdatbrth = '1960-11-11' where pssn = '999-09-9999'"
    sql2="update tbMember set mCmnt1 = 'tws' where mssn='999-09-9999'"
    sql3="update tbAnnual set aValue = 1000.01 where aMId = 70994 and aCode = 30 and aStartDate = '2005-01-01'"
    sql4="update tbBHSnapshot set bhBftAri = 2.33 where bhMid = 70994 and bhAccountType = 104"
    sql5="update tbFlagValue set vValue = ? where vFId = 49 and vTable = 'm' and vTableid = 70994 and vEffectiveDate = '2012-01-01'"
    sql6="update tbService set sEffectiveDate = '1979-09-30' where sId = 143367"
    sql7="update tbBeneficiaryQDRO set bqSSNSp = 'norwich' where bqId = 3155"
    sql8 = "delete from tbperson where pssn = '999-09-9997'"
    for sql in [sql1,sql2,sql3,sql4, sql6, sql7, sql8]:
        cursor.execute(sql)
    cursor.execute(sql5,(repr('sshhnk')))
    cnxn.commit()    
    PV=ProValLoad(None, 'c:\pje\dt6.xls', 270, 61, date(2012,1,1), date(2012,1,1)) #- this is a useful small test file
    #PV=ProValLoad(None, 'c:/pje/nacoerase2.xls', 220, 25, date(2012,1,1), date(2012,1,1)) # small naco test file
    PV.checkData()
    PV.saveData()
    dbprint('finished')
  
