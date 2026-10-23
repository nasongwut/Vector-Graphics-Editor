"""Write packaging/windows/version_info.txt (Windows EXE version resource) from vectra.__version__."""
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
with open(os.path.join(ROOT, "vectra", "__init__.py"), encoding="utf-8") as f:
    version = re.search(r'__version__\s*=\s*"([^"]+)"', f.read()).group(1)
nums = [int(x) for x in re.findall(r"\d+", version)[:4]]
nums += [0] * (4 - len(nums))
tup = tuple(nums)

TEMPLATE = f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers={tup}, prodvers={tup}, mask=0x3f, flags=0x0, OS=0x40004,
                    fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040904B0', [
      StringStruct('CompanyName', 'City Art'),
      StringStruct('FileDescription', 'Vectra vector graphics editor'),
      StringStruct('FileVersion', '{version}'),
      StringStruct('InternalName', 'Vectra'),
      StringStruct('OriginalFilename', 'Vectra.exe'),
      StringStruct('ProductName', 'Vectra'),
      StringStruct('ProductVersion', '{version}')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""
os.makedirs(os.path.join(HERE, "windows"), exist_ok=True)
with open(os.path.join(HERE, "windows", "version_info.txt"), "w", encoding="utf-8") as f:
    f.write(TEMPLATE)
print(version)
