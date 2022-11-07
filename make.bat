@ECHO OFF

REM make.bat is designed to replicated make functionality or npm scripts

IF %1 EQU build pyinstaller --clean underwrite-property.spec
REM config.json is the configuration file our exe ACTUALLY uses
REM keep-config.json overwrites config.json when building
REM If making temp changes to keep-config, default-config is used to store default settings
IF %1 EQU default-config COPY ".ignore\default-config.json" ".ignore\keep-config.json"
if %1 EQU setup pip install -r requirements.txt

REM Remind user of available functions
IF %1 EQU --help (
  ECHO --------------
  ECHO AVAILABLE ARGS
  ECHO --------------
  ECHO build
  ECHO default-config
  ECHO setup
  ECHO --------------
)