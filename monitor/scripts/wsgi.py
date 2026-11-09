# -*- coding: utf-8 -*-
"""WSGI 入口：生产部署用 waitress-serve / gunicorn 的 scripts.wsgi:app
   （08_api_server.py 文件名以数字开头，无法直接作为模块 import 路径）
   waitress-serve --listen=0.0.0.0:5000 --threads=8 scripts.wsgi:app
"""
import importlib
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))  # scripts 目录

_api = importlib.import_module("08_api_server")
app = _api.app