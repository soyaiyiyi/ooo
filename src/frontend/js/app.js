const websiteList = [{
    name: '弘宇支付',
    value: 'https://supplier.hongyuzhifu.com/',
    type: 1,
}, {
    name: '安豪支付',
    value: 'https://supplier.anhaozhifu.com/',
    type: 1,
}, {
    name: '天堂支付',
    value: 'https://supplier.tiantangzhifu.vip/',
    type: 2,
}]

const App = {
    el: '#app',
    data() {
        return {
            logList: [],
            // 登录状态
            isLoggedIn: true,
            // 当前视图
            currentView: '1',
            // 登录表单
            loginForm: {
                username: '',
                password: '',
                remember: false
            },
            // 用户信息
            userInfo: undefined,
            checkAllPaymentMethods: false,
            // 抢单表单
            orderForm: {
                minPrice: 1000, //最低价
                maxPrice: 10000, //最高价
                enabledPriceRange: false, //开启价格范围
                enableGrabSound: true, //开启抢单声
                enableGrabDetailLog: false, //开启抢单详细日志
                stopTime: null, //定时停止
                stopOrderCount: 100, //抢单达到订单数停止
                paymentMethods: [], //支付方式
                orderFrequency: 'fixed',
                orderInterval: 1, //抢单频率
                successScheme: 'continue', //抢单模式成功后方案
                retryInterval: 10, //重试间隔
            },
            // 抢单状态
            isGrabbing: false,
            orderStatus: {
                active_threads: 0,
                total_threads: 0,
                queue_size: 0,
                history_count: 0
            },
            // 订单历史
            orderHistory: [],
            historyLoading: false,
        
            // 应用信息
            appInfo: {
                name: '抢单助手',
                version: '1.0.0',
                platform: '',
                time: ''
            },
            // 订单详情
            orderDetailVisible: false,
            selectedOrder: null,
            // 状态更新定时器
            statusTimer: null,
            // 网络请求监控
            networkRequests: [],
            isIndeterminate: false,
            isLoadingNetworkRequests: false,
            paymentMethodsOption: [
                { label: '支付宝', value: 'alipay' },
                { label: '不抢二次支付宝', value: 'alipay_2' },
                { label: '银行卡', value: 'bank' },
                { label: '不抢二次银行卡', value: 'bank_2' },
            ],
        };
    },
    created() {
        // 初始化应用
        this.initApp();
    },
    methods: {
        formatTime() {
            const date = new Date();
            return date.toLocaleString();
        },

        ocrSite() {
            const url = new URL(this.orderForm.inputSite)
            const info = websiteList.find(item => item.value.includes(url.hostname))
            if (!info) {
                return this.$message.error('未识别到网站，请联系客服')
            }
            this.orderForm.site = info.value
            this.orderForm.haveSite = true
        },
        // 初始化应用
        async initApp() {
            try {
                // 获取应用信息
                const appInfo = await window.pywebview.api.get_app_info();
                this.appInfo = appInfo;

                // 获取配置
                const config = await window.pywebview.api.get_config();
                console.log('%c🤪 ~ file: /Users/soya/Desktop/getorder_python_gui/src/frontend/js/app.js:118 [] -> config : ', 'color: #c2c331', config);

                // 恢复之前保存的抢单表单数据
                if (config) {
                    console.log('检测到已保存的抢单表单数据，正在恢复...');
                    this.orderForm = { ...this.orderForm, ...config };
                    if (this.orderForm.paymentMethods.length === this.paymentMethodsOption.length) {
                        this.checkAllPaymentMethods = true
                    }
                    console.log('抢单表单数据已恢复');
                }

                // 检查是否有保存的token
                const savedToken = localStorage.getItem('token');
                if (savedToken) {
                    console.log('检测到已保存的token，尝试自动登录');
                    this.autoLoginWithToken(savedToken);
                }
                // 如果没有token但有保存的登录信息
                else if (config.username && config.remember_password) {
                    this.loginForm.username = config.username;
                    this.loginForm.password = config.password;
                    this.loginForm.remember = true;

                    // 如果设置了自动登录，则自动登录
                    if (config.auto_login) {
                        this.submitLogin();
                    }
                }
            } catch (error) {
                console.error('初始化应用失败:', error);
                this.$message.error('初始化应用失败，请重新启动应用');
            }
        },

        // 提交登录
        async submitLogin() {
            try {
                const result = await window.pywebview.api.login(
                    this.loginForm.username,
                    this.loginForm.password,
                    this.loginForm.remember
                );

                console.log('%c🤪 ~ file: /Users/soya/Desktop/getorder_python_gui/src/frontend/js/app.js:105 [] -> result : ', 'color: #f06a1a', result);


                if (result.success) {
                    this.$message.success('登录成功');
                    this.isLoggedIn = true;

                    // 获取用户信息
                    this.userInfo = await window.pywebview.api.get_user_info();

                    // 保存token到本地存储
                    if (result.token) {
                        localStorage.setItem('token', result.token);
                        console.log('token已保存到本地存储');
                    }

                    // 开始状态更新定时器
                    this.startStatusTimer();
                } else {
                    this.$message.error(result.message || '登录失败');
                }
            } catch (error) {
                console.error('登录失败:', error);
                this.$message.error('登录请求失败，请检查网络连接');
            }
        },

        // 重置登录表单
        resetLoginForm() {
            this.$refs.loginForm.resetFields();
        },
        handleCheckAllChange(val) {
            this.orderForm.paymentMethods = val ? this.paymentMethodsOption.map(item => item.value) : []
            this.checkAllPaymentMethods = val

        },

        handleCheckedCitiesChange(value) {
            const checkedCount = value.length
            this.checkAllPaymentMethods = checkedCount === this.paymentMethodsOption.length
            this.isIndeterminate = checkedCount > 0 && checkedCount < this.paymentMethodsOption.length
        },

        // 登出
        async logout() {
            try {
                const result = await window.pywebview.api.logout();

                if (result.success) {
                    this.$message.success('已退出登录');
                    this.isLoggedIn = false;
                    this.currentView = '1';
                    this.stopStatusTimer();

                    // 清除保存的token
                    localStorage.removeItem('token');
                    console.log('token已从本地存储中清除');
                } else {
                    this.$message.error(result.message || '退出登录失败');
                }
            } catch (error) {
                console.error('退出登录失败:', error);
                this.$message.error('请求失败，请检查网络连接');
            }
        },

        // 使用token自动登录
        async autoLoginWithToken(token) {
            try {
                console.log('尝试使用token自动登录');
                // 调用后端验证token的API
                const result = await window.pywebview.api.verify_token(token);

                if (result && result.success) {
                    console.log('token验证成功，自动登录');
                    this.isLoggedIn = true;

                    // 获取用户信息
                    this.userInfo = await window.pywebview.api.get_user_info();

                    // 开始状态更新定时器
                    this.startStatusTimer();
                } else {
                    console.log('token已过期或无效，清除token');
                    localStorage.removeItem('token');
                }
            } catch (error) {
                console.error('使用token自动登录失败:', error);
                // token可能已过期，清除它
                localStorage.removeItem('token');
            }
        },

        // 开始抢单
        async startGrabbing() {
            try {
                const result = await window.pywebview.api.start_grabbing(this.orderForm);
                console.log('%c🤪 ~ file: /Users/soya/Desktop/getorder_python_gui/src/frontend/js/app.js:259 [] -> result : ', 'color: #352e8d', result);
                if (result.success) {
                    // 开始抢单成功，保存表单数据到配置
                    // try {
                    //     await window.pywebview.api.update_config('savedOrderForm', this.orderForm);
                    //     console.log('抢单表单数据已保存');
                    // } catch (saveError) {
                    //     console.error('保存表单数据失败:', saveError);
                    // }

                    this.$message.success(result.message || '已开始抢单');
                    this.isGrabbing = true;
                    this.refreshStatus();
                } else {
                    this.$message.error(result.message || '开始抢单失败');
                }
            } catch (error) {
                console.error('开始抢单失败:', error);
                this.$message.error('请求失败，请检查网络连接');
            }
        },

        // 停止抢单
        async stopGrabbing() {
            try {
                const result = await window.pywebview.api.stop_grabbing();

                if (result.success) {
                    this.$message.success(result.message || '已停止抢单');
                    this.isGrabbing = false;
                    this.refreshStatus();
                } else {
                    this.$message.error(result.message || '停止抢单失败');
                }
            } catch (error) {
                console.error('停止抢单失败:', error);
                this.$message.error('请求失败，请检查网络连接');
            }
        },

        // 刷新抢单状态
        async refreshStatus() {
            try {
                const status = await window.pywebview.api.get_order_status();
                this.orderStatus = status;
                this.isGrabbing = status.is_grabbing;
            } catch (error) {
                console.error('刷新状态失败:', error);
            }
        },

        // 开始状态更新定时器
        startStatusTimer() {
            // 每5秒更新一次状态
            this.statusTimer = setInterval(() => {
                this.refreshStatus();
            }, 5000);
        },

        // 停止状态更新定时器
        stopStatusTimer() {
            if (this.statusTimer) {
                clearInterval(this.statusTimer);
                this.statusTimer = null;
            }
        },

        // 刷新订单历史
        async refreshHistory() {
            this.historyLoading = true;
            try {
                const history = await window.pywebview.api.get_order_history();
                this.orderHistory = history;
            } catch (error) {
                console.error('刷新历史失败:', error);
                this.$message.error('获取订单历史失败');
            } finally {
                this.historyLoading = false;
            }
        },

        // 添加账号
        async handleAddAccount() {
            if (!this.orderForm.site) {
                this.$message.error('请先识别网站');
                return;
            }

            try {
                this.isLoadingNetworkRequests = true;

                // 清空之前的请求记录
                this.networkRequests = [];

                // 打开账号窗口
                const result = await window.pywebview.api.open_account_window(this.orderForm.site);
                if (!result.success) {
                    this.$message.error(result.message || '打开账号窗口失败');
                }
            } catch (error) {
                console.error('打开账号窗口失败:', error);
                this.$message.error('请求失败，请检查网络连接');
            } finally {
                this.isLoadingNetworkRequests = false;
            }
        },

        // 删除账号
        handleDeleteAccount() {
            this.orderForm.haveSite = false;
            this.orderForm.site = '';
            this.orderForm.inputSite = '';
            // 关闭网络请求监控
            this.networkRequestsVisible = false;
            this.networkRequests = [];
            if (this.networkRequestsTimer) {
                clearInterval(this.networkRequestsTimer);
                this.networkRequestsTimer = null;
            }
            // 移除事件监听器
            window.removeEventListener('networkRequest', this.handleNetworkRequest);
        },

        addLog(log) {
            console.log('%c🤪 ~ 日志数据: ', 'color: #125db0', log);

            // 如果数据不合法，直接返回
            if (!log || typeof log !== 'object') {
                return;
            }

            const timestamp = new Date().toLocaleTimeString();
            const { code, data, msg, type } = log;
            if (type === 'order-success') {
                this.logList.unshift({
                    code,
                    msg,
                    type
                });
                const audio = document.getElementById('notificationSound');
                audio.play();
                return
            }
            // 错误信息处理 (code = -1)
            if (code === -1) {

                // 检查是否与上一条错误日志相同
                const lastLog = this.logList.length > 0 ? this.logList[0] : null;
                if (lastLog && lastLog.type === 'error' && lastLog.msg === msg) {
                    // 重复错误消息，只更新计数和时间
                    lastLog.count++;
                    lastLog.timestamp = timestamp;
                } else {
                    // 新的错误消息
                    this.logList.unshift({
                        type,
                        msg: msg,
                        timestamp: timestamp,
                        count: 1
                    });
                    console.log('%c🤪 ~ file: /Users/soya/Desktop/getorder_python_gui/src/frontend/js/app.js:411 [] ->  this.logList : ', 'color: #fa376e', this.logList);

                    // 显示通知
                    // window.showNotification(msg, 'error');
                }
            }
            // 成功数据处理 (code = 0)
            else if (code === 0) {
                if (type === 'order-success') {
                    this.logList.unshift({
                        type: 'order-success',
                        msg: msg || '获取数据成功',
                        timestamp: timestamp,
                        count: 1
                    });
                }
                if (!data) {
                    return
                }

                // 如果有数据，显示通知
                if (data.records.length > 0) {
                    data.records.forEach(item => {
                        this.logList.unshift({
                            type: 'message',
                            msg: `检测到订单信息: 订单ID: ${item.systemOrderNumber} 订单金额: ${item.orderAmount} 支付方式: ${item.channelTypeName} 创建时间: ${this.formatTime()}`,
                            timestamp: timestamp,
                            count: 1
                        });
                    });
                } else {
                    this.logList.unshift({
                        type: 'warning',
                        msg: '未检测到订单信息  ----  ' + this.formatTime(),
                    });
                }
            }
            // 其他情况的处理
            else {
                this.logList.unshift({
                    type: 'warning',
                    msg: msg || '未知状态信息',
                    code: code,
                });
            }

            // 限制日志数量，防止过多影响性能
            if (this.logList.length > 100) {
                this.logList = this.logList.slice(0, 100);
            }
            console.log('%c🤪 ~ file: /Users/soya/Desktop/getorder_python_gui/src/frontend/js/app.js:456 [] -> this.logList : ', 'color: #e62327', this.logList);

        },
        async loginSuccess() {
           const res = await window.pywebview.api.get_info();
           this.userInfo = res
           console.log('%c🤪 ~ file: /Users/soya/Desktop/getorder_python_gui/src/frontend/js/app.js:469 [] -> res : ', 'color: #f57db2', res);
        },
        handleChangeAccount() {
            window.pywebview.api.exit();
        }
    },
    mounted() {
        window.addLog = this.addLog;
        window.loginSuccess = this.loginSuccess;
        window.showNotification = (title, type) => {
            this.$message({
                message: title,
                type: type,
            });
        }
    },
    beforeDestroy() {
        // 组件销毁前清除定时器
        this.stopStatusTimer();

        // 清除网络请求监控定时器
        if (this.networkRequestsTimer) {
            clearInterval(this.networkRequestsTimer);
            this.networkRequestsTimer = null;
        }

        // 移除网络请求事件监听器
        window.removeEventListener('networkRequest', this.handleNetworkRequest);
    }
}
const app = Vue.createApp(App);
app.use(ElementPlus);
app.mount("#app");


