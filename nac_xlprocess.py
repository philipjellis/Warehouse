import xlrd

def social_fix(ssn):
    #takes an integer social and puts in the dashes
    ss = str(ssn)
    while len(ss) < 9:
	ss = '0' + ss
    return ss[:3] + '-' + ss[3:5] + '-' + ss[5:]

def process_xl(fn, start, end, curs_mon, curs_wh):
    cols_needed = ['ELNAME','EFNAME','EINIT','ESSNUM','KTEARN']
    cols_written = ['NameLast','NameFirst','NameMiddle','SSN_NoHyphen','SSN','StartDate',\
		    'EndDate','FullTimeComp','PartTimeComp','EECont','pid','eid']
    row_written = 0
    xl_workbook = xlrd.open_workbook(fn)
    sheet_names = xl_workbook.sheet_names()
    sheets_wanted = [i for i in sheet_names if ((i[-1] == '%') or (i in ['Other','Capped']))]
    sql_pideid = 'select eid, epid from tbemployee where ssn = ? and erid = 25'
    sql_ins = 'insert into nacomonthly (' + ','.join(cols_needed) + ') values (' + ','.join(['?' for i in cols_needed]) + ')'
    for sheet in sheets_wanted:
	xl_sht = xl_workbook.sheet_by_name(sheet)
	#check we have the cols we need
	row1 = [i.value for i in xl_sht.row(0)]
	if all([True if i in row1  else False for i in cols_needed]):
	    col_keys = list(col_needed)
	    if 'FUNDING' in row1:
	        funding = True
	    else:
		funding = False
	    for row_num in range(1,xl_sht.nrows):
		row = [i.value for i in xl_sht.row(row_num)]
		row_d = dict((k,v) for k,v in zip(row1,row))
		new_row = {}
		new_row['NameLast'] = row_d['ELNAME']
		new_row['NameFirst'] = row_d['EFNAME']
		new_row['NameMiddle'] = row_d['EINIT']
		new_row['SSN_NoHyphen'] = row_d['ESSNUM']
		new_row['SSN'] = social_fix(row_d['ESSNUM'])
		new_row['StartDate'] = Start
		new_row['EndDate'] = End
		if sheet == 'Other':
		    new_row['FullTimeComp'] = None
		    new_row['PartTimeComp'] = row_d['KTEARN']
		else:
		    new_row['FullTimeComp'] = row_d['KTEARN']
		    new_row['PartTimeComp'] = None
		    if funding:
		        new_row['EECont'] = row_d['FUNDING']
		    else:
		        new_row['EECont'] = None
		curs_wh.execute(sql_pideid,(new_row['SSN'],))
		ids = curs_wh.fetchone()
		if ids:
		    new_row['pid'] = ids[1]
		    new_row['eid'] = ids[0]
		else:
		    new_row['pid'] = None
		    new_row['eid'] = None
		curs_mon.execute(sql_ins,[new_row[i] for i in cols_written])
		rows_written += 1
	else:
	    Message('Some of the following columns are missing from sheet ' + sheet + '\n'.join(cols_needed))
    Message(OK_CANCEL,'Sheets ' + ','.join(sheet_names) + 'processed.  Press OK to write to database')



            
            
	



