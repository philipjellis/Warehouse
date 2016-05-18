from decimal import *
import pyodbc
import wx
from collections import defaultdict, namedtuple
import xlrd
import xlwt
from datetime import date, datetime
from operator import attrgetter, itemgetter
from utilities import *
import csv # for debugging can take this out 
#from ProValLoad import processErr # just for debugging - ie writing out to a file
import time

class Timer:    
    def __enter__(self):
        self.start = time.clock()
        return self

    def __exit__(self, *args):
        self.end = time.clock()
        self.interval = self.end - self.start
        
def createVWallPEMB ():
    """ This strange function creates a view every time it is run.
This view used to just sit in the database like a normal view.
The problem was that every time anyone added a column to (say) the member table
the view has to be updated.  I would forget and this would create a problem.
Now this function will just recreate the view with the new column in it"""

    cst = connStringViewCreate()
    cnxn = pyodbc.connect(cst)
    cursor = cnxn.cursor()
    cols = ['nShortPlanName'] # need this one col from plan table
    for table in ['tbEmployer','tbEmployee','tbMember','tbBeneficiaryQDRO','tbPerson', 'tbLocation']:
        cols += getColHeads(table,cursor)[0]
    badCols = ['rIbCtrlFlag','rPersonFlag','rDatairER','eId','ePid','eRid','eEffectiveDate','eSSN',\
               'bqMid','bqEffectiveDate','pId','pKSS','pEffectiveDate','pSSN','lpid']
    UpCols = [i.upper() for i in cols]
    for c in badCols:
        u = c.upper()
        ix = UpCols.index(u)
        UpCols.pop(ix)
        cols.pop(ix)
    sql = 'drop view vwAllPEMB'
    try:
        cursor.execute(sql)
    except:
        pass # if the view is not there then fine
    cnxn.commit()
    sql = 'create view vwAllPEMB as select '+', '.join(cols)
    sql += ' FROM dbo.tbBeneficiaryQDRO RIGHT OUTER JOIN \
                          dbo.tbMember ON dbo.tbBeneficiaryQDRO.bqMid = dbo.tbMember.mId INNER JOIN \
                          dbo.tbEmployee ON dbo.tbMember.mEId = dbo.tbEmployee.eId INNER JOIN \
                          dbo.tbPerson ON dbo.tbMember.mPId = dbo.tbPerson.pId AND dbo.tbEmployee.ePId = dbo.tbPerson.pId INNER JOIN \
                          dbo.tbEmployer ON dbo.tbEmployee.eRId = dbo.tbEmployer.rId INNER JOIN \
                          dbo.tbPlan ON dbo.tbMember.mNId = dbo.tbPlan.nID left outer join \
                          dbo.tbLocation ON dbo.tbPerson.pid = dbo.tbLocation.lpid '
    #print sql
    cursor.execute(sql)
    cnxn.commit()
    cnxn.close()

class xyz99:
    class getSnapColsTyps:
        # this creates the colnames, coltypes and the bh/bc/.. prefix for the snapshot tables
        # this created as a lookup table for the rest of the program
        def __init__(self,cursor):
            SNTnt = namedtuple('SNTnt','Names Types Pre Id Mid FDate LDate CodSta')
            self.tbl = {}
            for table in Snapshots.keys():
                SnapCols,SnapTypes = getColHeads(table, cursor)
                for ti in ['bhMid','bcMid','bhLoadDate']:#['bhId','bcId','bhMid','bcMid','bhLoadDate']
                    if ti in SnapCols:
                        ix = SnapCols.index(ti)
                        SnapCols.remove(ti) # we don't want the snapshot record id in the titles
                        SnapTypes.pop(ix)
                pre = table[2:4].lower()
                Id = pre+'Id'
                Mid = pre+'mid'
                FDate = pre+'EffectiveDate'
                LDate = pre+'LoadDate'
                CodSta = pre+'CodSta'
                self.tbl[table]=SNTnt(SnapCols,SnapTypes,pre,Id,Mid,FDate,LDate, CodSta)

    def __init__(self, parent, ssnScheme, nID, Year, ssn,  numYears=10, justLatest = False):
        #Set up
        ContYears = numYears #sets number of years back to look for contribution data - used to be 3
        SalYears = numYears # number of years to look back for salary and months comp data
        #self.MaxDate = date(Year,12,31) # last day in year chosen
        self.cnxn = accP2()
        #if lowercase: pyodbc.lowercase = True
        self.cursor = self.cnxn.cursor()

        self.AnnualComp = 'aCmpPln'
        self.MosComp = 'aCmpMosPd'
        createVWallPEMB()
        #PEMB = Person, Employee, Member, BeneficiaryQDRO
        allHeads, allTypes = getColHeads('vwAllPEMB',self.cursor)
        self.snap = self.getSnapColsTyps(self.cursor)
        
        self.colHeads = dict(zip(allHeads, allTypes)) 

        if ssnScheme == 'scheme': # get the set for a scheme
            shortName, Date = self.getSchemeHeads (nID, Year) # takes a year as input - eg 2009, returns a date as start date for that scheme - eg 2009-11-01
            self.title = shortName+' DB Plan' #eg 'PEC DB Plan'
            mainSql = "select "+','.join(allHeads)+" from vwAllPEMB where mNId = ?"
            self.param = nID
            D1 = datetime.datetime.strptime(Date,"%Y-%m-%d")
            # Note D1 the main date gets set globally here for scheme - but gets set for each line if ssn
            midSql = "(select mid from tbmember where mnid = ?)" # this  bit of sql is important it gets the members for a scheme or an individual
            # and gets added to other sql in one or two places     
            eidSql = "(select distinct meid from tbmember where mnid = ?)" # same for eids - needed for service records
            pidSql = "(select distinct mpid from tbmember where mnid = ?)"
        elif ssnScheme == 'ssn': # get the set for a social
            self.ssn = ssn
            mainSql = "select "+','.join(allHeads)+" from vwAllPEMB where mSSN = ?"
            self.param = ssn
            self.title = 'SingleSSN'+self.ssn
            midSql = "(select mid from tbmember where mssn = ?)"
            eidSql = "(select distinct meid from tbmember where mssn = ?)"
            pidSql = "(select distinct mpid from tbmember where mssn = ?)"
        #print mainSql
        self.cursor.execute(mainSql,(self.param,))
        # get all the data and put it into a list 
        self.PEMBData = self.cursor.fetchall() # get rid of any blank columns
        PBDTr = zip(*self.PEMBData) # transpose rows and columns to delete blanks
        blankCols=[]
        colsNeeded = ['bqId'] # this list contains any columns that must be present in the output, even if blank
        for colNo, col in enumerate(PBDTr): 
            if any(col) or allHeads[colNo] in colsNeeded:
                pass # if there is any data in the column, or it is a neeeded column then keep it
            else:
                blankCols.append(colNo)
        blankCols.reverse() # you have to process from the biggest column down - otherwise you mess up the bigger columns
        for colNo in blankCols: 
            col = allHeads.pop(colNo)
            PBDTr.pop(colNo)
            allTypes.pop(colNo)
            del self.colHeads[col]
        self.PEMBData = zip(*PBDTr) #transpose it back to the original data
        #
        # set up the gauge on the screen - need to look back to the parent here
        #
        if ssnScheme == 'scheme' and parent: #only display this if the parent is a wx object, if none, then nothing to display
            self.rnge = len(self.PEMBData)
            gaugeRange = [i*self.rnge/100 for i in range(1,100)]+[self.rnge+1]
            dlg = wx.ProgressDialog("Extract Progress",
                                    "Please wait while I get the records",
                                    maximum = self.rnge,
                                    parent=parent,
                                    style =  wx.PD_APP_MODAL #wx.PD_CAN_ABORT
                                    #| wx.PD_ELAPSED_TIME
                                    #| wx.PD_ESTIMATED_TIME
                                    #| wx.PD_REMAINING_TIME
                                    )
        #
        self.rows = [] # keep all the rows here
        #  let's prepare for getting the details as fast as poss:
        #  First identify some indices
        mIx = allHeads.index('mId')
        pIx = allHeads.index('mPId')
        eIx = allHeads.index('mEId')
        bqIx = allHeads.index('bqId')
        annSql = """select amid, aStartDate, cDescription, aValue, aEndDate from vwannualdetails where amid in """+midSql
        self.cursor.execute(annSql,self.param)
        self.annDick = defaultdict(list)
        for v in self.cursor.fetchall():
            self.annDick[v[0]].append(v[1:])        
        #  get a dictionary of snapshot types
        sql = 'select cDescription, cCode from tbCodes where cSnapShots = 1'
        self.cursor.execute(sql)
        self.SSDick = dict(self.cursor.fetchall())
        #  make a dictionary with all the snapshot rows in it for each snapshot table
        self.SSbigdatalist=[] 
        """ one dictionary goes in self.SSbigdatalist for each type of snapshot table processed
          we are going to pick up all the relevant snapshot rows in the code below
          then we are going to process them under the comment Process SSbigdatalist
          """
        for table, idField in Snapshots.iteritems() : #always process in this order and you will always pick up the right dictionary
            snap = self.snap.tbl[table]
            ssSql = 'select '+idField+','+','.join(snap.Names) + ' from '+table+' where '+idField+' in '+midSql
            self.cursor.execute(ssSql, self.param)
            bigSSdata = defaultdict(list)
            for v in self.cursor.fetchall():
                bigSSdata[v[0]].append(v[1:])
            self.SSbigdatalist.append(bigSSdata)
        # make a dictionary with all the service rows in it - remember service rows are keyed by employee not member
        servSql = 'select seid, ccolumntitle, seffectivedate from vwservicetitles where seid in '+eidSql
        self.cursor.execute(servSql,self.param)
        self.servDick = defaultdict(list)
        for v in self.cursor.fetchall():
            self.servDick[v[0]].append(v[1:])
        # make 3 dictionaries with all the flags in
        self.mFlagDick = defaultdict(list)
        self.eFlagDick = defaultdict(list)
        self.pFlagDick = defaultdict(list)
        for tablech, dick, sql in zip(['m','e','p'],[self.mFlagDick,self.eFlagDick,self.pFlagDick], [midSql,eidSql,pidSql]):
            flagSql = 'select vtableid, veffectivedate, fname, vvalue, ftype from vwflagDetails where vtable = ? and vtableid in '+sql
            self.cursor.execute(flagSql,(tablech,self.param))
            for v in self.cursor.fetchall():
                dick[v[0]].append(v[1:])
        for rownum, row in enumerate(self.PEMBData):
            self.rowDick = dict(zip(allHeads, row))
            mId = row[mIx]
            pId = row[pIx]
            eId = row[eIx]
            bqId = row[bqIx]
            if not bqId:
                bqId = 0
            ER = row[allHeads.index('rTLA')]
            if ER == 'TYL': #kludge to force Tyler to be 50, feel free to improve
                SalYears = 50
            else:
                SalYears = ContYears
            if ssnScheme == 'ssn':
                effDix = allHeads.index('mEffectiveDate')
                effD = row[effDix]
                D1 = effD
            else:
                if parent:
                    if (rownum > gaugeRange[0]):
                        dlg.Update(rownum)
                        while rownum > gaugeRange[0]: gaugeRange.pop(0)
            thisYear = D1.year
            self.firstSalYear = thisYear - SalYears  -1
            self.firstContYear = thisYear - ContYears 
            for key, table, data in zip([pId,eId,mId], PEM, [self.pFlagDick,self.eFlagDick,self.mFlagDick]): #Only Person, Employee and Member tables can have flags attached
                for (colName, colData, colType) in self.getFlags(key,table, data): 
                    self.AddDataAndCols(colName, colData, colType)
            # Get the relevant Annual data items, and add the annuals to the Headings and Data 
            for (colName, colData) in self.getAnns(mId): self.AddDataAndCols(colName, colData, 'decimal')
            #
            #Process SSbigdatalist
            #
            # Do the following for both the Benefit History and Benefit Contribution snapshots - otherwise same as before
            #  May need to add new snapshot for retiree medical
            for table, data in zip(Snapshots.keys(),self.SSbigdatalist):
                for (ssCol, ssData, ssType) in self.getSnap(mId, table, data): self.AddDataAndCols(ssCol, ssData, ssType)
            # And finally do the service records
            for (svcName, svcData, svcType) in self.getService(eId, justLatest): self.AddDataAndCols(svcName, svcData, svcType)
            self.rows.append(self.rowDick)
       
        # sort them in the funny sequence - modify it by messing around with SortSeq
        self.fieldsSorted = [self.sortSeq(fld) for fld in self.colHeads.keys()]  #prefix with sort prefix
        self.fieldsSorted.sort() #do the sort
        self.fieldsSorted = [fld[1:] for fld in self.fieldsSorted] # remove the prefix
        for rw in self.rows:
            for fld in self.fieldsSorted:
                if fld not in rw: rw[fld] = None
        self.OutData = [[row[field] for field in self.fieldsSorted] for row in self.rows]
        self.Fields = self.fieldsSorted #self.rowDick.keys()
        self.Types = [self.colHeads[i] for i in self.Fields]
        self.Types = [i if 'aCmp' not in j else 'money' for i,j in zip(self.Types,self.Fields)]

        self.cnxn.close()
        if ssnScheme == 'scheme' and parent : dlg.Destroy()
        
    def makeDick(self, colHeads, lowerCase = False):
        def lower_keys(d):
            if lowerCase:
                if type(d) is dict:
                    return dict([(k.lower(), lower_keys(v)) for k, v in d.items()])
                else:
                    return d
            else:
                return d
        self.Dick = dict((row['mId'], lower_keys(row)) for row in self.rows)
        for key in self.Dick:
            for col in colHeads:
                if col not in self.Dick[key]:
                    self.Dick[key][col]=None
        #now fix any blank cells.  Strip any spaces, and turn '' into None
        for key in self.Dick:
            for col in self.Dick[key]:
                try:
                    test = self.Dick[key][col].strip()
                    if not test:
                        self.Dick[key][col] = None
                except:
                    pass
                    
        
            
        
    def AddDataAndCols(self, colName, colData, colType):
        if colName not in self.colHeads: self.colHeads[colName] = colType
        self.rowDick[colName] = colData

    def getSchemeHeads(self, nID, Year):
        sql = 'select nshortplanname, nstartdate from tbplan where nID = ?'
        self.cursor.execute(sql,nID)
        row = self.cursor.fetchall()
        if len(row) == 0: #error invalid scheme identifier
            shortName = 'InvalidPlanIdPleaseCheck'
            startDate = Year
        else:
            shortName = row[0][0]
            startDate = str(Year)+'-'+str(row[0][1])
        return shortName, startDate

    def WriteSS (self, outfn):
        NNCols = ['nshortplanname','rname', 'rtla', 'bqid', 'meid', 'mnid', 'mpid', 'rid','bhid','bcid'] # mId?? columns not needed for output
        """ These columns should stil be output onto the IBControl screen so if people want to edit them, they can see the right ID fields"""
        cnxn = accP2()
        cursor = cnxn.cursor()
        datefield = 1
        genfield = 2
        numfield = 3
        moneyfield = 4
        intfield = 5
        sql='select cMoney from tbcodes where cdescription = ?'
        wb = xlwt.Workbook()
        ws0 = wb.add_sheet(self.title)
        dateStyle = xlwt.easyxf(num_format_str='MM/DD/YYYY')
        currStyle = xlwt.easyxf(num_format_str = '$#,##0.00')
        genStyle = xlwt.easyxf(num_format_str = 'general')
        numStyle = xlwt.easyxf(num_format_str="#,###.00")
        intStyle = xlwt.easyxf(num_format_str="#,###")
        colStyles, colFlds = [], []
        self.fieldsSorted = [col for col in self.fieldsSorted if col.lower() not in NNCols]
        self.fieldsSorted = [col for col in self.fieldsSorted if col[:4].lower() not in NNCols] # get the bhId and bcID, which have had suffixes added
        for colNum, fld in enumerate(self.fieldsSorted): # write the col headings, prepare list of column styles
            ws0.write(0,colNum,fld)
            if self.colHeads[fld] == 'date':
                st = dateStyle
                f = datefield
            elif self.colHeads[fld] == 'money':
                st = currStyle
                f = moneyfield
            elif self.colHeads[fld] == 'decimal':
                st = numStyle
                f = numfield
            elif self.colHeads[fld] in ['int','smallint','tinyint']:
                st = intStyle
                f = intfield            
            else:
                st = genStyle
                f = genfield
            #  check if it is an annual field.  If it is, and it is money, then make the field currency
            if fld[0] == 'a':
                test = fld
                while not test.isalpha(): test = test[:-1] # strip off the date string to leave the tbCodes field
                cursor.execute(sql,test)
                data = cursor.fetchone()
                if data:
                    if data[0] : 
                        st = currStyle
                        f = moneyfield
            colStyles.append(st)
            colFlds.append(f)
        

        with Timer() as t:
            for rowNum, row in enumerate(self.rows):
                dataRow = [None if field not in row else row[field] for field in self.fieldsSorted]
                for colNum, (f, data) in enumerate(zip(colFlds,dataRow)):
                    if not data:
                        pass # don't waste time
                    else:
                        try:
                            data = data.decode('latin-1')
                        except:
                            pass
                        if f == genfield:
                            ws0.write(rowNum+1,colNum,data,genStyle)
                        elif f == numfield :
                            ws0.write(rowNum+1,colNum,data, numStyle)
                        elif f == moneyfield:
                            ws0.write(rowNum+1,colNum,data, currStyle)
                        elif f == datefield:
                            ws0.write(rowNum+1,colNum,data, dateStyle)
                        elif f == intfield:
                            ws0.write(rowNum+1,colNum,data, intStyle)
                        else:
                            print 'aargh',colNum,rowNum,data
        try:
            wb.save(outfn)
            result = rowNum + 1 #rownum starts from zero
        except:
            result = 0
            msg = 'Could not save spreadsheet '+outfn+'.\nPlease check the filename is good and the sheet is not open.\n'+str(result)+' rows processed.'
            print msg
        #outf = open('c:/pje/eraseme/test.csv','wb')
        #outfw = csv.writer(outf,dialect='excel')
        #keys = self.rows[0].keys()
        #outfw.writerow(keys)
        #for row in self.rows:
        #    data = [row[k] for k in keys]
        #    outfw.writerow(data)
        #outf.close()
        #print('ssWrite took %.03f sec.' % t.interval)        
        return result

    def outStringTable(self):
        result = [self.Fields]
        moneyAnnuals = [True if self.AnnualComp in fld else False for fld in self.Fields]
        typs = ['money' if mon == True else col for mon,col in zip(moneyAnnuals,self.Types)]
        # the Annual Comp is money - but the annual field is a decimal - need to convert the type
        # will need to extend this to cope with more money annual fields should we get any
        for row in self.OutData:
            strinrow = [convert(col,typ) for col,typ in zip(row,typs)]
            result.append(strinrow)
        rslt = zip(*result)
        for i in range(len(rslt)):
            row = rslt.pop(0)
            tst = row[1:]
            if set(tst) - EmptSet <> set([]): rslt.append(row)
        return rslt

    def sortSeq(self,s):
        #s = s.upper()
        if s[-2:] == 'Id':
            return 'z'+ s
        elif s[0] == 'n':
            return '0'+s
        elif 'MSSN' in s.upper():
            return '1'+s
        elif s[0] == 'p':
            return '2'+ s
        elif s[0] == 'e':
            return '3' + s
        elif s[0] == 'm':
            return '4' + s
        elif s[0] == 'a':
            return '5' + s
        elif s[0] == 'S':
            return '6' + s
        elif s[0:2] == 'bh':
            if s[-6:] == 'ThisYr':
                return '7' + s
            elif s[-6:] == 'LastYr':
                return '8' + s
            else:
                return '9' + s
        elif s[0:2] == 'bc':
            return 'a' + s
        elif s[0:2] == 'bq':
            return 'b' + s
        elif s[0:3] == 'flg':
            return 'c' + s
        else:
            return 'y'+s

    def getFlags (self, Id, Table, Data):
        result = []
        Fdata = sorted(Data[Id], key = itemgetter(1)) #first thing is to get the rows for the ID and sort by name
        Fdata = [ [i[0],i[1],eval(i[2]) ,i[3]] for i in Fdata]
        fNames = set([i[1] for i in Fdata])
        for name in fNames:
            subData = [i for i in Fdata if (i[1] == name) ]
            subData.sort() #will naturally sort by date as this the first column in the sql above
            if subData: 
                latest = subData[-1]
                result.append((latest[1], latest[2], latest[3])) # return the latest items for each flag type
        return result

    def getAnns (self, Id):
        result = []
        AnnDetails = self.annDick[Id] 
        fNames = set([i[1] for i in AnnDetails]) #set of annual codes retrieved
        for name in fNames:
            subDetails = [i for i in AnnDetails if (i[1] == name) and (i[2] not in EmptSet)] #select all rows for this code if value not Empty
            subDetails.sort() # will sort in date order (date the first field)
            while len(subDetails) > 0 : #go through line by line
                temp = subDetails.pop()
                if temp[1] in [self.AnnualComp, self.MosComp]:
                    # 10 years data (or whatever) for these fields, 3 for the rest
                    firstYear = self.firstSalYear
                else:
                    firstYear = self.firstContYear
                    # Cont and everything except salary just gets 3 years, salaries get 10 records
                if temp[0].year >= firstYear:
                    if not isinstance(temp[3],date): temp[3] = date(temp[0].year+1,temp[0].month,temp[0].day)
                    strst = temp[0].strftime("%Y%m%d")
                    stren = temp[3].strftime("%Y%m%d")
                    name = temp[1]+strst+'_'+stren
                    result.append([name,temp[2]]) #temp[2] is the value, see above
        return result

    def getSnap (self, Id, snaptable, data):
        
        def addRow(row, suffix):
            for colNo, col in enumerate(row):
                if col:
                    if 'AccountType' not in SnapCols[colNo]:
                        result.append((SnapCols[colNo]+suffix, col, SnapTypes[colNo]))
        
        result = []
        snapRows = data[Id]
        Snap = self.snap.tbl[snaptable]
        SnapCols = Snap.Names
        SnapTypes = Snap.Types
        AccountTypeName = Snap.Pre+'AccountType'
        AccountTypeIx = SnapCols.index(AccountTypeName)
        FDIx = SnapCols.index(Snap.FDate)
        CodStaIx = SnapCols.index(Snap.CodSta)
        IdIx = SnapCols.index(Snap.Id)
        annRows = [row for row in snapRows if not row[AccountTypeIx]] # chooses rows with null accounttypes - ie annual rows
        annRowsS = sorted(annRows, key=itemgetter(FDIx)) # sorts annual rows newest first\
        if annRowsS: 
            ThisY = annRowsS.pop()
            addRow(ThisY,'ThisYr')
        if annRowsS: 
            lastYRow = annRowsS.pop() # only want codsta from last yr
            result.append((Snap.CodSta+'LastYr',lastYRow[CodStaIx],SnapTypes[CodStaIx]))
            result.append((Snap.FDate+'LastYr',lastYRow[FDIx],SnapTypes[FDIx]))
            result.append((Snap.Id+'LastYr',lastYRow[IdIx],SnapTypes[IdIx]))
        for k,v in self.SSDick.iteritems():
            # look for all the items in snapRows with this code
            DickTyps = [row for row in snapRows if row[AccountTypeIx] == v]
            if DickTyps:  # then sort and take the most recent
                DickTypsS = sorted(DickTyps, key=itemgetter(FDIx))
                addRow(DickTypsS.pop(),k)
        return result

    def getService (self, eId, justLatest = False):
        result = []
        if not justLatest:
            data = self.servDick[eId]
            titles = set([i[0] for i in data]) #usually this is just ['HireDat','TermDat'] - can easily be extended, probably automatically
            titDick = dict((i,0) for i in titles) #just stores the integer we have got to - eg HireDat: 3, TermDat : 2
            for row in data:
                result.append((row[0]+str(titDick[row[0]]),row[1],'date'))
                titDick[row[0]] += 1
        else:
            # we are just going for first hiredate, most recent term date, most recent rehiredate
            # PJE note this bit 'never' gets executed I think, (maybe for THA).  If you have some slow plans, this will be a possible reason
            HireCode = 1
            TermCode = 2
            # First hire
            sql = 'select min(seffectivedate) from vwServiceTitles where seid = ? and sCode = ?'
            self.cursor.execute(sql,(eId,HireCode))
            data = self.cursor.fetchall()
            if len(data) == 0:
                result.append(('sFirstHireDat',None,'date'))
            else:
                result.append(('sFirstHireDat',data[0][0],'date'))
            #Last Hire
            sql = 'select max(seffectivedate) from vwServiceTitles where seid = ? and sCode = ?'
            self.cursor.execute(sql,(eId,HireCode))
            data = self.cursor.fetchall()
            if len(data) == 0:
                result.append(('sLastHireDat',None,'date'))
            else:
                result.append(('sLastHireDat',data[0][0],'date'))
            #Last term 
            sql = 'select max(seffectivedate) from vwServiceTitles where seid = ? and sCode = ?'
            self.cursor.execute(sql,(eId,TermCode))
            data = self.cursor.fetchall()
            if len(data) == 0:
                result.append(('sLastTermDat',None,'date'))
            else:
                result.append(('sLastTermDat',data[0][0],'date'))
        return result

printout = True
if __name__ == '__main__':
#   Here is the init from above...
#    def __init__(self, flag, nID, Year, ssn, salyrs, justLatest):
#   the parameters are as follows
#   FLAG is scheme or ssn - tells the program to extract everyone for a scheme
#        or just everyone with a certain social
#   nID is the plan identifier (from tbPlan)
#   YEAR is the text year you want to start from - eg 2009   
#   SSN is  only included if you are doing a single social
#   SALYRS is the number of salary years you want to pull off.  If you want
#   them all - as for Tyler - just put a big number like 50 in.
#
#   OUTFN is the filename you want. Put it in quotes: "c:/My Directory/My File.xls"
    """
    import sys
    flag = sys.argv[1]
    nID = sys.argv[2]
    year = sys.argv[3]
    numYears = sys.argv[4]    
    outfn = sys.argv[5]
    dataSet = xyz99(flag, nID, year, None, numYears)
    rowswr = dataSet.WriteSS(outfn)
    print 'Finished, ',rowswr, ' rows written to ', outfn """
##else:
    # this remaining just here for testing - will be commented out
    #ssn = '129-26-2205'
    #dataSet = xyz99('scheme',237,'2009',None,)
    #dataSet = xyz99('ssn',None,None,ssn)
    #print 'done dataSet'



