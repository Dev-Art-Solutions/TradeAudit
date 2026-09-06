; Inno Setup 6 Script for TradeAudit Windows Installer
; Generated for TradeAudit Windows Desktop Application

#define MyAppName "TradeAudit"
; MyAppVersion is normally passed in via `ISCC /DMyAppVersion=X.Y.Z` from
; scripts\build_installer.ps1, which reads the single source of truth at
; src\tradeaudit\__init__.py's __version__. This fallback only applies when
; compiling the .iss directly (e.g. from the Inno Setup IDE).
#ifndef MyAppVersion
  #define MyAppVersion "1.0.0"
#endif
#define MyAppPublisher "Dev Art Solutions"
#define MyAppExeName "TradeAudit.exe"
#define MyAppURL "https://github.com/Dev-Art-Solutions/TradeAudit"

[Setup]
; Unique AppId to prevent duplicate installations
AppId={{E59C762E-5D34-4C51-B2C1-8B0492EFA91B}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=..\dist\installer
OutputBaseFilename=TradeAudit-Setup-v{#MyAppVersion}
SetupIconFile=..\resources\icons\tradeaudit.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
DisableProgramGroupPage=auto

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Main application binaries and dependencies from PyInstaller distribution
Source: "..\dist\TradeAudit\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\resources\icons\tradeaudit.ico"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; IconFilename: "{app}\resources\icons\tradeaudit.ico"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
