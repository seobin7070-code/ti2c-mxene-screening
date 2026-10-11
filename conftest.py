"""pytest가 project/ 를 import 루트로 인식하도록 보장한다.

이 파일의 존재만으로 project/ 가 sys.path 에 추가되어
`import core...` 가 어느 디렉토리에서 실행하든 동작한다.
"""
