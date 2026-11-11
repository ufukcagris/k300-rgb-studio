; K300 RGB Studio kurulum betigi (Inno Setup 6).  Derleme: scripts/build.ps1
; Elle:  ISCC.exe /DAppVersion=1.0.0 installer\setup.iss   (once pyinstaller ile dist\ olusmali)
#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif
#ifndef DistDir
  ; PyInstaller ciktisi (/DDistDir=... ile degistirilebilir)
  #define DistDir "..\dist\K300RGBStudio"
#endif
#ifndef OutDir
  ; setup.exe nereye yazilsin (/DOutDir=... ile degistirilebilir)
  #define OutDir "..\dist"
#endif
#define AppName "K300 RGB Studio"
#define AppExe "K300RGBStudio.exe"

[Setup]
AppId={{AE13631F-C12C-4862-8406-855764F31CC8}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=K300 RGB Studio contributors
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir={#OutDir}
OutputBaseFilename=K300RGBStudio-Setup-{#AppVersion}
SetupIconFile=..\assets\icon.ico
UninstallDisplayIcon={app}\{#AppExe}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
; Yonetici yetkisi gerekmez: varsayilan olarak yalnizca bu kullanici icin kurulur.
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
VersionInfoVersion={#AppVersion}

[Languages]
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[CustomMessages]
turkish.AutoStart=Windows ile birlikte başlat (sistem tepsisinde)
english.AutoStart=Start with Windows (in the system tray)
turkish.DefaultFolderBtn=Varsayılan
english.DefaultFolderBtn=Default
turkish.NeedAdminForProgramFiles=Program Files klasörüne kurmak için yönetici izni gerekir.%n%nİki yol var:%n  1) Kurulum yardımcısını yeniden başlatıp açılışta "Tüm kullanıcılar için" seçeneğini seçin (yönetici onayı istenir).%n  2) Yönetici izni gerektirmeyen varsayılan klasörü kullanın:%n      %1%n%nVarsayılan klasöre dönülsün mü?
english.NeedAdminForProgramFiles=Installing into Program Files requires administrator rights.%n%nYou have two options:%n  1) Restart the installer and choose "Install for all users" at the start (you will be asked to approve).%n  2) Use the default folder, which needs no administrator rights:%n      %1%n%nSwitch back to the default folder?

[Messages]
; Inno'nun resmi Turkce cevirisinde son sayfadaki dugme "Kur" oldugu halde aciklama "Sonraki" diyordu.
turkish.ReadyLabel2a=Kuruluma başlamak için Kur üzerine, ayarları gözden geçirip değiştirmek için Önceki üzerine tıklayın.
turkish.ReadyLabel2b=Kuruluma başlamak için Kur üzerine tıklayın.

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "autostart"; Description: "{cm:AutoStart}"; Flags: unchecked

[Files]
Source: "{#DistDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "K300RGBStudio"; ValueData: """{app}\{#AppExe}"" --minimized"; Tasks: autostart

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{userappdata}\K300FX"

[Code]
procedure StopApp;
var
  R: Integer;
begin
  Exec('taskkill.exe', '/im {#AppExe} /f', '', SW_HIDE, ewWaitUntilTerminated, R);
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  StopApp;          { calisan eski surum dosyalari kilitlemesin }
  Result := '';
end;

function IsProtectedFolder(Dir: String): Boolean;
begin
  Dir := Lowercase(Dir);
  Result := (Pos(Lowercase(ExpandConstant('{commonpf32}')), Dir) = 1)
         or (Pos(Lowercase(ExpandConstant('{commonpf64}')), Dir) = 1)
         or (Pos(Lowercase(ExpandConstant('{win}')), Dir) = 1);
end;

var
  DefaultDirBtn: TNewButton;

function DefaultInstallDir: String;
begin
  Result := ExpandConstant('{autopf}\{#AppName}');
end;

procedure DefaultDirBtnClick(Sender: TObject);
begin
  WizardForm.DirEdit.Text := DefaultInstallDir;
end;

procedure InitializeWizard;
begin
  { Klasor sayfasina "Varsayilan" dugmesi (Goz at'in altina): kapatip yeniden acmadan varsayilana don. }
  DefaultDirBtn := TNewButton.Create(WizardForm);
  DefaultDirBtn.Parent := WizardForm.SelectDirPage;
  DefaultDirBtn.Left := WizardForm.DirBrowseButton.Left;
  DefaultDirBtn.Top := WizardForm.DirBrowseButton.Top + WizardForm.DirBrowseButton.Height + ScaleY(8);
  DefaultDirBtn.Width := WizardForm.DirBrowseButton.Width;
  DefaultDirBtn.Height := WizardForm.DirBrowseButton.Height;
  DefaultDirBtn.Caption := CustomMessage('DefaultFolderBtn');
  DefaultDirBtn.OnClick := @DefaultDirBtnClick;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  { Yonetici izni yokken Program Files secildiyse, kurulumun SONUNDA "Hata 5: Erisim engellendi" ile
    patlamak yerine, daha klasor sayfasinda ne yapilacagini soyle ve tek tikla varsayilana donmeyi sun. }
  if (CurPageID = wpSelectDir) and (not IsAdminInstallMode) and IsProtectedFolder(WizardDirValue) then
  begin
    if MsgBox(FmtMessage(CustomMessage('NeedAdminForProgramFiles'), [DefaultInstallDir]), mbError, MB_YESNO) = IDYES then
      WizardForm.DirEdit.Text := DefaultInstallDir;
    Result := False;
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usUninstall then
  begin
    StopApp;
    { uygulamanin kendi "Windows ile baslat" ayarini da temizle }
    RegDeleteValue(HKCU, 'Software\Microsoft\Windows\CurrentVersion\Run', 'K300RGBStudio');
  end;
end;
