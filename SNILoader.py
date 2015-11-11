"""ScrippsMonthly Update

Read in monthly pay file
Add all records to database

"""
import pyodbc
from datetime import datetime as dt
import xlwt
from utilities import *
import time

SSdateFormat = "%m-%d-%Y" # this is used for formatting date strings to dates using strptime()
FFdateFormat = "%m%d%Y" #this is the format the data comes in from the flat file

class Timer:    
    def __enter__(self):
        self.start = time.clock()
        return self

    def __exit__(self, *args):
        self.end = time.clock()
        self.interval = self.end - self.start

def getCn():
    cst = ConnString(9) # this gets the SNI Monthly database
    pyodbc.lowercase=True
    return pyodbc.connect(cst)


def processFile(fn, writeXL, writeDB):
    XLmsg, DBmsg = '',''
    inf = open(fn,'r') #Process the header record, write an error and exit if bad
    flines = inf.readlines()
    hLine=flines[0]
    hfields='recid filename begindate enddate clientname filler'.split()
    places = [1,7,27,35,43,53,600]
    starts = places[:-1]
    ends=places[1:]
    headRec = namedtuple('HR', hfields)
    dat = [ hLine[i-1:j-1] for i,j in zip(starts,ends)]
    H = headRec(*dat)
    goOn = False
    msg = ''
    if (H.filename.strip() == 'EDS PENSION MONTHLY') and \
       (H.clientname.strip() == 'SCRIPPSNET') :
        goOn = True
    else:
        msg = 'Bad header data, should be EDS PENSION MONTHLY SCRIPPSNET, I got '+ H.filename + H.clientname
    """
    Process the main file
      all fields have prefix of 'm' as monthly fields (!)
    """               
    mfields='SSN Employeeid Salutation Firstname Midinit Lastname Gender Birthdate Orghiredate \
    Rechiredate filler Address1 Address2 Address3 City State Zip Country Homephonenum \
    filler Locationdate Payrollloccode Pencompcode Russcompcode Unioncode filler \
    Empstatusdate Payrollstatuscode Payrollactreacode Payrollreasoncode filler Earns Bonusearns \
    Hours filler Salratedate Salannual Salschedhrs Saltargetbonus Suffix filler'.split()
    mfields = ['m'+i.lower() for i in mfields]
    places = [1,10,21,26,56,61,91,94,102,110,118,138,173,208,243,273,279,289,295,319,339,347,\
              352,355,358,362,381,389,395,407,419,439,454,469,477,494,502,513,520,525,528,544]
    starts=places[:-1]
    ends=places[1:]
    rows=[] # this stores all the results
    fillerCols = [colNo for colNo, col in enumerate(mfields) if  col == 'mfiller']
    fillerCols.reverse() # we are going to pop these, so pop the biggest ones first or you will mess up the indexes
    for i in fillerCols: mfields.pop(i)
    # now add some extra fields for messages and the begin end dates
    appendData = [H.begindate, H.enddate]
    mfields.extend(['mbegindate','menddate'])
    dateCols=[colNo for colNo, col in enumerate(mfields) if 'date' in col]
    div100Cols = ['mearns','mbonusearns','msalannual','msalschedhrs','mhours','msaltargetbonus'] # div100Cols are the numeric columns that have to be divided by 100 - these are money
    div100Cols = [mfields.index(i) for i in div100Cols]
    div1Cols = ['msalschedhrs'] #div1Cols are the numeric columns that are strings to be converted to integers - not divided by anything
    div1Cols = [mfields.index(i) for i in div1Cols]
    moneyCols = ['mearns', 'msalannual', 'mbonusearns']
    moneyCols = [mfields.index(i) for i in moneyCols]
    for L in flines[1:-1]: #make this [1:12] to just test the first 10
        dat = [L[i-1:j-1] for i,j in zip(starts,ends)]
        dat = [i.strip() for i in dat] # just take off any leading or trailing blanks
        dat[0] = dat[0][:3] + '-' + dat[0][3:5] + '-' + dat[0][5:] # make a social out of the first field - social comes in as an integer
        for i in fillerCols: dat.pop(i) # throw out the fillers
        dat.extend(appendData)
        for col in dateCols: 
            if dat[col]:
                dat[col] = dt.strptime(dat[col], FFdateFormat)
        for col in div100Cols:
            dat[col] = (Decimal(dat[col])/100)
        for col in div1Cols:
            dat[col] = (int(dat[col]))
        R = dict(zip(mfields, dat))
        rows.append(R)
    # now write the spreadsheet out
    if writeXL:
        outfn = fn[:-3]+'xls'
        wb = xlwt.Workbook()
        ws = wb.add_sheet('MonthlyData')
        dateStyle = xlwt.easyxf(num_format_str='MM/DD/YYYY')
        currStyle = xlwt.easyxf(num_format_str = '$#,##0.00')
        genStyle = xlwt.easyxf(num_format_str = 'general')
        numStyle = xlwt.easyxf(num_format_str="#,###.00")
        intStyle = xlwt.easyxf(num_format_str="#,###")
        colStyles, colFlds = [], []
        for colNum, fld in enumerate(mfields): # write the col headings, prepare list of column styles
            ws.write(0,colNum,fld)
        with Timer() as t:
            for rowNum, row in enumerate(rows):
                dataRow = [row[k] for k in mfields]
                for colNum, col in enumerate(dataRow):
                    if colNum in dateCols:
                        ws.write(rowNum+1,colNum,col,dateStyle)
                    elif colNum in div100Cols:
                        if colNum in moneyCols: # then it is a decimal and money too
                            ws.write(rowNum+1,colNum,col, currStyle) 
                        else: # it is just a decimal
                            ws.write(rowNum+1,colNum,col, numStyle) 
                    elif colNum in div1Cols:
                        ws.write(rowNum+1,colNum,col, intStyle)
                    else:
                        ws.write(rowNum+1,colNum,col, genStyle)
        try:
            wb.save(outfn)
            result = rowNum + 1 #rownum starts from zero
        except:
            result = 0
            msg = 'Could not save spreadsheet '+outfn+'.\nPlease check the filename is good and the sheet is not open.\n'+str(result)+' rows processed.\n\n'
            #print msg
        #print('ssWrite took %.03f sec.' % t.interval)        
        XLmsg = 'Spreadsheet ' + outfn + ' written. \n' + str(result) + ' rows added.\n\n'
        if result == 0:
            XLmsg = 'Error! \n' + msg
            print msg
    #  now write the databsae
    if writeDB:
        cn = getCn()
        cursor = cn.cursor()
        outMsgs = fn[:-4]+'Msg.txt'
        msgF = open(outMsgs,'w')
        keyCols = ['mbegindate','mssn']
        # sql to insert into snimonthlypay
        sqlIns = "insert into sniMonthlypay (" + ",".join(mfields) + ") values ( " + ','.join('? ' for i in mfields) + ")"
        # sql to updaqte snimonthlypay
        sqlUpd = "update sniMonthlypay set "
        updfields = [i for i in mfields if i not in keyCols]
        sqlUpd2 = " = ?,".join(updfields) + '=? where '
        sqlUpd3 = '=? and '.join(keyCols) + '=?'
        sqlUpd = sqlUpd + sqlUpd2 + sqlUpd3
        # sql to check for existing value - ie whether to do update or insert
        sqlCheck = 'select mbegindate from snimonthlypay where mbegindate = ? and mssn = ?'
        #messages and counters
        dbErrors = []
        rowsUpd, rowsIns = 0,0
        for row in rows:
            # check if this date and ssn thing already in 
            keyVals = [row[k] for k in keyCols]
            dataInDB = cursor.execute(sqlCheck, keyVals).fetchall()
            if dataInDB: #then to an update
                updRow = [row[k] for k in updfields]
                try: 
                    cursor.execute(sqlUpd,updRow + keyVals)
                except pyodbc.Error as er:  # something went wrong
                    errNo, errData = er
                    errStrin = 'Unexpected update error-->'+str(errNo)+'\n'+str(errData)+'\n'
                    dbErrors.append(errStrin)
                else:
                    rowsUpd += 1
                    msgF.write(sqlUpd+'\n'+str(updRow)+'\n'+str(keyVals)+'\n')
            else: # do an insert
                dataRow = [row[k] for k in mfields]
                try: 
                    cursor.execute(sqlIns,dataRow)
                except pyodbc.Error as er:  
                    errNo, errData = er
                    errStrin = 'Unexpected update error-->'+str(errNo)+'\n'+str(errData)+'\n'
                    dbErrors.append(errStrin)
                else:
                    rowsIns += 1
                    msgF.write(sqlIns+'\n'+str(dataRow)+'\n')       
        numErrors = len(dbErrors)
        DBmsg = 'Database table sniMonthlyPay written. \n' + str(rowsUpd) + ' rows updated, ' + str(rowsIns) + ' rows inserted, ' + str(numErrors) + ' errors.\n'
        # need to backout if any errors, and return error messages...
        if numErrors > 0:
            cn.rollback()
            DBmsg += 'Errors reported, so database records rolled back.  First 10 errors are:'
            for i in range(10):
                DBmsg += dbErrors[i]
        else:
            cn.commit()
        msgF.close()
    return (XLmsg+DBmsg)

if __name__ == '__main__':
    months = ['01','02','03','04','05','06','07','08','09','10','11','12']
    days = ['31','29','31','30','31','30','31','31','30','31','30','31']
    for m,d in zip(months,days):
        inf = 'J:/SNI/DB/2012/CLNTFR/rcotwcon_sni_2012'+m+'01-2012'+m+d+'.txt'
        print 'processing ',inf
        msg = processFile(inf, True, True)
        print msg
    
    

        
        

