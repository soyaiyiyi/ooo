#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import queue
import time
import logging
import threading
import requests
import traceback
from queue import Queue
from src.backend.config import Config


logger = logging.getLogger(__name__)


class OrderManager:
    """订单管理器，处理多线程抢单逻辑"""

    def __init__(self, config: Config):
        self.config = config
        self.session = requests.Session()
        self.is_grabbing = False
        self.grab_threads = []
        self.order_queue = Queue()
        self.history = []
        self.user_info = None
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.cookies = {}
        self.headers = {}
        self.user_agent = ""
        self.auth_token = ""
        self.site = ""
        self.window = None
        self.count = 0

    def set_window(self, window):
        """设置窗口实例"""
        self.window = window

    def login(self, username, password):
        """用户登录"""
        try:
            # 这里实现实际的登录逻辑，与目标网站交互
            # 示例代码，实际实现需要根据目标网站API调整
            response = self.session.post(
                "http://order.pronhub.sbs/base/loginNoCaptcha",
                json={"username": username, "password": password},
                timeout=10,
            )

            if response.status_code == 200:
                data = response.json()
                logger.info(f"登录返回数据: {data}")
                if data.get("code") == 0:
                    self.user_info = data.get("data", {})
                    self.config.update_config(
                        "token", data.get("data", {}).get("token")
                    )
                    logger.info(f"用户 {username} 登录成功")
                    return True

            logger.warning(f"登录失败: {data.get('msg')}")
            return False
        except Exception as e:
            logger.error(f"登录异常: {str(e)}")
            return False

    def logout(self):
        """用户登出"""
        # 停止所有抢单线程
        self.stop_grabbing()

        # 清除会话
        self.session = requests.Session()
        self.user_info = None
        self.cookies = {}
        self.user_agent = ""
        self.auth_token = ""
        logger.info("用户已登出")

    def get_user_info(self):
        """获取用户信息"""
        return self.user_info or {}

    def start_grabbing(self, params):
        """开始抢单"""
        with self.lock:
            if self.is_grabbing:
                logger.warning("抢单已经在进行中")
                return

            # 重置状态
            self.stop_event.clear()
            self.is_grabbing = True

            # 清空旧的抢单线程
            self.grab_threads = []

            # 创建并启动抢单线程
            thread_count = self.config.user_config.get("thread_count", 4)
            for i in range(thread_count):
                thread = threading.Thread(
                    target=self._grab_order_worker, args=(params, i + 1), daemon=True
                )
                self.grab_threads.append(thread)
                thread.start()

            logger.info(f"已启动 {thread_count} 个抢单线程")

    def stop_grabbing(self):
        """停止抢单"""
        if not self.is_grabbing:
            return

        logger.info("正在停止抢单...")
        self.stop_event.set()

        # 等待所有线程结束
        for thread in self.grab_threads:
            if thread.is_alive():
                thread.join(timeout=2.0)

        self.grab_threads = []
        self.is_grabbing = False
        self.count = 0
        self.window.evaluate_js(f"addLog({json.dumps({
            'code': 0,
            'type': 'success',
            'msg': '抢单已停止',
        })})")

    def _grab_order_worker(self, params, worker_id):
        """抢单工作线程"""
        logger.info(f"抢单线程 {worker_id} 已启动")

        while not self.stop_event.is_set():
            try:
                # 如果已经停止了，就break
                if self.stop_event.is_set():
                    break

                token = self.auth_token

                # 检查我们是否有有效的token
                if not token:
                    logger.warning("没有发现可用的token")

                # 设置请求头
                headers = {
                    "User-Agent": self.user_agent,
                    "Authorization": f"Bearer {token}",
                }

                # 发送请求
                try:
                    # 确保cookies是字典类型
                    print("类型", type(self.cookies))
                    if not isinstance(self.cookies, dict):
                        if hasattr(self.cookies, "get_dict"):
                            cookies_to_use = self.cookies.get_dict()
                        else:
                            cookies_to_use = {}
                    else:
                        cookies_to_use = self.cookies

                    url = self.site + "/prod-api/lws/agentOrder/rushOrderList"

                    json_params = {
                        "pageNum": 1,
                        "pageSize": 30,
                        "startAmount": params.get("minPrice", 1000),
                        "endAmount": params.get("maxPrice", 100000),
                    }
                    response = requests.get(
                        url,
                        params=json_params,
                        headers=headers,
                        cookies=cookies_to_use,
                        timeout=5,
                    )

                    # 如果返回状态码为200，处理数据
                    if response.status_code == 200:
                        self.count += 1
                        data = response.json()
                        self.window.evaluate_js(f"addLog({json.dumps({
                            'code': 0,
                            'type': 'message',
                            'msg': '第' + str(self.count) + '次刷新订单',
                        })})")
                        if data.get("code") == 0:
                            # 如果data存在并且有record的长度不为0的时候
                            info = data.get("data")
                            records = info.get("records")
                            if info and len(records) > 0:
                                self.process_result(
                                    records,
                                    {
                                        "cookies": cookies_to_use,
                                        "headers": headers,
                                    },
                                    params
                                )
                            else:
                                message = {
                                    "code": 1,
                                    "type": "warning",
                                    "msg": "未检测到订单信息  ----  " + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                                }
                                self.window.evaluate_js(f"addLog({json.dumps(message)})")

                except Exception as e:
                    # 记录请求异常
                    error_traceback = traceback.format_exc()
                    logger.error(f"请求发送异常: {e}\n{error_traceback}")
                    continue

                # 根据配置的刷新间隔休眠
                refresh_interval = (
                    params.get("orderInterval", 1)
                )
                time.sleep(refresh_interval)

            except Exception as e:
                # 使用traceback获取详细错误信息，包括行号
                error_traceback = traceback.format_exc()
                error_message = (
                    f"线程 {worker_id} 抢单异常: {e}\n错误详情:\n{error_traceback}"
                )
                logger.error(error_message)
                time.sleep(2)  # 出错后稍微等待长一点

        logger.info(f"抢单线程 {worker_id} 已停止")

    # 处理抢单结果的数据
    def process_result(self, result, cookies, params):
        # 遍历result
        for item in result:
            payment_methods = params.get("paymentMethods", [])
            is_alipay = False
            is_bank = False
            if item.get("channelTypeCode") == "601" and item.get("payInfo"):
                pay_info = json.loads(item.get("payInfo"))
                if len(pay_info.get("账号")) < 13:
                    is_alipay = True
            if item.get("channelTypeCode") == "600" and item.get("payInfo"):
                pay_info = json.loads(item.get("payInfo"))
                if len(pay_info.get("账号")) < 13:
                    is_bank = True

            if is_alipay and "alipay" in payment_methods:
                self.getOrder(item, cookies)
            elif is_bank and "bank" in payment_methods:
                self.getOrder(item, cookies)
            else:
                message = {
                    "code": 1,
                    "type": "error",
                    "msg": "跳过订单：支付方式不匹配"
                    + item.get("systemOrderNumber")
                    + " 收款方式："
                    + item.get("channelTypeName")
                    + " 收款金额："
                    + str(item.get("orderAmount"))
                    + "当前时间："
                    + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                }
                self.window.evaluate_js(f"addLog({json.dumps(message)})")

    def getOrder(self, item, cookies):
        """处理抢单"""
        # 如果已经停止了，就break
        if self.stop_event.is_set():
            return
        
        info = requests.get(
            self.site
            + "/prod-api/lws/agentOrder/rushOrder?orderNo="
            + item.get("systemOrderNumber"),
            headers=cookies.get("headers"),
            cookies=cookies.get("cookies"),
        )
        logger.info(f"抢单返回数据: {info.json()}")
        if info.status_code == 200:
            data = info.json()
            if data.get("code") == 0:
                message = {
                    "code": 0,
                    "type": "order-success",
                    "msg": item,
                }
                self.window.evaluate_js(f"addLog({json.dumps(message)})")
            else:
                message = {
                    "code": 1,
                    "type": "error",
                    "msg": "抢单失败："
                    + data.get("msg")
                    + "当前时间："
                    + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                }
                self.window.evaluate_js(f"addLog({json.dumps(message)})")

    def _process_results(self):
        """处理抢单结果的线程"""
        logger.info("结果处理线程已启动")

        while not self.stop_event.is_set() or not self.order_queue.empty():
            try:
                # 非阻塞方式获取队列数据
                try:
                    result = self.order_queue.get(block=True, timeout=1.0)
                except queue.Empty:
                    continue

                # 处理抢单结果
                if result.get("success"):
                    # 添加到历史记录
                    self.history.append(result)

                    # 保持历史记录不超过100条
                    if len(self.history) > 100:
                        self.history = self.history[-100:]

                    # 这里可以添加通知逻辑
                    logger.info(
                        f"成功抢到订单: {result.get('order_info', {}).get('order_id')}"
                    )

                self.order_queue.task_done()

            except Exception:
                # 使用traceback获取详细错误信息包括行号
                error_traceback = traceback.format_exc()
                logger.error(f"处理抢单结果异常:\n{error_traceback}")

        logger.info("结果处理线程已停止")

    def get_status(self):
        """获取抢单状态"""
        return {
            "is_grabbing": self.is_grabbing,
            "active_threads": len([t for t in self.grab_threads if t.is_alive()]),
            "total_threads": len(self.grab_threads),
            "queue_size": self.order_queue.qsize(),
            "history_count": len(self.history),
        }

    def get_history(self):
        """获取抢单历史"""
        return self.history
