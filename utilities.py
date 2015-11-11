import pyodbc
from decimal import Decimal
import datetime
import sys
#import locale
from collections import namedtuple
from string import ascii_letters
import os
import wx
# some constants
""" HERE IS THE TEST VARIABLE _ CHANGE THIS TO MOVE TO TEST or PROD """
test = False

"""  End of Test variable! """
tbPersonKey = ['pId']
tbEmployeeKey = ['eId']
tbMemberKey = ['mId']
tbBHSnapShotKey = ['bhId']
tbBCSnapShotKey = ['bcId']
tbBQkey = ['bqId']
tbAnnualKey =['aMid','aStartDate','aCode']
tbFlagValueKey = ['vfId','vTable','vTableid','vEffectiveDate']
tbServiceKey = ['sId']
#table names
AnnualTable = 'tbAnnual'
IBControlTable = 'tbIbctrl'
EmployerTable = 'tbEmployer'
ServiceTable = 'tbService'
DetailTable = 'tbFinRecs'
PersonTable = 'tbPerson'
EmployeeTable = 'tbEmployee'
MemberTable = 'tbMember'
bhSnapShotTable = 'tbBHSnapshot'
bcSnapShotTable = 'tbBCSnapshot'
PayTable = 'tbPayRecords'
FlagValueTable = 'tbFlagValue'
bqTable = 'tbBeneficiaryQDRO'
LocationTable = 'tblocation'

PEM = (PersonTable, EmployeeTable, MemberTable)
Snapshots =  {bhSnapShotTable: 'bhMid',bcSnapShotTable: 'bcMid'} #lookup table giving member key field for a snapshot
SnapshotPrefixes = ['bh','bc'] # add more if new snapshot tables created eg Retiree Medical
DummyDate = datetime.date(2000,1,1) # just used for comparing date types to
#some standard error codes
Serious = 'Serious'
Setup = 'Setup'
Data = 'Data'
Normal = 'Normal'
# add others if  you need them

CambridgeBlue = '#AFEEEE'
LightBrown = '#FFFACD'
LightPink = '#FFAEB9'
LightGreen = '#C1FFC1'
LightBlue = '#87CEFA'

EmptSet=set(['',' ','.',None,'None', '$0.00',chr(32),chr(10)]) # try this one now we are processing zeroes
#locale.setlocale( locale.LC_ALL, 'en_CA.UTF-8' )
""" 
ConnStrings contains all the connection strings.   Open the file to see how it is arranged
In brief line 1 is normal test, 3 is normal prod, 5 is view create test, 7 is view create prod
Normal use of this program in production requires both line 3 and line 7 - they are returned by the two connectionString functions below
"""
def ConnString (lineNum): 
    CstFilName = 'l:\\warehouse\lz\connStrings.txt'
    CstF = open(CstFilName,'r')
    ConnStrings = CstF.readlines()
    CstF.close()
    return ConnStrings[lineNum].strip()

def accP2(): # simple read access
    return pyodbc.connect(connectionString())

def connectionString(): 
    if test :
        CS = ConnString(1)
    else:
        CS = ConnString(3)
    #print CS, ' normal connection string'
    return CS

def connStringViewCreate():
    if test :
        CS = ConnString(5)
    else:
        CS = ConnString(7)
    #print CS, ' view create string'
    return CS

def sniCn(): #gets the connection for Scripps
    cst = ConnString(9) # this gets the SNI Monthly database
    pyodbc.lowercase=True
    return pyodbc.connect(cst)

def getColHeads(table, cursor, lower = False):
    sql2 = "select COLUMN_NAME, DATA_TYPE from INFORMATION_SCHEMA.COLUMNS where TABLE_NAME = ?"
    cursor.execute(sql2,table)
    dat = cursor.fetchall()
    cols = [i[0] for i in dat]
    typs = [i[1] for i in dat]
    if lower:
        cols = [i.lower() for i in cols]
        typs = [i.lower() for i in typs]
    return cols, typs

def getColDetails(table, cursor):
    def low(x):
        try:
            return x.lower()
        except:
            return x

    sql2 = "select COLUMN_NAME, DATA_TYPE, character_maximum_length, numeric_scale  from INFORMATION_SCHEMA.COLUMNS where TABLE_NAME = ?"
    cursor.execute(sql2,table)
    dat = cursor.fetchall()
    dat = [[low(j) for j in i ] for i in dat] # weird I know - I want all the strings in lower case .  Don't do j.lower() on, say, an integer as you will get an error
    colDetails = namedtuple('cd','name typ leng scale')
    return [colDetails(*i) for i in dat]

def make64(a,b): 
    """makes a 64 bit integer out of two ints.  used extensively to create unique key for mid/bqid"""
    return a << 32 | b

def break64(x):
    """ returns two numbers back """
    a = x >> 32
    b = x & 0xFFFFFFFF
    if not b:
        b = None
    else: b = int(b)
    return int(a),b

def getERs(AllFlag, onlyIBs = False):
    cnxn=accP2()
    cursor=cnxn.cursor()
    sql="""select rTLA from {0} """.format(EmployerTable)
    if onlyIBs:
        sql += ' where rIbCtrlFlag = 1 '
    sql +=  ' order by rTLA asc'
    cursor.execute(sql)
    columns = cursor.fetchall()
    colList = [i[0] for i in columns]
    if AllFlag: colList = ['All'] + colList 
    cnxn.close()
    return colList

def chooseEmployer(ERs):
    ERdialog = wx.SingleChoiceDialog(None, "Choose the employer for this participant.\n Default is first employer", "Employer Chooser", ERs)
    if ERdialog.ShowModal() == wx.ID_OK:
        answer = ERdialog.GetStringSelection()
    else:
        answer = ERs[0]
    return answer

def ntAdder(nt1,nt2, name = 'newtup'):
    flds = nt1._fields + nt2._fields
    newtup = namedtuple('newtup',flds)
    data = tuple(nt1)+tuple(nt2)
    return newtup(*data)

def socialCheck(social):
    Good = False
    result = social
    ssn = str(social)
    if (len(ssn) == 11) and (ssn[3] == '-') and (ssn[6] == '-'):
        try:
            i = int(ssn[0:3])
            i = int(ssn[4:6])
            i = int(ssn[7:11])
            Good = True
            result = ssn
        except:
            pass
    # now check for integer formatted
    else:
        try:
            ssn = str(int(social))
            while len(ssn) < 9: 
                ssn = '0' + ssn
            ssn = ssn[0:3]+'-'+ssn[3:5]+'-'+ssn[5:9]
            Good = True
            result = ssn
        except:
            pass
    return Good, result

def convert(dat,typ):
    if dat == None:
        return None
    elif typ in ['date','datetime']:
        return dat.strftime("%Y-%m-%d")
    elif typ == 'money':
        return '${:,.2f}'.format(dat)
    elif typ == 'int':
        return str(dat)
    elif typ == 'decimal':
        return str(dat.quantize(Decimal('.0001')))
    else:
        stringin = str(dat)
        stringin = stringin.replace('>','&gt;')
        stringin = stringin.replace('<','&lt;')
        return stringin

def getibData(SSN,cursor):
    ibcols, ibtypes = getColHeads(IBControlTable,cursor)
    sql = 'select ' + ', '.join(ibcols) + ' from ' + IBControlTable +  ' where SOCSEC = ?'
    cursor.execute(sql,(SSN,))
    data = cursor.fetchall()
    result = [[convert(dat,typ) for dat,typ in zip(datarow,ibtypes)] for datarow in data]
    return zip(ibcols,*result)

def ntDelBlanks(nt):
    flds = nt._fields
    vals = [i for i in nt]
    newflds = [f for f,v in zip(flds,vals) if v not in EmptSet]
    newvals = [v for v in vals if v not in EmptSet]
    newNT = namedtuple('newNT',newflds)
    return newNT(*newvals)

class HTMLWindow(wx.Frame):
    def __init__(self, parent, title, text, width=None, height=None):
        if width:
            sz  = (width,height)
        else:
            sz = wx.DefaultSize
        wx.Frame.__init__(self, parent, -1, title, size=sz)
        html = wx.html.HtmlWindow(self)
        if "gtk2" in wx.PlatformInfo:
            html.SetStandardFonts()
        html.SetPage(text)  
