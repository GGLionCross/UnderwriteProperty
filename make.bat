@ECHO OFF

REM make.bat is designed to replicated make functionality or npm scripts

IF %1 EQU build pyinstaller --clean underwrite-property.spec

REM Remind user of available functions
IF %1 EQU --help (
  ECHO --------------
  ECHO AVAILABLE ARGS
  ECHO --------------
  ECHO build
  ECHO --------------
)