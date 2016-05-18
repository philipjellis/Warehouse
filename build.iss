; Script generated by the Inno Setup Script Wizard.
; SEE THE DOCUMENTATION FOR DETAILS ON CREATING INNO SETUP SCRIPT FILES!

[Setup]
; NOTE: The value of AppId uniquely identifies this application.
; Do not use the same AppId value in installers for other applications.
; (To generate a new GUID, click Tools | Generate GUID inside the IDE.)
AppId={{849908CF-BAE9-4221-8B29-1B314E73E84D}
AppName=Warehouse
AppVersion=1.57
;AppVerName=Warehouse 1.57
AppPublisher=Rudd and Wisdom
DefaultDirName={userpf}\Warehouse
DefaultGroupName=Warehouse
OutputBaseFilename=setup
Compression=lzma
SolidCompression=yes
PrivilegesRequired=none

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "C:\Users\Philip\Documents\GitHub\gitWH\livedist\Whouse.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\Users\Philip\Documents\GitHub\gitWH\livedist\w9xpopen.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\Users\Philip\Documents\GitHub\gitWH\livedist\library.zip"; DestDir: "{app}"; Flags: ignoreversion
; NOTE: Don't use "Flags: ignoreversion" on any shared system files

[Icons]
Name: "{group}\Warehouse"; Filename: "{app}\Whouse.exe"
Name: "{group}\{cm:UninstallProgram,WareHouse}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\Warehouse"; Filename: "{app}\Whouse.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Whouse.exe"; Description: "{cm:LaunchProgram,Warehouse}"; Flags: nowait postinstall skipifsilent

[Code]
function IsRegularUser(): Boolean;
begin
Result := not (IsAdminLoggedOn or IsPowerUserLoggedOn);
end;

function DefDirRoot(Param: String): String;
begin
if IsRegularUser then
Result := ExpandConstant('{localappdata}')
else
Result := ExpandConstant('{pf}')
end;