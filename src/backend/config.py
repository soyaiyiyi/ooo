#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys  # 添加缺失的导入
import os
import json
from dotenv import load_dotenv


class Config:
    """配置管理类"""

    def __init__(self):
        # 加载环境变量
        load_dotenv()

        # 应用设置
        self.app_name = "抢单助手"
        self.version = "1.0.0"
        self.debug_mode = os.getenv("DEBUG", "False").lower() == "true"
        print(f"Debug mode: {self.debug_mode}")
        # 用户配置文件路径
        self.user_data_dir = self._get_user_data_dir()
        self.config_file = os.path.join(self.user_data_dir, "config.json")

        # 确保用户数据目录存在
        os.makedirs(self.user_data_dir, exist_ok=True)

        # 加载用户配置
        self.user_config = self._load_user_config()

    def _get_user_data_dir(self):
        """获取用户数据目录"""
        if sys.platform == "win32":
            base_dir = os.path.join(os.environ["APPDATA"], self.app_name)
        elif sys.platform == "darwin":
            base_dir = os.path.join(
                os.path.expanduser("~/Library/Application Support"), self.app_name
            )
        else:
            base_dir = os.path.join(os.path.expanduser("~/.config"), self.app_name)
        return base_dir

    def _load_user_config(self):
        """加载用户配置"""
        default_config = {
            "minPrice": 1000,  # 最低价
            "maxPrice": 10000,  # 最高价
            "enabledPriceRange": False,  # 开启价格范围
            "enableGrabSound": True,  # 开启抢单声
            "enableGrabDetailLog": False,  # 开启抢单详细日志
            "stopTime": None,  # 定时停止
            "stopOrderCount": 100,  # 抢单达到订单数停止
            "paymentMethods": [],  # 支付方式
            "orderFrequency": "fixed",
            "orderInterval": 1,  # 抢单频率
            "successScheme": "continue",  # 抢单模式成功后方案
            "retryInterval": 10,  # 重试间隔
        }

        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    user_config = json.load(f).get("savedOrderForm", {})
                    print(f"加载配置文件成功: {user_config}")

                    # 合并默认配置和用户配置
                    for key, value in default_config.items():
                        # 是在savedOrderForm下面
                        if key not in user_config:
                            user_config[key] = value
                    return user_config
            except Exception as e:
                print(f"加载配置文件失败: {e}")

        # 如果配置文件不存在或加载失败，使用默认配置
        return default_config

    def save_config(self):
        """保存用户配置"""
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.user_config, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存配置文件失败: {e}")
            return False

    def update_config(self, key, value):
        """更新配置项如果key不存在则添加"""
        self.user_config[key] = value
        return self.save_config()

    def get_config(self):
        """获取配置"""
        return self.user_config
