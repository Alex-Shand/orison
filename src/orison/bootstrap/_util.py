BOOTSTRAP = """\
echo "Starting Orison custom boostrap hook" >>$HOME/bootstrap.log
powershell -c "irm https://astral.sh/uv/install.ps1 | iex" 2>&1 | % ToString | Tee-Object -FilePath $HOME/bootstrap.log -Append
$env:Path = "C:\\Users\\Admin\\.local\\bin;$env:Path"
Start-Process powershell -Verb runAs -ArgumentList "-C &{{ uv run E:\\hook.py 2>&1 | % ToString | Tee-Object -FilePath $HOME/bootstrap.log -Append }}"
"""

HOOK = """\
import os
import sys
import runpy
os.chdir('E:\\\\')
sys.path.insert(0, './orison.pyz')
runpy.run_module('orison.bootstrap.script')
"""
