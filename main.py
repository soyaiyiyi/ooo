#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import webview
import logging
from src.backend.api import API
from src.backend.config import Config
from src.backend.order_manager import OrderManager

# 检查是否使用Qt引擎
USE_QT = True  # 设置为True表示使用QtWebEngine

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def get_resource_path(relative_path):
    """获取资源文件的绝对路径"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def main():
    # 加载配置
    config = Config()
    
    # 创建订单管理器（处理多线程抢单）
    order_manager = OrderManager(config)
    
    # 创建API实例
    api = API(config, order_manager)
    
    # 确定前端资源路径
    frontend_dir = get_resource_path('src/frontend')
    index_path = os.path.join(frontend_dir, 'index.html')
    
    # 不再需要为QtWebEngine准备API注入脚本
    # PyWebview 会自动处理API桥接，无需手动注入JavaScript
    
    # 创建窗口
    logger.info("启动应用程序...")
    
    # 创建窗口并直接使用标准的PyWebview API方式
    logger.info(f"{'使用QtWebEngine作为渲染引擎...' if USE_QT else '使用默认渲染引擎...'}")
    window = webview.create_window(
        '抢单助手', 
        index_path,
        js_api=api,  # 直接传递API对象，PyWebview会自动处理API暴露
        width=1100,
        height=700,
        min_size=(800, 600)
    )
    
    api.set_window(window)
    order_manager.set_window(window)

    # 从config中获取cookie
    cookies = config.get_config().get("webview_cookies")
    logger.info(f"获取到cookie: {cookies}")
    
    # 注册窗口关闭事件处理程序
    def on_window_close():
        logger.info("应用程序正在关闭，停止所有线程...")
        # 停止所有抢单线程
        order_manager.stop_grabbing()
        # 返回True表示允许窗口关闭
        return True
    
    # 设置窗口关闭事件处理程序
    window.events.closing += on_window_close
    
    # 启动应用
    webview.start(debug=config.debug_mode, gui='cef')
    # http_server=True 确保本地文件可以正确加载

if __name__ == "__main__":
    main()
