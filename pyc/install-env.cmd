pip install -i  https://pypi.tuna.tsinghua.edu.cn/simple pywin32
pip install -i  https://pypi.tuna.tsinghua.edu.cn/simple flask
pip install -i  https://pypi.tuna.tsinghua.edu.cn/simple flask_cors
pip install -i  https://pypi.tuna.tsinghua.edu.cn/simple requests
pip install -i  https://pypi.tuna.tsinghua.edu.cn/simple peewee
pip install -i  https://pypi.tuna.tsinghua.edu.cn/simple pyautogui
pip install -i  https://pypi.tuna.tsinghua.edu.cn/simple system_hotkey
pip install -i  https://pypi.tuna.tsinghua.edu.cn/simple pyperclip
pip install -i  https://pypi.tuna.tsinghua.edu.cn/simple pytesseract
rem # https://github.com/UB-Mannheim/tesseract/wiki 
rem #  下载中文训练数据文件。中文训练数据文件可以从Tesseract的GitHub仓库下载，文件名为chi_sim.traineddata（简体中文）
rem #  将下载的文件放到Tesseract安装目录下的tessdata文件夹中
rem #  https://github.com/tesseract-ocr/tessdata/blob/main/chi_sim.traineddata    简体中文训练数据文件，放入C:\Program Files\Tesseract-OCR\tessdata
rem #  pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'