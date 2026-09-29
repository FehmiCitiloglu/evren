#ifndef AppVersion
  #error AppVersion is required
#endif
[Setup]
AppId={{A52AB91C-69CB-4777-9FA1-B4DD6C942179}
AppName=evren
AppVersion={#AppVersion}
AppPublisher=EVREN
DefaultDirName={localappdata}\Programs\evren
DefaultGroupName=evren
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\release_assets
OutputBaseFilename=evren-{#AppVersion}-windows-x64-setup
SetupIconFile=..\evren_agent\ui\assets\icon.ico
UninstallDisplayIcon={app}\evren.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
[Files]
Source: "..\dist\evren.exe"; DestDir: "{app}"; Flags: ignoreversion
[Icons]
Name: "{group}\evren"; Filename: "{app}\evren.exe"
Name: "{autodesktop}\evren"; Filename: "{app}\evren.exe"; Tasks: desktopicon
[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked
[Run]
Filename: "{app}\evren.exe"; Description: "Launch evren"; Flags: nowait postinstall skipifsilent
