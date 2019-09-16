# CameraAdjust

virtualenv環境を作成
```
virtualenv -p /usr/bin/python env
```
virtualenv環境を起動
```
source env/bin/activate.csh
```
### Pythonの必要パッケージをインストール
```
pip install -r requirements.txt
```
### pythonの文字コードをUTF-8に設定
env\Lib\site-packagesにsitecustomize.pyを作成
sitecustomize.py
```
import sys
sys.setdefaultencoding('utf-8')
```
