use PJE_Tasks
delete from History
delete from Tasks
delete from Projects
delete from Users
delete from Status
delete from clients

insert into Users (username) values ('Chelsea'),
('Brandon'),
('Lesley'),
('Chris'),
('Michael'),
('Hua-Yu'),
('Michelle'),
('Carl'),
('Mitchell'),
('Jake'),
('Ray'),
('Amanda'),
('Aubrey'),
('Shannon'),
('Greg'),
('Brett'),
('Daniel'),
('GregH'),
('Jordan'),
('Ryan'),
('Sheryl'),
('Toby'),
('Philip');

insert into Status (StatusDescription) values 
('1 Not Started'),
('2 In Progress'),
('3 Being Checked'),
('4 Rework'),
('5 Complete'),
('6 Cancelled');

insert into Clients (ClientCode) values
('ANS'),
('ATH'),
('CAR'),
('CIT'),
('CLK'),
('CRK'),
('DIM'),
('FAI'),
('GEO'),
('GIL'),
('GUA'),
('HEN'),
('HHS'),
('HRS'),
('HUN'),
('JAC'),
('JAX'),
('KDH'),
('LCR'),
('LIM'),
('MFH'),
('MSO'),
('MTV'),
('NAC'),
('NTM'),
('PEC'),
('PIT'),
('QUI'),
('RHS'),
('STA'),
('SWE'),
('TAR'),
('THA'),
('TMC'),
('TPA'),
('TRI'),
('TYL'),
('YUM'),
('AFL'),
('AMI'),
('FAL'),
('PSP'),
('BND'),
('ACG'),
('KJZ'),
('TBB'),
('CLI'),
('SWB'),
('FCC'),
('TST'),
('ALM'),
('TPB'),
('SON'),
('SST'),
('MGE'),
('AGA'),
('DAV'),
('SNI'),
('(None)');

insert into Projects (pClient, pProject, pOwner, pStatus) values
('NAC','2015 Val','Michael','1 Not Started'),
('NAC','2015 Pension Center','Philip','5 Complete'),
('NAC','2015 Misc','Michael','2 In Progress'),
('SNI','2015 Val','Chris','2 In Progress'),
('SNI','2015 Pension Center','Philip','5 Complete'),
('SNI','2015 Misc','Mitchell','2 In Progress'),
('(None)','2015 RiskFirst','Philip','2 In Progress'),
('(None)','2015 Warehouse','Philip','2 In Progress');

insert into Tasks (tClient, tProject, tTaskId, tDescription, tResponsible, tDue, tExpected, tProgress, tStatus) values
('NAC','2015 Val',10,'Census Data Preparation','Chelsea','2015-10-20','2015-10-20','','2 In Progress'),
('NAC','2015 Val',20,'Initial Proval Load','Chelsea','2015-10-20','2015-10-25','','2 In Progress'),
('NAC','2015 Val',22,'Merge Data and Compare to last year','Brandon','2015-11-10','2015-10-20','','2 In Progress'),
('NAC','2015 Val',30,'Prepare 5500','Ray','2015-10-20','2015-11-20','','2 In Progress'),
('NAC','2015 Val',40,'Load Warehouse','Chelsea','2015-10-20','2015-11-30','','2 In Progress'),
('(None)','2015 Warehouse',10,'Get rid of Flag table','Philip','2015-11-30','','','2 In Progress'),
('(None)','2015 Warehouse',20,'Mock up improved front end','Philip','2015-08-30','2015-09-30','','2 In Progress');

