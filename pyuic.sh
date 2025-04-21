#! /bin/bash
LD_LIBRARY_PATH="${ORSPATH}/libs:${LD_LIBRARY_PATH}" "${ORSPYTHONHOME}/bin/python3" "${ORSPYTHON}/OrsScripts/pyuicWithImportCorrections.py" "./mainformdsb.ui" "./ui_mainformdsb.py"
