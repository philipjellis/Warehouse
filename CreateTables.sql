/****** Script for SelectTopNRows command from SSMS 
this is to set up the various tables for the projects section of the warehouse front end ******/
use PJE_Tasks
drop table History;
drop table Tasks;
drop table Projects;
drop table Users;
drop table Status;
drop table Client;
drop view vw_all

Create table Users (
	Username varchar(50) not null);
	
alter table users add constraint pk_users primary key clustered (Username);

Create table Status (
	StatusDescription varchar(20) not null);

alter table Status add constraint pk_status primary key clustered (StatusDescription);
	
Create table Client (
	ClientCode varchar(10) not null);

alter table Client add constraint pk_client primary key clustered (ClientCode);

create table Projects (
	pClient varchar(10) not null,
	pProject varchar(20) not null,
	pOwner varchar(20) not null,
	pStatus varchar(20) not null);
	
alter table Projects 
	add constraint pk_projects primary key clustered (pClient, pProject)
	
alter table Projects
	add constraint fk_projects foreign key (pClient) references Client (ClientCode);

create table Tasks (
	tClient varchar(10) not null,
	tProject varchar(20) not null,
	tTaskid integer not null,
	tDescription varchar(50) not null,
	tResponsible varchar(20) null,
	tDue date null,
	tStarted date null,
	tExpected date null,
	tProgress text null,
	tStatus varchar(20) null);

alter table tasks
	add constraint pk_tasks primary key clustered (tClient, tProject, tTaskid);

alter table tasks
	add constraint fk_tasks foreign key (tClient, tProject) references Projects (pClient, pProject);

create table History (
	hClient varchar(10) not null,
	hProject varchar(20) not null,
	hTaskid integer not null,
	hWho varchar(50) not null,
	hWhen datetime not null,
	hAction text null);
	
alter table History
	add constraint pk_history primary key clustered (hClient, hProject, hTaskid, hWho, hWhen);

alter table History	
	add constraint fk_history foreign key (hClient, hProject,hTaskid) references Tasks (tClient, tProject, tTaskid);

create view vw_all	as
SELECT     dbo.Tasks.tClient, dbo.Tasks.tProject, dbo.Tasks.tTaskid, dbo.Projects.pOwner, dbo.Tasks.tResponsible, 
			dbo.Tasks.tDescription, dbo.Tasks.tStatus, dbo.Tasks.tDue, dbo.Tasks.tStarted, dbo.Tasks.tExpected, dbo.Tasks.tProgress
FROM         dbo.Tasks INNER JOIN
                      dbo.Projects ON dbo.Projects.pProject = dbo.Tasks.tProject and pclient = tclient
             inner join Clients on clientcode = tclient


