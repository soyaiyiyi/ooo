#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging
import uuid
import json

import requests
import webview
import threading

from datetime import datetime, timedelta
from src.backend.order_manager import OrderManager
from src.backend.config import Config

logger = logging.getLogger(__name__)


class API:
    """API类，处理前端与后端的通信"""

    def __init__(self, config: Config, order_manager: OrderManager):
        self.config = config
        self.order_manager = order_manager
        self.window = None
        self.tokens = {}  # 存储用户token和过期时间
        self.account_window = None  # 账号添加窗口
        self.network_requests = []  # 存储捕获的网络请求
        self.monitoring = False  # 是否正在监控网络请求
        self.monitor_lock = threading.Lock()  # 监控锁

    def set_window(self, window):
        """设置窗口实例"""
        self.window = window

    # ===== 用户认证相关 =====

    def login(self, username, password, remember=False):
        """用户登录"""
        try:
            # 这里实现实际的登录逻辑
            success = self.order_manager.login(username, password)

            if success:
                # 如果记住密码，则保存到配置中
                if remember:
                    self.config.update_config("username", username)
                    self.config.update_config("password", password)
                    self.config.update_config("remember_password", True)

                # 生成token
                token = str(uuid.uuid4())
                # token有效期7天
                expiry = datetime.now() + timedelta(days=7)

                # 保存token和用户信息
                self.tokens[token] = {
                    "username": username,
                    "expiry": expiry.timestamp(),
                    "user_info": self.order_manager.get_user_info(),
                }

                # 保存tokens到配置文件
                self._save_tokens()

                return {"success": True, "message": "登录成功", "token": token}
            else:
                return {"success": False, "message": "用户名或密码错误"}
        except Exception as e:
            logger.error(f"登录失败: {str(e)}")
            return {"success": False, "message": f"登录失败: {str(e)}"}

    def logout(self):
        """用户登出"""
        try:
            self.order_manager.logout()
            # 如果前端传入了token，则清除该token
            # 注：实际方案中应该从请求中获取token
            return {"success": True, "message": "已退出登录"}
        except Exception as e:
            logger.error(f"登出失败: {str(e)}")
            return {"success": False, "message": f"登出失败: {str(e)}"}

    def get_user_info(self):
        """获取用户信息"""
        return self.order_manager.get_user_info()

    # ===== 订单相关 =====

    def start_grabbing(self, params):
        """开始抢单"""
        try:
            logger.info(f"开始抢单: {params} {type(params)}")
            if not params.get("site"):
                return {"success": False, "message": "请先选择网站"}

            self.config.update_config("savedOrderForm", params)
            self.order_manager.start_grabbing(params)
            return {"success": True, "message": "已开始抢单"}
        except Exception as e:
            logger.error(f"开始抢单失败: {str(e)}")
            return {"success": False, "message": f"开始抢单失败: {str(e)}"}

    def stop_grabbing(self):
        """停止抢单"""
        try:
            self.order_manager.stop_grabbing()
            return {"success": True, "message": "已停止抢单"}
        except Exception as e:
            logger.error(f"停止抢单失败: {str(e)}")
            return {"success": False, "message": f"停止抢单失败: {str(e)}"}

    def get_order_status(self):
        """获取抢单状态"""
        return self.order_manager.get_status()

    def get_order_history(self):
        """获取抢单历史"""
        return self.order_manager.get_history()

    # ===== 配置相关 =====

    def get_config(self):
        """获取配置"""
        # 返回安全的配置（不包含敏感信息）
        safe_config = dict(self.config.user_config)
        if "password" in safe_config:
            safe_config["password"] = "******" if safe_config["password"] else ""
        return safe_config

    def update_config(self, key, value):
        """更新配置"""
        success = self.config.update_config(key, value)
        return {
            "success": success,
            "message": "配置已更新" if success else "更新配置失败",
        }

    def reset_config(self):
        """重置配置"""
        # 重置为默认配置
        self.config.user_config = self.config._load_user_config()
        success = self.config.save_config()
        return {
            "success": success,
            "message": "配置已重置" if success else "重置配置失败",
        }

    # ===== 系统相关 =====

    def verify_token(self, token):
        """验证token是否有效"""
        try:
            # 加载保存的tokens
            self._load_tokens()

            if token in self.tokens:
                token_data = self.tokens[token]
                # 检查token是否过期
                if datetime.now().timestamp() < token_data["expiry"]:
                    # token有效，设置用户已登录状态
                    self.order_manager.set_logged_in(
                        token_data["username"], token_data["user_info"]
                    )
                    return {"success": True, "message": "token验证成功"}

            return {"success": False, "message": "无效或过期的token"}
        except Exception as e:
            logger.error(f"token验证失败: {str(e)}")
            return {"success": False, "message": f"token验证失败: {str(e)}"}

    def _save_tokens(self):
        """保存tokens到配置文件"""
        try:
            # 转换tokens为可序列化格式
            serializable_tokens = {}
            for token, data in self.tokens.items():
                serializable_tokens[token] = data

            # 保存到配置文件
            token_path = os.path.join(
                os.path.dirname(self.config.config_path), "tokens.json"
            )
            with open(token_path, "w", encoding="utf-8") as f:
                json.dump(serializable_tokens, f)
            return True
        except Exception as e:
            logger.error(f"保存tokens失败: {str(e)}")
            return False

    def _load_tokens(self):
        """从配置文件加载tokens"""
        try:
            token_path = os.path.join(
                os.path.dirname(self.config.config_path), "tokens.json"
            )
            if os.path.exists(token_path):
                with open(token_path, "r", encoding="utf-8") as f:
                    self.tokens = json.load(f)
                return True
            return False
        except Exception as e:
            logger.error(f"加载tokens失败: {str(e)}")
            self.tokens = {}
            return False

    def get_app_info(self):
        """获取应用信息"""
        return {
            "name": self.config.app_name,
            "version": self.config.version,
            "platform": os.name,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    def exit_app(self):
        """退出应用"""
        # 确保停止所有线程
        self.order_manager.stop_grabbing()
        # 关闭窗口
        if self.account_window:
            self.account_window.destroy()
        if self.window:
            self.window.destroy()
        return {"success": True}

    def open_account_window(self, url):
        """打开账号添加窗口并监控网络请求"""
        try:
            logger.info(f"正在打开账号添加窗口: {url}")
            self.order_manager.site = url
            # 清空之前捕获的网络请求
            with self.monitor_lock:
                self.network_requests = []
                self.monitoring = True

            # 创建一个处理网络请求的JS脚本
            js_monitor = """
                // 重写XMLHttpRequest
                (function() {
                    const originalXHR = window.XMLHttpRequest;
                    window.XMLHttpRequest = function() {
                        const xhr = new originalXHR();
                        
                        // 保存原始的open方法
                        const originalOpen = xhr.open;
                        xhr.open = function(method, url, async, user, password) {
                            // 调用原始的open方法
                            originalOpen.apply(xhr, arguments);
                            xhr._method = method;
                            xhr._url = url;
                        };
                        
                        // 保存原始的send方法
                        const originalSend = xhr.send;
                        xhr.send = function(data) {
                            xhr._data = data;
                            
                            // 请求完成时触发
                            xhr.addEventListener('loadend', function() {
                                try {
                                    let responseData = xhr.responseText;
                                    try {
                                        responseData = JSON.parse(responseData);
                                    } catch(e) {}
                                    
                                    // 收集请求信息
                                    const requestInfo = {
                                        method: xhr._method,
                                        url: xhr._url,
                                        status: xhr.status,
                                        requestData: xhr._data ? xhr._data : null,
                                        responseData: responseData,
                                        headers: xhr.getAllResponseHeaders(),
                                        timestamp: new Date().toISOString()
                                    };
                                    
                                    // 发送到Python后端
                                    window.pywebview.api.capture_network_request(requestInfo);
                                } catch(e) {
                                    console.error('捕获网络请求失败:', e);
                                }
                            });
                            
                            // 调用原始的send方法
                            originalSend.apply(xhr, arguments);
                        };
                        
                        return xhr;
                    };
                    
                    // 重写Fetch API
                    const originalFetch = window.fetch;
                    window.fetch = function(input, init) {
                        const request = new Request(input, init);
                        const method = request.method;
                        const url = request.url;
                        
                        // 克隆请求数据以便访问
                        let requestData = null;
                        try {
                            if(init && init.body) {
                                requestData = init.body;
                            }
                        } catch(e) {}
                        
                        return originalFetch.apply(this, arguments)
                            .then(response => {
                                // 克隆响应以便访问
                                const clonedResponse = response.clone();
                                
                                clonedResponse.text().then(text => {
                                    try {
                                        let responseData = text;
                                        try {
                                            responseData = JSON.parse(text);
                                        } catch(e) {}
                                        
                                        // 收集请求信息
                                        const requestInfo = {
                                            method: method,
                                            url: url,
                                            status: response.status,
                                            requestData: requestData,
                                            responseData: responseData,
                                            headers: Array.from(response.headers.entries()),
                                            timestamp: new Date().toISOString()
                                        };
                                        
                                        // 发送到Python后端
                                        window.pywebview.api.capture_network_request(requestInfo);
                                    } catch(e) {
                                        console.error('捕获Fetch请求失败:', e);
                                    }
                                });
                                
                                return response;
                            });
                    };
                })();
                console.log('已开始监控网络请求...');
            """

            # 关闭之前的窗口（如果存在）
            if self.account_window:
                self.account_window.destroy()

            # 仅在开发环境下使用持久化cookies和localStorage
            window_params = {
                "title": "添加账号",
                "url": url,
                "js_api": self,
                "width": 800,
                "height": 600,
                "resizable": True,
            }

            # 仅在调试模式下加载和保存会话状态
            if self.config.debug_mode:
                logger.info("开发环境: 启用账号窗口会话持久化")

                # 检查是否有保存的cookies
                saved_cookies = self.config.get_config().get("webview_cookies", {})
                logger.info(f"从配置中获取到已保存的cookies: {saved_cookies}")

                # 如果存在保存的cookie则使用
                if saved_cookies:
                    window_params["cookies"] = saved_cookies

                # 创建加载完成处理函数，包含恢复localStorage的脚本
                def on_loaded():
                    # 注入监控脚本
                    self.account_window.evaluate_js(js_monitor)

                    # 恢复本地存储数据
                    restore_js = """
                    try {
                        // 恢复localStorage数据
                        const storedData = %s;
                        if (storedData) {
                            for (const key in storedData) {
                                localStorage.setItem(key, storedData[key]);
                                console.log('【开发模式】恢复localStorage数据:', key);
                            }
                        }
                        console.log('【开发模式】本地存储数据恢复完成');
                    } catch(e) {
                        console.error('恢复本地存储数据失败:', e);
                    }
                    """ % json.dumps(
                        self.config.get_config().get("webview_localstorage", {})
                    )

                    self.account_window.evaluate_js(restore_js)

            else:
                logger.info("生产环境: 不启用账号窗口会话持久化")

                # 在生产环境下，只注入监控脚本
                def on_loaded():
                    self.account_window.evaluate_js(js_monitor)

            # 创建窗口
            self.account_window = webview.create_window(**window_params)

            # 设置加载和关闭事件
            self.account_window.events.loaded += on_loaded

            # 通知前端窗口已打开
            return {"success": True, "message": "账号窗口已打开"}

        except Exception as e:
            logger.error(f"打开账号窗口失败: {str(e)}")
            return {"success": False, "message": f"打开账号窗口失败: {str(e)}"}

    def capture_network_request(self, request_info):
        """捕获网络请求信息"""
        try:
            with self.monitor_lock:
                if not self.monitoring:
                    return {"success": False, "message": "未开启监控"}

                logger.info(f"捕获到网络请求: {request_info['url']}")
                self.network_requests.append(request_info["responseData"])

                if request_info["url"].endswith("/prod-api/login"):
                    logger.info(f"捕获到登录请求: {request_info['responseData']}")
                    response = request_info["responseData"]
                    if response["code"] == 200:
                        # 获取cookie对象列表
                        cookies_list = self.account_window.get_cookies()
                        logger.info(
                            f"获取到cookie类型: {type(cookies_list)}, 内容: {cookies_list}"
                        )

                        # 初始化admin_token和cookies_dict
                        admin_token = ""
                        cookies_dict = {}

                        # 处理SimpleCookie对象列表
                        try:
                            # 遍历SimpleCookie对象列表
                            for cookie_obj in cookies_list:
                                logger.info(f"Processing cookie object: {cookie_obj}")
                                # 如果是SimpleCookie对象
                                if hasattr(cookie_obj, "items"):
                                    for key, morsel in cookie_obj.items():
                                        cookies_dict[key] = morsel.value
                                        if key == "Admin-Token":
                                            admin_token = morsel.value
                                            logger.info(
                                                f"从对象中提取到Admin-Token: 长度={len(admin_token)}"
                                            )

                        except Exception as e:
                            import traceback

                            logger.error(
                                f"解析cookie对象时出错: {e}\n{traceback.format_exc()}"
                            )
                            logger.error(
                                f"原始数据类型: {type(cookies_list)}, 内容: {cookies_list}"
                            )

                        # 设置到OrderManager
                        self.order_manager.cookies = cookies_dict

                        # 获取user-agent
                        get_ua_js = "navigator.userAgent;"
                        user_agent = self.account_window.evaluate_js(get_ua_js)
                        self.order_manager.auth_token = (
                            admin_token  # 优先使用解析出的Admin-Token
                        )
                        if user_agent:
                            self.order_manager.user_agent = user_agent

                        logger.info(f"登录成功: {response['msg']}")
                        # 通知前端登录成功
                        self.window.evaluate_js(
                            f"window.loginSuccess({json.dumps(response)})"
                        )

                        # 取消监听
                        self.stop_monitoring()

                return {"success": True}
        except Exception as e:
            logger.error(f"处理网络请求失败: {str(e)}")
            return {"success": False, "message": str(e)}

    def get_network_requests(self):
        """获取已捕获的网络请求"""
        with self.monitor_lock:
            return self.network_requests

    def clear_network_requests(self):
        """清空捕获的网络请求"""
        with self.monitor_lock:
            self.network_requests = []
        return {"success": True, "message": "已清空网络请求记录"}

    def stop_monitoring(self):
        """停止监控网络请求"""
        with self.monitor_lock:
            self.monitoring = False
        return {"success": True, "message": "已停止监控网络请求"}

    # 异步获取用户信息
    def get_info(self):
        """获取用户信息"""
        userinfo = requests.get(
            self.order_manager.site + "/prod-api/getInfo",
            headers={
                "User-Agent": self.order_manager.user_agent,
                "Authorization": f"Bearer {self.order_manager.auth_token}",
            },
            cookies=self.order_manager.cookies,
        )
        logger.info(f"用户信息: {userinfo.text}")
        return userinfo.json()

    def exit(self):
        """退出全部窗口"""
        self.order_manager.stop_grabbing()
        self.account_window.destroy()
        self.window.destroy()
        return {"success": True}
