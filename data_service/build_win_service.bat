@echo off
pyinstaller --clean --onefile --add-data "resources\api_mapping.json;resources" --add-data "gui\web_gui\*.html;gui\web_gui" --hidden-import win32timezone winservice.py