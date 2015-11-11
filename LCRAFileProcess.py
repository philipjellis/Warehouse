from datetime import datetime, date
import xlrd
import xlwt
import pyodbc
import MySQLdb
import encodings

colHeads=['socsec', 'paydate', 'eename', 'address1', 'city', 'state', 'zip', 'loccode', \
          'birthdate', 'hiredate', 'sex', 'paycode', 'fullpart', 'regproj', 'sickleave', \
          'grosswage', 'nonbase', 'payrate', 'excludable', 'hours', 'empid', 'orighd','plancomp']
colTypes=['varchar(11)','date','varchar(30)', 'varchar(30)','varchar(20)','varchar(2)','varchar(10)',\
          'varchar(3)','date','date','char(1)','char(1)','char(1)','char(1)','decimal(6,2)',\
          'money','money','money','money','decimal(6,2)','varchar(4)','date','money']
keyCols = ['socsec','paydate']
colHeads_nokey = [i for i in colHeads if i not in keyCols]
# 
# now the columns for the simplified web database.  No unneeded columns and no socials in this.
colHeadsWeb = ['pid','paydate','grosswage','payrate','hours','plancomp'] # all the columns except id which is autoinserted
colHeadsWebkey = ['pid','paydate'] # just the key
colHeadsWebnokey = ['grosswage','payrate','hours','plancomp'] # all the ones that are not a key
#
# SQL for WH
create_sql = 'create table lcramonthlypay ('+','.join([i+' '+j for i,j in zip(colHeads, colTypes)])+')'
insert_sql = 'insert into lcramonthlypay ( '+', '.join(colHeads)+' ) values ( ' + ','.join(['?' for i in colHeads]) + ')'
check_sql = 'select socsec from lcramonthlypay where socsec = ? and paydate = ?'
update_sql = 'update lcramonthlypay set ' + " = ?,".join(colHeads_nokey) + "=? where socsec = ? and paydate = ?"
#SQL for web
insert_sqlweb = 'insert into tbmonthly ( '+', '.join(colHeadsWeb)+' ) values ( ' + ','.join(['%s' for i in colHeadsWeb]) + ');'
update_sqlweb = 'update tbmonthly set ' + " = %s,".join(colHeadsWebnokey) + "=%s where pid = %s and paydate = %s;"
check_sqlweb = 'select pid from tbmonthly where pid = %s and paydate = %s;'
#
# Connection to monthly database on main database server
cstMonthly = 'DRIVER={SQL Server Native Client 10.0}; SERVER=RWDB1;DATABASE=ClientMonthly;UID=RWUser; PWD=RuddWisd0m'
cn_month = pyodbc.connect(cstMonthly)
curs_month = cn_month.cursor()
#
#  Connection to Data Warehouse to do checks on valid people and so on
cstWarehouse = 'DRIVER={SQL Server Native Client 10.0}; SERVER=RWDB1;DATABASE=Warehouse;UID=RWUser; PWD=RuddWisd0m'
cn_wh = pyodbc.connect(cstWarehouse)
curs_wh = cn_wh.cursor()
#
# Connection to website database using MySQL 
conn_web = MySQLdb.connect(host="107.170.126.197",port=3306,user="phile",passwd="abbddy!", db="lcra")
#conn_web = MySQLdb.connect(host="192.168.1.30",port=3306,user="pje",passwd="hamlet", db="lcratest")
cursor_web = conn_web.cursor()

empty_set = [None,'']
pid_lookup = {}
text_file = []

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
        result = Float(str(dat))
    if typ == 'Text':
        result = dat.strip()
    if dat in empty_set: result = None
    return result

def date_try(y,m,d):
    try:
        return date(int(y),int(m),int(d))
    except:
        return None

def social_and_dates(vals):
    """ fix the string social in col 0 and the dates in col 1,8,9,21"""
    vals[0] = vals[0][:3]+'-'+vals[0][3:5]+'-'+vals[0][5:] #social
    vals[1] = date_try(vals[1][2:], vals[1][:2],1)#pay month mmyyyy
    if vals[8]:
        vals[8] = date_try(vals[8][-4:],vals[8][:2], vals[8][2:4]) #birthdate
    if vals[9]:
        vals[9] = date_try(vals[9][-4:],vals[9][:2], vals[9][2:4]) #hiredate
    if vals[21]:
        vals[21] = date_try(vals[21][-4:],vals[21][:2], vals[21][2:4]) #orighd
    return vals

def text_line_process(line):
    limits=[9,6,30,30,20,2,10,3,8,8,1,1,1,1,6,8,8,8,8,6,4,8]
    vals = []
    for i in limits:
        vals.append(line[:i])
        line = line[i:]
    vals = social_and_dates(vals)
    #sex, paycode, fullpart, regproj all 1 char
    vals[14] = int(vals[14])/100.0 #sickleave
    vals[15] = int(vals[15])/100.0 #grosswage
    vals[16] = int(vals[16])/100.0 #nonbase
    vals[17] = int(vals[17])/100.0 #payrate
    vals[18] = int(vals[18])/100.0 #excludable
    vals[19] = int(vals[19])/100.0 #hours
    for i in [2,3,4,6]: #tidy up the ones with lots of trailing spaces
        vals[i] = vals[i].strip()
    return vals

def read_xl():
    # note the file name hard coded in here!!!!!
    # this is an initial load file - for use once only.
    book = xlrd.open_workbook("J:/LCRA/DB/PAYROLL/SALHIST_4_1_2014.xlsx")
    sht=book.sheet_by_index(0)
    dMode = book.datemode
    typs={0 : 'Empty', 1 : 'Text', 2: 'Number', 3 : 'Date', 4 : 'Boolean',5 : 'Error', 6 : 'Empty'}
    rnge = sht.nrows
    for row in range(1,sht.nrows): #miss out row 0 as this is headings 
        thisR = [(sht.cell_value(row,col), sht.cell_type(row,col)) for col in range(sht.ncols)]
        line = [convertdat(cell[0],typs[cell[1]],dMode) for cell in thisR]
        for col in range(14,20):
            if not line[col]:
                line[col] = 0.0
        line.append(line[15]-line[18])
        line = social_and_dates(line)
        yield dict((i,j) for i,j in zip(colHeads, line))    
    
def read_text_file(filename):
    fil=open(filename)
    for line in fil.readlines():
        line = text_line_process(line)
        line.append(line[15]-line[18])
        text_file.append(dict((i,j) for i,j in zip(colHeads, line)))

def make_table():
    sql = 'drop table lcraMonthlyPay'
    try:
        curs_month.execute(sql)
    except:
        pass #table not there so nothing to drop
    curs_month.execute(create_sql)
    cn_month.commit()

def load_table():
    ct=0
    for line in read_xl():
        curs_month.execute(insert_sql,[line[i] for i in colHeads])
        ct += 1
        if ct % 10000 == 0:
            print ct
            cn_month.commit()
    cn_month.commit()
            
def load_month_warehouse(filename, check=True):
    #first check everyone is in tbMember
    print filename
    sql = """select mssn, mpid from tbmember
                 inner join tbbhsnapshot on bhmid = mid
                 where 
                 mnid =241 and
                 bhCodSta in ('3','4') and
                 bheffectivedate = 
                      (select MAX(bheffectivedate) 
                      from tbBHSnapshot inner join tbMember 
                      on bhMid = mId and mNId = 241)"""
    #old code was select mssn , mpid from tbmember where mnid = 241'
    curs_wh.execute(sql)
    for row in curs_wh.fetchall():
        pid_lookup[row[0]] = row[1]
    new_socials = []
    lines_inserted, lines_updated = 0,0
    read_text_file(filename)
    for line in text_file:
        if line['socsec'] not in pid_lookup.keys():
            new_socials.append(line['socsec'])
        # check if data here
        curs_month.execute(check_sql,(line['socsec'],line['paydate']))
        data = curs_month.fetchall()
        if data: # if there was data in the check then update
            if not check:
                curs_month.execute(update_sql, [line[i] for i in colHeads_nokey]+[line[i] for i in keyCols])
            lines_updated += 1
        else: #the check returned no data, so insert
            if not check:
                curs_month.execute(insert_sql, [line[i] for i in colHeads])
            lines_inserted += 1
    if not check:
        cn_month.commit()
    msg_lines = str(lines_inserted+lines_updated) + ' rows processed.\n'
    if check:
        msg_lines += str(lines_inserted) + ' rows not present and \n' + str(lines_updated) + \
            ' rows already in monthly pay table.\n'
    else:
        msg_lines += str(lines_inserted) + ' lines inserted and \n' + str(lines_updated) + \
            ' lines updated to monthly pay table.\n'
    if new_socials:
        msg_lines += str(len(new_socials)) + ' socials were not in the data warehouse.\n'
        n_socials_shown = min([10,len(new_socials)])
        msg_lines += 'First ' + str(n_socials_shown) + ' missing socials:\n'
        for i in range(n_socials_shown):
            msg_lines += new_socials[i] + '\n'
    return msg_lines

def load_month_website(filename, parent):
    # initialize a couple of things
    new_socials = []
    lines_read, lines_inserted, lines_updated = 0,0,0
    #get all the socials for this date
    #cursor_web.execute(check_sqlweb,(line['paydate'],))
    #records_thisdate = cursor_web.fetchall()
    filesize = len(text_file)
    for line in text_file:
        lines_read += 1
        if lines_read % 10 == 0:
            msg = 'Processed ' + str(lines_read) + '/' + str(filesize)
            parent.change_statusbar(msg)
        if line['socsec'] not in pid_lookup.keys(): # then we have a new person not in the pla.  But the plan is closed so they don't get processed.
            new_socials.append(line['socsec'])
        else: # they are in so we get their pid, which we need for the key to the MySQL table (socials were removed from this table).
            line['pid'] = pid_lookup[line['socsec']]
            cursor_web.execute(check_sqlweb,(line['pid'],line['paydate']))
            data = cursor_web.fetchall()
            if data: # if there was data in the check, then update.  We don't mind reprocessing a month - maybe it is a correction.
                cursor_web.execute(update_sqlweb, [line[i] for i in colHeadsWebnokey]+[line[i] for i in colHeadsWebkey])
                lines_updated += 1
            else: #the check returned no data, so insert
                try:
                    cursor_web.execute(insert_sqlweb, [line[i] for i in colHeadsWeb])
                except:
                    print 'sql', insert_sqlweb
                    print 'colHeadsWeb', colHeadsWeb
                    print 'data', [line[i] for i in colHeadsWeb]
                    fail=1/0
                lines_inserted += 1
    conn_web.commit()
    msg_lines = str(lines_read) + ' rows processed.\n'
    msg_lines += str(lines_inserted) + ' lines inserted and \n' + str(lines_updated) + \
            ' lines updated to monthly pay table.\n'
    if new_socials:
        msg_lines += str(len(new_socials)) + ' socials were not in the monthly pay table.\n'
        n_socials_shown = min([10,len(new_socials)])
        msg_lines += 'First ' + str(n_socials_shown) + ' missing socials:\n'
        for i in range(n_socials_shown):
            msg_lines += new_socials[i] + '\n'
    return msg_lines

def extract_person(ssn, filename):
    sql = 'select ' + ','.join(colHeads) + ' from lcramonthlypay where socsec = ? order by paydate desc'
    #print sql
    curs_month.execute(sql,(ssn,))
    data = curs_month.fetchall()
    wb = xlwt.Workbook()
    ws0 = wb.add_sheet('ssn '+ssn)
    dateStyle = xlwt.easyxf(num_format_str='MM/DD/YYYY')
    currStyle = xlwt.easyxf(num_format_str = '$#,##0.00')
    genStyle = xlwt.easyxf(num_format_str = 'general')
    numStyle = xlwt.easyxf(num_format_str="#,###.00")
    intStyle = xlwt.easyxf(num_format_str="#,###")
    style_cols = [genStyle for i in colHeads]
    for i in [1,8,9,21]: style_cols[i] = dateStyle
    for i in [14,19]: style_cols[i] = numStyle
    for i in [15,16,17,18,22]: style_cols[i] = currStyle
    for colNum, fld in enumerate(colHeads): # write the col headings, prepare list of column styles
        ws0.write(0,colNum,fld,genStyle)
    for rowNum, row in enumerate(data):
        for colNum, (colStyle, col) in enumerate(zip(style_cols,row)):
            if not col:
                pass # don't waste time
            else:
                ws0.write(rowNum+1,colNum,col,colStyle) #note rownum + 1 as headings are in first row
    try:
        wb.save(filename)
        if not data:
            rowNum = -1
        msg = str(rowNum + 1) + ' rows written to ' + filename #rownum starts from zero
    except:
        msg = 'Could not save spreadsheet ' + filename + '.\nPlease check the filename is good and the sheet is not open.\n'+str(result)+' rows processed.'
    return msg    

def empty_zip(): # now checks for empty zip fields and a few other empty fields - see below
    def err(text):
        print lineno, text, line['socsec'], line['paydate'], line['eename'], line['address1'], line['city'],\
              line['state'], line['zip'], line['paydate'], line['birthdate'], line['hiredate']
    for lineno,line in enumerate(read_xl()):
        if not line['zip']:
            err('warning')
        if (not line['paydate']) or (not line['birthdate']) or (not line['hiredate']):
            err('fatal')                                        
        if lineno % 50000 == 0:
            print lineno
    
def find_duplicate_keys():
    sql = 'select socsec, paydate from lcramonthlypay order by socsec asc, paydate asc'
    curs_month.execute(sql)
    data = curs_month.fetchall()
    print 'got data'
    test = data.pop(0)
    for i in range(len(data)):
        newtest = data.pop(0)
        if newtest == test:
            print newtest
        else:
            test = newtest

def hi60calc(ssn):
    def hi60(cursor, sql, value):
        # call the database and get the plancomp data in date order
        cursor.execute(sql,(value,))
        length = 60
        data = [i[0] for i in cursor.fetchall()]
        len_d = len(data)
        # do the hi 60 calculation
        if len_d >= length:
            high60s = []
            for i in range(len_d - length + 1):
                sum60 = sum(data[i:i+length])
                high60s.append(sum60)
            high60 = float(max(high60s))
        else:
            high60 = float(sum(data))
        # format the message - make it clear if there were fewer than 60 records
        if len_d < length:
            result = 'Only ' + str(len(data)) + ' salary records, sum is ${:,}'.format(round(high60,2))
        else:
            result = 'Hi' + str(length) + ' = ${:,}'.format(round(high60,2))
        l = min(length, len_d)
        average_monthly = high60 / l
        average_annual = average_monthly * 12.0
        result += '\nAverage annual = ${:,}'.format(round(average_annual,2))
        result += '\nAverage monthly = ${:,}'.format(round(average_monthly,2)) + '\n'
        return result
        
        
    # first see if this is called with two parameters, a social and the word Yes or Y
    params = ssn.split()
    if (len(params) == 2) and (params[1][0].upper() == 'Y'):
        ssn = params[0]
        pid = curs_wh.execute('select pid from tbperson where pssn = ?',(ssn,)).fetchone()[0]
        message = 'Web database result\n'
        hi60_web = hi60(cursor_web,'select plancomp from tbmonthly where pid = %s order by paydate asc', pid)
        message += hi60_web
        message += 'Monthly table in warehouse result\n'
        hi60_wh  = hi60(curs_month,'select plancomp from lcramonthlypay where socsec = ? order by paydate asc', ssn)
        message += hi60_wh
    else:
        message = hi60(curs_month,'select plancomp from lcramonthlypay where socsec = ? order by paydate asc',ssn)
    return message
        
def latestpay(table):
    # pass over the cursor for either lcramonthlypay or tbmonthlypay and the table name
    if table == 'lcramonthlypay':
        cursor = curs_month
    elif table == 'tbmonthly':
        cursor = cursor_web
    sql = 'select MAX(paydate) from ' + table
    cursor.execute(sql)
    dt = cursor.fetchone()[0]
    return dt.strftime("%B %Y")
    