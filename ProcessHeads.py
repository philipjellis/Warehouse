import xlrd
from collections import namedtuple
from utilities import *
from datetime import date, datetime


class Constants:
    """ a pile of constants and whatnot"""
    TLookup = {'p':'tbPerson','e':'tbEmployee','m':'tbMember','bh':'tbBHSnapshot','bc':'tbBCSnapshot','bq':'tbBeneficiaryQDRO'}
    
    TD = {}
    
    cnxn = accP2()
    cursor = cnxn.cursor()
    for table in TLookup.values():
        sql = "select COLUMN_NAME,DATA_TYPE from INFORMATION_SCHEMA.COLUMNS where TABLE_NAME = '{0}'"
        sql = sql.format(table)
        cursor.execute(sql)
        ColTypes = dict((i[0],i[1]) for i in cursor.fetchall())
        TD[table] = ColTypes
        
    LongWayOff = date(3000,1,1)
    TLookup['a'] = 'tbAnnual'
    TLookup['f'] = 'tbFlagValues'
    TLookup['s'] = 'tbService'
    sqlf = 'select fName, fId, fType from tbFlag'
    sqla1 = 'select cDescription, cCode from tbCodes where cAnnuals = 1'
    sqla2 = 'select cDescription, cCode from tbCodes where cMoney = 1'
    sqls = 'select cColumnTitle, cCode from tbCodes where cServiceCodes =1 and cMoney = 0'
    sqlss = 'select cDescription, cCode from tbCodes where cSnapShots = 1'
    sqlER = 'select rId from tbemployer'
    sqlSch = 'select nId from tbPlan'
    #flags
    cursor.execute(sqlf)
    FlagData = cursor.fetchall()
    FAS = namedtuple('FAS','Name Id Typ') # tuple to store data about flag, annuals, service
    Flags = [FAS(row[0].strip(),row[1],row[2].strip()) for row in FlagData]
    ColTypes = dict((i.Name,i.Typ) for i in Flags)
    TD['tbFlagValues'] = ColTypes
    #annuals
    cursor.execute(sqla1)
    Annuals = [FAS(row[0],row[1],'decimal') for row in cursor.fetchall()]
    cursor.execute(sqla2)
    Annuals += [FAS(row[0],row[1],'money') for row in cursor.fetchall()]
    ColTypes = dict((i.Name,i.Typ) for i in Annuals)
    TD['tbAnnual'] = ColTypes
    # service
    cursor.execute(sqls)
    Service = [FAS(row[0],row[1],'Date') for row in cursor.fetchall()]
    SvcCodes = [i.Id for i in Service]

    ColTypes = dict((i.Name,'Date') for i in Service)
    TD['tbService'] = ColTypes
    # snapshots
    cursor.execute(sqlss)
    SSData = [FAS(row[0],row[1],'') for row in cursor.fetchall()]
    SSCodeLookUp = dict((i[0],i[1]) for i in SSData)
    SSDescLookUp = dict((i[1],i[0]) for i in SSData)
    #Employers
    cursor.execute(sqlER)
    Employers = [i[0] for i in cursor.fetchall()]
    #Schemes
    cursor.execute(sqlSch)
    Schemes = [i[0] for i in cursor.fetchall()]

class EmptyCol:
    def __init__(self, Num, Name):
        self.Num = Num
        self.Name = Name
        self.error = ''
        
class C:
    """ 
    This class contains the set up details for a column and carries out 
    some checks depending on the column to make sure it is valid.  Invalid
    columns will be flagged and not processed.
    """
    def __init__(self,chs,colName,colNum,Map,Heads, K):
        self.error = ''
        self.table = K.TLookup[chs]
        self.colName = colName
        self.colNum = colNum
        self.effD = None
        self.Typ = None
        self.code = None
        self.tablePtr = None
        self.suffix = None # this is the suffix such as 'Last Year' on a snapshot field
        if chs == 'a':
            oldCol = self.colName #just keep this in case of an error message
            enDstr = self.colName[-8:]
            self.colName = self.colName[:-9] #misses out the underscore
            stDstr = self.colName[-8:]
            self.colName = self.colName[:-8] # whatever remains after stripping off the dates
            try:
                enD = datetime.strptime(enDstr,"%Y%m%d")
                stD =  datetime.strptime(stDstr,"%Y%m%d")
                self.startDate = date(stD.year, stD.month, stD.day)
                self.endDate = date(enD.year, enD.month, enD.day)
            except:
                self.error += '\n'+oldCol+' invalid date in annual column'
        elif chs == 'f':
            self.tablePtr = self.colName[3] # p,m,e to point to table
        elif chs == 's':
            self.colName = self.colName[:-1] # miss out the last char (1,2,3...)
        elif chs in SnapshotPrefixes:
            #1 strip out the suffix
            suffixes = ['Latest']+[i.Name for i in K.SSData]
            codes = [None,None]+[i.Id for i in K.SSData]
            notFound = True
            for sn, suff in enumerate(suffixes):
                ls = len(suff)
                if self.colName[-ls:] == suff:
                    self.code = codes[sn]
                    self.suffix = suff
                    self.colName = self.colName[:-ls]
                    notFound = False
            if notFound: self.error+='\n'+self.colName+' invalid suffix in snapshot'
            #2 get the effective Date
            # do not do this for now - process in the 
        if self.colName not in K.TD[self.table]:
            self.error += '\n'+self.colName+' not in '+self.table
        else:
            self.Typ = K.TD[self.table][self.colName]
        if self.error == '':
            if chs == 'a':
                # Here are the annual names from the named tuple
                aNames = [i.Name for i in K.Annuals]
                # Here is the index of the name we are dealing with
                tempIx = aNames.index(self.colName)
                #Here is the named tuple
                tempNT = K.Annuals[tempIx]
                self.code = tempNT.Id
            elif chs == 'f':
                fNames = [i.Name for i in K.Flags]
                tempIx = fNames.index(self.colName)
                tempNT = K.Flags[tempIx]
                self.code = tempNT.Id
            elif chs == 's':
                sNames = [i.Name for i in K.Service]
                tempIx = sNames.index(self.colName)
                tempNT = K.Service[tempIx]
                self.code = tempNT.Id
            Map.append(colNum)
            Heads.append(self.colName)
            
class processHeads:
    """ 
    This class creates some global variables to hold headings and 
    column maps, and it creates a list of Columns - all of class C.  
    Each column contains appropriate class details for that column and
    also an error message if the column is invalid for some reason
    """
    def __init__ (self,inFile,errf,K):
        # set up the column headings for each table
        self.pHeads, self.mHeads, self.eHeads, self.bhHeads = [], [], [], []
        self.bcHeads, self.aHeads, self.fHeads, self.sHeads = [], [], [], []
        self.bqHeads = []
        
        # now the Map of col numbers in the XL file to each table
        self.pMap, self.mMap, self.eMap, self.bhMap = [], [], [], []
        self.bcMap, self.aMap, self.fMap, self.sMap = [], [], [], []
        self.bqMap = []
        # the following four FD (EffectiveDate) lists are purely to insert the EffectiveDate
        # field into the required tables - the spreadsheet has the mEffectiveDate and the bh/bc EffectiveDates
        # and no others (to avoid confusion).  This puts the others back.
        FDMap = [self.pMap,self.eMap, self.bqMap]
        FDNames = ['p','e','bq']
        FDHeads = [self.pHeads,self.eHeads,self.bqHeads]
        # now a set of indexes to make it easy to get ids - eg pId and mId
        self.pIx, self.mIx, self.eIx, self.SSNix = 0,0,0,0
        self.bqIx, self.FDix, self.Sexix, self.Fnameix = 0,0,0,0
        self.cols = []
        #set up the list of column details - each item is an instance of the class C
        #  the items are in the same order as the columns in the spreadsheet
        # 
        book = xlrd.open_workbook(inFile)
        sht = book.sheet_by_index(0) #assume always sheet 0
        self.colHeads  = [sht.cell_value(0,col) for col in range(sht.ncols)] 
#        
        for colNum, col in enumerate(self.colHeads):
            if col[0] == 'p':
                self.cols.append(C('p',col,colNum,self.pMap,self.pHeads,K))
            elif col[0] == 'm':
                self.cols.append(C('m',col,colNum,self.mMap,self.mHeads,K))
            elif col[0] == 'e':
                self.cols.append(C('e',col,colNum,self.eMap,self.eHeads,K))
            elif col[:2] == 'bh':
                self.cols.append(C('bh',col,colNum,self.bhMap,self.bhHeads,K))
            elif col[:2] == 'bc':
                self.cols.append(C('bc',col,colNum,self.bcMap,self.bcHeads,K))
            elif col[:2] =='bq':
                self.cols.append(C('bq',col,colNum,self.bqMap,self.bqHeads,K))
            elif col[0] == 'a':
                self.cols.append(C('a',col,colNum,self.aMap,self.aHeads,K))
            elif col[0] == 'f':
                self.cols.append(C('f',col,colNum,self.fMap,self.fHeads,K))
            elif col[:3] == 'Dat':
                self.cols.append(C('s',col,colNum,self.sMap,self.sHeads,K))
            else:
                self.cols.append(EmptyCol(colNum,col))
        #chlist=[self.colHeads,self.pHeads, self.mHeads, self.eHeads, self.bhHeads,self.bcHeads, self.aHeads, self.fHeads, self.sHeads ]
       # strlis = ['self.colHeads','self.pHeads', 'self.mHeads','self.eHeads', 'self.bhHeads','self.bcHeads', 'self.aHeads', 'self.fHeads','self.sHeads' ]
                
        #if len(self.pMap) > 0: # 
        if 'mPId' in self.mHeads:
            self.pIx = self.colHeads.index('mPId')
        else:
            errf.Add(Setup, 'I need a column named mPId for the index to tbPerson\n')
        #if len(self.eMap) > 0:
        if 'mEId' in self.mHeads:
            self.eIx = self.colHeads.index('mEId') 
        else:
            errf.Add(Setup, 'I need a column named mEId for the index to tbEmployee\n')
        #if len(self.mMap) > 0:
        if 'mId' in self.mHeads:
            self.mIx = self.colHeads.index('mId') 
            self.tossOut('mId',self.mHeads,self.mMap)
        else:
            errf.Add(Setup, 'I need a column named mId for the index to tbMember\n')
        if 'mSSN' in self.mHeads:
            self.SSNix = self.colHeads.index('mSSN')
        else:
            errf.Add(Setup,'I need a column named mSSN to help add data to tbEmployee and tbMember\n')
        if 'pSex' in self.pHeads:
            self.Sexix = self.colHeads.index('pSex')
        else:
            errf.Add(Setup,'I need a column named pSex to help split up the name into name, title etc\n')
        if 'pNameFirst' in self.pHeads:
            self.Fnameix = self.colHeads.index('pNameFirst')
        else:
            errf.Add(Setup,'I need a column named pNameFirst to help split up the name into name, title etc\n')
        if 'pName' in self.pHeads:
            self.Nameix = self.colHeads.index('pName')
        else:
            errf.Add(Setup,'I need a column named pName to help split up the name into name, title etc\n')
        if 'pNameLast' in self.pHeads:
            self.Lnameix = self.colHeads.index('pNameLast')
        else:
            errf.Add(Setup,'I need a column named pNameLast to help split up the name into name, title etc\n')
        if 'pNameMiddle' in self.pHeads:
            self.Mnameix = self.colHeads.index('pNameMiddle')
        else:
            errf.Add(Setup,'I need a column named pNameMiddle to help split up the name into name, title etc\n')
        if 'pNameTitle' in self.pHeads:
            self.Titleix = self.colHeads.index('pNameTitle')
        else:
            errf.Add(Setup,'I need a column named pNameTitle to help split up the name into name, title etc\n')
        if 'mEffectiveDate' in self.mHeads:
            self.FDix = self.colHeads.index('mEffectiveDate')
            for hds,mp,chs in zip(FDHeads, FDMap, FDNames):
                hds.append(chs+'EffectiveDate')
                mp.append(self.FDix)
        else:
            errf.Add(Setup, 'I need a column called mEffectiveDate to get the correct date\n')
        if 'bqId' in self.bqHeads:
            self.bqIx = self.colHeads.index('bqId')
            self.tossOut('bqId',self.bqHeads,self.bqMap)
        else:
            errf.Add(Setup,'I need a column named bqId for the index to tbBeneficiaryQDRO\n')
        if 'rId' in self.colHeads:
            self.ridIx = self.colHeads.index('rId')
        else:
            errf.Add(Setup, 'I need a column called rId with the code to identify the employer\n')
        if 'mNId' in self.colHeads:
            self.nidIx = self.colHeads.index('mNId')
        else:
            errf.Add(Setup, 'I need a column called mNId to identify the plan code\n')

    def tossOut(self,key,lis1,lis2):
        ix = lis1.index(key)
        lis1.pop(ix)
        lis2.pop(ix)
   
