from decimal import Decimal
from utilities import *


class htmlString:
    """ This class contains various helper functions to format an html string
    for display or printing
    v is the value of the string
    methods beginning in v do not return anything they change the attribute v 
    methods beginning in ht return an html string
    """

    def __init__ (self, httext='<html><body bgcolor="AliceBlue" ><SMALL><table width="550" height="1000">'):
        """ you can start the class off with an initial value if you like, or it will
            default to a begin string"""
        self.v=httext #v is the value
        self.httable = """
            <center><table bgcolor="#FFF4F4"
            cellspacing="0" cellpadding="2" border="1"
            bordercolor="980000" width="100%">
            """
        self.httableend = '</center></table>'
        self.htline = ''
        self.htdataend = '</td>'
        self.EmptSet=set(['',' ',Decimal('0.0'),0,0.0,0.00,'0','0.0','0.00','.',None,'$0.00'])

    def htsocialerror(self, table, social): # format an error message
        messages={EmployeeTable:'''<center>Employee Record<br>Social Security number {0} not found</center>''',
                IBControlTable: '''<center>IB Control Record<br>Social Security number {0} not found</center>''',
                AnnualTable:'''<center>Annual Records<br>Social Security number {0} not found</center>'''}
        return """<font face="Arial" size='2'>"""+messages[table].format(social)+'</font><br>'
    
    def htrow(self, t): #put table row tags on a row of table data
        return '<tr>'+str(t)+'</tr>'

    def htheadtext(self, t): #Heading
        return """<font size='3'>"""+t+'</font><br><br>'

    def htheadcell(self, t): #format a heading cell - t is text to be formatted
        return """
            <td align="left">
            <font face="Arial", size='1'>"""+t+"""</font></td>
            """

    def htdatacell(self, t): #format a data cell - t is text to be formatted
        return"""
            <td bgcolor="#FFF4F4" align="right">
            <font size='1'><B>"""+str(t)+"""</B></font></td>
            """
    
    def vend(self):
        self.v+= '</SMALL></body></html>'
        return

    def vreduceFont(self):
        """ call this method before printing out - otherwise the print will be too big
        """
        temp=self.v
        temp=temp.replace("""size='1'""","""size='1'""")
        temp=temp.replace("""size='2'""","""size='1'""")
        temp=temp.replace("""size='3'""","""size='1'""")
        return temp

    def vtable(self, title, table, social, DickList, *arguments):
        #the arguments sent over are just used as table headings - then 
        # removed from the DickList
        if table == EmployeeTable:
            self.v+='<tr><td valign="top">'
        setdatvals = set([i['COLDATA'] for i in DickList])
        if (len(DickList) == 0) or (setdatvals - EmptSet == set([])):
            self.v+=self.htsocialerror(table, social)
        else:
            self.v+='<font face="Arial" size="2"><center>'+title+'</center></font>'
            for arg in arguments: #put some of the data as headings
                for row in DickList:
                    if row['COLNAME'] == arg:
                        self.v+=str(row['COLDATA'])
                        DickList.remove(row)
            self.v+=self.httable
            for row in DickList:
                if row['COLDATA'] not in self.EmptSet:
                    if row['COLTYPE'] == 'datetime':
                        coldata = str(row['COLDATA'])
                        splitcoldata = coldata.split()[0]
                        row['COLDATA'] = splitcoldata                        
                    self.v+=self.htrow(self.htheadcell(row['COLNAME'])+self.htdatacell(row['COLDATA']))
            self.v+=self.httableend
        if table == EmployeeTable:
            self.v+=self.htdataend
        self.v+='<br>'
        


    def vtableAnnual (self, table, social, headings, datalist):
        
        if len (datalist) == 0:
            self.v+='<td valign="top" width="175">'+self.htsocialerror(table, social)
        else:
            self.v+='<td valign="top">'
            self.v+='<font face="Arial" size="2"><center>Annual Record</font>'
            self.v+=self.httable
            self.v+=self.htrow(''.join([self.htheadcell(col) for col in headings]))
            for row in datalist:
                rowdate = str(row[0])
                datestrip = rowdate.split()[0]
                row[0] = datestrip
                self.v+=self.htrow(''.join([self.htdatacell(col) for col in row]))
            self.v+=self.httableend
        self.v+=self.htline
        self.v+='</center></td></tr>'
        
    def vfirstrow(self, table, social, DickList, *arguments):
        setdatvals = set([i['COLDATA'] for i in DickList])
        if (len(DickList) == 0) or (setdatvals - EmptSet == set([])):
            self.v+=self.htsocialerror(table, social)
        else:
            self.v+='<tr><td valign="top"><font face="Arial" size="2">'
            for arg in arguments: 
                for row in DickList:
                    if row['COLNAME'] == arg:
                        self.v+=str(row['COLDATA'])+' '
                        DickList.remove(row)
            today = datetime.date.today()
            self.v+='</font></td><td></td><td valign="top" align="right"><font face="Arial" size="2">'+str(today)+'</font></td></tr>'
            
