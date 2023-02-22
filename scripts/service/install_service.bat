@echo off

if exist data_service\ (

	net session >nul 2>&1
	if %errorLevel% == 0 (
		echo Proceeding to install the data_service as a windows service

		REM copy the latest API mapping to the System32 folder
		copy /Y data_service\resources\api_mapping.json %WINDIR%\system32\resources
		copy /Y data_service\local_settings.json %WINDIR%\system32

		data_service\dist\winservice.exe install
		
	) else (
		echo Please run this script as Administrator to install the Windows service
	)

) else (
	echo Please run this script from the top level repo folder, under which the data_service folder is present
)
