; Script generated by the Inno Setup Script Wizard.
; SEE THE DOCUMENTATION FOR DETAILS ON CREATING INNO SETUP SCRIPT FILES!

#define MyAppName "Warehouse"
#define MyAppVersion "1.5"
#define MyAppPublisher "Rudd and Wisdom"

#define MyAppExeName "Whouse.exe"

[Setup]
; NOTE: The value of AppId uniquely identifies this application.
; Do not use the same AppId value in installers for other applications.
; (To generate a new GUID, click Tools | Generate GUID inside the IDE.)
AppId={{9FEE2DE0-2DEC-40CA-91E8-776AED1A0F8A}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
;AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
;DefaultDirName={pf}\{#MyAppName}
DefaultDirName={userpf}\Warehouse
OutputDir=C:\Users\Philip\Documents\GitHub\gitWH\build
OutputBaseFilename=setup
SetupIconFile=C:\Users\Philip\Documents\GitHub\gitWH\infinity.ico
Compression=lzma
SolidCompression=yes
PrivilegesRequired=none

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "C:\Users\Philip\Documents\GitHub\gitWH\dist\Whouse.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\Users\Philip\Documents\GitHub\gitWH\dist\_ctypes.pyd"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\Users\Philip\Documents\GitHub\gitWH\dist\_elementtree.pyd"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\Users\Philip\Documents\GitHub\gitWH\dist\_hashlib.pyd"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\Users\Philip\Documents\GitHub\gitWH\dist\_mysql.pyd"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\Users\Philip\Documents\GitHub\gitWH\dist\_socket.pyd"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\Users\Philip\Documents\GitHub\gitWH\dist\_ssl.pyd"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\Users\Philip\Documents\GitHub\gitWH\dist\bz2.pyd"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\Users\Philip\Documents\GitHub\gitWH\dist\CRYPT32.dll"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\Users\Philip\Documents\GitHub\gitWH\dist\library.zip"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\Users\Philip\Documents\GitHub\gitWH\dist\pyexpat.pyd"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\Users\Philip\Documents\GitHub\gitWH\dist\pyodbc.pyd"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\Users\Philip\Documents\GitHub\gitWH\dist\python27.dll"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\Users\Philip\Documents\GitHub\gitWH\dist\select.pyd"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\Users\Philip\Documents\GitHub\gitWH\dist\unicodedata.pyd"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\Users\Philip\Documents\GitHub\gitWH\dist\Whouse.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\Users\Philip\Documents\GitHub\gitWH\dist\wx._controls_.pyd"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\Users\Philip\Documents\GitHub\gitWH\dist\wx._core_.pyd"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\Users\Philip\Documents\GitHub\gitWH\dist\wx._gdi_.pyd"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\Users\Philip\Documents\GitHub\gitWH\dist\wx._html.pyd"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\Users\Philip\Documents\GitHub\gitWH\dist\wx._misc_.pyd"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\Users\Philip\Documents\GitHub\gitWH\dist\wx._windows_.pyd"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\Users\Philip\Documents\GitHub\gitWH\dist\wxbase30u_net_vc90_x64.dll"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\Users\Philip\Documents\GitHub\gitWH\dist\wxbase30u_vc90_x64.dll"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\Users\Philip\Documents\GitHub\gitWH\dist\wxmsw30u_adv_vc90_x64.dll"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\Users\Philip\Documents\GitHub\gitWH\dist\wxmsw30u_core_vc90_x64.dll"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\Users\Philip\Documents\GitHub\gitWH\dist\wxmsw30u_html_vc90_x64.dll"; DestDir: "{app}"; Flags: ignoreversion
; NOTE: Don't use "Flags: ignoreversion" on any shared system files

[Icons]
Name: "{commonprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent


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
