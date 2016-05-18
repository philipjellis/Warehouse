"""Scripps Person Check

Take a social and report all interesting changes to the person over the months's they are present

"""
from utilities import sniCn, getColHeads
from copy import copy
from collections import OrderedDict
import HTML
from decimal import Decimal
import os

def writeOut(social,text, prefix):
    # this writes html text to a file on the desktop called temp111_22_3333.html
    social = social.replace('-','_')
    text = text + htend()
    filename = os.getenv("HOMEDRIVE") + os.getenv("HOMEPATH") + '/Desktop/' + prefix + social + ".html"
    file = open(filename, 'w')
    file.write(text)
    file.close()
    return filename
    
def htStart():
    return '<html><body bgcolor="AliceBlue" ><SMALL><table width="550" height="1000">'

def htnewpara():
    return '<p>'

def htparaend():
    return '</p>'

def htend():
    return '</SMALL></body></html>'

def hthead(t):
    return  """<font size='3'>"""+t+'</font><br><br>'

def htline(t):
    return  """<font size='2'>"""+t+'</font><br>'

def getData(social):
    cn = sniCn()
    cursor = cn.cursor()
    colNames, colTypes = getColHeads('snimonthlypay', cursor, lower=True)
    sqlgetData = 'select ' + ','.join(colNames) + ' from snimonthlypay where mssn = ? order by mbegindate asc'
    data = cursor.execute(sqlgetData,social).fetchall()
    return data, colNames

def dataSSN(social):
    data, colNames = getData(social)
    if not data:
        result = htStart() + htline('No data returned for ' + social) 
    else:
        displayData = [colNames] + [list(i) for i in data]
        displayData = zip(*displayData) # transpose
        result = htStart() + hthead('Table showing data for '+social) + HTML.table(displayData[1:], header_row = displayData[0])
    filename = writeOut(social, result, 'data')
    result += htline('This data written to ' + filename) + htend()
    return result
    

def processSSN(social, colsToCheck, writeMe = True):
    # step 1 get all the data rows out in order
    data, colNames = getData(social)
    if data:
        rowDicks = [OrderedDict(zip(colNames,i)) for i in data]
        firstRow = rowDicks[0].values()
        lastRow = rowDicks[-1].values()
        remainingRows = rowDicks[1:]
        latestData = copy(rowDicks[0])
        if len(rowDicks) == 1:
            displayData = zip(colNames, firstRow)
            return htStart() + hthead('Only one row for this social.') + HTML.table(displayData[1:], header_row = displayData[0])
        msg = ''
        for row in remainingRows:
            rowData = [row[col] for col in colsToCheck]
            chgdData = dict((key,val) for key, val in zip(colsToCheck,rowData) if val <> latestData[key])
            if chgdData:
                msg += htnewpara() + htline('row ' + str(row['mbegindate']) + ' has new items ')
                for k,v in chgdData.iteritems():
                    msg += htline(str(k)+ ':' + str(v))
                msg += htparaend()
                for k,v in chgdData.iteritems():
                    latestData[k] = v
        displayData = zip(colNames, firstRow, lastRow)
        result = htStart() + hthead('Table showing first and last rows returned') + HTML.table(displayData[1:], header_row=displayData[0]) 
        if msg:
            result = hthead('Changes between first and last rows') + msg + result
        else:
            result = htline('No changes identified for ' + social) + result
        if writeMe:
            filename = writeOut(social, result, 'changes')
            result += htline('This data written to ' + filename) + htend()
        else:
            result += htend()
        return result
    else:
        return htStart() + hthead('No data returned for ' + social) + htend()

if __name__ == "__main__":
    socials = ['123-45-555', '147-90-4744','189-64-4698','294-96-9884','415-43-3038','415-19-6336']
    for ssn in socials:
        msg = processSSN(ssn)
        print msg
                    
    
            
                
    
                    
    
