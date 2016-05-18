import pyodbc
import csv

conn_tasks = pyodbc.connect('DRIVER={SQL Server Native Client 10.0}; SERVER=RWDB1;DATABASE=PJE_Tasks;UID=RWUser; PWD=RuddWisd0m')
cur_tasks = conn_tasks.cursor()
conn_wh = pyodbc.connect("DRIVER={SQL Server Native Client 10.0}; SERVER=RWDB1;DATABASE=WarehouseTest;UID=RWUser; PWD=RuddWisd0m")
cur_wh = conn_wh.cursor()
clients = [i[0] for i in cur_wh.execute('select rtla from tbemployer')]

# get clients
cl_f = open('j:/users/phil_ellis/2015ClientAssign.csv','rb')
cl_r = csv.reader(cl_f)
clients = [row[:2] for row in cl_r] # reads in tuple - client code, actuary

for cl, act in clients:
    print cl, act
    cur_tasks.execute('insert into clients (clientcode, actuary) values (?,?)',(cl,act))
    cur_tasks.execute('insert into projects (pclient, pproject,powner, pstatus) values (?,?,?,?)',(cl, '2015 Misc.', act,'2 In Progress'))


cur_tasks.execute('insert into clients (clientcode, actuary) values (?,?)',('Technology','Phil'))
for proj in ['LCRA','CIT','JPS','NAC','SNI','SSTAR']:
    cur_tasks.execute('insert into projects (pclient, pproject,powner, pstatus) values (?,?,?,?)',('Technology', '2015 '+proj+' website', 'Phil','2 In Progress'))
cur_tasks.execute('insert into projects (pclient, pproject,powner, pstatus) values (?,?,?,?)',('Technology', 'Warehouse', 'Phil','2 In Progress'))                  
conn_tasks.commit()
