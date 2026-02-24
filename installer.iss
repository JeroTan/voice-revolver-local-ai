; Voice Revolver AI - Windows Installer Script
; Requires Inno Setup 6.x (https://jrsoftware.org/isinfo.php)

#define MyAppName "Voice Revolver AI"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Voice Revolver AI"
#define MyAppURL "https://github.com/yourusername/voice-revolver-local-ai"
#define MyAppExeName "VoiceRevolverAI.exe"

[Setup]
; Basic Information
AppId={{8F9A2C3D-1E4B-5C6D-7E8F-9A0B1C2D3E4F}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}

; Installation Directories
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes

; Output Configuration
OutputDir=build\installer
OutputBaseFilename=VoiceRevolverAI-Setup-v{#MyAppVersion}
; SetupIconFile={#MyAppIconName}
; UninstallDisplayIcon={app}\{#MyAppExeName}

; Compression (LZMA2 max for best compression)
Compression=lzma2/max
SolidCompression=yes
LZMAUseSeparateProcess=yes
LZMADictionarySize=1048576
LZMANumFastBytes=273

; Visual Appearance
WizardStyle=modern
DisableWelcomePage=no
ShowLanguageDialog=no

; System Requirements
MinVersion=10.0.17763
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

; Privileges (need admin to install to Program Files)
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog

; Disk Space (19GB venvs + 2GB app + 1GB temp)
ExtraDiskSpaceRequired=22000000000

; Misc
DisableDirPage=auto
DisableReadyPage=no
AlwaysShowDirOnReadyPage=yes
AlwaysShowGroupOnReadyPage=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode

[Files]
; Main executable and core files
Source: "build\VoiceRevolverAI\VoiceRevolverAI.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "build\VoiceRevolverAI\README.txt"; DestDir: "{app}"; Flags: ignoreversion

; Internal libraries and dependencies (_internal folder)
Source: "build\VoiceRevolverAI\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs

; NOTE: Installer size warning
; The following files are very large (19GB total). 
; The installer creation and installation will take significant time and disk space.

[Icons]
; Start Menu shortcut
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Comment: "AI-Powered Voice Transformation Suite"

; Desktop shortcut (optional)
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; Comment: "AI-Powered Voice Transformation Suite"

; Quick Launch shortcut (optional, Windows 7 and below)
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

; Uninstaller in Start Menu
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"

[Run]
; Option to launch after installation
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Clean up AppData venvs on uninstall
Type: filesandordirs; Name: "{localappdata}\VoiceRevolverAI"

[Code]
var
  ProgressPage: TOutputProgressWizardPage;
  
procedure InitializeWizard;
begin
  // Create custom progress page for venv extraction
  ProgressPage := CreateOutputProgressPage('Installing Components', 'Please wait while Setup installs Voice Revolver AI on your computer.');
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
begin
  if CurStep = ssPostInstall then
  begin
    ProgressPage.SetText('Finalizing installation...', '');
    ProgressPage.SetProgress(100, 100);
    ProgressPage.Hide;
  end;
end;

function InitializeSetup(): Boolean;
var
  AvailableSpace: Integer;
  RequiredSpace: Integer;
begin
  Result := True;
  RequiredSpace := 22000; // 22GB in MB
  
  // Check disk space
  AvailableSpace := GetSpaceOnDisk(ExpandConstant('{autopf}'), False) div (1024 * 1024);
  
  if AvailableSpace < RequiredSpace then
  begin
    MsgBox('Insufficient disk space. This application requires approximately 22 GB of free space.' + #13#10 + 
           'Available: ' + IntToStr(AvailableSpace) + ' MB' + #13#10 +
           'Required: ' + IntToStr(RequiredSpace) + ' MB', mbError, MB_OK);
    Result := False;
  end;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  
  if CurPageID = wpReady then
  begin
    // Warn about installation time
    if MsgBox('This installation will take 10-30 minutes depending on your disk speed.' + #13#10 + #13#10 +
              'The application includes:' + #13#10 +
              '- AI voice transformation engine' + #13#10 +
              '- RVC training environment (~5 GB)' + #13#10 +
              '- MDX audio separation (~7 GB)' + #13#10 +
              '- AI enhancement engine (~7 GB)' + #13#10 + #13#10 +
              'Do you want to continue?', mbConfirmation, MB_YESNO) = IDNO then
    begin
      Result := False;
    end;
  end;
end;

[Messages]
WelcomeLabel1=Welcome to [name/ver] Setup
WelcomeLabel2=This will install [name] on your computer.%n%nThis application provides professional-grade AI voice transformation, including voice cloning, stem separation, and RVC model training.%n%nIt is recommended that you close all other applications before continuing.%n%nNote: This installation requires approximately 22 GB of disk space and may take 10-30 minutes to complete.
FinishedLabel=Setup has finished installing [name] on your computer.%n%nOn first launch, the application will extract virtual environments to:%n{localappdata}\VoiceRevolverAI\venvs%n%nThis one-time extraction may take 2-3 minutes.
