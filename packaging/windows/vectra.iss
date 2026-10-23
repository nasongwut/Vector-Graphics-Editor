; Inno Setup 6 script — Vectra installer wizard for Windows 10 / 11 (64-bit)
; Build:  iscc /DAppVersion=3.3.0 packaging\windows\vectra.iss
; Input:  dist\Vectra\  (PyInstaller one-folder output)
; Output: dist\installer\Vectra-Setup-<version>-win-x64.exe

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#define AppName "Vectra"
#define AppExe "Vectra.exe"
#define AppPublisher "City Art"
#define Root "..\.."

[Setup]
AppId={{80B2C86B-2072-49C6-9E5E-5FF1693D05BC}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
VersionInfoVersion={#AppVersion}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\{#AppExe}
SetupIconFile=..\vectra.ico
WizardStyle=modern
WizardSizePercent=110
Compression=lzma2/max
SolidCompression=yes
OutputDir={#Root}\dist\installer
OutputBaseFilename=Vectra-Setup-{#AppVersion}-win-x64
; Windows 10 (build 10240) and Windows 11, 64-bit (also runs on Windows 11 ARM via x64 emulation)
MinVersion=10.0.10240
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
; per-user or all-users: the wizard asks
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ChangesAssociations=yes
CloseApplications=yes
ShowLanguageDialog=auto

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
; Thai wizard: bundled with newer Inno Setup releases, otherwise a downloaded Thai.isl next to this script
#if FileExists(CompilerPath + "Languages\Thai.isl")
Name: "thai"; MessagesFile: "compiler:Languages\Thai.isl"
  #define HaveThai
#elif FileExists(SourcePath + "Thai.isl")
Name: "thai"; MessagesFile: "Thai.isl"
  #define HaveThai
#endif

[CustomMessages]
english.AssocGroup=File associations:
english.AssocAI=Open Adobe Illustrator files (.ai) with Vectra
english.AssocEPS=Open EPS files (.eps) with Vectra
#ifdef HaveThai
thai.AssocGroup=การเชื่อมโยงไฟล์:
thai.AssocAI=เปิดไฟล์ Adobe Illustrator (.ai) ด้วย Vectra
thai.AssocEPS=เปิดไฟล์ EPS (.eps) ด้วย Vectra
#endif

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "assocai"; Description: "{cm:AssocAI}"; GroupDescription: "{cm:AssocGroup}"; Flags: unchecked
Name: "assoceps"; Description: "{cm:AssocEPS}"; GroupDescription: "{cm:AssocGroup}"; Flags: unchecked

[Files]
Source: "{#Root}\dist\Vectra\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Registry]
; "Open with" entry for every supported type
Root: HKA; Subkey: "Software\Classes\Applications\{#AppExe}\shell\open\command"; ValueType: string; ValueData: """{app}\{#AppExe}"" ""%1"""; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\Applications\{#AppExe}\SupportedTypes"; ValueType: string; ValueName: ".ai"; ValueData: ""
Root: HKA; Subkey: "Software\Classes\Applications\{#AppExe}\SupportedTypes"; ValueType: string; ValueName: ".eps"; ValueData: ""
Root: HKA; Subkey: "Software\Classes\Applications\{#AppExe}\SupportedTypes"; ValueType: string; ValueName: ".pdf"; ValueData: ""
Root: HKA; Subkey: "Software\Classes\Applications\{#AppExe}\SupportedTypes"; ValueType: string; ValueName: ".json"; ValueData: ""
Root: HKA; Subkey: "Software\Classes\.ai\OpenWithProgids"; ValueType: string; ValueName: "Vectra.Document"; ValueData: ""; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\.eps\OpenWithProgids"; ValueType: string; ValueName: "Vectra.Document"; ValueData: ""; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\Vectra.Document"; ValueType: string; ValueData: "Vectra Document"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\Vectra.Document\DefaultIcon"; ValueType: string; ValueData: "{app}\{#AppExe},0"
Root: HKA; Subkey: "Software\Classes\Vectra.Document\shell\open\command"; ValueType: string; ValueData: """{app}\{#AppExe}"" ""%1"""
; optional default handler (only when the user ticks the box)
Root: HKA; Subkey: "Software\Classes\.ai"; ValueType: string; ValueData: "Vectra.Document"; Flags: uninsdeletevalue; Tasks: assocai
Root: HKA; Subkey: "Software\Classes\.eps"; ValueType: string; ValueData: "Vectra.Document"; Flags: uninsdeletevalue; Tasks: assoceps

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent
